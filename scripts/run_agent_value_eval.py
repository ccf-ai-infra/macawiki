#!/usr/bin/env python3
"""Run deterministic proxy checks for Macawiki's before/after Agent value."""

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


def check_case(case: dict[str, Any], pages: list[Page]) -> dict[str, Any]:
    loaded = [page for _, page in search(case["terms"], {})]
    shallow = shallow_search(pages, case["terms"])
    expected = set(case["expected_pages"])
    loaded_ids = {page.metadata.get("id") for page in loaded}
    shallow_ids = {page.metadata.get("id") for page in shallow}
    target = next((page for page in loaded if page.metadata.get("id") in expected), None)
    corpus_text = searchable_text(target) if target else ""
    source_ids = set(target.metadata.get("sources", [])) if target else set()
    missing_sources = sorted(set(case["required_sources"]) - source_ids)
    missing_content = [item for item in case["must_contain"] if item.casefold() not in corpus_text]
    forbidden_found = [item for item in case["must_not_contain"] if item.casefold() in corpus_text]
    loaded_pass = bool(expected & loaded_ids) and not missing_sources and not missing_content and not forbidden_found
    return {
        "id": case["id"],
        "prompt": case["prompt"],
        "before_shallow_metadata": sorted(shallow_ids),
        "after_loaded_corpus": sorted(loaded_ids),
        "expected_pages": sorted(expected),
        "loaded_pass": loaded_pass,
        "evidence": {"sources": sorted(source_ids), "missing_sources": missing_sources, "missing_content": missing_content, "forbidden_found": forbidden_found},
        "interpretation": "The proxy measures retrieval and evidence availability; it is not a claim about an LLM's exact answer quality.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    cases = load_data(CASES)["cases"]
    pages = discover_pages()
    results = [check_case(case, pages) for case in cases]
    report = {"schema_version": 1, "cases": results, "passed": all(item["loaded_pass"] for item in results), "note": "Before/after is a deterministic shallow-metadata vs full-corpus proxy; it does not fabricate model outputs."}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Macawiki Agent value proxy")
        for item in results:
            print(f"{'PASS' if item['loaded_pass'] else 'FAIL'} {item['id']}: before={item['before_shallow_metadata']} after={item['after_loaded_corpus']}")
            if item["evidence"]["missing_content"]:
                print(f"  missing: {item['evidence']['missing_content']}")
        print("This is a retrieval/evidence proxy, not an LLM benchmark.")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
