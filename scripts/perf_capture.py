#!/usr/bin/env python3
"""Capture runtime performance baselines on C500+MXMACA hardware.

Runs a set of lightweight microbenchmarks (add, matmul, softmax, memory
bandwidth) and logs results via ``signal_logger.log_performance()`` for the
self-evolution pipeline.  Optionally wraps a command with ``mcTracer`` for
kernel-level profiling.

Usage::

    python3 scripts/perf_capture.py                    # quick microbenchmarks
    python3 scripts/perf_capture.py --full             # extended benchmark suite
    python3 scripts/perf_capture.py --profile <cmd>    # mcTracer wrapper
    python3 scripts/perf_capture.py --json             # JSON output
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .common import ROOT
except ImportError:
    from common import ROOT  # type: ignore[no-redef]

MCTRACER_PATH = "/opt/maca/bin/mcTracer"

# ---------------------------------------------------------------------------
# Quick microbenchmark cases
# ---------------------------------------------------------------------------

MICRO_CASES = [
    {"operator": "add", "shape": [4096], "dtype": "float32"},
    {"operator": "softmax", "shape": [64, 128], "dtype": "float32"},
    {"operator": "matmul", "shape": [64, 128, 64], "dtype": "float32"},
    {"operator": "matmul", "shape": [1024, 1024, 1024], "dtype": "float32"},
    {"operator": "layer_norm", "shape": [64, 128], "dtype": "float32"},
    {"operator": "transpose", "shape": [128, 4096], "dtype": "float32"},
]

FULL_CASES = MICRO_CASES + [
    {"operator": "matmul", "shape": [4096, 4096, 4096], "dtype": "float32"},
    {"operator": "quantize", "shape": [8192], "dtype": "float32"},
]


@dataclass
class PerfResult:
    """A single microbenchmark result."""
    operator: str
    shape: list[int]
    backend: str = "pytorch"
    dtype: str = "float32"
    warmup_iters: int = 5
    timed_iters: int = 50
    mean_ms: float = 0.0
    median_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    passed_correctness: bool | None = None  # None = no correctness check was run
    error: str | None = None


def _has_torch() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def _has_cuda() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Operator implementations
# ---------------------------------------------------------------------------


def _bench_op(
    op_name: str,
    shape: list[int],
    dtype_str: str = "float32",
    warmup: int = 5,
    iterations: int = 50,
) -> PerfResult:
    """Run a single operator microbenchmark."""
    result = PerfResult(
        operator=op_name,
        shape=list(shape),
        warmup_iters=warmup,
        timed_iters=iterations,
    )

    try:
        import torch
        dtype = getattr(torch, dtype_str)
    except (ImportError, AttributeError) as e:
        result.error = str(e)
        return result

    device = "cuda"
    timings: list[float] = []

    try:
        if op_name == "add":
            x = torch.randn(*shape, device=device, dtype=dtype)
            y = torch.randn(*shape, device=device, dtype=dtype)
            for _ in range(warmup):
                _ = torch.add(x, y)
            torch.cuda.synchronize()
            for _ in range(iterations):
                t0 = time.perf_counter()
                _ = torch.add(x, y)
                torch.cuda.synchronize()
                timings.append((time.perf_counter() - t0) * 1000)

        elif op_name == "softmax":
            x = torch.randn(*shape, device=device, dtype=dtype)
            for _ in range(warmup):
                _ = torch.softmax(x, dim=-1)
            torch.cuda.synchronize()
            for _ in range(iterations):
                t0 = time.perf_counter()
                _ = torch.softmax(x, dim=-1)
                torch.cuda.synchronize()
                timings.append((time.perf_counter() - t0) * 1000)

        elif op_name == "matmul":
            if len(shape) == 3:
                m, k, n = shape
            else:
                m = n = shape[0]
                k = shape[1] if len(shape) > 1 else shape[0]
            x = torch.randn(m, k, device=device, dtype=dtype)
            y = torch.randn(k, n, device=device, dtype=dtype)
            for _ in range(warmup):
                _ = torch.mm(x, y)
            torch.cuda.synchronize()
            for _ in range(iterations):
                t0 = time.perf_counter()
                _ = torch.mm(x, y)
                torch.cuda.synchronize()
                timings.append((time.perf_counter() - t0) * 1000)

        elif op_name == "layer_norm":
            x = torch.randn(*shape, device=device, dtype=dtype)
            normalized_shape = [shape[-1]]
            for _ in range(warmup):
                _ = torch.nn.functional.layer_norm(x, normalized_shape)
            torch.cuda.synchronize()
            for _ in range(iterations):
                t0 = time.perf_counter()
                _ = torch.nn.functional.layer_norm(x, normalized_shape)
                torch.cuda.synchronize()
                timings.append((time.perf_counter() - t0) * 1000)

        elif op_name == "transpose":
            x = torch.randn(*shape, device=device, dtype=dtype)
            for _ in range(warmup):
                _ = x.t().contiguous()
            torch.cuda.synchronize()
            for _ in range(iterations):
                t0 = time.perf_counter()
                _ = x.t().contiguous()
                torch.cuda.synchronize()
                timings.append((time.perf_counter() - t0) * 1000)

        elif op_name == "quantize":
            x = torch.randn(*shape, device=device, dtype=dtype)
            scale = torch.tensor(1.0, device=device)
            for _ in range(warmup):
                _ = torch.quantize_per_tensor(x, 1.0, 0, torch.qint8)
            torch.cuda.synchronize()
            for _ in range(iterations):
                t0 = time.perf_counter()
                _ = torch.quantize_per_tensor(x, 1.0, 0, torch.qint8)
                torch.cuda.synchronize()
                timings.append((time.perf_counter() - t0) * 1000)
        else:
            result.error = f"unknown operator: {op_name}"
            return result

    except Exception as e:
        result.error = str(e)
        return result

    if timings:
        sorted_t = sorted(timings)
        result.mean_ms = sum(timings) / len(timings)
        result.median_ms = sorted_t[len(sorted_t) // 2]
        result.min_ms = sorted_t[0]
        result.max_ms = sorted_t[-1]

    return result


def _bench_memory_bandwidth() -> dict[str, Any]:
    """Estimate device-to-device memory bandwidth."""
    try:
        import torch
        size = 100_000_000  # 100M floats ≈ 400 MB
        x = torch.randn(size, device="cuda")
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(10):
            y = x.clone()
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - t0
        gb_per_sec = (size * 4 / 1024**3 * 10) / elapsed
        return {"bandwidth_gb_s": round(gb_per_sec, 1), "test_size_mb": round(size * 4 / 1024**2)}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# mcTracer integration
# ---------------------------------------------------------------------------


def _mctracer_available() -> bool:
    return os.path.exists(MCTRACER_PATH)


def profile_with_mctracer(command: list[str], output_dir: str | None = None) -> dict[str, Any]:
    """Wrap *command* with mcTracer for kernel-level profiling.

    Args:
        command: The command and its arguments to trace.
        output_dir: Where to write trace outputs (default: cwd).

    Returns:
        Dict with exit_code, stdout, stderr, and trace_files.
    """
    if not _mctracer_available():
        return {"error": f"mcTracer not found at {MCTRACER_PATH}", "exit_code": -1}

    odname = output_dir or f"mctracer_out_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    cmd = [MCTRACER_PATH, "--mctx", "--odname", odname, "--name", "perf_capture"] + list(command)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)

    # Find generated trace files
    trace_files: list[str] = []
    cwd = Path.cwd()
    for pattern in [f"{odname}/*", "tracer_out*", "*.trace", "*.csv"]:
        for p in sorted(cwd.glob(pattern)):
            if p.is_file():
                trace_files.append(str(p))

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout[:5000] if result.stdout else "",
        "stderr": result.stderr[:5000] if result.stderr else "",
        "trace_files": trace_files,
        "output_dir": odname,
    }


# ---------------------------------------------------------------------------
# Main capture
# ---------------------------------------------------------------------------


def capture(cases: list[dict[str, Any]] | None = None, full: bool = False) -> dict[str, Any]:
    """Run microbenchmarks and return structured results.

    Logs each result via ``signal_logger.log_performance()`` when available.
    """
    if not _has_torch():
        return {"error": "PyTorch not available", "results": []}
    if not _has_cuda():
        return {"error": "CUDA/MXMACA device not available", "results": []}

    import torch

    selected = FULL_CASES if full else (cases or MICRO_CASES)
    results: list[dict[str, Any]] = []
    device_name = torch.cuda.get_device_name(0)

    for case in selected:
        op = case["operator"]
        shape = case["shape"]
        dtype_str = case.get("dtype", "float32")
        perf = _bench_op(op, shape, dtype_str)
        rec = {
            "operator": perf.operator,
            "shape": perf.shape,
            "backend": perf.backend,
            "dtype": perf.dtype,
            "warmup_iters": perf.warmup_iters,
            "timed_iters": perf.timed_iters,
            "mean_ms": round(perf.mean_ms, 6),
            "median_ms": round(perf.median_ms, 6),
            "min_ms": round(perf.min_ms, 6),
            "max_ms": round(perf.max_ms, 6),
            "device_name": device_name,
            "correctness_checked": perf.passed_correctness is not None,
        }
        if perf.error:
            rec["error"] = perf.error
        results.append(rec)

        # Log to signal system
        try:
            from signal_logger import log_performance  # type: ignore[import-untyped]
        except ImportError:
            try:
                from scripts.signal_logger import log_performance  # type: ignore[import-untyped,no-redef]
            except ImportError:
                log_performance = None

        if log_performance and not perf.error:
            log_performance(
                operator=perf.operator,
                shape=perf.shape,
                backend=perf.backend,
                mean_ms=perf.mean_ms,
                median_ms=perf.median_ms,
                std_ms=0.0,
                warmup_iters=perf.warmup_iters,
                timed_iters=perf.timed_iters,
                dtype=perf.dtype,
                passed_correctness=perf.passed_correctness,
            )

    # Memory bandwidth
    bw = _bench_memory_bandwidth()

    return {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "device_name": device_name,
        "operator_results": results,
        "memory_bandwidth": bw,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Run extended benchmark suite")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--profile", nargs=argparse.REMAINDER,
                        help="Wrap a command with mcTracer (e.g. --profile python3 my_script.py)")
    parser.add_argument("--mctracer-out", type=str, default=None,
                        help="Output directory for mcTracer trace files")
    args = parser.parse_args()

    if args.profile:
        if not _mctracer_available():
            print(f"Error: mcTracer not found at {MCTRACER_PATH}", file=sys.stderr)
            return 1
        result = profile_with_mctracer(args.profile, args.mctracer_out)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"mcTracer exit: {result.get('exit_code')}")
            print(f"output dir:   {result.get('output_dir')}")
            trace_files = result.get("trace_files", [])
            if trace_files:
                print(f"trace files:  {len(trace_files)} file(s)")
                for f in trace_files:
                    print(f"  {f}")
            else:
                print("(no trace files generated)")
        return result.get("exit_code", 0)

    report = capture(full=args.full)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if report.get("error"):
            print(f"Error: {report['error']}", file=sys.stderr)
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        print(f"=== Performance Capture ({report['captured_at_utc'][:19]}) ===")
        print(f"Device: {report['device_name']}")
        bw = report.get("memory_bandwidth", {})
        if bw.get("bandwidth_gb_s"):
            print(f"Mem BW: {bw['bandwidth_gb_s']} GB/s (D2D copy)")
        print()
        for r in report.get("operator_results", []):
            if r.get("error"):
                print(f"  {r['operator']:<12} {str(r['shape']):<20} ERROR: {r['error']}")
            else:
                print(f"  {r['operator']:<12} {str(r['shape']):<20} "
                      f"median={r['median_ms']:.4f}ms  mean={r['mean_ms']:.4f}ms  "
                      f"min={r['min_ms']:.4f}ms  max={r['max_ms']:.4f}ms")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
