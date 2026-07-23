#!/usr/bin/env python3
"""Interactive tutorial walkthrough for Macawiki."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    from .common import ROOT
except ImportError:
    from common import ROOT


def pause():
    input("\n[Press Enter to continue]")


def run(cmd: list[str]) -> str:
    result = subprocess.run(
        [sys.executable, *cmd],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return result.stdout


def main() -> int:
    print("=" * 60)
    print("  Macawiki Tutorial")
    print("  Evidence-first MXMACA knowledge base for AI agents")
    print("=" * 60)
    print()

    # Step 1: Project overview
    print("Step 1: What is Macawiki?")
    print("-" * 40)
    print("Macawiki is a version-scoped, evidence-backed knowledge base")
    print("for MXMACA (MetaX MACA GPU) development.")
    print()
    print("Content model:")
    print("  sources/ — single-source records with metadata")
    print("  wiki/    — multi-source synthesis pages")
    print("  queries/ — auto-generated indices (never hand-edit)")
    print("  data/    — schemas, vocabularies, aliases, version claims")
    pause()

    # Step 2: Repository health
    print("\nStep 2: Check repository health")
    print("-" * 40)
    print("Running: python3 scripts/doctor.py")
    print()
    doctor_out = run(["scripts/doctor.py"])
    print(doctor_out)
    pause()

    # Step 3: Search the corpus
    print("\nStep 3: Search the corpus")
    print("-" * 40)
    print("Running: python3 scripts/query.py '算子' --compact")
    print()
    query_out = run(["scripts/query.py", "算子", "--compact"])
    print(query_out)
    print()
    print("Try OR mode for broader searches:")
    print("  python3 scripts/query.py '性能 基线 算子' --mode or --compact")
    pause()

    # Step 4: Read a page and trace evidence
    print("\nStep 4: Read a page and trace its evidence")
    print("-" * 40)
    page_id = "pattern-establish-performance-baseline"
    print(f"Running: python3 scripts/get_page.py {page_id} --follow-sources")
    print()
    page_out = run(["scripts/get_page.py", page_id, "--follow-sources"])
    # Show just the first 20 lines
    lines = page_out.split("\n")
    for line in lines[:20]:
        print(line)
    if len(lines) > 20:
        print(f"... ({len(lines) - 20} more lines)")
    pause()

    # Step 5: Grep for symbols
    print("\nStep 5: Search for symbols or error text")
    print("-" * 40)
    print("Running: python3 scripts/grep_wiki.py 'mcProfiler|roofline'")
    print()
    grep_out = run(["scripts/grep_wiki.py", "mcProfiler|roofline"])
    print(grep_out[:500])
    pause()

    # Step 6: Run full validation
    print("\nStep 6: Run full validation (make all)")
    print("-" * 40)
    print("Running: make all")
    print("(this may take a few seconds...)")
    result = subprocess.run(["make", "all"], cwd=str(ROOT), capture_output=True, text=True)
    print(result.stdout[-800:] if len(result.stdout) > 800 else result.stdout)
    if result.returncode != 0:
        print("WARNING: make all had issues (expected at v0.3 for advisory gates)")
    pause()

    # Step 7: How to contribute
    print("\nStep 7: How to contribute")
    print("-" * 40)
    print("1. Read CONTRIBUTING.md and AGENTS.md")
    print("2. Add source records to sources/ or data/source-registry.yaml")
    print("3. Write wiki pages in wiki/ with at least one source ID")
    print("4. Update data/aliases.yaml if adding new terms")
    print("5. Run: make all")
    print("6. Create a PR with format: type: description")
    print()
    print("PR checklist includes:")
    print("  - No fabricated performance numbers")
    print("  - No CUDA-as-MXMACA assumptions")
    print("  - Version-scoped claims")
    print("  - Source URLs and retrieval dates")
    pause()

    # Step 8: Agent integration
    print("\nStep 8: Use Macawiki in your AI agent")
    print("-" * 40)
    print("Claude Code:  /macawiki <your MXMACA question>")
    print("Codex:        $macawiki <your MXMACA question>")
    print()
    print("To install the skill:")
    print("  python3 scripts/install.py --agent claude --mode symlink")
    print("  python3 scripts/install.py --agent codex --mode symlink")
    pause()

    # Done
    print("\n" + "=" * 60)
    print("  Tutorial complete!")
    print()
    print("  Quick reference:")
    print("    query:     python3 scripts/query.py '<terms>' --compact")
    print("    read:      python3 scripts/get_page.py <id> --follow-sources")
    print("    grep:      python3 scripts/grep_wiki.py '<pattern>'")
    print("    validate:  make all")
    print("    quality:   make quality")
    print("    coverage:  make coverage")
    print("    recall:    make recall")
    print("    freshness: make freshness")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
