#!/usr/bin/env python3
"""Validate Macawiki pages, vocabularies, references, candidates, and artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from common import ROOT, Page, discover_pages, load_data


ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_FIELDS = ("verified_at", "retrieved_at")
VOCAB_FIELDS = {
    "status": "status",
    "languages": "languages",
    "hardware": "hardware",
    "components": "components",
    "tags": "topic_tags",
    "confidence": "confidence",
    "reproducibility": "reproducibility",
    "source_category": "source_category",
    "license_status": "license_status",
}


def _check_required(page: Page, schema: dict[str, Any], errors: list[str]) -> None:
    metadata = page.metadata
    required = schema["common_required"] + schema["page_types"][metadata.get("type", "")]["required"]
    for field in required:
        if field not in metadata or metadata[field] is None:
            errors.append(f"{page.relative_path}: missing required field '{field}'")


def _check_lists(page: Page, schema: dict[str, Any], errors: list[str]) -> None:
    metadata = page.metadata
    for field in schema["list_fields"]:
        if field not in metadata:
            continue
        value = metadata[field]
        if not isinstance(value, list):
            errors.append(f"{page.relative_path}: field '{field}' must be a list")
            continue
        serial = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value]
        if len(serial) != len(set(serial)):
            errors.append(f"{page.relative_path}: field '{field}' contains duplicate values")


def _check_vocabulary(page: Page, vocab: dict[str, list[str]], errors: list[str]) -> None:
    metadata = page.metadata
    for field, vocab_key in VOCAB_FIELDS.items():
        if field not in metadata:
            continue
        value = metadata[field]
        values = value if isinstance(value, list) else [value]
        allowed = set(vocab[vocab_key])
        for item in values:
            if item not in allowed:
                errors.append(f"{page.relative_path}: '{item}' is not valid for '{field}'")


def _check_dates(page: Page, errors: list[str]) -> None:
    for field in DATE_FIELDS:
        value = page.metadata.get(field)
        if value is None:
            continue
        try:
            date.fromisoformat(value)
        except (TypeError, ValueError):
            errors.append(f"{page.relative_path}: field '{field}' must be YYYY-MM-DD")


def _check_links(page: Page, errors: list[str]) -> None:
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", page.body):
        if target.startswith(("http://", "https://", "#")):
            continue
        local_target = target.split("#", 1)[0]
        if local_target and not (page.path.parent / local_target).resolve().exists():
            errors.append(f"{page.relative_path}: broken local link '{target}'")


def _validate_pages() -> tuple[list[Page], list[str]]:
    schema = load_data(ROOT / "data" / "schemas.yaml")
    vocab = load_data(ROOT / "data" / "tags.yaml")
    errors: list[str] = []
    pages: list[Page] = []
    try:
        pages = discover_pages()
    except ValueError as exc:
        return [], [str(exc)]

    ids: dict[str, Path] = {}
    source_ids: set[str] = set()
    all_ids: set[str] = set()
    page_types = schema["page_types"]

    for page in pages:
        metadata = page.metadata
        page_id = metadata.get("id")
        page_type = metadata.get("type")
        if not isinstance(page_id, str) or not ID_RE.fullmatch(page_id):
            errors.append(f"{page.relative_path}: invalid or missing id")
        elif page_id in ids:
            errors.append(f"{page.relative_path}: duplicate id '{page_id}' also in {ids[page_id]}")
        else:
            ids[page_id] = page.relative_path
            all_ids.add(page_id)
        if page_type not in page_types:
            errors.append(f"{page.relative_path}: unknown page type '{page_type}'")
            continue
        expected_scope = page_types[page_type]["scope"]
        actual_scope = page.relative_path.parts[0]
        if actual_scope != ("sources" if expected_scope == "source" else "wiki"):
            errors.append(f"{page.relative_path}: type '{page_type}' belongs in {expected_scope} scope")
        if expected_scope == "source" and isinstance(page_id, str):
            source_ids.add(page_id)
        _check_required(page, schema, errors)
        _check_lists(page, schema, errors)
        _check_vocabulary(page, vocab, errors)
        _check_dates(page, errors)
        _check_links(page, errors)

    claim_ids = {item["id"] for item in load_data(ROOT / "data" / "version-claims.yaml")["claims"]}
    for page in pages:
        metadata = page.metadata
        page_type = metadata.get("type", "")
        for source_id in metadata.get("sources", []):
            if source_id not in source_ids:
                errors.append(f"{page.relative_path}: unknown source id '{source_id}'")
        if page_type.startswith("wiki-") and not metadata.get("sources"):
            errors.append(f"{page.relative_path}: wiki page must cite at least one source")
        for field in ("related", "prerequisites"):
            for target in metadata.get(field, []):
                if target not in all_ids:
                    errors.append(f"{page.relative_path}: unknown {field} id '{target}'")
        claim = metadata.get("version_sensitive")
        if claim and claim not in claim_ids:
            errors.append(f"{page.relative_path}: unknown version claim '{claim}'")
    return pages, errors


def _validate_registry(source_ids: set[str]) -> list[str]:
    errors: list[str] = []
    registry = load_data(ROOT / "data" / "source-registry.yaml")
    seen: set[str] = set()
    for row in registry.get("sources", []):
        source_id = row.get("id")
        if source_id in seen:
            errors.append(f"data/source-registry.yaml: duplicate id '{source_id}'")
        seen.add(source_id)
        if source_id not in source_ids:
            errors.append(f"data/source-registry.yaml: id '{source_id}' has no source page")
        for field in ("name", "url", "access", "license_status", "capture_policy"):
            if not row.get(field):
                errors.append(f"data/source-registry.yaml: '{source_id}' missing '{field}'")
    if seen != source_ids:
        missing = sorted(source_ids - seen)
        errors.append(f"data/source-registry.yaml: missing source IDs {missing}")
    return errors


def _validate_candidates() -> list[str]:
    errors: list[str] = []
    allowed_decisions = {"include", "defer", "exclude"}
    for path in sorted((ROOT / "candidates").glob("*.yaml")):
        data = load_data(path)
        seen: set[str] = set()
        for row in data.get("candidates", []):
            row_id = row.get("id")
            if row_id in seen:
                errors.append(f"{path.relative_to(ROOT)}: duplicate candidate '{row_id}'")
            seen.add(row_id)
            if row.get("decision") not in allowed_decisions:
                errors.append(f"{path.relative_to(ROOT)}: invalid decision for '{row_id}'")
            for field in ("url", "reason"):
                if not row.get(field):
                    errors.append(f"{path.relative_to(ROOT)}: '{row_id}' missing '{field}'")
    return errors


def _validate_artifacts() -> list[str]:
    errors: list[str] = []
    artifact_root = ROOT / "artifacts"
    if not artifact_root.exists():
        return errors
    manifests = sorted(artifact_root.rglob("PROVENANCE.yaml"))
    for manifest in manifests:
        data = load_data(manifest)
        for field in ("origin_url", "license", "retrieved_at", "asset_mode", "files"):
            if field not in data:
                errors.append(f"{manifest.relative_to(ROOT)}: missing '{field}'")
        bundle_root = manifest.parent.resolve()
        for entry in data.get("files", []):
            relative = entry.get("local_path", "")
            path = (bundle_root / relative).resolve()
            if bundle_root != path and bundle_root not in path.parents:
                errors.append(f"{manifest.relative_to(ROOT)}: path escapes bundle '{relative}'")
                continue
            if not path.is_file():
                errors.append(f"{manifest.relative_to(ROOT)}: missing file '{relative}'")
                continue
            expected = entry.get("sha256")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if expected != actual:
                errors.append(f"{manifest.relative_to(ROOT)}: sha256 mismatch for '{relative}'")
    return errors


def validate() -> tuple[list[Page], list[str]]:
    try:
        pages, errors = _validate_pages()
        source_ids = {page.metadata["id"] for page in pages if page.relative_path.parts[0] == "sources"}
        errors.extend(_validate_registry(source_ids))
        errors.extend(_validate_candidates())
        errors.extend(_validate_artifacts())
        return pages, errors
    except (ValueError, KeyError, TypeError) as exc:
        return [], [str(exc)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit a machine-readable report")
    args = parser.parse_args()
    pages, errors = validate()
    if args.json:
        print(json.dumps({"pages": len(pages), "errors": errors}, ensure_ascii=False, indent=2))
    else:
        print(f"Validated {len(pages)} pages.")
        if errors:
            print(f"Found {len(errors)} error(s):")
            for error in errors:
                print(f"  ERROR: {error}")
        else:
            print("All checks passed.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
