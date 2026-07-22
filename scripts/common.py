#!/usr/bin/env python3
"""Shared helpers for Macawiki's dependency-free tools."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent.parent
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


@dataclass(frozen=True)
class Page:
    path: Path
    metadata: dict[str, Any]
    body: str

    @property
    def relative_path(self) -> Path:
        return self.path.relative_to(ROOT)


def load_data(path: Path) -> Any:
    """Load JSON-compatible YAML used by Macawiki v0.1."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing data file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON-compatible YAML in {path.relative_to(ROOT)}: {exc}") from exc


def read_page(path: Path) -> Page:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{path.relative_to(ROOT)}: missing JSON-compatible frontmatter")
    try:
        metadata = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.relative_to(ROOT)}: invalid frontmatter: {exc}") from exc
    if not isinstance(metadata, dict):
        raise ValueError(f"{path.relative_to(ROOT)}: frontmatter must be an object")
    return Page(path=path, metadata=metadata, body=text[match.end() :])


def discover_pages() -> list[Page]:
    pages: list[Page] = []
    for directory in (ROOT / "sources", ROOT / "wiki"):
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.md")):
            pages.append(read_page(path))
    return pages


def page_map(pages: Iterable[Page] | None = None) -> dict[str, Page]:
    result: dict[str, Page] = {}
    for page in pages if pages is not None else discover_pages():
        page_id = page.metadata.get("id")
        if isinstance(page_id, str):
            result[page_id] = page
    return result


def normalize_alias(value: str, aliases: dict[str, list[str]]) -> str:
    candidate = value.casefold()
    for canonical, variants in aliases.items():
        if candidate == canonical.casefold() or any(candidate == variant.casefold() for variant in variants):
            return canonical
    return value


def searchable_text(page: Page) -> str:
    metadata = page.metadata
    values = [
        metadata.get("id", ""),
        metadata.get("title", ""),
        metadata.get("summary", ""),
        page.body,
    ]
    for field in ("aliases", "tags", "hardware", "mxmaca_versions", "components", "symptoms"):
        value = metadata.get(field, [])
        if isinstance(value, list):
            values.extend(str(item) for item in value)
    return "\n".join(str(value) for value in values).casefold()
