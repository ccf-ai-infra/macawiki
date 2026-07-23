#!/usr/bin/env python3
"""Aggregate query signals into prioritized backlog items for self-evolution.

Reads evals/signals/*.jsonl, groups by pattern, and generates backlog items
in evals/claude/iteration-state.json. Supports check-only and merge modes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .common import ROOT, discover_pages, load_data
except ImportError:
    from common import ROOT, discover_pages, load_data

SIGNAL_DIR = Path(os.environ.get("MACAWIKI_SIGNAL_DIR", ROOT / "evals" / "signals"))
STATE_PATH = ROOT / "evals" / "claude" / "iteration-state.json"


def _load_signals() -> list[dict[str, Any]]:
    """Load all signal records from JSONL files."""
    signals: list[dict[str, Any]] = []
    if not SIGNAL_DIR.exists():
        return signals
    for path in sorted(SIGNAL_DIR.glob("*.jsonl")):
        try:
            for line in path.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    signals.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            continue
    return signals


def _group_zero_results(signals: list[dict], min_count: int = 3) -> list[dict[str, Any]]:
    """Group zero-result signals by (terms, filters)."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for s in signals:
        if s.get("type") == "zero_result":
            key = (tuple(sorted(s.get("terms", []))), json.dumps(s.get("filters", {}), sort_keys=True))
            groups[key].append(s)

    items: list[dict[str, Any]] = []
    for (terms_tuple, filters_json), sigs in groups.items():
        if len(sigs) < min_count:
            continue
        terms = list(terms_tuple)
        filters = json.loads(filters_json)
        items.append({
            "source": "signal",
            "signal_type": "zero_result",
            "signal_count": len(sigs),
            "signal_query_terms": terms,
            "signal_filters": filters,
            "auto_fixable": False,
            "auto_fix_hint": "Create wiki page or source covering these terms; consider adding aliases",
        })
    return items


def _group_coverage_gaps(signals: list[dict]) -> list[dict[str, Any]]:
    """Group coverage gap signals by unmatched term."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for s in signals:
        if s.get("type") == "coverage_gap":
            for term in s.get("unmatched", []):
                groups[term].append(s)

    items: list[dict[str, Any]] = []
    for term, sigs in groups.items():
        items.append({
            "source": "signal",
            "signal_type": "coverage_gap",
            "signal_count": len(sigs),
            "signal_query_terms": [term],
            "signal_filters": {},
            "auto_fixable": False,
            "auto_fix_hint": f"Add '{term}' to data/aliases.yaml or data/tags.yaml, or add a relevant wiki page",
        })
    return items


def _detect_staleness(freshness_days: int = 180) -> list[dict[str, Any]]:
    """Check source pages for staleness and generate backlog items."""
    pages = discover_pages()
    source_pages = [p for p in pages if str(p.metadata.get("type", "")).startswith("source-")]
    now = datetime.now(timezone.utc).date()
    items: list[dict[str, Any]] = []

    for p in source_pages:
        retrieved_str = str(p.metadata.get("retrieved_at", ""))
        if not retrieved_str:
            continue
        try:
            from datetime import date
            dt = date.fromisoformat(retrieved_str)
            age = (now - dt).days
            if age > freshness_days:
                page_id = str(p.metadata.get("id", "?"))
                items.append({
                    "source": "signal",
                    "signal_type": "staleness",
                    "signal_count": 1,
                    "signal_query_terms": [page_id],
                    "signal_filters": {},
                    "auto_fixable": True,
                    "auto_fix_hint": f"Source {page_id} last retrieved {age} days ago (window: {freshness_days}d)",
                    "auto_fix_strategy": "freshness_update",
                })
        except (ValueError, TypeError):
            pass

    return items


def _group_perf_regressions(signals: list[dict], min_count: int = 2) -> list[dict[str, Any]]:
    """Group performance regression signals by (operator, backend).

    Regressions must appear at least *min_count* times to produce a backlog
    item, avoiding noise from single-run variance.
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for s in signals:
        if s.get("type") == "performance":
            key = (s.get("operator", "?"), s.get("backend", "?"))
            groups[key].append(s)

    items: list[dict[str, Any]] = []
    for (operator, backend), sigs in groups.items():
        if len(sigs) < min_count:
            continue
        # Compare latest median against the earliest in this batch
        medians = [sig.get("median_ms", 0) for sig in sigs]
        latest = medians[-1]
        earliest = medians[0]
        if earliest > 0 and latest > earliest * 1.15:
            ratio = round(latest / earliest, 2)
            items.append({
                "source": "signal",
                "signal_type": "perf_regression",
                "signal_count": len(sigs),
                "signal_query_terms": [operator, backend],
                "signal_filters": {},
                "auto_fixable": False,
                "auto_fix_hint": (
                    f"Operator {operator} on {backend}: median {latest}ms vs {earliest}ms "
                    f"(×{ratio}); may need re-benchmarking or investigation"
                ),
            })
    return items


def _group_token_hotspots(signals: list[dict], min_count: int = 3, threshold_tokens_per_result: float = 300.0) -> list[dict[str, Any]]:
    """Identify high-token-cost query patterns.

    Groups token-log entries by (terms, mode) and flags patterns with
    consistently high token consumption per result.
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for s in signals:
        if s.get("type") == "token_usage":
            key = (tuple(sorted(s.get("query_terms", []))), s.get("mode", "?"))
            groups[key].append(s)

    items: list[dict[str, Any]] = []
    for (terms_tuple, mode), sigs in groups.items():
        if len(sigs) < min_count:
            continue
        avg_tpr = sum(s.get("tokens_per_result", 0) for s in sigs) / len(sigs)
        if avg_tpr >= threshold_tokens_per_result:
            terms = list(terms_tuple)
            items.append({
                "source": "signal",
                "signal_type": "token_hotspot",
                "signal_count": len(sigs),
                "signal_query_terms": terms,
                "signal_filters": {"mode": mode},
                "auto_fixable": True,
                "auto_fix_strategy": "token_efficiency_hint",
                "auto_fix_hint": (
                    f"Query '{' '.join(terms)}' in {mode} mode averages "
                    f"{avg_tpr:.0f} tokens/result ({len(sigs)} occurrences). "
                    f"Consider adding aliases or narrowing with filters."
                ),
            })
    return items


def _group_env_changes(signals: list[dict]) -> list[dict[str, Any]]:
    """Track environment version changes between snapshots.

    Generates informational backlog items when MACA, driver, mxcc, or
    PyTorch versions change.
    """
    env_signals = [s for s in signals if s.get("type") == "environment"]
    if len(env_signals) < 2:
        return []

    items: list[dict[str, Any]] = []
    previous = env_signals[-2]
    current = env_signals[-1]

    VERSION_FIELDS = [
        ("maca_version", "MACA"),
        ("driver_version", "Driver"),
        ("mxcc_version", "mxcc"),
        ("pytorch_version", "PyTorch"),
        ("tilelang_version", "TileLang"),
    ]

    for field, label in VERSION_FIELDS:
        old_v = previous.get(field)
        new_v = current.get(field)
        if old_v and new_v and old_v != new_v:
            items.append({
                "source": "signal",
                "signal_type": "env_change",
                "signal_count": 1,
                "signal_query_terms": [label, old_v, new_v],
                "signal_filters": {},
                "auto_fixable": True,
                "auto_fix_strategy": "perf_baseline_update",
                "auto_fix_hint": (
                    f"{label} changed: {old_v} → {new_v}. "
                    f"Benchmark baselines may need updating."
                ),
            })

    return items


def _deduplicate(new_items: list[dict], existing_backlog: list[dict]) -> list[dict]:
    """Remove items that already have equivalent open backlog entries."""
    existing_keys: set[tuple] = set()
    for item in existing_backlog:
        etype = item.get("signal_type", "")
        eterms = tuple(sorted(item.get("signal_query_terms", [])))
        efilters = json.dumps(item.get("signal_filters", {}), sort_keys=True)
        if item.get("status") in ("open", "pending"):
            existing_keys.add((etype, eterms, efilters))

    result = []
    for item in new_items:
        key = (item.get("signal_type", ""), tuple(sorted(item.get("signal_query_terms", []))), json.dumps(item.get("signal_filters", {}), sort_keys=True))
        if key not in existing_keys:
            result.append(item)
    return result


def _next_auto_id(backlog: list[dict], prefix: str) -> str:
    """Generate the next auto-generated backlog ID."""
    max_n = 0
    for item in backlog:
        bid = item.get("id", "")
        if bid.startswith(prefix):
            try:
                n = int(bid.split("-")[-1])
                max_n = max(max_n, n)
            except (ValueError, IndexError):
                pass
    return f"{prefix}{max_n + 1:03d}"


def aggregate(max_items: int = 10, min_count: int = 3) -> dict[str, Any]:
    """Run full aggregation and return report."""
    signals = _load_signals()
    total = len(signals)
    zero_count = sum(1 for s in signals if s.get("type") == "zero_result")
    gap_count = sum(1 for s in signals if s.get("type") == "coverage_gap")
    perf_count = sum(1 for s in signals if s.get("type") == "performance")
    token_count = sum(1 for s in signals if s.get("type") == "token_usage")
    env_count = sum(1 for s in signals if s.get("type") == "environment")

    new_items = (
        _group_zero_results(signals, min_count=min_count)
        + _group_coverage_gaps(signals)
        + _detect_staleness()
        + _group_perf_regressions(signals, min_count=max(2, min_count - 1))
        + _group_token_hotspots(signals, min_count=min_count)
        + _group_env_changes(signals)
    )

    # Load existing backlog for dedup
    try:
        state = load_data(STATE_PATH)
        existing = state.get("backlog", []) if isinstance(state, dict) else []
    except (ValueError, FileNotFoundError):
        existing = []

    new_items = _deduplicate(new_items, existing)[:max_items]

    # Assign IDs
    ID_PREFIX_MAP = {
        "zero_result": "auto-sig-",
        "coverage_gap": "auto-cov-",
        "staleness": "auto-stale-",
        "perf_regression": "auto-perf-",
        "token_hotspot": "auto-token-",
        "env_change": "auto-env-",
    }
    for item in new_items:
        prefix = ID_PREFIX_MAP.get(item["signal_type"], "auto-unk-")
        item["id"] = _next_auto_id(existing + new_items, prefix)

    return {
        "total_signals": total,
        "zero_results": zero_count,
        "coverage_gaps": gap_count,
        "perf_signals": perf_count,
        "token_signals": token_count,
        "env_signals": env_count,
        "new_items": len(new_items),
        "items": new_items,
    }


def merge_backlog() -> dict[str, Any]:
    """Aggregate signals and merge into iteration-state.json."""
    report = aggregate()

    if not report["items"]:
        return {**report, "merged": False, "message": "No new items to merge"}

    # Load state
    state = load_data(STATE_PATH)

    # Append new items to backlog
    backlog = state.get("backlog", [])
    SEVERITY_MAP = {
        "zero_result": "P2",
        "coverage_gap": "P3",
        "staleness": "P3",
        "perf_regression": "P2",
        "token_hotspot": "P3",
        "env_change": "P3",
    }
    for item in report["items"]:
        stype = item["signal_type"]
        if stype in ("zero_result", "coverage_gap", "token_hotspot"):
            desc = f"{stype}: terms={item['signal_query_terms']} ({item['signal_count']} occurrences)"
        elif stype == "perf_regression":
            desc = f"{stype}: {item['auto_fix_hint']}"
        elif stype == "staleness":
            desc = item["auto_fix_hint"]
        elif stype == "env_change":
            desc = item["auto_fix_hint"]
        else:
            desc = f"{stype}: {item['signal_query_terms']} ({item['signal_count']} occurrences)"

        backlog.append({
            "id": item["id"],
            "description": desc,
            "workstream": "auto-signal",
            "severity": SEVERITY_MAP.get(stype, "P3"),
            "source": item["source"],
            "signal_type": stype,
            "signal_count": item["signal_count"],
            "signal_query_terms": item["signal_query_terms"],
            "signal_filters": item["signal_filters"],
            "auto_fixable": item["auto_fixable"],
            "auto_fix_hint": item["auto_fix_hint"],
            "auto_fix_strategy": item.get("auto_fix_strategy"),
            "status": "open",
            "confidence": "medium" if stype == "zero_result" else "high",
            "effort": "low" if item.get("auto_fix_strategy") else "medium",
            "dependencies": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Update signal stats
    state["signal_stats"] = {
        "last_aggregation": datetime.now(timezone.utc).isoformat(),
        "total_queries_logged": report["total_signals"],
        "total_zero_results": report["zero_results"],
        "total_coverage_gaps": report["coverage_gaps"],
        "auto_items_generated": len(report["items"]),
    }

    # Write back
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Archive processed signals
    archive_dir = SIGNAL_DIR / "archive" / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_dir.mkdir(parents=True, exist_ok=True)
    for path in SIGNAL_DIR.glob("*.jsonl"):
        try:
            path.rename(archive_dir / path.name)
        except OSError:
            pass

    return {**report, "merged": True, "message": f"Merged {len(report['items'])} items into backlog"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Analyze signals and print report (no state changes)")
    parser.add_argument("--merge", action="store_true", help="Analyze signals, merge into backlog, archive signals")
    parser.add_argument("--reset", action="store_true", help="Archive all signal logs and start fresh")
    parser.add_argument("--json", action="store_true", help="Output report as JSON")
    parser.add_argument("--min-count", type=int, default=3, help="Min signal occurrences for zero_result backlog item")
    parser.add_argument("--max-items", type=int, default=10, help="Max auto-generated backlog items per run")
    args = parser.parse_args()

    if args.reset:
        archive_dir = SIGNAL_DIR / "archive" / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        archive_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for path in SIGNAL_DIR.glob("*.jsonl"):
            try:
                path.rename(archive_dir / path.name)
                count += 1
            except OSError:
                pass
        print(f"Archived {count} signal log(s) to {archive_dir}")
        return 0

    if args.merge:
        report = merge_backlog()
    else:
        report = aggregate(max_items=args.max_items, min_count=args.min_count)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"=== Signal Aggregation Report ===")
        print(f"Total signals: {report['total_signals']}")
        print(f"Zero results:  {report['zero_results']}")
        print(f"Coverage gaps: {report['coverage_gaps']}")
        print(f"New items:     {report['new_items']}")
        if report.get("merged"):
            print(f"\nMerged into backlog: {report.get('message', '')}")
        if report["items"]:
            print(f"\nNew backlog items ({len(report['items'])}):")
            for item in report["items"]:
                print(f"  [{item['id']}] {item['signal_type']}: {item.get('auto_fix_hint', '')} ({item['signal_count']} occurrences)")
        else:
            print("\nNo new backlog items generated.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
