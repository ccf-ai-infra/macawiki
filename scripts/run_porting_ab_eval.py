#!/usr/bin/env python3
"""Run the torch-scatter porting A/B experiment (Macawiki agent-value, Tier: end-to-end).

Group A runs codebuddy on a pinned torch-scatter tarball WITHOUT the Macawiki
skill; Group B runs the identical prompt WITH the skill installed (--mode copy)
into the worktree's .codebuddy/skills/ (the only path codebuddy discovers). All artifacts live under evals/porting-ab/ and are
status=recorded, reviewed=false. Nothing here grants `verified`.

Single C500: groups must run sequentially (separate invocations).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .common import ROOT, load_data
except ImportError:
    from common import ROOT, load_data

EVAL_DIR = ROOT / "evals" / "porting-ab"
TASK_FILE = EVAL_DIR / "task.yaml"
WORKSPACES = Path(os.environ.get("MACAWIKI_PORTING_AB_WORKSPACES", Path.home() / "porting-ab-workspaces"))
CACHE = WORKSPACES / "cache"

GATE_ORDER = ("environment", "build", "correctness", "timing", "comparability", "conclusion")

# Upstream benchmark scripts (argparse exits rc=2 without required args).
# Only upstream scripts are gated — agent-created helpers under benchmark/ are excluded.
UPSTREAM_BENCHMARKS = {"gather": [], "scatter_segment": ["--reduce", "sum"]}

# Pre-seeded SuiteSparse matrices (downloaded once) to keep slow-network noise
# out of the agent phase. Populated from a completed run's benchmark/ dir.
PRESEED_MATS = CACHE / "mats"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_logged(cmd: list[str], log: Path, cwd: Path | None = None, env: dict[str, str] | None = None,
               timeout: int = 3600) -> dict[str, Any]:
    """Run cmd, tee combined output to log, return rc/wall-time/timeout flag."""
    log.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    timed_out = False
    with open(log, "w", encoding="utf-8") as fh:
        fh.write("$ " + " ".join(cmd) + "\n\n")
        fh.flush()
        try:
            proc = subprocess.run(cmd, cwd=cwd, env=env, stdout=fh, stderr=subprocess.STDOUT,
                                  text=True, timeout=timeout, check=False)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            rc = None
            timed_out = True
            fh.write(f"\n[harness] TIMEOUT after {timeout}s\n")
    return {"returncode": rc, "wall_time_s": round(time.monotonic() - start, 1), "timed_out": timed_out,
            "log": str(log)}


def fetch_source(task: dict[str, Any], dry_run: bool) -> Path:
    sha = task["upstream"]["commit_sha"]
    tarball = CACHE / f"pytorch_scatter-{sha[:7]}.tar.gz"
    if tarball.exists():
        return tarball
    if dry_run:
        print(f"would fetch {task['upstream']['tarball']} -> {tarball}")
        return tarball
    CACHE.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sfL", "-o", str(tarball), task["upstream"]["tarball"]],
                   check=True, timeout=600)
    return tarball


def prepare_worktree(task: dict[str, Any], run_id: str, group: str, dry_run: bool) -> Path:
    src = WORKSPACES / run_id / "src"
    if dry_run:
        print(f"would extract tarball -> {src}")
        if group == "B":
            print(f"would install skill: scripts/install.py --agent codebuddy --scope project "
                  f"--project-dir {src} --mode copy --replace")
        return src
    if not src.exists():
        src.mkdir(parents=True, exist_ok=True)
        tarball = fetch_source(task, dry_run=False)
        with tarfile.open(tarball) as tf:
            tf.extractall(src, filter="data")
        # tarball has a single top-level dir; flatten it into src
        entries = list(src.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            inner = entries[0]
            for item in inner.iterdir():
                item.rename(src / item.name)
            inner.rmdir()
    if PRESEED_MATS.is_dir():
        import shutil
        bench = src / "benchmark"
        bench.mkdir(exist_ok=True)
        for mat in PRESEED_MATS.glob("*.mat"):
            target = bench / mat.name
            if not target.exists():
                shutil.copy2(mat, target)
    if group == "B":
        # The experiment agent is `codebuddy`, which only discovers skills under
        # .codebuddy/skills/ — installing into .agents/skills/ makes the skill
        # invisible and silently invalidates the whole A/B (see reports/).
        subprocess.run([sys.executable, str(ROOT / "scripts" / "install.py"), "--agent", "codebuddy",
                        "--scope", "project", "--project-dir", str(src), "--mode", "copy", "--replace"],
                       check=True)
    return src


def codebuddy_command(task: dict[str, Any], session_id: str) -> list[str]:
    agent = task["agent"]
    return ["codebuddy", "-p", task["prompt"],
            "--output-format", agent["output_format"],
            "--model", agent["model"],
            "--max-turns", str(agent["max_turns"]),
            "--permission-mode", agent["permission_mode"],
            "--session-id", session_id,
            "--no-session-persistence"]


def parse_agent_output(path: Path) -> dict[str, Any]:
    """Best-effort extraction of usage/turns from codebuddy output.

    Supports both `--output-format json` (single message array, written at
    exit) and `stream-json` (JSONL events; the last {"type": "result"} line
    carries usage/turns). Stream format survives harness timeouts.
    """
    metrics: dict[str, Any] = {"turns": None, "tokens_in": None, "tokens_out": None}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return metrics
    data: Any = None
    stripped = text.strip()
    if stripped.startswith("["):
        try:
            events = json.loads(stripped)
            data = next((item for item in reversed(events)
                         if isinstance(item, dict) and item.get("type") == "result"), None)
        except json.JSONDecodeError:
            data = None
    else:
        for line in stripped.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict) and event.get("type") == "result":
                data = event  # keep the last result event
    if isinstance(data, dict):
        usage = data.get("usage") or {}
        metrics["tokens_in"] = usage.get("input_tokens")
        metrics["tokens_out"] = usage.get("output_tokens")
        metrics["turns"] = data.get("num_turns")
        metrics["agent_duration_ms"] = data.get("duration_ms")
        metrics["is_error"] = data.get("is_error")
        denials = data.get("permission_denials")
        metrics["permission_denials"] = len(denials) if isinstance(denials, list) else None
    return metrics


def parse_pytest(log: Path) -> dict[str, Any]:
    stats = {"passed": None, "failed": None, "errors": None, "skipped": None}
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return stats
    for key, pattern in (("passed", r"(\d+) passed"), ("failed", r"(\d+) failed"),
                         ("errors", r"(\d+) error"), ("skipped", r"(\d+) skipped")):
        matches = re.findall(pattern, text)
        if matches:
            stats[key] = int(matches[-1])
    return stats


def count_signals(signal_dir: Path) -> int | None:
    log = signal_dir / "query-log.jsonl"
    if not log.exists():
        return None
    return sum(1 for _ in log.open(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=["A", "B"], required=True)
    parser.add_argument("--repetition", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--gates-only", action="store_true",
                        help="skip the agent run; re-run gates on the existing worktree")
    parser.add_argument("--agent-timeout", type=int, default=7200)
    parser.add_argument("--gate-timeout", type=int, default=3600)
    args = parser.parse_args()

    task = load_data(TASK_FILE)
    run_id = f"{args.group.lower()}{args.repetition}"
    run_dir = EVAL_DIR / "runs" / run_id
    session_id = f"porting-ab-{run_id}-{uuid.uuid4().hex[:8]}"
    src = WORKSPACES / run_id / "src"

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "task_id": task["id"],
        "group": args.group,
        "repetition": args.repetition,
        "commit_sha": task["upstream"]["commit_sha"],
        "model": task["agent"]["model"],
        "max_turns": task["agent"]["max_turns"],
        "permission_mode": task["agent"]["permission_mode"],
        "session_id": session_id,
        "worktree": str(src),
        "prompt_sha256": hashlib.sha256(task["prompt"].encode()).hexdigest(),
        "skill_installed": args.group == "B",
        "skill_mode": "copy" if args.group == "B" else None,
        "gates_only": args.gates_only,
        "started_at": now_iso(),
    }

    cmd = codebuddy_command(task, session_id)
    if args.dry_run:
        print(f"run_id={run_id} group={args.group} rep={args.repetition}")
        prepare_worktree(task, run_id, args.group, dry_run=True)
        if not args.gates_only:
            print(f"would run (cwd={src}):\n  " + " ".join(cmd[:1] + ["-p", "<prompt>"] + cmd[3:]))
        print(f"would run gates -> {run_dir}/ (capture_environment, import, pytest, benchmark)")
        print(f"would write manifests/{run_id}.yaml and results/{run_id}.yaml")
        return 0

    prepare_worktree(task, run_id, args.group, dry_run=False)
    write_json(EVAL_DIR / "manifests" / f"{run_id}.yaml", manifest)

    gates = {name: "not_run" for name in GATE_ORDER}
    process: dict[str, Any] = {"wall_time_s": None, "agent_returncode": None, "human_interventions": 0,
                               "macawiki_queries": None}
    agent_metrics: dict[str, Any] = {}

    if not args.gates_only:
        env = dict(os.environ)
        env["CODEBUDDY_IS_SANDBOX"] = "1"  # fully non-interactive; dedicated eval host
        if args.group == "B":
            env["MACAWIKI_SIGNAL_DIR"] = str(run_dir / "signals")
        out_path = run_dir / "session-stream.jsonl"
        log_path = run_dir / "session.log"
        run_dir.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        timed_out = False
        with out_path.open("w", encoding="utf-8") as out_fh, log_path.open("w", encoding="utf-8") as err_fh:
            err_fh.write("$ codebuddy -p <prompt> " + " ".join(cmd[3:]) + "\n\n")
            err_fh.flush()
            try:
                proc = subprocess.run(cmd, cwd=src, env=env, stdout=out_fh, stderr=err_fh,
                                      text=True, timeout=args.agent_timeout, check=False)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                rc = None
                timed_out = True
                err_fh.write(f"\n[harness] TIMEOUT after {args.agent_timeout}s\n")
        process["wall_time_s"] = round(time.monotonic() - start, 1)
        process["agent_returncode"] = rc
        process["agent_timed_out"] = timed_out
        agent_metrics = parse_agent_output(out_path)
    else:
        # gates-only: recover agent metrics from the previous run's artifacts
        # instead of clobbering them with nulls. Supports both the legacy
        # codebuddy-output.json and the stream-json session-stream.jsonl.
        out_path = run_dir / "session-stream.jsonl"
        if not out_path.exists():
            out_path = run_dir / "codebuddy-output.json"
        if out_path.exists():
            agent_metrics = parse_agent_output(out_path)
        previous: dict[str, Any] = {}
        prev_path = EVAL_DIR / "results" / f"{run_id}.yaml"
        try:
            previous = json.loads(prev_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
        prev_proc = previous.get("process") or {}
        duration_s = agent_metrics.get("agent_duration_ms")
        process["wall_time_s"] = prev_proc.get("wall_time_s") or (
            round(duration_s / 1000, 1) if isinstance(duration_s, (int, float)) else None)
        process["agent_returncode"] = prev_proc.get("agent_returncode")
        process["agent_timed_out"] = prev_proc.get("agent_timed_out")

    # Gate 1: environment fingerprint
    env_result = run_logged([sys.executable, str(ROOT / "scripts" / "capture_environment.py"),
                             "--output", str(run_dir / "environment.json")],
                            run_dir / "environment-gate.log", timeout=120)
    gates["environment"] = "pass" if env_result["returncode"] == 0 else "fail"

    # Gate 2: build (extension importable)
    build_result = run_logged([sys.executable, "-c", "import torch_scatter; print(torch_scatter.__version__)"],
                              run_dir / "build.log", cwd=src, timeout=args.gate_timeout)
    gates["build"] = "pass" if build_result["returncode"] == 0 else "fail"

    # Gate 3: correctness (upstream pytest suite)
    pytest_result = run_logged([sys.executable, "-m", "pytest", "test/", "-q", "--tb=short"],
                               run_dir / "pytest.log", cwd=src, timeout=args.gate_timeout)
    pytest_stats = parse_pytest(run_dir / "pytest.log")
    pytest_stats["returncode"] = pytest_result["returncode"]
    gates["correctness"] = "pass" if pytest_result["returncode"] == 0 else "fail"

    # Gate 4: timing (upstream benchmark scripts only)
    benchmark: dict[str, Any] = {}
    timing_ok = True
    for name, script_args in UPSTREAM_BENCHMARKS.items():
        script = src / "benchmark" / f"{name}.py"
        if not script.exists():
            benchmark[name] = {"returncode": None, "missing": True}
            timing_ok = False
            continue
        result = run_logged([sys.executable, str(script), *script_args],
                            run_dir / f"benchmark-{name}.log",
                            cwd=src, timeout=args.gate_timeout)
        benchmark[name] = {"returncode": result["returncode"], "timed_out": result["timed_out"]}
        timing_ok = timing_ok and result["returncode"] == 0 and not result["timed_out"]
    gates["timing"] = "pass" if (benchmark and timing_ok) else "fail"

    if args.group == "B":
        process["macawiki_queries"] = count_signals(run_dir / "signals")

    results: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "task_id": task["id"],
        "group": args.group,
        "repetition": args.repetition,
        "commit_sha": task["upstream"]["commit_sha"],
        "model": task["agent"]["model"],
        "session_id": session_id,
        "finished_at": now_iso(),
        "environment_fingerprint": _read_fingerprint(run_dir / "environment.json"),
        "gates": gates,
        "pytest": pytest_stats,
        "benchmark": benchmark,
        "process": {**process, **agent_metrics},
        "status": "recorded",
        "reviewed": False,
        "note": "comparability/conclusion gates are computed at report time; "
                "timing-gate warmup/sync compliance requires human log review.",
    }
    write_json(EVAL_DIR / "results" / f"{run_id}.yaml", results)
    print(f"[{run_id}] gates={gates}")
    print(f"[{run_id}] results -> {EVAL_DIR / 'results' / f'{run_id}.yaml'}")
    return 0


def _read_fingerprint(path: Path) -> str | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("environment_fingerprint")
    except (OSError, json.JSONDecodeError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
