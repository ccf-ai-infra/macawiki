#!/usr/bin/env python3
"""Install Macawiki as a CodeBuddy, Codex and/or Claude Code skill."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    from .common import ROOT
except ImportError:
    from common import ROOT


AGENT_PATHS = {
    "codex": Path(".agents/skills/macawiki"),
    "claude": Path(".claude/skills/macawiki"),
    "codebuddy": Path(".codebuddy/skills/macawiki"),
}
TOP_LEVEL_EXCLUDED = {
    ".git", ".DS_Store", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".macawiki-v0.3-build", ".agents", ".claude", ".codebuddy", "tests",
    "README.md", "CLAUDE.md", "Makefile", "LICENSE", "VERSION",
}

# docs/ mixes contributor planning with files the skill contract tells agents
# to read. Ship only the ones an installed skill can actually resolve;
# otherwise SKILL.md/AGENTS.md point at a file the copy install never made.
DOCS_DIR_NAME = "docs"
SHIPPED_DOCS = {"hardware-validation.md", "source-and-license-policy.md"}


def copy_ignore(path: str, names: list[str]) -> set[str]:
    """Keep the installed skill useful without copying contributor-only files."""
    ignored = {name for name in names if name in {".git", ".DS_Store", "__pycache__", ".pytest_cache", ".mypy_cache", "results"}}
    resolved = Path(path).resolve()
    if resolved == ROOT.resolve():
        ignored.update(name for name in names if name in TOP_LEVEL_EXCLUDED)
    elif resolved == (ROOT / DOCS_DIR_NAME).resolve():
        ignored.update(name for name in names
                       if name not in SHIPPED_DOCS and Path(path, name).is_file())
    return ignored


def destinations(agent: str, scope_root: Path) -> list[tuple[str, Path]]:
    names = list(AGENT_PATHS) if agent == "both" else [agent]
    return [(name, scope_root / AGENT_PATHS[name]) for name in names]


def _remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def install(source: Path, destination: Path, mode: str, replace: bool, dry_run: bool) -> str:
    source = source.resolve()
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() and destination.resolve() == source and mode == "symlink":
            return f"unchanged {destination} -> {source}"
        if not replace:
            raise FileExistsError(f"target exists (use --replace after review): {destination}")
    action = f"{mode} {source} -> {destination}"
    if dry_run:
        return f"would {action}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        _remove_existing(destination)
    if mode == "symlink":
        destination.symlink_to(source, target_is_directory=True)
    else:
        shutil.copytree(source, destination, ignore=copy_ignore)
    return action


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=["codex", "claude", "codebuddy", "both"], default="both")
    parser.add_argument("--scope", choices=["user", "project"], default="user")
    parser.add_argument("--mode", choices=["symlink", "copy"], default="symlink")
    parser.add_argument("--target-root", type=Path, help="override the user home root (mainly for tests)")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--replace", action="store_true", help="replace one existing macawiki target")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    if not (source / "SKILL.md").is_file():
        parser.error(f"source has no SKILL.md: {source}")
    scope_root = (args.target_root or Path.home()) if args.scope == "user" else args.project_dir.resolve()
    if args.scope == "project" and scope_root == source:
        parser.error("Macawiki already contains repository adapters; project install is unnecessary")

    try:
        for name, destination in destinations(args.agent, scope_root):
            print(f"[{name}] {install(source, destination, args.mode, args.replace, args.dry_run)}")
    except (FileExistsError, OSError) as exc:
        print(f"install failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
