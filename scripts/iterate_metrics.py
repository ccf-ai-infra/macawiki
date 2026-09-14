#!/usr/bin/env python3
"""Measure the corpus metrics that an iteration cycle is judged on.

The loop's decisions are only as trustworthy as the numbers behind them. This
module is the single place that converts "run the gates and read the numbers"
into a flat dict, so a cycle's before/after comparison and the long-run trend
report can never disagree about what a metric means.

All three sources are existing stdlib scripts that already expose --json; this
module adds no new measurement logic of its own. A source that fails to run is
recorded as null rather than raising — a missing metric must be *visible* in
the trend, not silently zeroed or interpolated.

Usage:
    from scripts.iterate_metrics import collect_snapshot
    snap = collect_snapshot()          # -> {"pages": 28, "component_coverage": 18, ...}
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from .common import ROOT
except ImportError:
    from common import ROOT


# Metrics a cycle is allowed to set a target on. Kept in one place so the
# hypothesis validator and the trend report name the same things.
METRIC_KEYS: tuple[str, ...] = (
    "pages",
    "component_coverage",
    "component_total",
    "version_claims_specified",
    "version_claims_total",
    "draft_ratio",
    "unspecified_ratio",
    "license_known_ratio",
    "recall",
    "tests",
)

# Phrases a hypothesis may use to refer to each metric. Used only to *reject*
# a hypothesis that names nothing measurable; it never infers a target value.
METRIC_PHRASES: dict[str, tuple[str, ...]] = {
    "component_coverage": ("component coverage", "组件覆盖", "components covered"),
    "version_claims_specified": ("version-claims", "version claims", "版本声明"),
    "pages": ("pages", "页面"),
    "draft_ratio": ("draft", "draft ratio"),
    "unspecified_ratio": ("unspecified", "unspecified ratio", "unspecified 比例"),
    "license_known_ratio": ("license", "许可"),
    "recall": ("recall", "召回"),
    "tests": ("tests", "单元测试", "test count"),
}


def _run(name: str, *args: str) -> Any:
    path = ROOT / "scripts" / name
    r = subprocess.run(
        [sys.executable, str(path), *args],
        cwd=str(ROOT), capture_output=True, text=True, check=False, timeout=180,
    )
    if r.returncode != 0:
        return {"_error": f"{name} exited {r.returncode}: {r.stderr.strip()[:200]}"}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError as exc:
        return {"_error": f"{name} emitted no JSON: {exc}"}


def _test_count() -> int | None:
    """Count test methods; the suite is small enough to count statically.

    Counting via `unittest discover` would re-run the whole suite, which the
    accept gate already does. A static count can drift from the real number
    only if a test is written without a `test_` prefix, which the repo's own
    convention forbids — so it is accurate enough for trend purposes and
    costs nothing to collect.
    """
    count = 0
    for path in (ROOT / "tests").glob("test_*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None
        count += sum(1 for line in text.splitlines()
                     if line.strip().startswith("def test_"))
    return count or None


def collect_snapshot() -> dict[str, Any]:
    """Return a flat metric snapshot of the corpus as it stands right now."""
    out: dict[str, Any] = {}

    gates = _run("quality_gates.py", "--json")
    m = gates.get("metrics", {}) if isinstance(gates, dict) else {}
    out["_quality_gates_error"] = gates.get("_error") if isinstance(gates, dict) else None
    out["pages"] = m.get("total_pages")
    out["draft_ratio"] = m.get("draft_ratio")
    out["unspecified_ratio"] = m.get("unspecified_version_ratio")
    out["license_known_ratio"] = m.get("source_license_known_ratio")

    cov = _run("coverage_report.py", "--json")
    comp = (cov.get("coverage", {}) or {}).get("components", {}) if isinstance(cov, dict) else {}
    vc = cov.get("version_claims", {}) if isinstance(cov, dict) else {}
    out["_coverage_error"] = cov.get("_error") if isinstance(cov, dict) else None
    out["component_coverage"] = comp.get("covered")
    out["component_total"] = comp.get("total_known")
    out["version_claims_specified"] = vc.get("specified")
    out["version_claims_total"] = vc.get("total")

    rec = _run("recall_check.py", "--mode", "or", "--json")
    out["_recall_error"] = rec.get("_error") if isinstance(rec, dict) else None
    out["recall"] = rec.get("recall") if isinstance(rec, dict) else None

    out["tests"] = _test_count()
    return out


def snapshot_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, float]:
    """Signed deltas for every metric both snapshots actually measured.

    Ratios are reported in percentage points so a human reading the report
    sees "-9.5pp" rather than "-0.095". Metrics absent from either side are
    omitted: a delta fabricated from a missing value would be worse than no
    delta at all.
    """
    deltas: dict[str, float] = {}
    for key in METRIC_KEYS:
        b, a = before.get(key), after.get(key)
        if not isinstance(b, (int, float)) or not isinstance(a, (int, float)):
            continue
        if b == a:
            continue
        scale = 100.0 if key.endswith("_ratio") else 1.0
        deltas[key] = round((a - b) * scale, 1)
    return deltas


def fmt_value(key: str, value: Any) -> str:
    """Render one metric for a report table."""
    if value is None:
        return "n/a"
    if key.endswith("_ratio") and isinstance(value, (int, float)):
        return f"{value * 100:.1f}%"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def fmt_delta(key: str, delta: float) -> str:
    """Render a signed delta; for ratios it is already in percentage points."""
    sign = "+" if delta >= 0 else ""
    suffix = "pp" if key.endswith("_ratio") else ""
    return f"{sign}{delta}{suffix}"


def main() -> int:
    """Print the current snapshot; --json for machine-readable output."""
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="emit as JSON")
    args = parser.parse_args()

    snap = collect_snapshot()
    if args.json:
        print(json.dumps(snap, ensure_ascii=False, indent=2))
        return 0

    print("=== Corpus metrics (now) ===")
    for key in METRIC_KEYS:
        print(f"  {key:26} {fmt_value(key, snap.get(key))}")
    errors = {k: v for k, v in snap.items()
              if k.endswith("_error") and v}
    if errors:
        print("\n  measurement failures:")
        for name, msg in errors.items():
            print(f"  - {name}: {msg}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
