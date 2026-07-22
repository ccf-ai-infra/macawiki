#!/usr/bin/env python3
"""Capture non-invasive environment facts for a future MXMACA run."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def command_version(command: str) -> dict[str, str | int | None]:
    path = shutil.which(command)
    if not path:
        return {"path": None, "version": None}
    result = subprocess.run([path, "--version"], text=True, capture_output=True, check=False)
    return {"path": path, "version": (result.stdout or result.stderr).strip() or None, "returncode": result.returncode}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packages = {}
    for name in ("torch", "tilelang"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    facts = {
        "schema_version": 1,
        "captured_by": "scripts/capture_environment.py",
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "env": {key: os.environ.get(key) for key in ("MXMACA_HOME", "MACA_HOME", "CUDA_VISIBLE_DEVICES") if key in os.environ},
        "commands": {name: command_version(name) for name in ("mx-smi", "mxcc", "nvidia-smi")},
        "python_packages": packages,
        "notes": ["Command absence is recorded as null; this script never infers MXMACA support from CUDA.", "Review and redact host identifiers before publishing."],
    }
    fingerprint_payload = json.dumps(facts, ensure_ascii=False, sort_keys=True).encode()
    facts["environment_fingerprint"] = hashlib.sha256(fingerprint_payload).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(facts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
