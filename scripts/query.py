#!/usr/bin/env python3
"""Search Macawiki pages using text and structured filters."""

from __future__ import annotations

import argparse
import json
from typing import Any

from common import ROOT, Page, discover_pages, load_data, normalize_alias, searchable_text


FILTER_FIELDS = {
    "type": "type",
    "hardware": "hardware",
    "version": "mxmaca_versions",
    "component": "components",
    "tag": "tags",
    "confidence": "confidence",
}


def _matches_filter(page: Page, field: str, expected: str, aliases: dict[str, list[str]]) -> bool:
    value = page.metadata.get(field)
    expected = normalize_alias(expected, aliases).casefold()
    values = value if isinstance(value, list) else [value]
    return any(normalize_alias(str(item), aliases).casefold() == expected for item in values if item is not None)


def search(terms: list[str], filters: dict[str, str | None]) -> list[tuple[int, Page]]:
    aliases = load_data(ROOT / "data" / "aliases.yaml")
    normalized_terms = [normalize_alias(term, aliases).casefold() for term in terms if term]
    results: list[tuple[int, Page]] = []
    for page in discover_pages():
        if any(
            expected is not None and not _matches_filter(page, FILTER_FIELDS[name], expected, aliases)
            for name, expected in filters.items()
        ):
            continue
        haystack = searchable_text(page)
        if normalized_terms and not all(term in haystack for term in normalized_terms):
            continue
        title = str(page.metadata.get("title", "")).casefold()
        page_id = str(page.metadata.get("id", "")).casefold()
        score = sum(haystack.count(term) for term in normalized_terms)
        score += sum(5 for term in normalized_terms if term in title)
        score += sum(3 for term in normalized_terms if term in page_id)
        results.append((score, page))
    return sorted(results, key=lambda item: (-item[0], str(item[1].relative_path)))


def _record(score: int, page: Page) -> dict[str, Any]:
    metadata = page.metadata
    return {
        "score": score,
        "id": metadata.get("id"),
        "title": metadata.get("title"),
        "type": metadata.get("type"),
        "path": str(page.relative_path),
        "summary": metadata.get("summary"),
        "confidence": metadata.get("confidence"),
        "hardware": metadata.get("hardware", []),
        "mxmaca_versions": metadata.get("mxmaca_versions", []),
        "sources": metadata.get("sources", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terms", nargs="*", help="text terms; all terms must match")
    for name in FILTER_FIELDS:
        parser.add_argument(f"--{name}")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--paths-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    filters = {name: getattr(args, name) for name in FILTER_FIELDS}
    results = search(args.terms, filters)[: max(args.limit, 0)]
    if args.json:
        print(json.dumps([_record(score, page) for score, page in results], ensure_ascii=False, indent=2))
    elif args.paths_only:
        for _, page in results:
            print(page.relative_path)
    elif args.compact:
        for score, page in results:
            metadata = page.metadata
            print(f"{metadata['id']}\t{metadata['type']}\t{page.relative_path}\t{metadata['title']}\t{score}")
    else:
        if not results:
            print("No matching pages.")
        for score, page in results:
            record = _record(score, page)
            print(f"## {record['title']} ({record['id']})")
            print(f"- Path: `{record['path']}`")
            print(f"- Type: `{record['type']}`")
            print(f"- Scope: hardware={record['hardware']}, MXMACA={record['mxmaca_versions']}")
            if record["confidence"]:
                print(f"- Confidence: `{record['confidence']}`")
            print(f"- {record['summary']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
