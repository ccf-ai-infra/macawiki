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
