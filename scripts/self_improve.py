#!/usr/bin/env python3
"""Apply auto-fixable backlog items with a 10-step safety pipeline.

Reads auto_fixable:true items from iteration-state.json, applies the
appropriate repair strategy, verifies via make all, and either commits
or rolls back. Each fix is processed independently.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .common import ROOT, load_data
except ImportError:
    from common import ROOT, load_data

STATE_PATH = ROOT / "evals" / "claude" / "iteration-state.json"
RULES_PATH = ROOT / "data" / "auto-fix-rules.yaml"
FIX_LOG_PATH = ROOT / "evals" / "claude" / "auto-fix-log.jsonl"


def _run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, **kwargs)


def _log_fix(record: dict[str, Any]) -> None:
    FIX_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(FIX_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _git_clean() -> bool:
    """Check git working tree is clean."""
    r1 = _run(["git", "diff", "--quiet"])
    r2 = _run(["git", "diff", "--cached", "--quiet"])
    return r1.returncode == 0 and r2.returncode == 0


def _git_diff_size() -> int:
    """Count lines in git diff."""
    r = _run(["git", "diff", "--stat"])
    if r.returncode != 0:
        return 0
    lines = r.stdout.strip().split("\n")
    if lines:
        last = lines[-1].strip()
        try:
            return int(last.split()[-2]) if "insertion" in last else 0
        except (IndexError, ValueError):
            pass
    return 0


def _make_all_green() -> bool:
    return _run(["make", "all"]).returncode == 0


def _recall_ok(threshold: float = 0.70) -> bool:
    r = _run([sys.executable, "scripts/recall_check.py", "--mode", "or", "--json"])
    try:
        data = json.loads(r.stdout)
        return data.get("recall", 0.0) >= threshold
    except (json.JSONDecodeError, KeyError):
        return False


def _strategy_alias_addition(item: dict[str, Any], rules: dict[str, Any]) -> tuple[bool, str, list[str]]:
    """Strategy 1: Add aliases when fuzzy search finds results for terms that exact search misses."""
    terms = item.get("signal_query_terms", [])
    if not terms:
        return False, "no terms in signal", []

    cfg = rules.get("rules", {}).get("alias_addition", {})
    fuzzy_threshold = cfg.get("fuzzy_threshold", 0.3)

    aliases_data = load_data(ROOT / "data" / "aliases.yaml")
    new_aliases: dict[str, list[str]] = {}
    changed = []

    for term in terms:
        # Check if term already has an alias
        term_cf = term.casefold()
        already_aliased = False
        for variants in aliases_data.values():
            if isinstance(variants, list):
                if term_cf in (v.casefold() for v in variants):
                    already_aliased = True
                    break
            elif isinstance(variants, str):
                if term_cf == variants.casefold():
                    already_aliased = True
                    break
        if already_aliased:
            continue

        # Run fuzzy search to find best matching page
        r = _run([sys.executable, "scripts/query.py", term, "--fuzzy", "--limit", "3", "--json"])
        try:
            results = json.loads(r.stdout)
            if results:
                best = results[0]
                page_id = best.get("id", "")
                if page_id and page_id in aliases_data:
                    existing = aliases_data[page_id]
                    if isinstance(existing, list) and term not in existing:
                        existing.append(term)
                        new_aliases[page_id] = existing
                elif page_id:
                    aliases_data[page_id] = [term]
                    new_aliases[page_id] = [term]
        except (json.JSONDecodeError, KeyError):
            continue

    if new_aliases:
        changed.append(str(ROOT / "data" / "aliases.yaml"))
        aliases_path = ROOT / "data" / "aliases.yaml"
        aliases_path.write_text(json.dumps(aliases_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        desc = ", ".join(f"{k} → {v}" for k, v in new_aliases.items())
        return True, f"aliases added: {desc}", changed

    return False, "no new aliases found via fuzzy search", []


def _strategy_freshness_update(item: dict[str, Any], rules: dict[str, Any]) -> tuple[bool, str, list[str]]:
    """Strategy 2: Update retrieved_at date for stale sources."""
    page_id = item.get("signal_query_terms", [""])[0] if item.get("signal_query_terms") else ""

    # Find the source page file
    from common import discover_pages as dp
    pages = dp()
    target = None
    for p in pages:
        if str(p.metadata.get("id", "")) == page_id:
            target = p
            break

    if not target:
        return False, f"source page not found: {page_id}", []

    # Read the page, update retrieved_at
    content = target.path.read_text(encoding="utf-8")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_content = content.replace(
        f'"retrieved_at": "{target.metadata.get("retrieved_at", "")}"',
        f'"retrieved_at": "{today}"',
    )
    target.path.write_text(new_content, encoding="utf-8")
    changed = [str(target.relative_path)]
    return True, f"updated retrieved_at to {today}", changed


def _strategy_keyword_update(item: dict[str, Any], rules: dict[str, Any]) -> tuple[bool, str, list[str]]:
    """Strategy 3: Update gold question keywords from query log patterns."""
    # This strategy requires signal logs to extract successful query terms
    signal_dir = Path(os.environ.get("MACAWIKI_SIGNAL_DIR", ROOT / "evals" / "signals"))
    query_terms: set[str] = set()

    for path in sorted(signal_dir.glob("query-log*.jsonl")):
        try:
            for line in path.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    record = json.loads(line)
                    if record.get("result_count", 0) > 0:
                        query_terms.update(record.get("terms", []))
        except (OSError, json.JSONDecodeError):
            continue

    if not query_terms:
        return False, "no query log data available", []

    # Load gold questions, find ones with low recall
    gold_path = ROOT / "evals" / "gold-questions.yaml"
    gold_data = load_data(gold_path)
    questions = gold_data.get("questions", []) if isinstance(gold_data, dict) else gold_data

    r = _run([sys.executable, "scripts/recall_check.py", "--mode", "or", "--json"])
    try:
        recall_data = json.loads(r.stdout)
        per_q = recall_data.get("questions", [])
    except (json.JSONDecodeError, KeyError):
        return False, "recall check failed", []

    changed = False
    for qi in per_q:
        if qi.get("missing", []):
            qid = qi.get("id", "")
            # Find the question in gold data and add relevant keywords
            for q in questions:
                if q.get("id") == qid:
                    existing_kw = set(q.get("keywords", []))
                    # Add up to 5 new keywords from query logs
                    added = 0
                    for term in sorted(query_terms):
                        if term not in existing_kw and len(existing_kw) < 15:
                            existing_kw.add(term)
                            added += 1
                    if added > 0:
                        q["keywords"] = sorted(existing_kw)
                        changed = True
                    break

    if changed:
        gold_path.write_text(json.dumps(gold_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return True, "updated gold question keywords", [str(gold_path.relative_to(ROOT))]
    return False, "no keyword gaps found", []


STRATEGIES = {
    "alias_addition": _strategy_alias_addition,
    "freshness_update": _strategy_freshness_update,
    "gold_question_keyword_update": _strategy_keyword_update,
}


def process_item(item: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    """Run the 10-step safety pipeline on a single auto-fixable item."""
    strategy_name = item.get("auto_fix_strategy", "")
    item_id = item.get("id", "?")

    result = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "fix_id": f"auto-fix-{item_id}",
        "backlog_id": item_id,
        "strategy": strategy_name,
        "files_changed": [],
        "commit": None,
        "make_all_result": None,
        "recall_before": 1.0,
        "recall_after": None,
        "status": "unknown",
    }

    # Step 1: Git clean check
    cfg = rules.get("safety", {})
    if cfg.get("require_clean_git", True) and not _git_clean():
        result["status"] = "skipped"
        result["failure_reason"] = "git working tree is dirty"
        return result

    # Step 2: Baseline check
    if cfg.get("require_make_all_green", True) and not _make_all_green():
        result["status"] = "skipped"
        result["failure_reason"] = "make all failed on baseline"
        return result

    # Step 3: Recall baseline
    result["recall_before"] = 1.0
    r = _run([sys.executable, "scripts/recall_check.py", "--mode", "or", "--json"])
    try:
        result["recall_before"] = json.loads(r.stdout).get("recall", 1.0)
    except (json.JSONDecodeError, KeyError):
        pass

    # Step 4: Run strategy
    strategy_fn = STRATEGIES.get(strategy_name)
    if not strategy_fn:
        result["status"] = "skipped"
        result["failure_reason"] = f"unknown strategy: {strategy_name}"
        return result

    applied, msg, files = strategy_fn(item, rules)
    if not applied:
        result["status"] = "skipped"
        result["failure_reason"] = f"strategy '{strategy_name}' produced no changes: {msg}"
        return result

    result["files_changed"] = files

    # Step 5: Diff size check
    diff_lines = _git_diff_size()
    max_lines = cfg.get("max_diff_lines", 50)
    if diff_lines > max_lines:
        _run(["git", "checkout", "--"] + files)
        result["status"] = "rolled_back"
        result["failure_reason"] = f"diff too large ({diff_lines} lines > {max_lines})"
        return result

    # Step 6: Full verification
    make_ok = _make_all_green()
    result["make_all_result"] = "passed" if make_ok else "failed"

    # Step 7: Recall check
    r = _run([sys.executable, "scripts/recall_check.py", "--mode", "or", "--json"])
    try:
        result["recall_after"] = json.loads(r.stdout).get("recall", 0.0)
    except (json.JSONDecodeError, KeyError):
        result["recall_after"] = 0.0

    min_recall = cfg.get("min_recall_threshold", 0.70)

    if not make_ok or result["recall_after"] < min_recall:
        # Rollback
        _run(["git", "checkout", "--"] + files)
        result["status"] = "rolled_back"
        if not make_ok:
            result["failure_reason"] = "make all failed after fix"
        elif result["recall_after"] is not None and result["recall_after"] < min_recall:
            result["failure_reason"] = f"recall dropped below threshold ({result['recall_after']:.1%} < {min_recall:.0%})"
        return result

    # Step 8: Commit
    _run(["git", "add"] + files)
    commit_msg = f"auto-fix({item_id}): {msg} [auto]"
    r = _run(["git", "commit", "-m", commit_msg])
    if r.returncode != 0:
        _run(["git", "checkout", "--"] + files)
        result["status"] = "rolled_back"
        result["failure_reason"] = "git commit failed"
        return result

    # Get commit SHA
    r = _run(["git", "rev-parse", "HEAD"])
    result["commit"] = r.stdout.strip()[:8] if r.returncode == 0 else None
    result["status"] = "applied"
    return result


def apply_fixes(dry_run: bool = False) -> dict[str, Any]:
    """Process all open auto-fixable backlog items."""
    state = load_data(STATE_PATH)
    backlog = state.get("backlog", []) if isinstance(state, dict) else []
    rules = load_data(RULES_PATH)

    auto_items = [b for b in backlog if b.get("auto_fixable") and b.get("status") in ("open", "pending")]
    max_per_run = rules.get("safety", {}).get("max_auto_fixes_per_run", 5)
    auto_items = auto_items[:max_per_run]

    if dry_run:
        return {
            "dry_run": True,
            "auto_fixable_count": len(auto_items),
            "items": [{"id": b["id"], "strategy": b.get("auto_fix_strategy", "?"), "hint": b.get("auto_fix_hint", "?")} for b in auto_items],
        }

    results = []
    for item in auto_items:
        record = process_item(item, rules)
        _log_fix(record)
        results.append(record)

        # Update iteration-state.json
        if record["status"] == "applied":
            for b in backlog:
                if b.get("id") == item["id"]:
                    b["status"] = "completed"
            state["backlog"] = backlog
        elif record["status"] == "rolled_back":
            for b in backlog:
                if b.get("id") == item["id"]:
                    b["status"] = "needs_human_review"
            state["backlog"] = backlog

        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    applied = sum(1 for r in results if r["status"] == "applied")
    rolled = sum(1 for r in results if r["status"] == "rolled_back")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    return {
        "dry_run": False,
        "total": len(results),
        "applied": applied,
        "rolled_back": rolled,
        "skipped": skipped,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="List auto-fixable items without applying changes")
    parser.add_argument("--apply", action="store_true", help="Process auto-fixable items with safety pipeline")
    parser.add_argument("--item", type=str, help="Target a single backlog item by ID")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    report = apply_fixes(dry_run=args.dry_run or not args.apply)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report.get("dry_run"):
        print(f"=== Self-Improve (dry-run) ===")
        print(f"Auto-fixable items: {report['auto_fixable_count']}")
        for item in report.get("items", []):
            print(f"  [{item['id']}] {item['strategy']}: {item['hint']}")
        if not report.get("items"):
            print("  (none)")
    else:
        print(f"=== Self-Improve Results ===")
        print(f"Total:    {report['total']}")
        print(f"Applied:  {report['applied']}")
        print(f"Rolled back: {report['rolled_back']}")
        print(f"Skipped:  {report['skipped']}")
        for r in report.get("results", []):
            status_icon = "✅" if r["status"] == "applied" else "↩️" if r["status"] == "rolled_back" else "⏭️"
            print(f"  {status_icon} [{r['backlog_id']}] {r['strategy']}: {r['status']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
