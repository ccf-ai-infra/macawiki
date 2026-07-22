#!/usr/bin/env python3
"""Check whether a Macawiki checkout is structurally ready for Agent use."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import ROOT


REQUIRED = [
    "SKILL.md", "AGENTS.md", "CLAUDE.md", "data/schemas.yaml",
    "scripts/query.py", "scripts/validate.py", "benchmarks/README.md",
    ".agents/skills/macawiki/SKILL.md", ".claude/skills/macawiki/SKILL.md",
]


def _run(root: Path, *command: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, *command], cwd=root, text=True, capture_output=True, check=False
    )
    return {
        "ok": result.returncode == 0,
        "command": " ".join(command),
        "detail": (result.stdout or result.stderr).strip().splitlines()[-1] if (result.stdout or result.stderr) else "",
    }


def diagnose(root: Path) -> dict[str, Any]:
    root = root.resolve()
    files = {name: (root / name).is_file() for name in REQUIRED}
    checks = {
        "python": {"ok": sys.version_info >= (3, 9), "version": sys.version.split()[0]},
        "required_files": {"ok": all(files.values()), "files": files},
        "corpus": _run(root, "scripts/validate.py", "--json"),
        "indices": _run(root, "scripts/generate_indices.py", "--check"),
        "pytorch_optional": {
            "ok": True,
            "available": importlib.util.find_spec("torch") is not None,
            "detail": "optional; required only to execute the PyTorch baseline",
        },
    }
    return {"root": str(root), "ready": all(item["ok"] for item in checks.values()), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = diagnose(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Macawiki doctor: {'READY' if report['ready'] else 'NOT READY'}")
        for name, check in report["checks"].items():
            suffix = check.get("detail") or check.get("version") or ""
            print(f"  {'PASS' if check['ok'] else 'FAIL'} {name}: {suffix}")
        if not report["checks"]["pytorch_optional"]["available"]:
            print("  INFO PyTorch not found; corpus use is unaffected and baseline execution is skipped.")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
