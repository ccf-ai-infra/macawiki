#!/usr/bin/env python3
"""Shared signal-logging utilities for Macawiki self-evolution.

Writes structured JSONL records to evals/signals/ for query telemetry,
zero-result captures, and coverage gap detection. All writes are
best-effort — logging failures never break the query tool.

Log files auto-rotate at 10MB to prevent unbounded growth.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .common import ROOT
except ImportError:
    from common import ROOT

SIGNAL_DIR = Path(os.environ.get("MACAWIKI_SIGNAL_DIR", ROOT / "evals" / "signals"))
MAX_LOG_BYTES = int(os.environ.get("MACAWIKI_SIGNAL_MAX_BYTES", 10_485_760))  # 10 MiB


def _ensure_dir() -> None:
    SIGNAL_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_log(name: str, record: dict[str, Any]) -> None:
    _ensure_dir()
    path = SIGNAL_DIR / name

    # Rotate if needed
    try:
        if path.exists() and path.stat().st_size >= MAX_LOG_BYTES:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            rotated = SIGNAL_DIR / f"{path.stem}-{ts}{path.suffix}"
            path.rename(rotated)
    except OSError:
        pass

    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass  # Best-effort: never break the caller


def log_query(
    terms: list[str],
    filters: dict[str, str | None],
    mode: str,
    fuzzy: bool,
    result_count: int,
    result_ids: list[str],
    elapsed_ms: float,
) -> None:
    """Log a completed query execution."""
    _write_log("query-log.jsonl", {
        "ts": _now_iso(),
        "type": "query",
        "terms": list(terms),
        "filters": {k: v for k, v in filters.items() if v is not None},
        "mode": mode,
        "fuzzy": fuzzy,
        "result_count": result_count,
        "result_ids": list(result_ids),
        "elapsed_ms": round(elapsed_ms, 3),
    })


def log_zero_result(
    terms: list[str],
    filters: dict[str, str | None],
    mode: str,
    fuzzy: bool,
) -> None:
    """Log a query that returned zero results."""
    _write_log("zero-result-log.jsonl", {
        "ts": _now_iso(),
        "type": "zero_result",
        "terms": list(terms),
        "filters": {k: v for k, v in filters.items() if v is not None},
        "mode": mode,
        "fuzzy": fuzzy,
    })


def log_coverage_gap(
    terms: list[str],
    unmatched: list[str],
    result_count: int,
) -> None:
    """Log query terms that are not in the controlled vocabulary."""
    _write_log("gap-log.jsonl", {
        "ts": _now_iso(),
        "type": "coverage_gap",
        "terms": list(terms),
        "unmatched": list(unmatched),
        "result_count": result_count,
    })


# ---------------------------------------------------------------------------
# MXMACA-aware signal types (activate only when C500 is detected)
# ---------------------------------------------------------------------------

_mxmaca_checked: bool = False
_mxmaca_available: bool = False


def _check_mxmaca() -> bool:
    """Lazily detect C500+MXMACA environment (cached after first call)."""
    global _mxmaca_checked, _mxmaca_available
    if not _mxmaca_checked:
        try:
            from .env_detector import is_mxmaca_env as _is  # type: ignore[assignment]
        except ImportError:
            try:
                from env_detector import is_mxmaca_env as _is  # type: ignore[no-redef,assignment]
            except ImportError:
                _is = lambda: False  # noqa: E731
        try:
            _mxmaca_available = _is()
        except Exception:
            _mxmaca_available = False
        _mxmaca_checked = True
    return _mxmaca_available


def _enrich_with_env(record: dict[str, Any]) -> None:
    """Add environment context fields to *record* when on C500 hardware."""
    if not _check_mxmaca():
        return
    try:
        from .env_detector import detect as _detect  # type: ignore[assignment]
    except ImportError:
        try:
            from env_detector import detect as _detect  # type: ignore[no-redef,assignment]
        except ImportError:
            return
    try:
        env = _detect()
        record["hardware"] = "c500"
        record["device_name"] = env.device_name
        record["maca_version"] = env.maca_version
        record["driver_version"] = env.driver_version
        record["env_fingerprint"] = env.fingerprint[:16]
    except Exception:
        pass


def log_performance(
    operator: str,
    shape: list[int],
    backend: str,
    mean_ms: float,
    median_ms: float,
    std_ms: float = 0.0,
    warmup_iters: int = 0,
    timed_iters: int = 0,
    dtype: str = "float32",
    passed_correctness: bool | None = None,
) -> None:
    """Log operator-level performance data.

    Called by benchmark runners or manually after running benchmarks on C500
    hardware.  On non-MXMACA systems this is a no-op.
    """
    if not _check_mxmaca():
        return

    record: dict[str, Any] = {
        "ts": _now_iso(),
        "type": "performance",
        "operator": operator,
        "shape": list(shape),
        "backend": backend,
        "dtype": dtype,
        "warmup_iters": warmup_iters,
        "timed_iters": timed_iters,
        "mean_ms": round(mean_ms, 6),
        "median_ms": round(median_ms, 6),
        "std_ms": round(std_ms, 6),
    }
    if passed_correctness is not None:
        record["passed_correctness"] = passed_correctness
    _enrich_with_env(record)
    _write_log("perf-log.jsonl", record)


def log_environment(
    trigger: str = "manual",
    baseline_fingerprint: str | None = None,
) -> None:
    """Log an environment snapshot for change detection.

    Args:
        trigger: Why the snapshot was taken (\"startup\", \"periodic\", \"manual\").
        baseline_fingerprint: Previous fingerprint for diff detection.
    """
    if not _check_mxmaca():
        return

    try:
        from .env_detector import detect as _detect  # type: ignore[assignment]
    except ImportError:
        try:
            from env_detector import detect as _detect  # type: ignore[no-redef,assignment]
        except ImportError:
            return

    env = _detect()
    record: dict[str, Any] = {
        "ts": _now_iso(),
        "type": "environment",
        "trigger": trigger,
        "is_c500": env.is_c500,
        "device_name": env.device_name,
        "maca_version": env.maca_version,
        "driver_version": env.driver_version,
        "mxcc_version": env.mxcc_version,
        "pytorch_version": env.pytorch_version,
        "tilelang_version": env.tilelang_version,
        "fingerprint": env.fingerprint,
    }
    if baseline_fingerprint:
        record["baseline_fingerprint"] = baseline_fingerprint
        record["changed"] = env.fingerprint != baseline_fingerprint

    _write_log("env-log.jsonl", record)


def log_token_usage(
    operation: str,
    query_terms: list[str],
    mode: str = "or",
    result_count: int = 0,
    estimated_input_tokens: int = 0,
    estimated_output_tokens: int = 0,
) -> None:
    """Log estimated token consumption for a query or operation.

    Token counts use a heuristic (chars ÷ 4 for Latin, chars ÷ 1.5 for CJK)
    and are labelled as estimates.  The *operation* field distinguishes
    \"query\", \"get_page\", \"eval\", \"benchmark\", etc.

    On non-MXMACA systems this still writes the log — token tracking is useful
    everywhere, not just on C500 hardware.
    """
    total = estimated_input_tokens + estimated_output_tokens
    tokens_per_result = round(total / max(result_count, 1), 1) if total > 0 else 0.0

    record: dict[str, Any] = {
        "ts": _now_iso(),
        "type": "token_usage",
        "operation": operation,
        "query_terms": list(query_terms),
        "mode": mode,
        "result_count": result_count,
        "estimated_input_tokens": estimated_input_tokens,
        "estimated_output_tokens": estimated_output_tokens,
        "total_tokens": total,
        "tokens_per_result": tokens_per_result,
    }
    _enrich_with_env(record)
    _write_log("token-log.jsonl", record)
