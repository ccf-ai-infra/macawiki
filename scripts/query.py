#!/usr/bin/env python3
"""Search Macawiki pages using text and structured filters.

Modes:
  --mode and   All terms must appear in the page (default, high precision).
  --mode or    Any term may appear (better recall for broad exploration).
  --fuzzy      Use n-gram Jaccard similarity scoring instead of exact substring
               matching. Useful when exact AND/OR returns zero results.
               Character bigrams work for both CJK and Latin text.
  --auto-fuzzy Fall back to fuzzy mode when exact search returns 0 results.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from typing import Any

try:
    from .common import ROOT, Page, discover_pages, load_data, normalize_alias, searchable_text
except ImportError:
    from common import ROOT, Page, discover_pages, load_data, normalize_alias, searchable_text

PICKLE_INDEX_PATH = ROOT / "queries" / "index.pickle"


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


def _ngrams(text: str, n: int = 2) -> set[str]:
    """Generate character n-grams from text. Works for both CJK and Latin scripts."""
    if len(text) < n:
        return {text}
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity coefficient: |A ∩ B| / |A ∪ B|."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _fuzzy_search(
    terms: list[str],
    pages: list[Page],
    filters: dict[str, str | None],
    aliases: dict,
    page_map: dict[str, Page],
    limit: int = 20,
) -> list[tuple[float, Page]]:
    """Search using n-gram Jaccard similarity for each term against each page.

    Uses character bigrams (n=2) which work well for both CJK and Latin text.
    Scores are summed across terms, so pages matching more query terms rank higher.
    """
    # Pre-compute page n-grams from cached pickle index if available
    page_ngrams: dict[str, set[str]] = {}
    try:
        with open(PICKLE_INDEX_PATH, "rb") as f:
            index = pickle.load(f)
        for pid, data in index.get("pages", {}).items():
            text = data.get("_text", "")
            page_ngrams[pid] = _ngrams(text, n=2)
    except (FileNotFoundError, pickle.UnpicklingError):
        pass

    # Compute term n-gram sets
    term_ngram_sets: list[set[str]] = []
    for term in terms:
        # Generate both the raw term n-grams and combined query n-grams
        term_ngrams = _ngrams(term, n=2)
        term_ngram_sets.append(term_ngrams)

    results: list[tuple[float, Page]] = []

    for page in pages:
        pid = str(page.metadata.get("id", ""))
        # Apply filters
        if any(
            expected is not None and not _matches_filter(page, FILTER_FIELDS[name], expected, aliases)
            for name, expected in filters.items()
        ):
            continue

        # Get page n-grams (from cache or compute on the fly)
        if pid in page_ngrams:
            p_ngrams = page_ngrams[pid]
        else:
            p_ngrams = _ngrams(searchable_text(page), n=2)

        if not p_ngrams:
            continue

        # Score: average Jaccard across all terms, with bonuses
        title = str(page.metadata.get("title", "")).casefold()
        page_id_str = str(page.metadata.get("id", "")).casefold()

        score = 0.0
        for i, term in enumerate(terms):
            t_ngrams = term_ngram_sets[i]
            sim = _jaccard(t_ngrams, p_ngrams)
            score += sim

        # Bonuses for title and ID matches (exact substring)
        for term in terms:
            if term in title:
                score += 0.5
            if term in page_id_str:
                score += 0.3

        if score > 0.0:
            results.append((round(score, 4), page))

    results.sort(key=lambda item: (-item[0], str(item[1].relative_path)))
    return results[:limit]


def _search_with_pickle(
    terms: list[str], filters: dict[str, str | None], mode: str, aliases: dict, page_map: dict[str, Page],
) -> list[tuple[int, Page]]:
    """Use pre-built pickle index: filter by field, then substring-match cached text."""
    try:
        with open(PICKLE_INDEX_PATH, "rb") as f:
            index = pickle.load(f)
    except (FileNotFoundError, pickle.UnpicklingError):
        return []

    cached = index.get("pages", {})
    by_field = index.get("by_field", {})
    if not cached:
        return []

    # Filter candidates by field first using pre-built indices
    candidate_ids: set[str] | None = None
    for name, expected in filters.items():
        if expected is None:
            continue
        field_name = FILTER_FIELDS[name]
        field_index = by_field.get(field_name, {})
        expected_norm = normalize_alias(expected, aliases).casefold()
        # Find matching values
        matching_ids: set[str] = set()
        for val, ids in field_index.items():
            if normalize_alias(val, aliases).casefold() == expected_norm:
                matching_ids.update(ids)
        if candidate_ids is None:
            candidate_ids = matching_ids
        else:
            candidate_ids &= matching_ids
        if not candidate_ids:
            return []

    results: list[tuple[int, Page]] = []
    match_op = all if mode == "and" else any

    for pid, data in cached.items():
        if candidate_ids is not None and pid not in candidate_ids:
            continue
        page = page_map.get(pid)
        if page is None:
            continue
        haystack = data.get("_text", "")
        if terms and not match_op(term in haystack for term in terms):
            continue
        title = data.get("_title", "")
        page_id = data.get("_id", "")
        score = sum(haystack.count(term) for term in terms)
        score += sum(5 for term in terms if term in title)
        score += sum(3 for term in terms if term in page_id)
        results.append((score, page))
    return results


def search(terms: list[str], filters: dict[str, str | None], mode: str = "and") -> list[tuple[int, Page]]:
    aliases = load_data(ROOT / "data" / "aliases.yaml")
    normalized_terms = [normalize_alias(term, aliases).casefold() for term in terms if term]

    all_pages = discover_pages()
    page_map = {str(p.metadata.get("id", "")): p for p in all_pages}

    # Try pickle index first for fast filtered search
    if PICKLE_INDEX_PATH.exists():
        results = _search_with_pickle(normalized_terms, filters, mode, aliases, page_map)
        if results:
            return sorted(results, key=lambda item: (-item[0], str(item[1].relative_path)))

    # Fallback: full scan over live pages
    results: list[tuple[int, Page]] = []
    match_op = all if mode == "and" else any
    for page in all_pages:
        if any(
            expected is not None and not _matches_filter(page, FILTER_FIELDS[name], expected, aliases)
            for name, expected in filters.items()
        ):
            continue
        haystack = searchable_text(page)
        if normalized_terms and not match_op(term in haystack for term in normalized_terms):
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
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("terms", nargs="*", help="text terms; with --mode and (default) all terms must match, with --mode or any term may match")
    for name in FILTER_FIELDS:
        parser.add_argument(f"--{name}")
    parser.add_argument("--mode", choices=("and", "or"), default="and", help="match all terms (and, default) or any term (or)")
    parser.add_argument("--fuzzy", action="store_true", help="use n-gram Jaccard similarity scoring (ignores --mode)")
    parser.add_argument("--auto-fuzzy", action="store_true", help="fall back to fuzzy search when exact search returns 0 results")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--paths-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    filters = {name: getattr(args, name) for name in FILTER_FIELDS}
    active_filters = {k: v for k, v in filters.items() if v is not None}

    if args.fuzzy:
        # Fuzzy mode: use n-gram Jaccard similarity
        aliases = load_data(ROOT / "data" / "aliases.yaml")
        normalized_terms = [normalize_alias(term, aliases).casefold() for term in args.terms if term]
        all_pages = discover_pages()
        page_map = {str(p.metadata.get("id", "")): p for p in all_pages}
        raw_results = _fuzzy_search(normalized_terms, all_pages, filters, aliases, page_map, limit=max(args.limit, 0))
        results = [(int(score * 1000), page) for score, page in raw_results]
    else:
        results = search(args.terms, filters, mode=args.mode)[: max(args.limit, 0)]
        # Auto-fuzzy: fall back when exact search returns nothing
        if not results and args.auto_fuzzy and args.terms:
            aliases = load_data(ROOT / "data" / "aliases.yaml")
            normalized_terms = [normalize_alias(term, aliases).casefold() for term in args.terms if term]
            all_pages = discover_pages()
            page_map = {str(p.metadata.get("id", "")): p for p in all_pages}
            raw_results = _fuzzy_search(normalized_terms, all_pages, filters, aliases, page_map, limit=max(args.limit, 0))
            results = [(int(score * 1000), page) for score, page in raw_results]

    # Smart hints when no results found (stderr, doesn't affect output parsing)
    if not results:
        hints: list[str] = []
        if len(args.terms) > 1 and args.mode == "and" and not args.fuzzy:
            hints.append("try --mode or for broader multi-term matching")
        if not args.fuzzy and not args.auto_fuzzy:
            hints.append("try --fuzzy for approximate n-gram similarity matching")
            hints.append("try --auto-fuzzy to auto-fallback when exact search returns nothing")
        if active_filters:
            names = ", ".join(active_filters.keys())
            hints.append(f"try removing filters ({names}) to widen the search")
        if hints:
            print("No matching pages. Hints:", file=sys.stderr)
            for h in hints:
                print(f"  {h}", file=sys.stderr)
        elif not args.json and not args.paths_only and not args.compact:
            print("No matching pages.")
        return 0
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
