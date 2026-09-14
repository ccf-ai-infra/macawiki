#!/usr/bin/env python3
"""State-consistency gate for the Macawiki iteration loop.

Refuses to start a new cycle when evals/claude/iteration-state.json has
drifted out of sync with the repository. The loop is resumable only while
these structural invariants hold:

    next_cycle_id == max(cycle_id) + 1
    champion.commit exists in this repo's history

A champion that is a valid ancestor of HEAD but lags it is NOT blocking:
the normal loop flow is to commit work, then record it as a cycle and
re-point the champion, so HEAD legitimately outruns the last recorded
champion whenever work has happened since the last cycle. What would be
unresumable is a champion that never existed here, or a cycle-id that
would overwrite an existing report.

Unaggregated signal logs are likewise reported but do not block: the signal
dir is gitignored scratch space that can hold test noise, and deciding
whether to merge it is a maintainer judgement (see `make signals-merge`).

Usage:
    python3 scripts/iterate_precheck.py            # exit 0 = safe to cycle
    python3 scripts/iterate_precheck.py --json     # machine-readable
    python3 scripts/iterate_precheck.py --fix      # sync champion to HEAD
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from .common import ROOT, load_data
except ImportError:
    from common import ROOT, load_data

STATE_PATH = ROOT / "evals" / "claude" / "iteration-state.json"
SIGNAL_DIR = Path(__import__("os").environ.get("MACAWIKI_SIGNAL_DIR", ROOT / "evals" / "signals"))

# Adapters stay in lockstep; a diverging copy means one agent sees a
# different iteration protocol than the other.
ITERATE_COPIES = (
    ROOT / ".claude" / "skills" / "macawiki-iterate" / "SKILL.md",
    ROOT / ".agents" / "skills" / "macawiki-iterate" / "SKILL.md",
)


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git"] + args, cwd=str(ROOT), capture_output=True, text=True, check=False)


def _head() -> str | None:
    r = _git(["rev-parse", "HEAD"])
    return r.stdout.strip() if r.returncode == 0 else None


def _sha_exists(sha: str) -> bool:
    return bool(sha) and _git(["cat-file", "-e", sha]).returncode == 0


def _unaggregated_signals() -> dict[str, int]:
    """Count live records per signal log (archive/ is already processed)."""
    counts: dict[str, int] = {}
    if not SIGNAL_DIR.exists():
        return counts
    for path in sorted(SIGNAL_DIR.glob("*.jsonl")):
        try:
            n = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        except OSError:
            continue
        if n:
            counts[path.name] = n
    return counts


def check() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    def add(level: str, code: str, msg: str, fix: str | None = None) -> None:
        findings.append({"level": level, "code": code, "message": msg, "remedy": fix})

    head = _head()
    if head is None:
        add("critical", "no-git-head", "git repository HEAD could not be resolved", None)
        return {"ok": False, "head": None, "findings": findings}

    if not STATE_PATH.is_file():
        add("critical", "no-state", f"state file missing: {STATE_PATH.relative_to(ROOT)}",
            "create it from the template in docs/iteration-plan.md")
        return {"ok": False, "head": head, "findings": findings}

    try:
        state = load_data(STATE_PATH)
    except (OSError, ValueError) as exc:
        add("critical", "state-unparsable", f"state file is not valid JSON/YAML: {exc}", None)
        return {"ok": False, "head": head, "findings": findings}

    cycles = state.get("cycles", [])
    cycle_ids = [c.get("cycle_id") for c in cycles if isinstance(c.get("cycle_id"), int)]
    next_id = state.get("next_cycle_id")

    if not cycle_ids:
        add("critical", "no-cycles", "state records no completed cycles", None)
    elif next_id != max(cycle_ids) + 1:
        add("critical", "cycle-id-collision",
            f"next_cycle_id={next_id} but cycles 1..{max(cycle_ids)} exist; "
            f"the next cycle report would collide with an existing one",
            f"set next_cycle_id to {max(cycle_ids) + 1}")

    champion = state.get("champion") or {}
    champ_sha = champion.get("commit")

    if not champ_sha:
        add("critical", "no-champion", "champion.commit is not set",
            "set it to the current validated HEAD")
    elif not _sha_exists(champ_sha):
        add("critical", "champion-foreign-sha",
            f"champion.commit {champ_sha[:12]} does not exist in this repository's "
            "history (a SHA from another fork/branch makes the loop state unverifiable)",
            "set champion.commit to the real HEAD, then re-run this check")
    elif champ_sha != head:
        # Advisory: the normal loop flow commits work first and records it as
        # a cycle afterwards, so HEAD legitimately outruns the recorded
        # champion between cycles. Only the maintainer can tell 'work pending
        # a cycle write-up' from 'a cycle was never closed out'; demanding a
        # block here would make every legitimate mid-cycle commit a failure.
        behind = _git(["rev-list", "--count", f"{champ_sha}..{head}"]).stdout.strip()
        add("warn", "champion-lags-head",
            f"champion.commit {champ_sha[:12]} is {behind or 'some'} commit(s) behind "
            f"HEAD {head[:12]}; work exists that no cycle records yet",
            "close it out: write the cycle report and run "
            "python3 scripts/iterate_precheck.py --fix")

    signals = _unaggregated_signals()
    if signals:
        total = sum(signals.values())
        # Advisory, not blocking: merging is an explicit maintainer action,
        # and the signal dir is gitignored scratch space — it can hold stale
        # test noise that must NOT be merged into the backlog. Structural
        # drift (ids, champion SHA) is what blocks a cycle; signal cadence
        # is a judgement call for the maintainer running `make signals-merge`.
        add("warn", "signals-unaggregated",
            f"{total} unaggregated signal record(s) in {', '.join(signals)}; "
            "the backlog does not reflect current usage telemetry — verify "
            "these are real usage, not test noise, before merging",
            "run: make signals-merge")

    # Cycles without a report cannot be audited — a rejected change must
    # still leave a trail, or the loop repeats its own mistakes.
    unreported = [c.get("cycle_id") for c in cycles
                  if isinstance(c.get("cycle_id"), int) and not c.get("report")]
    if unreported:
        add("warn", "cycles-without-report",
            f"cycle(s) {unreported} have no report path; decisions are not traceable",
            "write evals/claude/reports/cycle-NNN.md for each")

    if all(p.is_file() for p in ITERATE_COPIES):
        bodies = [p.read_text(encoding="utf-8") for p in ITERATE_COPIES]
        if len(set(bodies)) != 1:
            add("warn", "iterate-copies-diverge",
                "the macawiki-iterate SKILL.md copies under .claude/ and .agents/ differ",
                "copy one over the other; they must stay identical")

    levels = {f["level"] for f in findings}
    ok = not (levels & {"critical", "error"})
    return {"ok": ok, "head": head, "findings": findings}


def fix() -> dict[str, Any]:
    """Sync champion.commit to HEAD, after the intervening work is recorded.

    Refuses only when the recorded SHA does not exist in this repo, since that
    state is unverifiable rather than merely stale.
    """
    head = _head()
    if head is None:
        return {"fixed": False, "reason": "git HEAD could not be resolved"}

    state = load_data(STATE_PATH)
    champion = state.get("champion") or {}
    current = champion.get("commit")

    if current == head:
        return {"fixed": False, "reason": f"champion already at HEAD {head[:12]}"}
    if current and not _sha_exists(current):
        return {"fixed": False,
                "reason": f"champion {current[:12]} does not exist in this repo; "
                          "resolve the foreign SHA by hand before fixing"}

    champion["commit"] = head
    note = champion.get("note")
    champion["note"] = (f"Re-pointed by iterate_precheck --fix; now tracks HEAD "
                        f"{head[:12]}. Previous note: {note}")
    state["champion"] = champion

    if isinstance(state.get("next_cycle_id"), int) and state.get("cycles"):
        ids = [c.get("cycle_id") for c in state["cycles"] if isinstance(c.get("cycle_id"), int)]
        if ids:
            state["next_cycle_id"] = max(ids) + 1

    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"fixed": True, "champion": head}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument("--fix", action="store_true",
                        help="re-point a foreign/invalid champion.commit at HEAD")
    args = parser.parse_args()

    if args.fix:
        result = fix()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"iterate_precheck --fix: {json.dumps(result, ensure_ascii=False)}")
        return 0 if result.get("fixed") else 1

    report = check()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        head = report["head"]
        print("=== Iteration precheck ===")
        print(f"HEAD: {head[:12] if head else 'unresolved'}")
        if not report["findings"]:
            print("OK — state is self-consistent; safe to start a cycle.")
        else:
            for f in report["findings"]:
                tag = {"critical": "CRITICAL", "error": "ERROR", "warn": "WARN"}[f["level"]]
                print(f"  [{tag}] {f['code']}: {f['message']}")
                if f.get("remedy"):
                    print(f"           remedy: {f['remedy']}")
            print("")
            if report["ok"]:
                print("Safe to start a cycle — warnings above are advisory.")
            else:
                print("Not safe to start a cycle — resolve critical/error findings first.")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
