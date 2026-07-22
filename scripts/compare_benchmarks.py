#!/usr/bin/env python3
"""Compare two result JSON files only when their contracts are comparable."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    baseline, candidate = load(args.baseline), load(args.candidate)
    if baseline.get("status") != "completed" or candidate.get("status") != "completed":
        print("not_comparable: both reports must be completed", file=sys.stderr)
        return 2
    if baseline.get("environment", {}).get("environment_fingerprint") != candidate.get("environment", {}).get("environment_fingerprint"):
        print("not_comparable: environment fingerprints differ", file=sys.stderr)
        return 2
    base_cases = {item["case_id"]: item for item in baseline.get("cases", [])}
    cand_cases = {item["case_id"]: item for item in candidate.get("cases", [])}
    rows = []
    for case_id in sorted(base_cases.keys() & cand_cases.keys()):
        left, right = base_cases[case_id], cand_cases[case_id]
        if not left.get("correctness", {}).get("passed") or not right.get("correctness", {}).get("passed"):
            rows.append({"case_id": case_id, "status": "not_comparable", "reason": "correctness gate failed"})
            continue
        left_ms, right_ms = left.get("timing", {}).get("median_ms"), right.get("timing", {}).get("median_ms")
        if not left_ms or not right_ms:
            rows.append({"case_id": case_id, "status": "not_comparable", "reason": "missing median timing"})
            continue
        rows.append({"case_id": case_id, "status": "comparable", "baseline_median_ms": left_ms, "candidate_median_ms": right_ms, "speedup": left_ms / right_ms})
    print(json.dumps({"baseline": str(args.baseline), "candidate": str(args.candidate), "comparisons": rows}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
