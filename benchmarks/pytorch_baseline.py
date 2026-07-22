#!/usr/bin/env python3
"""Run the PyTorch side of Macawiki's operator comparison contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from env_capture import environment, provenance

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "benchmarks" / "operator_cases.yaml"


def load_cases() -> dict[str, Any]:
    return json.loads(CASES.read_text(encoding="utf-8"))


def _sync(torch: Any, device: Any) -> None:
    if device.type == "cpu":
        return
    accelerator = getattr(torch, "accelerator", None)
    if accelerator is not None and hasattr(accelerator, "synchronize"):
        accelerator.synchronize()
        return
    if device.type == "cuda" and hasattr(torch, "cuda"):
        torch.cuda.synchronize(device)
        return
    raise RuntimeError(
        f"No validated synchronization method for device '{device}'. "
        "Adapt this runner in the C500 environment; do not assume CUDA semantics."
    )


def _run_op(torch: Any, case: dict[str, Any], x: Any, y: Any | None) -> Any:
    name = case["name"]
    params = case["parameters"]
    if name == "add":
        return torch.add(x, y, alpha=params["alpha"])
    if name == "softmax":
        return torch.softmax(x, dim=params["dim"])
    if name == "layer_norm":
        normalized = tuple(params["normalized_shape"])
        return torch.nn.functional.layer_norm(x, normalized, eps=params["eps"])
    if name == "matmul":
        return torch.matmul(x, y)
    raise ValueError(f"unsupported operator: {name}")


def _tensor_summary(torch: Any, output: Any) -> dict[str, Any]:
    detached = output.detach().to("cpu")
    values = detached.reshape(-1)
    return {
        "numel": int(values.numel()),
        "sum": float(values.sum().item()),
        "max_abs": float(values.abs().max().item()),
        "sha256": hashlib.sha256(detached.numpy().tobytes()).hexdigest(),
    }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def run_case(torch: Any, case: dict[str, Any], device: Any, warmup: int, iterations: int, correctness_only: bool) -> dict[str, Any]:
    torch.manual_seed(20260722)
    shape = tuple(case["shape"])
    dtype = getattr(torch, "float32")
    x = torch.randn(shape if case["name"] != "matmul" else (shape[0], shape[1]), device=device, dtype=dtype)
    y = None
    if case["name"] in {"add", "matmul"}:
        y_shape = shape if case["name"] == "add" else (shape[1], shape[2])
        y = torch.randn(tuple(y_shape), device=device, dtype=dtype)
    output = _run_op(torch, case, x, y)
    reference = output.detach().clone()
    max_abs_error = float((output - reference).abs().max().item())
    tol = case["tolerance"]
    correctness = {
        "reference": "pytorch-self-check",
        "passed": bool(torch.allclose(output, reference, atol=tol["atol"], rtol=tol["rtol"])),
        "max_abs_error": max_abs_error,
        "atol": tol["atol"],
        "rtol": tol["rtol"],
    }
    result: dict[str, Any] = {
        "case_id": case["case_id"],
        "operator": case["name"],
        "shape": case["shape"],
        "dtype": "float32",
        "parameters": case["parameters"],
        "seed": 20260722,
        "correctness": correctness,
        "output_summary": _tensor_summary(torch, output),
        "timing": None,
    }
    if correctness_only:
        return result
    _sync(torch, device)
    for _ in range(warmup):
        _run_op(torch, case, x, y)
    _sync(torch, device)
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        _run_op(torch, case, x, y)
        _sync(torch, device)
        samples.append((time.perf_counter() - started) * 1000.0)
    result["timing"] = {
        "unit": "ms",
        "warmup": warmup,
        "iterations": iterations,
        "samples_ms": samples,
        "median_ms": statistics.median(samples),
        "p95_ms": _percentile(samples, 0.95),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--operator", choices=["all", "add", "softmax", "layer_norm", "matmul"], default="all")
    parser.add_argument("--profile", choices=["smoke", "c500"], default="smoke")
    parser.add_argument("--device", default="auto", help="cpu, cuda, or a target-specific torch device string")
    parser.add_argument("--warmup", type=int)
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--correctness-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = load_cases()
    if args.list:
        for case in cases["operators"]:
            print(f"{case['case_id']}\t{case['name']}\tshape={case['shape']}")
        return 0
    if importlib.util.find_spec("torch") is None:
        print("PyTorch is not installed; install it only in a validated target environment.", file=sys.stderr)
        return 2
    import torch

    device_name = args.device
    if device_name == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_name)
    profile = cases["profiles"][args.profile]
    warmup = max(0, args.warmup if args.warmup is not None else profile["warmup"])
    iterations = max(1, args.iterations if args.iterations is not None else profile["iterations"])
    selected = [case for case in cases["operators"] if args.operator == "all" or case["name"] == args.operator]
    results = [run_case(torch, case, device, warmup, iterations, args.correctness_only) for case in selected]
    run_command = (
        f"python3 benchmarks/pytorch_baseline.py "
        f"--operator {args.operator} --profile {args.profile} --device {args.device} "
        f"--warmup {warmup} --iterations {iterations}"
        + (" --correctness-only" if args.correctness_only else "")
        + (f" --output {args.output}" if args.output else "")
    )
    report = {
        "schema_version": 1,
        "backend": "pytorch",
        "status": "completed",
        "reference_role": "reference-implementation",
        "environment": environment(torch, device, backend="pytorch", include_tilelang=False),
        "provenance": provenance(
            run_command,
            capture_command="python3 scripts/capture_environment.py --output benchmarks/results/environment.json",
            notes=[
                "PyTorch self-check is not independent backend validation; it is the correctness reference for the TileLang candidate.",
                "CPU results are workflow checks, not C500 evidence; C500 evidence requires device.type == cuda on a MetaX C500.",
            ],
        ),
        "config": {"profile": args.profile, "warmup": warmup, "iterations": iterations, "correctness_only": args.correctness_only},
        "cases": results,
        "limitations": ["PyTorch self-check is not independent backend validation.", "CPU results are workflow checks, not C500 evidence."],
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
