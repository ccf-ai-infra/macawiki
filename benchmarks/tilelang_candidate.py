#!/usr/bin/env python3
"""TileLang candidate for Macawiki's operator comparison contract.

Runs on the MetaX C500 via the `maca` target of TileLang and emits a JSON
report with the same schema as ``pytorch_baseline.py`` so that
``scripts/compare_benchmarks.py`` can diff them (same environment fingerprint,
same case ids). PyTorch is the correctness reference.

The TileLang install lives at /opt/tilelang-metax and is not on the default
PYTHONPATH; set it before running, e.g.::

    PYTHONPATH=/opt/tilelang-metax python3 benchmarks/tilelang_candidate.py --operator all --profile c500 --output benchmarks/results/tilelang_c500.json

TileLang is imported lazily so that ``--list`` and argparse work on machines
without the TileLang/MXMACA stack installed (the previous version imported
TileLang at module top level and crashed on ``--list``).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from env_capture import environment, provenance, tilelang_source_ref

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "benchmarks" / "operator_cases.yaml"

# ---------------------------------------------------------------------------
# TileLang kernels (target=maca). One block handles a tile of rows so that
# reductions stay within a block (no cross-block communication).
#
# These are defined inside ``_load_tilelang_backend`` rather than at module top
# level so that importing this module does not require TileLang to be present.
# ``--list`` (and argparse) therefore work without the TileLang/MXMACA stack.
# ---------------------------------------------------------------------------


def _load_tilelang_backend() -> tuple[Any, Any, dict[str, Any]]:
    """Import TileLang and register the maca kernels on first real use.

    Returns ``(tilelang, T, kernels)`` where ``kernels`` maps operator names
    to jit-compiled builder functions. Raises a clear error when TileLang is
    not importable.
    """
    import tilelang  # noqa: F401  (imported for side effects + __version__)
    import tilelang.language as T

    @tilelang.jit(target="maca")
    def tl_add(A, B, BLOCK_N, dtype, out_dtype, threads):
        N = T.const("N")
        A: T.Tensor((N,), dtype)
        B: T.Tensor((N,), dtype)
        C = T.empty((N,), out_dtype)
        with T.Kernel(T.ceildiv(N, BLOCK_N), threads=threads) as (bx,):
            a = T.alloc_shared((BLOCK_N,), dtype)
            b = T.alloc_shared((BLOCK_N,), dtype)
            c = T.alloc_shared((BLOCK_N,), out_dtype)
            T.copy(A[bx * BLOCK_N], a)
            T.copy(B[bx * BLOCK_N], b)
            for i in T.Parallel(BLOCK_N):
                c[i] = T.Cast(out_dtype, T.Cast(dtype, a[i]) + T.Cast(dtype, b[i]))
            T.copy(c, C[bx * BLOCK_N])
        return C

    @tilelang.jit(target="maca")
    def tl_softmax(X, BLOCK_M, BLOCK_N, dtype, out_dtype, threads):
        M, N = T.const("M, N")
        X: T.Tensor((M, N), dtype)
        Y = T.empty((M, N), out_dtype)
        accum = T.float32
        with T.Kernel(T.ceildiv(M, BLOCK_M), threads=threads) as (bm,):
            x = T.alloc_fragment((BLOCK_M, BLOCK_N), dtype)
            xf = T.alloc_fragment((BLOCK_M, BLOCK_N), accum)
            mx = T.alloc_fragment((BLOCK_M,), accum)
            s = T.alloc_fragment((BLOCK_M,), accum)
            yf = T.alloc_fragment((BLOCK_M, BLOCK_N), accum)
            ys = T.alloc_shared((BLOCK_M, BLOCK_N), out_dtype)
            for bn in T.Pipelined(T.ceildiv(N, BLOCK_N)):
                T.copy(X[bm * BLOCK_M, bn * BLOCK_N], x)
                for i, j in T.Parallel(BLOCK_M, BLOCK_N):
                    xf[i, j] = T.Cast(accum, x[i, j])
                T.reduce_max(xf, mx, dim=1, clear=True)
                for i, j in T.Parallel(BLOCK_M, BLOCK_N):
                    yf[i, j] = T.exp(xf[i, j] - mx[i])
                T.reduce_sum(yf, s, dim=1, clear=True)
                for i, j in T.Parallel(BLOCK_M, BLOCK_N):
                    ys[i, j] = T.Cast(out_dtype, yf[i, j] / s[i])
                T.copy(ys, Y[bm * BLOCK_M, bn * BLOCK_N])
        return Y

    @tilelang.jit(target="maca")
    def tl_layernorm(X, gamma, beta, D, eps: float, BLOCK_M, threads, dtype, out_dtype):
        N, D = T.const("N, D")
        X: T.Tensor((N, D), dtype)
        gamma: T.Tensor((D,), dtype)
        beta: T.Tensor((D,), dtype)
        Y = T.empty((N, D), out_dtype)
        accum = T.float32
        with T.Kernel(T.ceildiv(N, BLOCK_M), threads=threads) as (bx,):
            xs = T.alloc_shared((BLOCK_M, D), dtype)
            gs = T.alloc_shared((D,), dtype)
            bs = T.alloc_shared((D,), dtype)
            xf = T.alloc_fragment((BLOCK_M, D), accum)
            xsq = T.alloc_fragment((BLOCK_M, D), accum)
            sum_row = T.alloc_fragment((BLOCK_M,), accum)
            sumsq_row = T.alloc_fragment((BLOCK_M,), accum)
            mean_row = T.alloc_fragment((BLOCK_M,), accum)
            rstd_row = T.alloc_fragment((BLOCK_M,), accum)
            ys = T.alloc_shared((BLOCK_M, D), out_dtype)
            T.copy(X[bx * BLOCK_M, 0], xs)
            T.copy(gamma, gs)
            T.copy(beta, bs)
            for i, j in T.Parallel(BLOCK_M, D):
                xf[i, j] = T.Cast(accum, xs[i, j])
            for i, j in T.Parallel(BLOCK_M, D):
                xsq[i, j] = xf[i, j] * xf[i, j]
            T.reduce_sum(xf, sum_row, dim=1)
            T.reduce_sum(xsq, sumsq_row, dim=1)
            inv_D = T.float32(1.0) / T.Cast(accum, D)
            for i in T.Parallel(BLOCK_M):
                mean_row[i] = sum_row[i] * inv_D
                rstd_row[i] = T.rsqrt(sumsq_row[i] * inv_D - mean_row[i] * mean_row[i] + T.Cast(accum, eps))
            for i, j in T.Parallel(BLOCK_M, D):
                norm = (xf[i, j] - mean_row[i]) * rstd_row[i]
                ys[i, j] = T.Cast(out_dtype, norm * T.Cast(accum, gs[j]) + T.Cast(accum, bs[j]))
            T.copy(ys, Y[bx * BLOCK_M, 0])
        return Y

    @tilelang.jit(target="maca")
    def tl_matmul(A, B, BLOCK_M, BLOCK_N, BLOCK_K, threads, dtype, out_dtype, accum_dtype):
        # Naive tiled GEMM (no TensorCore intrinsics): avoids the fp32 tf32 mma
        # codegen path that the maca compiler mis-emits. Standard layout: A=(M,K),
        # B=(K,N), C=(M,N). Per-tile math: c[i,j] += a[i,k]*b[k,j].
        M, N, K = T.const("M, N, K")
        A: T.Tensor((M, K), dtype)
        B: T.Tensor((K, N), dtype)
        C = T.empty((M, N), out_dtype)
        with T.Kernel(T.ceildiv(N, BLOCK_N), T.ceildiv(M, BLOCK_M), threads=threads) as (bx, by):
            a_s = T.alloc_shared((BLOCK_M, BLOCK_K), dtype)
            b_s = T.alloc_shared((BLOCK_K, BLOCK_N), dtype)
            c_l = T.alloc_fragment((BLOCK_M, BLOCK_N), accum_dtype)
            T.clear(c_l)
            for ko in T.Pipelined(T.ceildiv(K, BLOCK_K), num_stages=2):
                T.copy(A[by * BLOCK_M, ko * BLOCK_K], a_s)
                T.copy(B[ko * BLOCK_K, bx * BLOCK_N], b_s)
                for i, j, k in T.grid(BLOCK_M, BLOCK_N, BLOCK_K):
                    c_l[i, j] = c_l[i, j] + T.Cast(accum_dtype, a_s[i, k]) * T.Cast(accum_dtype, b_s[k, j])
            for i, j in T.Parallel(BLOCK_M, BLOCK_N):
                c_l[i, j] = T.Cast(out_dtype, c_l[i, j])
            T.copy(c_l, C[by * BLOCK_M, bx * BLOCK_N])
        return C

    @tilelang.jit(target="maca")
    def tl_quantize(X, scale: float, BLOCK_N, dtype, out_dtype, threads):
        # INT8 symmetric fake-quantize then dequantize: clamp(round(x/s),-128,127)*s.
        # Elementwise, one block per tile of elements (same shape as tl_add).
        N = T.const("N")
        X: T.Tensor((N,), dtype)
        Y = T.empty((N,), out_dtype)
        accum = T.float32
        sf = T.float32(scale)
        lo = T.float32(-128.0)
        hi = T.float32(127.0)
        with T.Kernel(T.ceildiv(N, BLOCK_N), threads=threads) as (bx,):
            x = T.alloc_shared((BLOCK_N,), dtype)
            ys = T.alloc_shared((BLOCK_N,), out_dtype)
            T.copy(X[bx * BLOCK_N], x)
            for i in T.Parallel(BLOCK_N):
                qf = T.Cast(accum, x[i]) / sf
                qf = T.max(lo, T.min(hi, T.Cast(accum, T.round(qf))))
                ys[i] = T.Cast(out_dtype, qf * sf)
            T.copy(ys, Y[bx * BLOCK_N])
        return Y

    @tilelang.jit(target="maca")
    def tl_transpose(X, BLOCK_M, BLOCK_N, dtype, out_dtype, threads):
        # Tiled 2D transpose: write X[m, n] to Y[n, m]. Each block owns a
        # (BLOCK_M, BLOCK_N) tile and transposes it through shared memory so the
        # output is written coalesced in the transposed layout.
        M, N = T.const("M, N")
        X: T.Tensor((M, N), dtype)
        Y = T.empty((N, M), out_dtype)
        with T.Kernel(T.ceildiv(N, BLOCK_N), T.ceildiv(M, BLOCK_M), threads=threads) as (bx, by):
            xs = T.alloc_shared((BLOCK_M, BLOCK_N), dtype)
            ys = T.alloc_shared((BLOCK_N, BLOCK_M), out_dtype)
            T.copy(X[by * BLOCK_M, bx * BLOCK_N], xs)
            for i, j in T.Parallel(BLOCK_M, BLOCK_N):
                ys[j, i] = T.Cast(out_dtype, xs[i, j])
            T.copy(ys, Y[bx * BLOCK_N, by * BLOCK_M])
        return Y

    kernels = {
        "add": tl_add,
        "softmax": tl_softmax,
        "layer_norm": tl_layernorm,
        "matmul": tl_matmul,
        "quantize": tl_quantize,
        "transpose": tl_transpose,
    }
    return tilelang, T, kernels


# Known codegen gap: TileLang's fp32 GEMM via T.gemm dispatches the maca
# tf32 mma intrinsic (__builtin_mxc_mma_16x16x8tf32), which the maca compiler
# mis-emits for this tilelang build. A naive T.grid accumulation is not valid
# on the GPU target (fragment/local are thread-local, so the 128-thread block
# never reduces to a single accumulator). Rather than fake a result, we mark
# matmul as not_comparable and record the reason. (AGENTS.md: "A not_run result
# is more honest than a synthetic benchmark.")
MATMUL_NOT_RUN_REASON = (
    "TileLang fp32 GEMM on maca target hits a tf32 mma codegen error "
    "(__builtin_mxc_mma_16x16x8tf32) for this build; naive grid accumulation "
    "is not a valid GPU reduction. Marked not_comparable pending a fix."
)

# Known codegen gap: MoE routing needs a per-row top-k selection (a sorted
# comparison/scan over the gate row), which TileLang's maca primitives do not
# expose as a direct op and a hand-written cross-thread compare-swap reduction
# is not valid on this GPU target without an atomic/shared cross-lane primitive
# we have not validated. The softmax half is expressible (we reuse the tl_softmax
# pattern), but the top-k selection half is not. Rather than fake a result by
# returning only the softmax or an unsorted subset, we mark the whole op
# not_comparable and record the reason. (AGENTS.md: "A not_run result is more
# honest than a synthetic benchmark.")
MOE_ROUTING_NOT_RUN_REASON = (
    "TileLang/maca has no validated per-row top-k primitive; a hand-written "
    "compare-swap reduction is not valid on this target. Marked not_comparable "
    "pending a supported top-k path (softmax half is expressible, top-k is not)."
)


def load_cases() -> dict[str, Any]:
    return json.loads(CASES.read_text(encoding="utf-8"))


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def _tensor_summary(torch: Any, output: Any) -> dict[str, Any]:
    detached = output.detach().to("cpu")
    values = detached.reshape(-1)
    return {
        "numel": int(values.numel()),
        "sum": float(values.sum().item()),
        "max_abs": float(values.abs().max().item()),
        "sha256": hashlib.sha256(detached.numpy().tobytes()).hexdigest(),
    }


def _build_kernel(tilelang: Any, T: Any, kernels: dict[str, Any], case: dict[str, Any]):
    name = case["name"]
    shape = case["shape"]
    dtype = T.float32
    out = T.float32
    acc = T.float32
    if name == "add":
        return kernels["add"].compile(N=shape[0], BLOCK_N=128, dtype=dtype, out_dtype=out, threads=128), ("add", shape)
    if name == "softmax":
        m, n = shape
        return kernels["softmax"].compile(M=m, N=n, BLOCK_M=1, BLOCK_N=n, dtype=dtype, out_dtype=out, threads=128), ("softmax", shape)
    if name == "layer_norm":
        m, n = shape
        return kernels["layer_norm"].compile(N=m, D=n, eps=case["parameters"]["eps"], BLOCK_M=1, threads=256, dtype=dtype, out_dtype=out), ("layer_norm", shape)
    if name == "matmul":
        m, k_, n_ = shape  # [M, K, N]
        return kernels["matmul"].compile(M=m, N=n_, K=k_, BLOCK_M=16, BLOCK_N=16, BLOCK_K=16, threads=128, dtype=dtype, out_dtype=out, accum_dtype=acc), ("matmul", shape)
    if name == "quantize":
        n = shape[0]
        return kernels["quantize"].compile(N=n, scale=case["parameters"]["scale"], BLOCK_N=128, dtype=dtype, out_dtype=out, threads=128), ("quantize", shape)
    if name == "transpose":
        m, n = shape
        return kernels["transpose"].compile(M=m, N=n, BLOCK_M=16, BLOCK_N=16, dtype=dtype, out_dtype=out, threads=128), ("transpose", shape)
    raise ValueError(f"unsupported operator: {name}")


def _not_run_case(case: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "operator": case["name"],
        "shape": case["shape"],
        "dtype": "float32",
        "parameters": case["parameters"],
        "seed": 20260722,
        "status": "not_comparable",
        "reason": reason,
        "correctness": {"reference": "pytorch", "passed": False, "reason": reason},
        "output_summary": None,
        "timing": None,
    }


def _reference(torch: Any, case: dict[str, Any], x: Any, y: Any | None) -> Any:
    name = case["name"]
    p = case["parameters"]
    if name == "add":
        return torch.add(x, y, alpha=p["alpha"])
    if name == "softmax":
        return torch.softmax(x, dim=p["dim"])
    if name == "layer_norm":
        return torch.nn.functional.layer_norm(x, tuple(p["normalized_shape"]), eps=p["eps"])
    if name == "matmul":
        return torch.matmul(x, y)
    if name == "quantize":
        scale = p["scale"]
        return torch.clamp(torch.round(x / scale), -128, 127) * scale
    if name == "transpose":
        return torch.t(x)
    if name == "moe_routing":
        gate = torch.softmax(x, dim=p["dim"])
        vals, _idx = torch.topk(gate, k=p["topk"], dim=p["dim"])
        return vals
    raise ValueError(name)


def _inputs(torch: Any, case: dict[str, Any], device: Any):
    torch.manual_seed(20260722)
    shape = case["shape"]
    if case["name"] == "matmul":
        m, k_, n_ = shape
        x = torch.randn((m, k_), device=device, dtype=torch.float32)
        y = torch.randn((k_, n_), device=device, dtype=torch.float32)  # B is (K,N)
        return x, y
    x = torch.randn(shape, device=device, dtype=torch.float32)
    y = torch.randn(shape, device=device, dtype=torch.float32) if case["name"] == "add" else None
    return x, y


def _run_kernel(kernel, op: str, x: Any, y: Any | None, gamma: Any = None, beta: Any = None):
    if op == "add":
        return kernel(x, y)
    if op == "softmax":
        return kernel(x)
    if op == "layer_norm":
        return kernel(x, gamma, beta)
    if op == "matmul":
        return kernel(x, y)
    if op == "quantize":
        return kernel(x)
    if op == "transpose":
        return kernel(x)
    raise ValueError(op)


def run_case(torch: Any, tilelang: Any, T: Any, kernels: dict[str, Any], case: dict[str, Any], device: Any, warmup: int, iterations: int, correctness_only: bool) -> dict[str, Any]:
    if case["name"] == "matmul":
        return _not_run_case(case, MATMUL_NOT_RUN_REASON)
    if case["name"] == "moe_routing":
        return _not_run_case(case, MOE_ROUTING_NOT_RUN_REASON)
    kernel, (op, _shape) = _build_kernel(tilelang, T, kernels, case)
    x, y = _inputs(torch, case, device)
    gamma = beta = None
    if op == "layer_norm":
        d = case["parameters"]["normalized_shape"][0]
        gamma = torch.ones((d,), device=device, dtype=torch.float32)
        beta = torch.zeros((d,), device=device, dtype=torch.float32)
    output = _run_kernel(kernel, op, x, y, gamma, beta)
    reference = _reference(torch, case, x, y if op in {"add", "matmul"} else None)
    tol = case["tolerance"]
    max_abs_error = float((output - reference).abs().max().item())
    correctness = {
        "reference": "pytorch",
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

    call = (lambda: kernel(x, y)) if op == "add" else \
           (lambda: kernel(x)) if op == "softmax" else \
           (lambda: kernel(x, gamma, beta)) if op == "layer_norm" else \
           (lambda: kernel(x)) if op in {"quantize", "transpose"} else \
           (lambda: kernel(x, y))
    # Timing uses the SAME method as pytorch_baseline.py
    # (time.perf_counter + torch.cuda.synchronize) so the two backends are
    # directly comparable on the same C500. We do NOT use
    # tilelang.profiler.do_bench here: it reports a different (CUDA-event based)
    # metric, which would mix synchronization semantics across backends and
    # break the comparability gate in docs/hardware-validation.md.
    torch.cuda.synchronize(device)
    for _ in range(warmup):
        call()
    torch.cuda.synchronize(device)
    samples = []
    for _ in range(iterations):
        start = time.perf_counter()
        call()
        torch.cuda.synchronize(device)
        samples.append((time.perf_counter() - start) * 1000.0)
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
    parser.add_argument("--operator", choices=["all", "add", "softmax", "layer_norm", "matmul", "quantize", "transpose", "moe_routing"], default="all")
    parser.add_argument("--profile", choices=["smoke", "c500"], default="smoke")
    parser.add_argument("--device", default="auto")
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
    # TileLang is imported lazily so --list and argparse work without it.
    if importlib.util.find_spec("tilelang") is None:
        print(
            "TileLang is not importable. Set PYTHONPATH to the MetaX TileLang build, e.g.:\n"
            "  PYTHONPATH=/opt/tilelang-metax python3 benchmarks/tilelang_candidate.py ...",
            file=sys.stderr,
        )
        return 2
    tilelang, T, kernels = _load_tilelang_backend()
    import torch

    device_name = args.device
    if device_name == "auto":
        device_name = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_name)
    profile = cases["profiles"][args.profile]
    warmup = max(0, args.warmup if args.warmup is not None else profile["warmup"])
    iterations = max(1, args.iterations if args.iterations is not None else profile["iterations"])
    selected = [c for c in cases["operators"] if args.operator == "all" or c["name"] == args.operator]
    results = [run_case(torch, tilelang, T, kernels, c, device, warmup, iterations, args.correctness_only) for c in selected]

    run_command = (
        f"PYTHONPATH=/opt/tilelang-metax python3 benchmarks/tilelang_candidate.py "
        f"--operator {args.operator} --profile {args.profile} "
        f"--warmup {warmup} --iterations {iterations}"
        + (" --correctness-only" if args.correctness_only else "")
        + (f" --output {args.output}" if args.output else "")
    )
    report = {
        "schema_version": 1,
        "backend": "tilelang",
        "status": "completed",
        "reference_role": "candidate-implementation",
        "source_ref": {
            **tilelang_source_ref(tilelang),
            "synchronization_api": "time.perf_counter + torch.cuda.synchronize (identical method to pytorch_baseline.py for same-backend comparability)",
            "synchronization_api_note": "tilelang.profiler.do_bench (CUDA-event based) is available in the build but is NOT used in these results; mixing it with perf_counter timing across backends would violate the comparability gate.",
        },
        "environment": environment(torch, device, backend="tilelang", include_tilelang=True, tilelang_module=tilelang),
        "provenance": provenance(
            run_command,
            capture_command="python3 scripts/capture_environment.py --output benchmarks/results/environment.json",
            notes=[
                "Timed on the same C500 host and software stack as the PyTorch baseline; treat as same-environment relative timing, not an official C500 spec.",
                "matmul is recorded as not_comparable because of a TileLang/maca codegen gap; see MATMUL_NOT_RUN_REASON in the source.",
                "moe_routing is recorded as not_comparable because TileLang/maca has no validated per-row top-k primitive; see MOE_ROUTING_NOT_RUN_REASON in the source.",
            ],
        ),
        "config": {"profile": args.profile, "warmup": warmup, "iterations": iterations, "correctness_only": args.correctness_only},
        "cases": results,
        "limitations": [
            "Correctness reference is PyTorch on the same device, not an independent CPU reference.",
            "Timings use time.perf_counter + torch.cuda.synchronize, the same method as pytorch_baseline.py; they are same-environment relative timing, not an official C500 spec.",
        ],
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
