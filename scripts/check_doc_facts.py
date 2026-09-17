#!/usr/bin/env python3
"""Check prose numbers in docs/ against live-computed corpus facts.

Macawiki's docs used to hardcode corpus counts ("14 pages", "38 tests",
"9 cases"). Every one of those drifted the moment the corpus grew, and a
reader had no way to tell a stale number from a current one. This linter
makes each such number a *claim* registered in `docs/facts.json` and
re-derives the truth from the repository every time it runs, so a stale
number fails loudly instead of silently misinforming.

The sidecar is the only place a claim is registered. The docs themselves
stay plain prose -- no HTML comments, no placeholders -- so they remain
readable in any language and never need a rendering step.

A claim looks like::

    {"id": "charter-pages", "doc": "docs/charter.md",
     "pattern": "(\\d+) pages", "expect": "pages_total"}

The linter finds the first match in the document, reads the captured
integer, and compares it to ``facts[expect]``. A pattern may hold several
capturing groups; ``group`` (default 1) selects which one carries the
number, so a slash form like "17/17 passed" can register two claims -- one
per digit -- against the same sentence. Two failure modes are
distinguished because they need different fixes:

* ``drift`` -- the anchor is found, the number is wrong. Edit the doc.
* ``missing-anchor`` -- the pattern no longer matches anything at all,
  which usually means someone reworded the sentence. Fix the pattern,
  because a claim that cannot be located is not being checked at all.

Existence claims (``expect: script_exists`` etc.) take a ``path`` instead
of a ``pattern`` and assert that the referenced thing is real.

The linter also scans every doc for ``scripts/<name>`` references and
checks each one exists, so a doc can never point at a script that was
never written -- the failure that motivated this tool.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:
    from .common import ROOT, discover_pages, load_data
except ImportError:  # pragma: no cover
    from common import ROOT, discover_pages, load_data


TESTS_DIR = ROOT / "tests"
SCRIPTS_DIR = ROOT / "scripts"
# Optional env overrides follow the repo's existing convention
# (MACAWIKI_ROOT / MACAWIKI_SIGNAL_DIR / MACAWIKI_ITERATE_STATE): they let a
# test point the linter at a scratch sidecar or scratch docs without touching
# the real files.
FACTS_FILE = Path(os.environ.get("MACAWIKI_DOC_FACTS", ROOT / "docs" / "facts.json"))
DOCS_DIR = Path(os.environ.get("MACAWIKI_DOCS_DIR", ROOT / "docs"))

# Facts that describe something the repository claims to contain. Every
# one of these is recomputed from scratch on each run; none is cached.
_FACT_FUNCTIONS: dict[str, Callable[[], Any]] = {}


def _fact(name: str) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
    def decorate(func: Callable[[], Any]) -> Callable[[], Any]:
        _FACT_FUNCTIONS[name] = func
        return func

    return decorate


@_fact("sources")
def _sources() -> int:
    return sum(1 for p in discover_pages() if p.relative_path.parts[0] == "sources")


@_fact("wiki")
def _wiki() -> int:
    return sum(1 for p in discover_pages() if p.relative_path.parts[0] == "wiki")


@_fact("pages_total")
def _pages_total() -> int:
    return len(discover_pages())


@_fact("test_count")
def _test_count() -> int:
    """Count top-level test functions across tests/, the way unittest collects them.

    Mirrors `make test` without running it: the collection is the number
    of `def test_` definitions, so a doc quoting a test count can be
    checked in well under a second instead of ~380.
    """
    total = 0
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        total += len(re.findall(r"(?m)^\s*def test_", text))
    return total


@_fact("agent_cases_total")
def _agent_cases_total() -> int:
    return len(_agent_cases())


@_fact("agent_cases_positive")
def _agent_cases_positive() -> int:
    return sum(1 for c in _agent_cases() if "negative" not in str(c.get("id", "")).lower())


@_fact("agent_cases_negative")
def _agent_cases_negative() -> int:
    return sum(1 for c in _agent_cases() if "negative" in str(c.get("id", "")).lower())


def _agent_cases() -> list[dict[str, Any]]:
    data = load_data(ROOT / "evals" / "agent-value-cases.yaml")
    if isinstance(data, dict):
        cases = data.get("cases", [])
    else:
        cases = data
    return [c for c in cases if isinstance(c, dict)]


@_fact("gold_questions")
def _gold_questions() -> int:
    data = load_data(ROOT / "evals" / "gold-questions.yaml")
    questions = data.get("questions", []) if isinstance(data, dict) else []
    return len(questions)


@_fact("benchmark_operators")
def _benchmark_operators() -> int:
    data = load_data(ROOT / "benchmarks" / "operator_cases.yaml")
    operators = data.get("operators", []) if isinstance(data, dict) else []
    return len(operators)


@dataclass(frozen=True)
class Problem:
    claim_id: str
    kind: str  # "drift" | "missing-anchor" | "unknown-fact" | "missing-doc" | "bad-claim"
    detail: str


def collect_facts() -> dict[str, Any]:
    """Re-derive every registered fact from the repository right now."""
    return {name: func() for name, func in _FACT_FUNCTIONS.items()}


def _path_exists(relative: str) -> bool:
    return (ROOT / relative).exists()


def _git_tag_exists(name: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "tag", "-l", name],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        # No git available (or not a repo): cannot verify, so do not fail.
        return True
    return result.returncode == 0 and bool(result.stdout.strip())


# Existence facts assert that something the docs point at is real. Each
# returns True when the thing exists, so a doc referencing a script that
# was never written (or a tag never cut) fails the check.
_EXISTENCE_CHECKS: dict[str, Callable[[str], bool]] = {
    "script_exists": lambda name: _path_exists(f"scripts/{name}"),
    "dir_exists": _path_exists,
    "file_exists": _path_exists,
    "tag_exists": _git_tag_exists,
}


def check(claims: list[dict[str, Any]] | None = None, facts: dict[str, Any] | None = None) -> list[Problem]:
    """Compare every registered claim to the live facts.

    Returns an empty list when the docs agree with the repository.
    """
    facts = facts if facts is not None else collect_facts()
    claims = claims if claims is not None else load_claims()

    problems: list[Problem] = []
    # Dangling script references are found by scanning the docs, not by
    # registration, so this check runs even when the claim list is empty.
    problems.extend(find_dangling_script_refs())
    doc_cache: dict[str, str] = {}

    for claim in claims:
        claim_id = str(claim.get("id", "<no id>"))
        expect = claim.get("expect")

        if expect in _EXISTENCE_CHECKS:
            target = claim.get("path")
            if not isinstance(target, str) or not target:
                problems.append(Problem(claim_id, "bad-claim", "existence claim needs a string 'path'"))
                continue
            if not _EXISTENCE_CHECKS[expect](target):
                problems.append(
                    Problem(claim_id, "drift", f"{expect}('{target}') is false: referenced thing is missing")
                )
            continue

        if expect not in facts:
            problems.append(Problem(claim_id, "unknown-fact", f"no fact named '{expect}' is computed"))
            continue

        doc_path = claim.get("doc")
        if not isinstance(doc_path, str):
            problems.append(Problem(claim_id, "bad-claim", "claim needs a string 'doc'"))
            continue

        abs_doc = ROOT / doc_path
        if not abs_doc.is_file():
            problems.append(Problem(claim_id, "missing-doc", f"{doc_path} does not exist"))
            continue
        if doc_path not in doc_cache:
            doc_cache[doc_path] = abs_doc.read_text(encoding="utf-8")

        pattern = claim.get("pattern")
        if not isinstance(pattern, str):
            problems.append(Problem(claim_id, "bad-claim", "claim needs a string 'pattern' with one capture group"))
            continue

        match = re.search(pattern, doc_cache[doc_path])
        if match is None:
            problems.append(
                Problem(claim_id, "missing-anchor", f"pattern does not match {doc_path} anymore: {pattern!r}")
            )
            continue

        group = claim.get("group", 1)
        if not isinstance(group, int) or not (1 <= group <= len(match.groups())):
            problems.append(
                Problem(claim_id, "bad-claim", f"group must be 1..{len(match.groups())}, got {group!r}")
            )
            continue

        try:
            stated = int(match.group(group))
        except (TypeError, ValueError):
            problems.append(
                Problem(claim_id, "bad-claim", f"captured value {match.group(group)!r} is not an integer")
            )
            continue

        actual = facts[expect]
        if not isinstance(actual, int):
            problems.append(Problem(claim_id, "bad-claim", f"fact '{expect}' is not an integer"))
            continue

        if stated != actual:
            problems.append(
                Problem(claim_id, "drift", f"{doc_path} says {stated}, repository has {actual}")
            )

    return problems


def load_claims() -> list[dict[str, Any]]:
    data = load_data(FACTS_FILE)
    claims = data.get("claims", []) if isinstance(data, dict) else []
    return [c for c in claims if isinstance(c, dict)]


_SCRIPT_REF_RE = re.compile(r"scripts/([A-Za-z0-9_\-]+\.(?:py|sh))")


def find_dangling_script_refs() -> list[Problem]:
    """Scan every doc for `scripts/<name>` and check it exists.

    This is how the docs came to reference run_claude_ab_eval.py and
    score_claude_eval.py, neither of which has ever existed: a paragraph
    described a planned tool, the plan was abandoned, and the reference
    stayed. Checking the set the docs actually name keeps that from
    recurring without anyone having to remember to register a claim.
    """
    problems: list[Problem] = []
    if not DOCS_DIR.is_dir():
        return problems
    candidates = sorted(DOCS_DIR.glob("*.md"))
    if DOCS_DIR != ROOT / "docs":
        # A scratch docs dir does not contain README; only scan what is there.
        readme = DOCS_DIR / "README.md"
    else:
        readme = ROOT / "README.md"
    if readme.is_file():
        candidates.append(readme)
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        for name in sorted(set(_SCRIPT_REF_RE.findall(text))):
            if not (SCRIPTS_DIR / name).is_file():
                try:
                    label = path.relative_to(ROOT)
                except ValueError:
                    label = path
                problems.append(
                    Problem(
                        claim_id=f"doc-script-ref:{label}",
                        kind="dangling-ref",
                        detail=f"references scripts/{name}, which does not exist",
                    )
                )
    return problems


def _format(problems: list[Problem]) -> str:
    lines = [f"doc-facts: {len(problems)} problem(s) found", ""]
    for problem in problems:
        lines.append(f"  [{problem.kind}] {problem.claim_id}")
        lines.append(f"      {problem.detail}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="print nothing on success")
    args = parser.parse_args(argv)

    problems = check()
    if not problems:
        if not args.quiet:
            print("doc-facts: all registered claims match the repository")
        return 0

    print(_format(problems))
    print("")
    print("Drift is fixed by editing the doc to the reported number, not by")
    print("editing docs/facts.json. If the sentence was reworded, update the")
    print("pattern so the claim is locatable again.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
