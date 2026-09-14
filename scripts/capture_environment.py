#!/usr/bin/env python3
"""Capture non-invasive environment facts for a future MXMACA run."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
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


# Compute libraries whose presence/absence the corpus claims versions for.
# Recorded as evidence so a claim about mcBLAS/mcCL/mcDNN can be traced to a
# committed artifact instead of an unverifiable assertion.
_MACA_LIB_DIRS = ("/opt/maca/lib", "/opt/maca/lib64")
_MACA_LIBS = ("libmcblas.so", "libmccl.so", "libmcdnn.so", "libmcblasLt.so")
_MACA_TOOLS = {
    "mcTracer": "/opt/maca/bin/mcTracer",
    "macainfo": "/opt/maca/bin/macainfo",
    "mcclras": "/opt/maca/bin/mcclras",
    "mxvs": "/opt/maca/bin/mxvs",
    "mcProfiler": None,  # resolved from PATH
}

# Hostname is redacted by default: this artifact is committed to the repo and
# a machine name is not evidence for any MXMACA claim. --keep-hostname is for
# local debugging only.
_REDACTED = "<redacted>"

# Some tools (macainfo) dump full device topology on --version. That output is
# evidence for the device name and capabilities, but it also carries hardware
# UUIDs/serials and bloats the committed artifact, so it is capped and scrubbed.
_MAX_TOOL_OUTPUT = 2000
_UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                      r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")


def _sanitize_tool_output(text: str) -> str:
    """Redact hardware UUIDs and cap length in tool output bound for the repo."""
    scrubbed = _UUID_RE.sub("<uuid-redacted>", text)
    if len(scrubbed) <= _MAX_TOOL_OUTPUT:
        return scrubbed
    return scrubbed[:_MAX_TOOL_OUTPUT] + f"\n[truncated: {len(scrubbed)} chars total]"


def _library_inventory() -> dict[str, dict[str, str | None]]:
    """Locate each MACA compute library, following the /opt/maca symlink farm."""
    inventory: dict[str, dict[str, str | None]] = {}
    for name in _MACA_LIBS:
        entry: dict[str, str | None] = {"path": None, "real_path": None}
        for lib_dir in _MACA_LIB_DIRS:
            candidate = Path(lib_dir) / name
            if candidate.is_file():
                entry["path"] = str(candidate)
                try:
                    entry["real_path"] = str(candidate.resolve())
                except OSError:
                    entry["real_path"] = None
                break
        inventory[name] = entry
    return inventory


def _tool_inventory() -> dict[str, dict[str, str | int | None]]:
    tools: dict[str, dict[str, str | int | None]] = {}
    for name, hint in _MACA_TOOLS.items():
        path = shutil.which(name) or (hint if hint and Path(hint).exists() else None)
        if not path:
            tools[name] = {"path": None, "version": None}
            continue
        # mcTracer's --version is a trap: it treats the flag as a target program
        # to launch, exits 0, and prints no version at all. Its version string
        # lives in --help output. Probing --version first keeps a truthful
        # record of the attempt for every other tool.
        version_args = ["--help"] if name == "mcTracer" else ["--version"]
        result = subprocess.run([path, *version_args], text=True, capture_output=True,
                                timeout=15, check=False)
        raw = (result.stdout or result.stderr).strip() or None
        tools[name] = {
            "path": path,
            "version": _sanitize_tool_output(raw) if raw else None,
            "returncode": result.returncode,
            "version_args": version_args,
        }
    return tools


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--keep-hostname", action="store_true",
                        help="keep the real hostname (default: redact; the artifact is committed)")
    args = parser.parse_args()
    packages = {}
    for name in ("torch", "tilelang", "triton"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    facts = {
        "schema_version": 2,
        "captured_by": "scripts/capture_environment.py",
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node() if args.keep_hostname else _REDACTED,
        "env": {key: os.environ.get(key) for key in ("MXMACA_HOME", "MACA_HOME", "CUDA_VISIBLE_DEVICES") if key in os.environ},
        "commands": {name: command_version(name) for name in ("mx-smi", "mxcc", "nvidia-smi")},
        "tools": _tool_inventory(),
        "maca_libraries": _library_inventory(),
        "python_packages": packages,
        "notes": [
            "Command and library absence is recorded as null; this script never infers MXMACA support from CUDA.",
            "Hostname is redacted by default because this artifact is committed to the repository.",
            "maca_libraries records install evidence only; it does not assert API compatibility or performance.",
        ],
    }
    # The fingerprint must be stable across captures of the same machine, so
    # it is computed over the redacted form rather than the live hostname.
    fingerprint_payload = json.dumps(facts, ensure_ascii=False, sort_keys=True).encode()
    facts["environment_fingerprint"] = hashlib.sha256(fingerprint_payload).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(facts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
