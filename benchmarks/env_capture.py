#!/usr/bin/env python3
"""Capture reproducibility provenance for C500 benchmark runs.

This is a non-invasive environment probe shared by ``pytorch_baseline.py``
and ``tilelang_candidate.py`` so that every recorded result JSON carries the
same reproducibility facts required by ``docs/hardware-validation.md``:
hardware model, driver/MACA/mxcc versions, python/torch/tilelang versions, the
source ref, and the exact run command. It never infers MXMACA support from
CUDA, and missing commands are recorded as ``null`` rather than guessed.
"""

from __future__ import annotations

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
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TILELANG_ROOT = Path("/opt/tilelang-metax")
TILELANG_COMMIT_FILE = TILELANG_ROOT / ".git_commit.txt"


def _command_version(command: str) -> dict[str, Any]:
    path = shutil.which(command)
    if not path:
        return {"path": None, "version": None}
    result = subprocess.run([path, "--version"], text=True, capture_output=True, check=False)
    return {"path": path, "version": (result.stdout or result.stderr).strip() or None}


def _mx_smi_facts() -> dict[str, Any]:
    """Parse mx-smi for hardware model, MACA version, and driver version.

    Returns nulls when mx-smi is absent or the layout is unexpected; it never
    fabricates hardware facts from a CUDA-style query.
    """
    path = shutil.which("mx-smi")
    if not path:
        return {"mx_smi_path": None, "device_name": None, "maca_version": None, "driver_version": None}
    result = subprocess.run([path], text=True, capture_output=True, check=False, timeout=30)
    text = result.stdout or ""
    device_name = None
    board_match = re.search(r"^\|\s*\d+\s+([A-Za-z0-9 ]+?)\s+\|", text, re.MULTILINE)
    if board_match:
        candidate = board_match.group(1).strip()
        if candidate:
            device_name = candidate
    maca_match = re.search(r"MACA Version:\s*([^\s|]+)", text)
    driver_match = re.search(r"Kernel Mode Driver Version:\s*([0-9.]+)", text)
    return {
        "mx_smi_path": path,
        "device_name": device_name,
        "maca_version": (maca_match.group(1).strip() if maca_match else None),
        "driver_version": (driver_match.group(1).strip() if driver_match else None),
    }


def _python_package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def tilelang_source_ref(tilelang_module: Any | None = None) -> dict[str, Any]:
    """Return the TileLang source ref, or nulls when TileLang is not importable."""
    version = getattr(tilelang_module, "__version__", None) if tilelang_module is not None else None
    source_commit = None
    try:
        source_commit = TILELANG_COMMIT_FILE.read_text(encoding="utf-8").strip() or None
    except OSError:
        source_commit = None
    return {
        "tilelang_version": version,
        "source_root": str(TILELANG_ROOT) if TILELANG_ROOT.exists() else None,
        "source_commit": source_commit,
        "target": "maca",
        "license": "see /opt/tilelang-metax/LICENSE and THIRDPARTYNOTICES.txt",
    }


def environment(torch_module: Any | None, device: Any | None, *, backend: str, include_tilelang: bool, tilelang_module: Any | None = None) -> dict[str, Any]:
    """Build the reproducibility environment block for a result JSON.

    The fingerprint only covers facts that must match for two backends to be
    comparable (torch, device, platform), so ``compare_benchmarks.py`` keeps
    its existing equality check. Hardware/driver facts are recorded alongside
    for human reproducibility but intentionally excluded from the fingerprint.
    """
    device_name = None
    if torch_module is not None and device is not None and device.type == "cuda" and hasattr(torch_module, "cuda"):
        try:
            device_name = torch_module.cuda.get_device_name(0)
        except Exception:
            device_name = None
    mx_facts = _mx_smi_facts()
    env: dict[str, Any] = {
        "python": platform.python_version(),
        "torch": getattr(torch_module, "__version__", None) if torch_module is not None else None,
        "device": str(device) if device is not None else None,
        "device_name": device_name or mx_facts.get("device_name"),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "maca_version": mx_facts.get("maca_version"),
        "driver_version": mx_facts.get("driver_version"),
        "mxcc": _command_version("mxcc"),
        "nvidia_smi": _command_version("nvidia-smi"),
        "env_vars": {key: os.environ.get(key) for key in ("MXMACA_HOME", "MACA_HOME", "CUDA_VISIBLE_DEVICES") if key in os.environ},
        "python_packages": {
            "torch": _python_package_version("torch"),
            "tilelang": _python_package_version("tilelang"),
        },
    }
    if include_tilelang:
        env["tilelang"] = getattr(tilelang_module, "__version__", None) if tilelang_module is not None else None
        env["tilelang_source_ref"] = tilelang_source_ref(tilelang_module)
    fingerprint_payload = json.dumps(
        {"torch": env["torch"], "device": env["device"], "platform": env["platform"]},
        sort_keys=True,
    ).encode()
    env["environment_fingerprint"] = hashlib.sha256(fingerprint_payload).hexdigest()
    return env


def provenance(run_command: str, *, capture_command: str | None = None, notes: list[str] | None = None) -> dict[str, Any]:
    """Record how a result was produced, for the ``docs/hardware-validation.md``
    report gate (run command, capture command, and any caveats)."""
    facts: dict[str, Any] = {
        "run_command": run_command,
        "capture_command": capture_command,
        "captured_by": "benchmarks/env_capture.py",
    }
    if notes:
        facts["notes"] = notes
    return facts
