#!/usr/bin/env python3
"""Read a Macawiki page by ID or repository-relative path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .common import ROOT, Page, discover_pages
except ImportError:
    from common import ROOT, Page, discover_pages


def resolve_page(target: str, pages: list[Page]) -> Page:
    by_id = {page.metadata.get("id"): page for page in pages}
    if target in by_id:
        return by_id[target]
    path = (ROOT / target).resolve()
    if ROOT != path and ROOT not in path.parents:
        raise ValueError("path escapes the Macawiki repository")
    for page in pages:
        if page.path.resolve() == path:
            return page
    raise ValueError(f"page not found: {target}")


def render(page: Page, frontmatter_only: bool, body_only: bool) -> str:
    if frontmatter_only:
        return json.dumps(page.metadata, ensure_ascii=False, indent=2)
    if body_only:
        return page.body.rstrip()
    return page.path.read_text(encoding="utf-8").rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("--frontmatter-only", action="store_true")
    parser.add_argument("--body-only", action="store_true")
    parser.add_argument("--follow-sources", action="store_true")
    args = parser.parse_args()
    if args.frontmatter_only and args.body_only:
        parser.error("--frontmatter-only and --body-only are mutually exclusive")
    pages = discover_pages()
    try:
        page = resolve_page(args.target, pages)
    except ValueError as exc:
        parser.error(str(exc))
    output = [render(page, args.frontmatter_only, args.body_only)]
    if args.follow_sources:
        by_id = {item.metadata.get("id"): item for item in pages}
        for source_id in page.metadata.get("sources", []):
            source = by_id.get(source_id)
            if source:
                output.append(f"\n--- SOURCE: {source_id} ({source.relative_path}) ---\n")
                output.append(render(source, args.frontmatter_only, args.body_only))
    print("\n".join(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
