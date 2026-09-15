#!/usr/bin/env python3
"""Orchestrate one Macawiki iteration cycle — a thin wrapper, not a reimplementation.

The loop itself lives in `.claude/skills/macawiki-iterate/SKILL.md` as a
13-step algorithm meant to be *executed by an agent*, with the judgement
steps (forming a hypothesis, deciding accept/reject) done by it. This script
does not try to replace that judgement. It enforces the steps that are
mechanical but easy to skip, and refuses to let a cycle close without them:

    --begin   gate: state self-consistent (iterate_precheck)
              record the cycle as IN_PROGRESS with its hypothesis
              record measured BEFORE metrics

    --finish  measure AFTER metrics, diff against BEFORE, write the report,
              advance next_cycle_id. Required even when the cycle is
              rejected — a rejected change with no report is how the loop
              repeats its own mistakes (cycles 7-10 left `report: null`).

    --abandon for a cycle that never produced a change cluster. Records the
              cycle as abandoned with its reason, so an abandoned attempt
              stays visible in the trend rather than vanishing.

What this deliberately does NOT do:

    * It does not pick the backlog item or write the hypothesis. Choosing
      what to test and stating it falsifiably is the whole point of the
      agent step; auto-generating it would make the loop measurably worse.
    * It does not apply changes or run `make all`. Those belong to the
      agent's execution step (and to `make self-improve` for auto-fixable
      items). This script only measures and records.
    * It does not push, branch, or commit. `scripts/prepare_pr.sh` handles
      branching; committing stays with the maintainer.

A cycle started with --begin MUST be closed with --finish or --abandon. A
half-open cycle blocks the next one: --begin refuses while another is open,
and iterate_precheck will flag it as a cycle without a report.

Usage:
    python3 scripts/iterate_cycle.py --begin  --hypothesis "..." --workstream corpus
    ... agent executes the change cluster and runs make all ...
    python3 scripts/iterate_cycle.py --finish --accept   --reason "..."
    python3 scripts/iterate_cycle.py --finish --reject   --reason "..."
    python3 scripts/iterate_cycle.py --abandon           --reason "..."
    python3 scripts/iterate_cycle.py --status
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .common import ROOT, load_data
    from .iterate_metrics import (
        METRIC_KEYS, METRIC_PHRASES, collect_snapshot, fmt_delta, fmt_value,
        snapshot_diff,
    )
except ImportError:
    from common import ROOT, load_data
    from iterate_metrics import (
        METRIC_KEYS, METRIC_PHRASES, collect_snapshot, fmt_delta, fmt_value,
        snapshot_diff,
    )


# Overridable so a scratch checkout (or a test) can run a full cycle against
# throwaway state without touching the real loop history. Same convention as
# MACAWIKI_SIGNAL_DIR. Unset = the repository defaults.
STATE_PATH = Path(os.environ.get(
    "MACAWIKI_ITERATE_STATE",
    str(ROOT / "evals" / "claude" / "iteration-state.json")))
REPORT_DIR = Path(os.environ.get(
    "MACAWIKI_ITERATE_REPORTS",
    str(ROOT / "evals" / "claude" / "reports")))
IN_PROGRESS = "in_progress"
DONE_STATES = ("accepted", "rejected", "abandoned")

# A hypothesis shorter than this almost certainly states an activity
# ("improve docs") rather than a testable claim. Not a hard rule, just a
# floor below which a human should take another pass at it.
_MIN_HYPOTHESIS_LEN = 60

# A claim of a specific target ("coverage to 20") is checked against this
# bound so a hypothesis can never silently demand the impossible.
_COMPONENT_TOTAL_MAX = 64

# How far after a metric phrase its number may appear. Tight on purpose: bare
# phrases like "unspecified" and "draft" also name tags and statuses, and a
# wide window lets them latch onto a number belonging to a different metric a
# full sentence away. "coverage to 18" fits; "the 'unspecified' bucket ...
# coverage to 18" does not.
_TARGET_WINDOW = 40


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_state() -> dict[str, Any]:
    try:
        return load_data(STATE_PATH)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"cannot read state: {exc}")


def _write_state(state: dict[str, Any]) -> None:
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _repo_path(path: Path) -> str:
    """Record a path relative to the repo root, or absolute if outside it.

    Only matters for the MACAWIKI_ITERATE_* overrides, which can point at a
    scratch dir; for the repo defaults this is always a plain relative path.
    Readers resolve it via `ROOT / path`, which pathlib handles either way.
    """
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _open_cycle(state: dict[str, Any]) -> dict[str, Any] | None:
    """The single cycle that is IN_PROGRESS, if any."""
    for c in state.get("cycles", []):
        if c.get("status") == IN_PROGRESS:
            return c
    return None


def _metrics_tail(state: dict[str, Any]) -> dict[str, Any]:
    """Metrics recorded by the most recent *closed* cycle, as a baseline."""
    closed = [c for c in state.get("cycles", [])
              if c.get("status") in DONE_STATES and c.get("metrics_after")]
    if not closed:
        return {}
    return closed[-1].get("metrics_after") or {}


def _hypothesis_is_falsifiable(text: str) -> list[str]:
    """Reject a hypothesis that names no metric and no failure mode.

    'Add mcBLAS docs' is an intention. 'Adding measured /opt/maca component
    sources raises component coverage to >=15' is a hypothesis, because it
    can be wrong. Both checks are about the *shape* of the claim, never its
    content: we never decide whether a hypothesis is true.
    """
    problems: list[str] = []
    stripped = text.strip()
    if len(stripped) < _MIN_HYPOTHESIS_LEN:
        problems.append(
            f"hypothesis is only {len(stripped)} chars — too short to state both "
            "a claim and how it could be wrong; expected a testable prediction, "
            "not an intention")
    named = [k for k, phrases in METRIC_PHRASES.items()
             if any(p.lower() in stripped.lower() for p in phrases)]
    if not named:
        problems.append(
            "hypothesis names no measurable metric (component coverage, "
            "version-claims, pages, draft/unspecified ratio, license, recall, "
            "tests) — there is nothing to measure it against")
    # A falsification path is signalled by a failure-mode verb; without one,
    # the claim is unfalsifiable no matter how precise its target is.
    lowered = stripped.lower()
    if not any(v in lowered for v in (
        "falsif", "证伪", "reject", "failed", "fails", "cannot", "unable",
        "no gain", "regress", "if not", "若不", "否则", "未达",
    )):
        problems.append(
            "hypothesis states no failure mode — add the condition under which "
            "it should be rejected (e.g. 'if X cannot be measured, reject')")
    return problems


def _parse_targets(hypothesis: str) -> dict[str, float]:
    """Extract explicit 'X >= N' / 'X to N' targets, to sanity-check their range.

    Never used to auto-accept a cycle: a target met can still be a regression
    elsewhere, which is what the accept/reject decision exists to catch.

    Targets are stored in *display* units — percentages for ratios, counts
    otherwise — so they compare directly to what the report table prints.
    """
    targets: dict[str, float] = {}
    lowered = hypothesis.lower()
    for key, phrases in METRIC_PHRASES.items():
        for phrase in phrases:
            i = lowered.find(phrase.lower())
            if i < 0:
                continue
            # The number must follow the metric closely. A wide window is not
            # safe: bare phrases like "unspecified" or "draft" also name tags
            # and statuses, and would latch onto a number belonging to a
            # different metric up to a sentence away — a target the author
            # never wrote and the cycle could not reach.
            m = re.search(
                r"(>=|<=|>|<|\bto\b|\b至\b|\b到\b)\s*([0-9]*\.?[0-9]+)",
                lowered[i : i + _TARGET_WINDOW])
            if not m:
                continue
            num = float(m.group(2))
            if num <= 0:
                continue
            had_pct = lowered[i + m.end(2) : i + m.end(2) + 1].strip().startswith("%")
            if key.endswith("_ratio"):
                # "25" or "25%" means 25%; only a bare fraction below 1
                # (e.g. 0.25) needs scaling up.
                targets[key] = num if (had_pct or num > 1) else num * 100
            else:
                targets[key] = num
            break
    return targets


def _target_problems(targets: dict[str, float],
                     baseline: dict[str, Any]) -> list[str]:
    """Reject a target the corpus provably cannot reach.

    A hypothesis aiming past the ceiling (component coverage 25 when only 21
    components exist) is wrong on its face; catching it at --begin beats
    recording a cycle that could only ever fail. Targets within range are
    never second-guessed — whether they are *achieved* is the cycle's job.
    """
    problems: list[str] = []
    for key, value in targets.items():
        if key.endswith("_ratio") and not 0.0 <= value <= 100.0:
            problems.append(
                f"target for {key} is {value}, outside 0–100% — a ratio target "
                "must be a percentage")
        ceiling = None
        if key == "component_coverage":
            ceiling = baseline.get("component_total")
        elif key == "version_claims_specified":
            ceiling = baseline.get("version_claims_total")
        elif key == "component_total":
            ceiling = _COMPONENT_TOTAL_MAX
        if isinstance(ceiling, (int, float)) and value > ceiling:
            problems.append(
                f"target for {key} is {value:g} but only {ceiling:g} exist in "
                f"data/tags.yaml — the target is unreachable as stated")
    return problems


def _precheck_ok() -> bool:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "iterate_precheck.py")],
        cwd=str(ROOT), capture_output=True, text=True, check=False, timeout=120,
    )
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        return False
    return True


# ── state transitions ──────────────────────────────────────────────────

def begin(hypothesis: str, workstream: str, no_precheck: bool, force_hypothesis: bool,
          quiet: bool = False) -> dict[str, Any]:
    state = _read_state()

    if not no_precheck and not _precheck_ok():
        raise SystemExit(
            "iterate_precheck reports drift; fix it first (see output above). "
            "Pass --no-precheck only for a dry run in a scratch checkout.")

    existing = _open_cycle(state)
    if existing:
        raise SystemExit(
            f"cycle {existing.get('cycle_id')} is already IN_PROGRESS "
            f"(started {_fmt_ts(existing.get('started_at'))}); close it with "
            f"--finish or --abandon before starting another")

    problems = _hypothesis_is_falsifiable(hypothesis)
    cycle_id = state.get("next_cycle_id")
    if not isinstance(cycle_id, int):
        raise SystemExit(f"next_cycle_id is not an integer: {cycle_id!r}")

    # Measuring first lets the target check compare against the real ceiling,
    # not a hardcoded guess about how many components exist.
    before = collect_snapshot()
    targets = _parse_targets(hypothesis)
    problems.extend(_target_problems(targets, before))

    if problems and not force_hypothesis:
        print("Hypothesis is not ready to cycle on:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        raise SystemExit(
            "rewrite the hypothesis so it predicts a measurable change and "
            "states how it fails; --force-hypothesis bypasses this check")

    cycle = {
        "cycle_id": cycle_id,
        "status": IN_PROGRESS,
        "started_at": _utc(),
        "hypothesis": hypothesis.strip(),
        "workstream": workstream,
        "metrics_before": before,
        "targets": targets,
        "candidate_changes": [],
        "dev_result": None,
        "heldout_result": None,
        "report": None,
        "decision_reason": None,
    }
    state.setdefault("cycles", []).append(cycle)

    # Pre-empt the exact drift Phase 2 had to fix by hand: begin writes the
    # id now, so an interrupted cycle cannot collide with a later one.
    state["next_cycle_id"] = cycle_id + 1
    _write_state(state)

    if not quiet:
        print(f"=== Cycle {cycle_id} begun ({workstream}) ===")
        print(f"state: {_repo_path(STATE_PATH)} (next_cycle_id -> {cycle_id + 1})")
        print("\nBaseline metrics (BEFORE):")
        for k in METRIC_KEYS:
            print(f"  {k:26} {fmt_value(k, before.get(k))}")
        print("\nNow: make the change cluster, run `make all` + `make check-advisory`,")
        print("then: python3 scripts/iterate_cycle.py --finish --accept|--reject --reason ...")
    return {"cycle_id": cycle_id, "metrics_before": before}


def finish(accept: bool, reason: str, quiet: bool = False) -> dict[str, Any]:
    state = _read_state()
    cycle = _open_cycle(state)
    if not cycle:
        raise SystemExit(
            "no cycle is IN_PROGRESS; start one with --begin "
            "(or --abandon was already applied)")

    cycle_id = cycle.get("cycle_id")
    status = "accepted" if accept else "rejected"

    if not reason or not reason.strip():
        raise SystemExit(
            "a cycle decision requires a --reason; the trend report prints it, "
            "and a decision with no stated reason is not auditable")

    after = collect_snapshot()
    before = cycle.get("metrics_before") or {}
    deltas = snapshot_diff(before, after)

    # An accepted cycle that moved nothing is a red flag, not a pass: it
    # means the change cluster did not touch what the hypothesis claimed.
    # Ask for confirmation rather than refusing outright, since a genuine
    # no-op-acceptable case is the maintainer's call.
    if accept and not deltas:
        print(
            "WARNING: accepting a cycle whose metrics did not move at all.\n"
            "  The hypothesis predicted a measurable change; none of the tracked\n"
            "  metrics differs from the baseline. If the gain is real but not in\n"
            "  this metric set, say so explicitly in the reason.",
            file=sys.stderr)

    changed = _changed_files()
    if changed:
        cycle["candidate_changes"] = changed
    cycle["status"] = status
    cycle["finished_at"] = _utc()
    cycle["decision_reason"] = reason.strip()
    cycle["metrics_after"] = after

    report_path = REPORT_DIR / f"cycle-{cycle_id:03d}.md"
    report = _build_report(cycle, before, after, deltas, status, reason)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    cycle["report"] = _repo_path(report_path)
    cycle["dev_result"] = cycle["report"]

    _write_state(state)

    if not quiet:
        print(f"=== Cycle {cycle_id} {status.upper()} ===")
        print(f"report: {_repo_path(report_path)}")
        print("\nMetrics:")
        for k in METRIC_KEYS:
            b, a = before.get(k), after.get(k)
            d = deltas.get(k)
            line = f"  {k:26} {fmt_value(k, b)} -> {fmt_value(k, a)}"
            if d is not None:
                line += f"  ({fmt_delta(k, d)})"
            print(line)
        if not deltas:
            print("  (no tracked metric changed)")
    return {"cycle_id": cycle_id, "status": status, "report": str(report_path)}


def abandon(reason: str, quiet: bool = False) -> dict[str, Any]:
    state = _read_state()
    cycle = _open_cycle(state)
    if not cycle:
        raise SystemExit("no cycle is IN_PROGRESS to abandon")

    if not reason or not reason.strip():
        raise SystemExit("abandoning a cycle requires a --reason")

    cycle_id = cycle.get("cycle_id")
    cycle["status"] = "abandoned"
    cycle["finished_at"] = _utc()
    cycle["decision_reason"] = reason.strip()
    cycle["metrics_after"] = collect_snapshot()
    # An abandoned cycle leaves no report, so carry the reason in the state
    # and let the trend show it as an explicit no-change point.
    cycle["report"] = None

    _write_state(state)
    if not quiet:
        print(f"=== Cycle {cycle_id} ABANDONED ===")
        print(f"reason: {reason.strip()}")
        print("next_cycle_id stays advanced; the abandoned id is not reused.")
    return {"cycle_id": cycle_id, "status": "abandoned"}


def status(quiet: bool = False) -> dict[str, Any]:
    state = _read_state()
    cycle = _open_cycle(state)
    closed = [c for c in state.get("cycles", []) if c.get("status") in DONE_STATES]
    out = {
        "next_cycle_id": state.get("next_cycle_id"),
        "open_cycle": None,
        "closed_cycles": len(closed),
    }
    if cycle:
        out["open_cycle"] = {
            "cycle_id": cycle.get("cycle_id"),
            "hypothesis": (cycle.get("hypothesis") or "")[:160],
            "workstream": cycle.get("workstream"),
            "started_at": cycle.get("started_at"),
        }
        if not quiet:
            print(f"=== Cycle {cycle['cycle_id']} IN_PROGRESS ===")
            print(f"started: {cycle.get('started_at')}")
            print(f"hypothesis: {cycle.get('hypothesis')}")
            print("close with: --finish --accept|--reject --reason ...")
    else:
        # Fall back to the last closed cycle's metrics for a quick read on
        # where the corpus stands now.
        last = _metrics_tail(state)
        if not quiet:
            print(f"=== No cycle in progress; next is #{state.get('next_cycle_id')} ===")
            if last:
                print("last recorded metrics:")
                for k in METRIC_KEYS:
                    print(f"  {k:26} {fmt_value(k, last.get(k))}")
    return out


def _fmt_ts(ts: str | None) -> str:
    if not ts:
        return "(no timestamp)"
    return ts.split(".")[0].replace("T", " ")


def _changed_files() -> list[str]:
    """Files changed since HEAD, as the cycle's candidate change cluster."""
    r = subprocess.run(["git", "status", "--porcelain"],
                       cwd=str(ROOT), capture_output=True, text=True, check=False)
    out: list[str] = []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        name = line[2:].strip().split(" -> ")[-1].strip()
        # Untracked scratch dirs show up as 'dir/'; they are not corpus.
        if name.endswith("/") or name.startswith("."):
            continue
        out.append(name)
    return sorted(set(out))


# ── report generation ──────────────────────────────────────────────────

def _build_report(cycle: dict[str, Any], before: dict[str, Any],
                  after: dict[str, Any], deltas: dict[str, float],
                  status: str, reason: str) -> str:
    cycle_id = cycle.get("cycle_id")
    lines: list[str] = []
    title = f"Cycle {cycle_id:03d}"
    if status == "accepted":
        title += ": accepted change cluster"
    elif status == "rejected":
        title += ": rejected change cluster"
    lines.append(f"# {title}")
    lines.append("")

    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| Cycle ID | {cycle_id} |")
    lines.append(f"| Status | {status} |")
    lines.append(f"| Workstream | {cycle.get('workstream') or 'unspecified'} |")
    lines.append(f"| Date | {datetime.now().strftime('%Y-%m-%d')} |")
    lines.append(f"| Hypothesis | {(cycle.get('hypothesis') or '').strip()} |")
    lines.append("")

    lines.append("## Decision")
    lines.append("")
    lines.append(f"**{status}**. {reason.strip()}")
    lines.append("")

    lines.append("## Metrics (before → after)")
    lines.append("")
    lines.append("| Metric | Before | After | Δ |")
    lines.append("|--------|--------|-------|---|")
    for k in METRIC_KEYS:
        b, a = before.get(k), after.get(k)
        d = deltas.get(k)
        cell_d = fmt_delta(k, d) if d is not None else "—"
        lines.append(f"| {k} | {fmt_value(k, b)} | {fmt_value(k, a)} | {cell_d} |")
    if not deltas:
        lines.append("")
        lines.append("*No tracked metric changed between baseline and finish.*")
    lines.append("")

    changed = cycle.get("candidate_changes") or []
    if changed:
        lines.append("## Candidate changes")
        lines.append("")
        for f in changed:
            lines.append(f"- `{f}`")
        lines.append("")

    lines.append("## Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python3 scripts/iterate_metrics.py --json    # re-measure")
    lines.append("make all")
    lines.append("make check-advisory")
    lines.append("```")
    lines.append("")

    # Machine-readable block, not rendered. trend_report.py reads this, and
    # it lets any future tool join the trend without re-parsing markdown.
    lines.append("<!-- iterate_metrics")
    lines.append("```json")
    lines.append(json.dumps({"metrics_before": before, "metrics_after": after,
                             "deltas": deltas, "status": status},
                            ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("-->")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--begin", action="store_true",
                      help="start a cycle: precheck, record hypothesis + BEFORE metrics")
    mode.add_argument("--finish", action="store_true",
                      help="close a cycle: record AFTER metrics, write the report")
    mode.add_argument("--abandon", action="store_true",
                      help="close a cycle as abandoned (no change cluster produced)")
    mode.add_argument("--status", action="store_true",
                      help="show the open cycle and the last recorded metrics")

    parser.add_argument("--hypothesis", type=str,
                        help="the falsifiable hypothesis this cycle tests (--begin)")
    parser.add_argument("--workstream", type=str, default="corpus",
                        help="corpus | foundation | eval | ecosystem | maintenance (--begin)")
    parser.add_argument("--reason", type=str,
                        help="why the cycle was accepted/rejected/abandoned (--finish/--abandon)")
    parser.add_argument("--accept", action="store_true",
                        help="mark the cycle accepted (--finish)")
    parser.add_argument("--reject", action="store_true",
                        help="mark the cycle rejected (--finish)")
    parser.add_argument("--force-hypothesis", action="store_true",
                        help="bypass the falsifiability check (--begin)")
    parser.add_argument("--no-precheck", action="store_true",
                        help="skip iterate_precheck before --begin (scratch checkouts only)")
    parser.add_argument("--json", action="store_true", help="emit result as JSON")
    args = parser.parse_args()

    if args.begin and not args.hypothesis:
        parser.error("--begin requires --hypothesis")
    if args.finish and not (args.accept ^ args.reject):
        parser.error("--finish requires exactly one of --accept / --reject")

    quiet = args.json
    try:
        if args.begin:
            result = begin(args.hypothesis, args.workstream, args.no_precheck,
                           args.force_hypothesis, quiet)
        elif args.finish:
            result = finish(args.accept, args.reason, quiet)
        elif args.abandon:
            result = abandon(args.reason, quiet)
        else:
            result = status(quiet)
    except SystemExit:
        raise
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"iterate_cycle failed: {exc}")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
