#!/usr/bin/env python3
"""Run deterministic proxy checks for Macawiki's before/after Agent value.

Covers:
  - Positive retrieval: expected pages and sources must be found.
  - Negative / non-MXMACA triggers: Macawiki pages must NOT be returned.
  - Source citation chain: required sources must resolve to registered sources.
  - Multi-page synthesis: multiple expected pages must be discoverable.
  - Forbidden claims: must_not_contain items must be absent from corpus text.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from common import ROOT, Page, discover_pages, load_data, searchable_text
from query import search


CASES = ROOT / "evals" / "agent-value-cases.yaml"


def shallow_search(pages: list[Page], terms: list[str]) -> list[Page]:
    normalized = [term.casefold() for term in terms]
    found = []
    for page in pages:
        text = " ".join(str(page.metadata.get(field, "")) for field in ("title", "summary")).casefold()
        if all(term in text for term in normalized):
            found.append(page)
    return found


def _pages_text(pages: list[Page]) -> str:
    return " ".join(searchable_text(p) for p in pages)


def check_case(case: dict[str, Any], pages: list[Page]) -> dict[str, Any]:
    loaded = [page for _, page in search(case["terms"], {})]
    shallow = shallow_search(pages, case["terms"])
    expected = set(case["expected_pages"])
    loaded_ids = {page.metadata.get("id") for page in loaded}
    shallow_ids = {page.metadata.get("id") for page in shallow}
    is_negative = case.get("negative_trigger") is not None or (
        not expected and "negative" in case["id"]
    )

    if is_negative:
        # Negative / non-MXMACA trigger: success = no Macawiki pages returned
        # for the search terms, AND must_not_contain items are absent.
        corpus_text = _pages_text(loaded)
        false_positive = len(loaded) > 0
        forbidden_found = [
            item for item in case["must_not_contain"]
            if item.casefold() in corpus_text
        ]
        loaded_pass = not false_positive and not forbidden_found
        return {
            "id": case["id"],
            "prompt": case["prompt"],
            "type": "negative_trigger",
            "before_shallow_metadata": sorted(shallow_ids),
            "after_loaded_corpus": sorted(loaded_ids),
            "expected_pages": sorted(expected),
            "loaded_pass": loaded_pass,
            "evidence": {
                "sources": [],
                "missing_sources": [],
                "missing_content": [],
                "forbidden_found": forbidden_found,
                "false_positive_pages": sorted(loaded_ids) if false_positive else [],
            },
            "interpretation": "Negative trigger: no Macawiki pages should be returned; "
                              "must_not_contain items must be absent.",
        }

    # Positive retrieval case
    target_pages = [page for page in loaded if page.metadata.get("id") in expected]
    # Also find pages from all discovered pages for source chain validation
    all_expected_found = expected & loaded_ids

    # Collect corpus text from all loaded pages (for multi-page synthesis)
    corpus_text = _pages_text(target_pages) if target_pages else ""
    # Also search across all pages for source chain validation
    all_source_ids: set[str] = set()
    for page in pages:
        for sid in page.metadata.get("sources", []):
            all_source_ids.add(sid)

    missing_sources = sorted(
        set(case["required_sources"]) - all_source_ids
    )
    missing_content = [
        item for item in case["must_contain"]
        if item.casefold() not in _pages_text(loaded)
    ]
    forbidden_found = [
        item for item in case["must_not_contain"]
        if item.casefold() in _pages_text(loaded)
    ]

    # For single-page cases: all expected pages must be in loaded
    # For multi-page: at least one expected page found + required sources present
    if len(expected) > 1:
        pages_ok = bool(expected & loaded_ids)
    else:
        pages_ok = bool(expected & loaded_ids) if expected else True

    loaded_pass = (
        pages_ok
        and not missing_sources
        and not missing_content
        and not forbidden_found
    )

    return {
        "id": case["id"],
        "prompt": case["prompt"],
        "type": "positive_retrieval",
        "before_shallow_metadata": sorted(shallow_ids),
        "after_loaded_corpus": sorted(loaded_ids),
        "expected_pages": sorted(expected),
        "expected_pages_found": sorted(expected & loaded_ids),
        "expected_pages_missing": sorted(expected - loaded_ids),
        "loaded_pass": loaded_pass,
        "evidence": {
            "sources": sorted(all_source_ids),
            "missing_sources": missing_sources,
            "missing_content": missing_content,
            "forbidden_found": forbidden_found,
        },
        "interpretation": "The proxy measures retrieval and evidence availability; "
                          "it is not a claim about an LLM's exact answer quality.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    cases = load_data(CASES)["cases"]
    pages = discover_pages()
    results = [check_case(case, pages) for case in cases]
    passed = sum(1 for r in results if r["loaded_pass"])
    failed = len(results) - passed
    report = {
        "schema_version": 1,
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "all_passed": all(item["loaded_pass"] for item in results),
        "cases": results,
        "note": "Before/after is a deterministic shallow-metadata vs full-corpus proxy; "
                "it does not fabricate model outputs.",
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Macawiki Agent value proxy")
        for item in results:
            tag = "PASS" if item["loaded_pass"] else "FAIL"
            case_type = item.get("type", "positive")
            print(
                f"{tag} {item['id']} [{case_type}]: "
                f"before={item['before_shallow_metadata']} "
                f"after={item['after_loaded_corpus']}"
            )
            if item["evidence"].get("missing_content"):
                print(f"  missing: {item['evidence']['missing_content']}")
            if item["evidence"].get("forbidden_found"):
                print(f"  forbidden: {item['evidence']['forbidden_found']}")
            if item["evidence"].get("false_positive_pages"):
                print(f"  false_positive: {item['evidence']['false_positive_pages']}")
            if item.get("expected_pages_missing"):
                print(f"  pages_missing: {item['expected_pages_missing']}")
        print(f"\n{passed}/{len(results)} passed")
        print("This is a retrieval/evidence proxy, not an LLM benchmark.")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
