#!/usr/bin/env python3
"""Compare two result JSON files with schema, contract, and timing validation.

Gate order:
  1. Top-level schema (status, environment, cases must exist; status must be "completed")
  2. Environment fingerprint match
  3. Per-case schema and contract (case_id, operator, shape, dtype, correctness, timing)
  4. Missing cases (baseline-only, candidate-only)
  5. Correctness gate (both must pass)
  6. Timing gate (median_ms must be positive; warmup/iterations must match)
  7. Speedup calculation (only when all gates pass)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_TOP_KEYS = ["status", "environment", "cases"]
REQUIRED_ENV_KEYS = ["environment_fingerprint"]
REQUIRED_CASE_KEYS = ["case_id", "operator", "correctness"]
REQUIRED_CORRECTNESS_KEYS = ["passed"]
REQUIRED_TIMING_KEYS = ["median_ms", "warmup", "iterations"]


def _validate_top_level(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in REQUIRED_TOP_KEYS:
        if key not in data:
            issues.append(f"missing top-level key: {key}")
    if "cases" in data and not isinstance(data["cases"], list):
        issues.append("top-level 'cases' must be a list")
    return issues


def _validate_environment(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    env = data.get("environment", {})
    if not isinstance(env, dict):
        issues.append("top-level 'environment' must be an object")
        return issues
    for key in REQUIRED_ENV_KEYS:
        if key not in env:
            issues.append(f"missing environment key: {key}")
    return issues


def _validate_case(case: dict[str, Any], index: int) -> list[str]:
    issues: list[str] = []
    label = f"cases[{index}]"
    for key in REQUIRED_CASE_KEYS:
        if key not in case:
            issues.append(f"{label}: missing required key '{key}'")
            continue
    if "case_id" in case and not isinstance(case["case_id"], str):
        issues.append(f"{label}: 'case_id' must be a string")
    if "correctness" in case:
        corr = case["correctness"]
        if not isinstance(corr, dict):
            issues.append(f"{label}: 'correctness' must be an object")
        else:
            for key in REQUIRED_CORRECTNESS_KEYS:
                if key not in corr:
                    issues.append(f"{label}: missing correctness key '{key}'")
    # timing is optional when correctness.passed=false (valid not_comparable result);
    # when present, it must be an object with required sub-keys
    if "timing" in case and case["timing"] is not None:
        tim = case["timing"]
        if not isinstance(tim, dict):
            issues.append(f"{label}: 'timing' must be an object or null")
        else:
            for key in REQUIRED_TIMING_KEYS:
                if key not in tim:
                    issues.append(f"{label}: missing timing key '{key}'")
            if "median_ms" in tim and not isinstance(tim["median_ms"], (int, float)):
                issues.append(f"{label}: 'median_ms' must be numeric")
            elif "median_ms" in tim and tim["median_ms"] <= 0:
                issues.append(f"{label}: 'median_ms' must be positive, got {tim['median_ms']}")
    return issues


def _check_contract_match(
    left: dict[str, Any], right: dict[str, Any], case_id: str
) -> list[str]:
    issues: list[str] = []
    for field in ("operator", "shape", "dtype"):
        lv = left.get(field)
        rv = right.get(field)
        if lv is not None and rv is not None and lv != rv:
            issues.append(
                f"case {case_id}: {field} mismatch: baseline={lv}, candidate={rv}"
            )
    l_timing = left.get("timing") or {}
    r_timing = right.get("timing") or {}
    lw = l_timing.get("warmup")
    rw = r_timing.get("warmup")
    if lw is not None and rw is not None and lw != rw:
        issues.append(
            f"case {case_id}: warmup mismatch: baseline={lw}, candidate={rw}"
        )
    li = l_timing.get("iterations")
    ri = r_timing.get("iterations")
    if li is not None and ri is not None and li != ri:
        issues.append(
            f"case {case_id}: iterations mismatch: baseline={li}, candidate={ri}"
        )
    return issues


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()

    baseline = load(args.baseline)
    candidate = load(args.candidate)

    all_issues: list[str] = []

    # 1. Top-level schema
    all_issues += [f"baseline: {i}" for i in _validate_top_level(baseline)]
    all_issues += [f"candidate: {i}" for i in _validate_top_level(candidate)]

    # 2. Environment
    all_issues += [f"baseline: {i}" for i in _validate_environment(baseline)]
    all_issues += [f"candidate: {i}" for i in _validate_environment(candidate)]

    if all_issues:
        print(json.dumps({
            "baseline": str(args.baseline),
            "candidate": str(args.candidate),
            "status": "schema_error",
            "issues": all_issues,
            "comparisons": [],
        }, ensure_ascii=False, indent=2))
        return 1

    # Status gate
    if baseline.get("status") != "completed" or candidate.get("status") != "completed":
        print(json.dumps({
            "baseline": str(args.baseline),
            "candidate": str(args.candidate),
            "status": "not_comparable",
            "reason": "both reports must have status 'completed'",
            "comparisons": [],
        }, ensure_ascii=False, indent=2))
        return 2

    # Environment fingerprint gate
    b_fp = baseline["environment"]["environment_fingerprint"]
    c_fp = candidate["environment"]["environment_fingerprint"]
    if b_fp != c_fp:
        print(json.dumps({
            "baseline": str(args.baseline),
            "candidate": str(args.candidate),
            "status": "not_comparable",
            "reason": "environment fingerprints differ",
            "comparisons": [],
        }, ensure_ascii=False, indent=2))
        return 2

    # 3. Per-case schema validation
    base_cases_raw = baseline.get("cases", [])
    cand_cases_raw = candidate.get("cases", [])
    for i, case in enumerate(base_cases_raw):
        all_issues += [f"baseline: {i}" for i in _validate_case(case, i)]
    for i, case in enumerate(cand_cases_raw):
        all_issues += [f"candidate: {i}" for i in _validate_case(case, i)]

    if all_issues:
        print(json.dumps({
            "baseline": str(args.baseline),
            "candidate": str(args.candidate),
            "status": "schema_error",
            "issues": all_issues,
            "comparisons": [],
        }, ensure_ascii=False, indent=2))
        return 1

    base_cases = {item["case_id"]: item for item in base_cases_raw}
    cand_cases = {item["case_id"]: item for item in cand_cases_raw}

    # 4. Detect missing cases
    base_ids = set(base_cases.keys())
    cand_ids = set(cand_cases.keys())
    common = base_ids & cand_ids
    baseline_only = sorted(base_ids - cand_ids)
    candidate_only = sorted(cand_ids - base_ids)

    rows: list[dict[str, Any]] = []
    issues: list[str] = []

    for case_id in sorted(common):
        left, right = base_cases[case_id], cand_cases[case_id]

        # 5. Contract match
        contract_issues = _check_contract_match(left, right, case_id)
        if contract_issues:
            issues += contract_issues
            rows.append({
                "case_id": case_id,
                "status": "not_comparable",
                "reason": "contract mismatch: " + "; ".join(contract_issues),
            })
            continue

        # 6. Correctness gate
        if not left["correctness"]["passed"] or not right["correctness"]["passed"]:
            rows.append({
                "case_id": case_id,
                "status": "not_comparable",
                "reason": "correctness gate failed",
            })
            continue

        # 7. Timing gate (timing may be null when correctness fails — already
        #    caught by the correctness gate above, so this is a defense-in-depth)
        l_timing = left.get("timing")
        r_timing = right.get("timing")
        if not isinstance(l_timing, dict) or not isinstance(r_timing, dict):
            rows.append({
                "case_id": case_id,
                "status": "not_comparable",
                "reason": "missing or null timing",
            })
            continue
        l_ms = l_timing.get("median_ms")
        r_ms = r_timing.get("median_ms")
        if not isinstance(l_ms, (int, float)) or not isinstance(r_ms, (int, float)):
            rows.append({
                "case_id": case_id,
                "status": "not_comparable",
                "reason": "missing or non-numeric median_ms",
            })
            continue
        if l_ms <= 0 or r_ms <= 0:
            rows.append({
                "case_id": case_id,
                "status": "not_comparable",
                "reason": "median_ms must be positive",
            })
            continue
        rows.append({
            "case_id": case_id,
            "status": "comparable",
            "baseline_median_ms": l_ms,
            "candidate_median_ms": r_ms,
            "speedup": l_ms / r_ms,
        })

    report: dict[str, Any] = {
        "baseline": str(args.baseline),
        "candidate": str(args.candidate),
        "comparisons": rows,
    }

    if baseline_only:
        report["baseline_only"] = baseline_only
    if candidate_only:
        report["candidate_only"] = candidate_only
    if issues:
        report["issues"] = issues

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
