#!/usr/bin/env python3
"""Print compact corpus statistics."""

from __future__ import annotations

from collections import Counter

try:
    from .common import discover_pages
except ImportError:
    from common import discover_pages


def _print_counter(title: str, values: Counter[str]) -> None:
    print(f"{title}:")
    for name, count in sorted(values.items()):
        print(f"  {name}: {count}")


def main() -> int:
    pages = discover_pages()
    print(f"pages: {len(pages)}")
    _print_counter("scope", Counter(page.relative_path.parts[0] for page in pages))
    _print_counter("type", Counter(page.metadata.get("type", "unknown") for page in pages))
    _print_counter("status", Counter(page.metadata.get("status", "unknown") for page in pages))
    _print_counter(
        "confidence",
        Counter(page.metadata.get("confidence", "not-applicable") for page in pages),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
