#!/usr/bin/env python3
"""Regex search across Macawiki source and wiki pages."""

from __future__ import annotations

import argparse
import re

from common import discover_pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pattern")
    parser.add_argument("--only", choices=("sources", "wiki"))
    parser.add_argument("--ignore-case", action="store_true")
    args = parser.parse_args()
    flags = re.IGNORECASE if args.ignore_case else 0
    try:
        regex = re.compile(args.pattern, flags)
    except re.error as exc:
        parser.error(str(exc))
    count = 0
    for page in discover_pages():
        if args.only and page.relative_path.parts[0] != args.only:
            continue
        for line_number, line in enumerate(page.path.read_text(encoding="utf-8").splitlines(), 1):
            if regex.search(line):
                print(f"{page.relative_path}:{line_number}:{line}")
                count += 1
    return 0 if count else 1


if __name__ == "__main__":
    raise SystemExit(main())
