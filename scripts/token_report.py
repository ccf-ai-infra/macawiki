#!/usr/bin/env python3
"""Print a human-readable token consumption report from evals/signals/token-log*.jsonl.

Usage::

    python3 scripts/token_report.py          # human-readable report
    python3 scripts/token_report.py --json   # JSON output
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from .common import ROOT
except ImportError:
    from common import ROOT  # type: ignore[no-redef]

SIGNAL_DIR = Path(os.environ.get("MACAWIKI_SIGNAL_DIR", ROOT / "evals" / "signals"))


def load_records() -> list[dict]:
    """Load all token-log records (including archived)."""
    records: list[dict] = []
    for pattern in ["token-log*.jsonl", "archive/*/token-log*.jsonl"]:
        for p in sorted(SIGNAL_DIR.glob(pattern)):
            try:
                for line in p.read_text(encoding="utf-8").strip().split("\n"):
                    if line.strip():
                        records.append(json.loads(line))
            except (OSError, json.JSONDecodeError):
                continue
    return records


def generate_report() -> dict:
    """Analyse token records and return a structured report."""
    records = load_records()
    if not records:
        return {"total_records": 0, "message": "No token logs found."}

    queries = [r for r in records if r.get("operation") == "query"]
    total_tokens = sum(r.get("total_tokens", 0) for r in records)
    avg_tpr = (
        sum(r.get("tokens_per_result", 0) for r in records) / max(len(records), 1)
    )

    # Group by query pattern
    groups: dict[tuple, list[dict]] = {}
    for r in queries:
        key = (tuple(sorted(r.get("query_terms", []))), r.get("mode", "?"))
        groups.setdefault(key, []).append(r)

    # Identify hotspots
    hotspots = []
    for (terms_tuple, mode), grp in groups.items():
        if len(grp) < 2:
            continue
        avg = sum(g.get("tokens_per_result", 0) for g in grp) / len(grp)
        if avg >= 300:
            hotspots.append({
                "terms": list(terms_tuple),
                "mode": mode,
                "count": len(grp),
                "avg_tokens_per_result": round(avg, 1),
            })
    hotspots.sort(key=lambda h: h["avg_tokens_per_result"], reverse=True)

    return {
        "total_records": len(records),
        "total_queries": len(queries),
        "total_tokens": total_tokens,
        "avg_tokens_per_result": round(avg_tpr, 1),
        "hotspots": hotspots[:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--top-n", type=int, default=10, help="Max hotspots to show")
    args = parser.parse_args()

    report = generate_report()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if report.get("message"):
        print(report["message"])
        return 0

    print("=== Token Consumption Report ===")
    print(f"Total records:     {report['total_records']}")
    print(f"Total queries:     {report['total_queries']}")
    print(f"Total tokens:      {report['total_tokens']}")
    print(f"Avg tokens/result: {report['avg_tokens_per_result']:.1f}")
    if report.get("hotspots"):
        print(f"\nExpensive query patterns:")
        for h in report["hotspots"][: args.top_n]:
            terms_str = " ".join(h["terms"])
            print(f"  [{h['mode']}] {terms_str}: {h['count']}× queries, {h['avg_tokens_per_result']:.0f} tok/result")
    else:
        print("\nNo expensive query patterns detected.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
