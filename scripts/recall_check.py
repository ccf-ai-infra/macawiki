#!/usr/bin/env python3
"""Check query recall against gold questions from evals/gold-questions.yaml."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from .common import ROOT, load_data
except ImportError:
    from common import ROOT, load_data


def run_query(terms: list[str], mode: str, limit: int) -> set[str]:
    """Run query.py and return set of page IDs found."""
    import subprocess

    cmd = [sys.executable, str(ROOT / "scripts" / "query.py"), "--json"]
    cmd.extend(terms)
    cmd.extend(["--mode", mode, "--limit", str(limit)])

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    if result.returncode != 0:
        return set()

    try:
        data = json.loads(result.stdout)
        return {item["id"] for item in data if item.get("id")}
    except (json.JSONDecodeError, KeyError):
        return set()


def compute_recall(
    gold_path: str | None = None,
    k: int = 10,
    mode: str = "or",
) -> dict[str, Any]:
    gold_file = Path(gold_path) if gold_path else ROOT / "evals" / "gold-questions.yaml"
    raw = load_data(gold_file)
    questions = raw.get("questions", []) if isinstance(raw, dict) else raw

    per_question: list[dict[str, Any]] = []
    total_expected = 0
    total_found = 0

    for q in questions:
        # Derive search terms from keywords or question text
        terms = q.get("keywords") or q.get("terms") or []
        if not terms and q.get("question"):
            # Extract meaningful words from question text (simple heuristic)
            import re
            text = q["question"]
            # Remove punctuation and split into words
            words = re.findall(r'[\w一-鿿]+', text)
            # Filter out very short/stop words
            terms = [w for w in words if len(w) >= 2]
        expected = set(q.get("expected_pages", []))
        total_expected += len(expected)

        found = run_query(terms, mode=mode, limit=k)
        hits = expected & found
        total_found += len(hits)

        per_question.append({
            "id": q.get("id", "?"),
            "domain": q.get("domain", "?"),
            "terms": terms,
            "expected": len(expected),
            "found_total": len(found),
            "hits": len(hits),
            "missing": sorted(expected - found),
        })

    recall = total_found / total_expected if total_expected > 0 else 0.0

    return {
        "recall": round(recall, 3),
        "total_expected": total_expected,
        "total_found": total_found,
        "k": k,
        "mode": mode,
        "questions": per_question,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=str, help="Path to gold-questions.yaml")
    parser.add_argument("--k", type=int, default=10, help="Result limit per query")
    parser.add_argument("--mode", choices=("and", "or"), default="or", help="Search mode")
    parser.add_argument("--threshold", type=float, default=0.70, help="Minimum recall threshold (0.0-1.0)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    report = compute_recall(gold_path=args.gold, k=args.k, mode=args.mode)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"=== Recall Check (mode={report['mode']}, k={report['k']}) ===")
        print(f"Overall recall: {report['recall']:.1%} ({report['total_found']}/{report['total_expected']})")
        print()
        for q in report["questions"]:
            status = "PASS" if q["missing"] == [] else f"MISSING: {q['missing']}"
            print(f"  [{status}] {q['id']} ({q['domain']})")
            print(f"    Terms: {q['terms']}")
            print(f"    Found: {q['hits']}/{q['expected']}")
        print()

        passed = report["recall"] >= args.threshold
        print(f"Threshold: {args.threshold:.0%} — {'PASSED' if passed else 'FAILED'}")
        if not passed:
            print(f"Recall {report['recall']:.1%} is below threshold {args.threshold:.0%}")

    if report["recall"] < args.threshold:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
