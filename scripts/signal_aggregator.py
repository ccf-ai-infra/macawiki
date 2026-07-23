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

    new_items = (
        _group_zero_results(signals, min_count=min_count)
        + _group_coverage_gaps(signals)
        + _detect_staleness()
    )

    # Load existing backlog for dedup
    try:
        state = load_data(STATE_PATH)
        existing = state.get("backlog", []) if isinstance(state, dict) else []
    except (ValueError, FileNotFoundError):
        existing = []

    new_items = _deduplicate(new_items, existing)[:max_items]

    # Assign IDs
    for item in new_items:
        if item["signal_type"] == "zero_result":
            item["id"] = _next_auto_id(existing + new_items, "auto-sig-")
        elif item["signal_type"] == "coverage_gap":
            item["id"] = _next_auto_id(existing + new_items, "auto-cov-")
        elif item["signal_type"] == "staleness":
            item["id"] = _next_auto_id(existing + new_items, "auto-stale-")

    return {
        "total_signals": total,
        "zero_results": zero_count,
        "coverage_gaps": gap_count,
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
    for item in report["items"]:
        backlog.append({
            "id": item["id"],
            "description": (
                f"{item['signal_type']}: " + (
                    f"terms={item['signal_query_terms']} ({item['signal_count']} occurrences)"
                    if item["signal_type"] != "staleness"
                    else item["auto_fix_hint"]
                )
            ),
            "workstream": "auto-signal",
            "severity": "P2" if item["signal_type"] == "zero_result" else "P3",
            "source": item["source"],
            "signal_type": item["signal_type"],
            "signal_count": item["signal_count"],
            "signal_query_terms": item["signal_query_terms"],
            "signal_filters": item["signal_filters"],
            "auto_fixable": item["auto_fixable"],
            "auto_fix_hint": item["auto_fix_hint"],
            "auto_fix_strategy": item.get("auto_fix_strategy"),
            "status": "open",
            "confidence": "medium" if item["signal_type"] == "zero_result" else "high",
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
