#!/usr/bin/env python3
"""Per-cycle trend of the corpus metrics the iteration loop judges itself on.

Reads `evals/claude/iteration-state.json` and each cycle's report, and prints
one row per cycle: pages, component coverage, version-claims, draft ratio,
unspecified ratio, license, recall, tests — plus the accept/reject decision.

The point is to see whether the loop is actually improving the corpus over
time, or oscillating. A row that reads `n/a` is *information*: that cycle
predates metric recording (cycles 1-10 left no numbers), was abandoned, or
its report is missing. Those gaps are printed, never papered over — the
trend that silently drops its bad cycles is not a trend.

Historical note. Cycles 1-10 recorded no metrics at all, and cycles 7-10
left `report: null`, so their decisions are unrecoverable. That is why
`iterate_cycle.py --finish` now embeds metrics in every report it writes.

Usage:
    python3 scripts/trend_report.py             # markdown table to stdout
    python3 scripts/trend_report.py --json      # machine-readable
    python3 scripts/trend_report.py --last N    # only the most recent N cycles
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

try:
    from .common import ROOT, load_data
    from .iterate_metrics import METRIC_KEYS, fmt_value
except ImportError:
    from common import ROOT, load_data
    from iterate_metrics import METRIC_KEYS, fmt_value


# Overridable so the trend can be computed for a scratch checkout without
# reading the real loop state. Mirrors MACAWIKI_ITERATE_STATE in
# iterate_cycle.py; both must point at the same state file.
STATE_PATH = Path(os.environ.get(
    "MACAWIKI_ITERATE_STATE",
    str(ROOT / "evals" / "claude" / "iteration-state.json")))

# Columns shown in the table, in order. All of them come from METRIC_KEYS so a
# metric added to iterate_metrics appears here without a second edit.
COLUMNS: tuple[str, ...] = (
    "pages",
    "component_coverage",
    "version_claims_specified",
    "draft_ratio",
    "unspecified_ratio",
    "license_known_ratio",
    "recall",
    "tests",
)

# What each column means; printed as a legend so the numbers stay legible
# without the reader having to open iterate_metrics.py.
COLUMN_NOTES: dict[str, str] = {
    "pages": "total corpus pages",
    "component_coverage": "covered / known components in data/tags.yaml",
    "version_claims_specified": "version-claims.yaml entries with a real version",
    "draft_ratio": "share of wiki pages still in draft status",
    "unspecified_ratio": "share of wiki pages with no MXMACA version",
    "license_known_ratio": "share of sources with a determinable license",
    "recall": "gold-question recall (recall_check.py)",
    "tests": "unittest methods in tests/",
}

DECISION_SYMBOLS = {
    "accepted": "✅",
    "rejected": "❌",
    "abandoned": "⬜",
    "in_progress": "⏳",
}


def _state_cycles() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    state = load_data(STATE_PATH)
    return state.get("cycles") or [], state


def _report_metrics(state: dict[str, Any], cycle: dict[str, Any]) -> dict[str, Any]:
    """Metrics recorded for a cycle, falling back to its report's JSON block.

    Preference order: the state's own `metrics_after` (written by
    iterate_cycle --finish), then a metrics block embedded in the report
    file, then nothing. Older cycles fall through to nothing, which the
    table shows as `n/a` rather than a fabricated value.
    """
    own = cycle.get("metrics_after")
    if isinstance(own, dict) and any(k in own for k in METRIC_KEYS):
        return {k: v for k, v in own.items() if k in METRIC_KEYS}

    path = cycle.get("report")
    if not path:
        return {}
    full = ROOT / path
    if not full.is_file():
        return {"_missing_report": path}
    text = full.read_text(encoding="utf-8")
    marker = "<!-- iterate_metrics"
    i = text.find(marker)
    if i < 0:
        return {}
    start = text.find("```", i)
    end = text.find("```", start + 3) if start >= 0 else -1
    if start < 0 or end < 0:
        return {}
    try:
        data = json.loads(text[start + 3 : end])
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out = data.get("metrics_after") or {}
    return {k: v for k, v in out.items() if k in METRIC_KEYS}


def collect_trend() -> dict[str, Any]:
    """One trend row per cycle, oldest first, with gaps made explicit."""
    cycles, state = _state_cycles()
    rows: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for cycle in cycles:
        cid = cycle.get("cycle_id")
        status = cycle.get("status") or "unknown"
        metrics = _report_metrics(state, cycle)
        row = {
            "cycle_id": cid,
            "status": status,
            "workstream": cycle.get("workstream"),
            "metrics": metrics,
            "hypothesis": cycle.get("hypothesis"),
            "decision_reason": cycle.get("decision_reason"),
            "report": cycle.get("report"),
        }
        rows.append(row)

        # Record why a row is blank, in the maintainer's own terms. Judged on
        # whether any *metric* is present: a `_missing_report` marker alone
        # is a complaint, not a measurement.
        if not any(k in metrics for k in METRIC_KEYS):
            if status == "abandoned":
                gaps.append({"cycle_id": cid, "reason": "cycle was abandoned; no metrics recorded"})
            elif not cycle.get("report"):
                gaps.append({"cycle_id": cid, "reason":
                             "no report path in state (cycles 7-10); decision is not traceable"})
            elif metrics.get("_missing_report"):
                gaps.append({"cycle_id": cid, "reason":
                             f"report path in state is missing on disk: {metrics['_missing_report']}"})
            else:
                gaps.append({"cycle_id": cid, "reason":
                             "report predates metric recording and has no embedded metrics block"})

    accepted = sum(1 for r in rows if r["status"] == "accepted")
    rejected = sum(1 for r in rows if r["status"] == "rejected")
    abandoned = sum(1 for r in rows if r["status"] == "abandoned")
    in_progress = sum(1 for r in rows if r["status"] == "in_progress")

    return {
        "cycles_total": len(rows),
        "accepted": accepted,
        "rejected": rejected,
        "abandoned": abandoned,
        "in_progress": in_progress,
        "measured": len(rows) - len(gaps),
        "next_cycle_id": state.get("next_cycle_id"),
        "rows": rows,
        "gaps": gaps,
    }


def _cell(metrics: dict[str, Any], key: str) -> str:
    value = metrics.get(key)
    if value is None:
        return "n/a"
    if key == "component_coverage":
        total = metrics.get("component_total")
        return f"{value}/{total}" if total else str(value)
    if key == "version_claims_specified":
        total = metrics.get("version_claims_total")
        return f"{value}/{total}" if total else str(value)
    return fmt_value(key, value)


def render_markdown(trend: dict[str, Any], last_n: int | None = None) -> str:
    rows = trend["rows"]
    if last_n is not None and last_n > 0:
        rows = rows[-last_n:]

    lines: list[str] = []
    lines.append("# Macawiki iteration trend")
    lines.append("")
    lines.append(
        f"{trend['cycles_total']} cycles recorded: "
        f"{trend['accepted']} accepted, {trend['rejected']} rejected, "
        f"{trend['abandoned']} abandoned, {trend['in_progress']} in progress. "
        f"{trend['measured']} carry measurable metrics.")
    lines.append("")

    lines.append("| Cycle | Status | " + " | ".join(COLUMNS) + " |")
    lines.append("|-------|--------|" + "|".join(["---"] * len(COLUMNS)) + "|")
    for row in rows:
        sym = DECISION_SYMBOLS.get(row["status"], "?")
        cells = [_cell(row["metrics"], k) for k in COLUMNS]
        lines.append(f"| {row['cycle_id']} | {sym} {row['status']} | " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("Legend:")
    for key in COLUMNS:
        lines.append(f"- `{key}` — {COLUMN_NOTES.get(key, key)}")
    lines.append("")

    if trend["gaps"]:
        lines.append("## Cycles without metrics")
        lines.append("")
        lines.append("These contribute no trend point. Each gap is a record-keeping")
        lines.append("gap, not necessarily a bad outcome — but a loop that cannot")
        lines.append("audit its own past will repeat it.")
        lines.append("")
        for gap in trend["gaps"]:
            lines.append(f"- **cycle {gap['cycle_id']}**: {gap['reason']}")
        lines.append("")

    # Direction of travel across the cycles that actually carry numbers.
    measured = [r for r in rows if r["metrics"]]
    if len(measured) >= 2:
        lines.append("## Direction of travel")
        lines.append("")
        first, last = measured[0], measured[-1]
        for key in COLUMNS:
            a, b = first["metrics"].get(key), last["metrics"].get(key)
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                continue
            if a == b:
                lines.append(f"- `{key}`: flat at {fmt_value(key, b)}")
                continue
            scale = 100.0 if key.endswith("_ratio") else 1.0
            delta = round((b - a) * scale, 1)
            suffix = "pp" if key.endswith("_ratio") else ""
            direction = "up" if delta > 0 else "down"
            lines.append(f"- `{key}`: {fmt_value(key, a)} → {fmt_value(key, b)} "
                         f"({direction} {abs(delta)}{suffix})")
        lines.append("")
        lines.append(
            "Note: `up` is not always improvement. Draft ratio and unspecified")
        lines.append(
            "ratio are *better when lower*; the symbol only records direction.")
        lines.append("")

    # The most recent decision, printed in full because it is the one the
    # next cycle should build on (or avoid repeating).
    decided = [r for r in rows if r.get("decision_reason")]
    if decided:
        last_decided = decided[-1]
        lines.append("## Most recent decision")
        lines.append("")
        lines.append(f"**Cycle {last_decided['cycle_id']} ({last_decided['status']})**")
        lines.append("")
        lines.append(f"> {last_decided['decision_reason']}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="emit the trend as JSON")
    parser.add_argument("--last", type=int,
                        help="show only the most recent N cycles in the table")
    parser.add_argument("--markdown", type=str,
                        help="also write the markdown table to this path")
    args = parser.parse_args()

    trend = collect_trend()
    md = render_markdown(trend, args.last)

    if args.json:
        print(json.dumps(trend, ensure_ascii=False, indent=2))
    else:
        print(md)

    if args.markdown:
        out = Path(args.markdown)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md + "\n", encoding="utf-8")
        print(f"\n(written to {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
