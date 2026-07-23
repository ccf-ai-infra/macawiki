#!/usr/bin/env python3
"""Compute corpus-wide quality metrics against configurable thresholds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from .common import ROOT, discover_pages, load_data
except ImportError:
    from common import ROOT, discover_pages, load_data

THRESHOLDS_PATH = ROOT / "data" / "quality-thresholds.yaml"


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def compute_metrics() -> dict[str, Any]:
    pages = discover_pages()
    thresholds = load_data(THRESHOLDS_PATH)
    sources_registry = load_data(ROOT / "data" / "source-registry.yaml")
    sources_list = sources_registry.get("sources", []) if isinstance(sources_registry, dict) else sources_registry

    total_pages = len(pages)
    wiki_pages = [p for p in pages if str(p.metadata.get("type", "")).startswith("wiki-")]
    source_pages = [p for p in pages if str(p.metadata.get("type", "")).startswith("source-")]

    # Draft ratio
    draft_count = sum(1 for p in pages if p.metadata.get("status") == "draft")
    draft_ratio = _ratio(draft_count, total_pages)

    # Unspecified version ratio
    unspec_count = sum(
        1 for p in pages if "unspecified" in (p.metadata.get("mxmaca_versions") or [])
    )
    unspec_ratio = _ratio(unspec_count, total_pages)

    # Verified confidence ratio (wiki pages only)
    verified_count = sum(1 for p in wiki_pages if p.metadata.get("confidence") == "verified")
    verified_ratio = _ratio(verified_count, len(wiki_pages))

    # License known ratio
    license_known = sum(
        1 for s in sources_list
        if s.get("license_status") not in ("unknown", None, "")
    )
    license_ratio = _ratio(license_known, len(sources_list))

    # Source freshness ratio
    freshness_days = thresholds.get("source_freshness_ratio", {}).get("freshness_window_days", 180)

    fresh_count = 0
    total_sources = len(source_pages)
    for p in source_pages:
        retrieved = p.metadata.get("retrieved_at", "")
        if retrieved:
            try:
                from datetime import date
                dt = date.fromisoformat(str(retrieved))
                age = (date.today() - dt).days
                if age <= freshness_days:
                    fresh_count += 1
            except (ValueError, TypeError):
                pass
    freshness_ratio = _ratio(fresh_count, total_sources)

    # Body length violations
    min_body = thresholds.get("body_min_length", {}).get("value", 50)
    short_pages = [p.metadata.get("id", "?") for p in pages if len(p.body.strip()) < min_body]

    return {
        "total_pages": total_pages,
        "wiki_pages": len(wiki_pages),
        "source_pages": len(source_pages),
        "draft_ratio": round(draft_ratio, 3),
        "unspecified_version_ratio": round(unspec_ratio, 3),
        "verified_confidence_ratio": round(verified_ratio, 3),
        "source_license_known_ratio": round(license_ratio, 3),
        "source_freshness_ratio": round(freshness_ratio, 3),
        "short_body_pages": short_pages,
    }


def evaluate(metrics: dict[str, Any], thresholds: dict[str, Any]) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    failures: list[str] = []

    def check(key: str, value: float, thresh: dict[str, Any], comparison: str):
        warn_val = thresh.get("max_warn" if comparison == "le" else "min_warn")
        fail_val = thresh.get("max_fail" if comparison == "le" else "min_fail")
        hard = thresh.get("hard_fail", False)
        if fail_val is not None:
            if (comparison == "le" and value > fail_val) or (comparison == "ge" and value < fail_val):
                failures.append(f"{key}: {value:.1%} (threshold: {fail_val:.1%}){' [HARD FAIL]' if hard else ''}")
                return
        if warn_val is not None:
            if (comparison == "le" and value > warn_val) or (comparison == "ge" and value < warn_val):
                warnings.append(f"{key}: {value:.1%} (threshold: {warn_val:.1%})")

    check("draft_ratio", metrics["draft_ratio"], thresholds.get("draft_ratio", {}), "le")
    check("unspecified_version_ratio", metrics["unspecified_version_ratio"], thresholds.get("unspecified_version_ratio", {}), "le")
    check("verified_confidence_ratio", metrics["verified_confidence_ratio"], thresholds.get("verified_confidence_ratio", {}), "ge")
    check("source_license_known_ratio", metrics["source_license_known_ratio"], thresholds.get("source_license_known_ratio", {}), "ge")
    check("source_freshness_ratio", metrics["source_freshness_ratio"], thresholds.get("source_freshness_ratio", {}), "ge")

    # Body length (hard fail by default)
    if metrics["short_body_pages"]:
        hard = thresholds.get("body_min_length", {}).get("hard_fail", True)
        msg = f"short_body_pages: {metrics['short_body_pages']}{' [HARD FAIL]' if hard else ''}"
        if hard:
            failures.append(msg)
        else:
            warnings.append(msg)

    # Minimum page count (hard fail by default)
    min_pages = thresholds.get("minimum_page_count", {}).get("value", 12)
    hard = thresholds.get("minimum_page_count", {}).get("hard_fail", True)
    if metrics["total_pages"] < min_pages:
        msg = f"minimum_page_count: {metrics['total_pages']} < {min_pages}{' [HARD FAIL]' if hard else ''}"
        if hard:
            failures.append(msg)
        else:
            warnings.append(msg)

    return warnings, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Output metrics as JSON")
    parser.add_argument("--thresholds", type=str, default=str(THRESHOLDS_PATH), help="Path to thresholds file")
    args = parser.parse_args()

    thresholds = load_data(Path(args.thresholds)) if args.thresholds else {}
    metrics = compute_metrics()
    warnings, failures = evaluate(metrics, thresholds)

    if args.json:
        print(json.dumps({"metrics": metrics, "warnings": warnings, "failures": failures}, ensure_ascii=False, indent=2))
    else:
        print("=== Quality Gates ===")
        print(f"Pages: {metrics['total_pages']} ({metrics['wiki_pages']} wiki, {metrics['source_pages']} sources)")
        print(f"Draft ratio: {metrics['draft_ratio']:.1%}")
        print(f"Unspecified version ratio: {metrics['unspecified_version_ratio']:.1%}")
        print(f"Verified confidence ratio: {metrics['verified_confidence_ratio']:.1%} (wiki pages)")
        print(f"License known ratio: {metrics['source_license_known_ratio']:.1%}")
        print(f"Freshness ratio: {metrics['source_freshness_ratio']:.1%}")

        if warnings:
            print(f"\nWarnings ({len(warnings)}):")
            for w in warnings:
                print(f"  - {w}")

        if failures:
            print(f"\nFailures ({len(failures)}):")
            for f in failures:
                print(f"  - {f}")
        else:
            print("\nAll quality gates passed.")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
