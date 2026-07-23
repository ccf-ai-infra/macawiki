#!/usr/bin/env python3
"""Lightweight C500/MXMACA environment probe for the self-evolution pipeline.

Detects whether the current runtime is a C500+MXMACA environment by probing
mx-smi, mxcc, and Python package versions. Reuses the non-invasive probing
patterns from ``benchmarks/env_capture.py``.

On non-MXMACA systems all hardware fields are ``None`` and ``is_c500`` is
``False`` — callers should use :func:`is_mxmaca_env` to gate MXMACA-specific
behaviour.

Usage::

    python3 scripts/env_detector.py              # human-readable report
    python3 scripts/env_detector.py --json       # JSON output
    python3 scripts/env_detector.py --snapshot   # write env-snapshot.json
"""

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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .common import ROOT
except ImportError:
    from common import ROOT  # type: ignore[no-redef]

SIGNAL_DIR = Path(os.environ.get("MACAWIKI_SIGNAL_DIR", ROOT / "evals" / "signals"))
SNAPSHOT_PATH = SIGNAL_DIR / "env-snapshot.json"

# ---------------------------------------------------------------------------
# Cached module-level result — probe once, reuse everywhere
# ---------------------------------------------------------------------------
_cached_env: dict[str, Any] | None = None


@dataclass
class EnvInfo:
    """Immutable environment facts for a single probe."""

    is_c500: bool = False
    device_name: str | None = None
    maca_version: str | None = None
    driver_version: str | None = None
    mxcc_version: str | None = None
    pytorch_version: str | None = None
    tilelang_version: str | None = None
    mxmaca_home: str | None = None
    fingerprint: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Probe helpers (mirror benchmarks/env_capture.py patterns)
# ---------------------------------------------------------------------------


def _command_version(command: str) -> dict[str, Any]:
    """Run *command* ``--version`` and return ``{path, version}``."""
    path = shutil.which(command)
    if not path:
        return {"path": None, "version": None}
    try:
        result = subprocess.run(
            [path, "--version"], text=True, capture_output=True, timeout=15, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"path": path, "version": None}
    return {
        "path": path,
        "version": (result.stdout or result.stderr).strip() or None,
    }


def _mx_smi_facts() -> dict[str, Any]:
    """Parse ``mx-smi`` for device name, MACA version, and driver version.

    Returns nulls when mx-smi is absent or the output layout is unexpected.
    """
    path = shutil.which("mx-smi")
    if not path:
        return {"mx_smi_path": None, "device_name": None, "maca_version": None, "driver_version": None}

    try:
        result = subprocess.run([path], text=True, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"mx_smi_path": path, "device_name": None, "maca_version": None, "driver_version": None}

    text = result.stdout or ""

    # Device name — first column of the GPU table
    device_name: str | None = None
    board_match = re.search(r"^\|\s*\d+\s+([A-Za-z0-9 ]+?)\s+\|", text, re.MULTILINE)
    if board_match:
        candidate = board_match.group(1).strip()
        if candidate:
            device_name = candidate

    # MACA version
    maca_match = re.search(r"MACA\s+Version:\s*([^\s|]+)", text)
    maca_version = maca_match.group(1).strip() if maca_match else None

    # Driver version
    driver_match = re.search(r"Kernel\s+Mode\s+Driver\s+Version:\s*([0-9.]+)", text)
    driver_version = driver_match.group(1).strip() if driver_match else None

    return {
        "mx_smi_path": path,
        "device_name": device_name,
        "maca_version": maca_version,
        "driver_version": driver_version,
    }


def _package_version(name: str) -> str | None:
    """Return the installed version of *name*, or None."""
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect() -> EnvInfo:
    """Probe the current environment and return an :class:`EnvInfo`.

    Caches the raw result at module level so repeated calls are free.
    """
    global _cached_env

    if _cached_env is not None:
        return EnvInfo(**_cached_env)

    mx = _mx_smi_facts()
    mxcc = _command_version("mxcc")
    pytorch_ver = _package_version("torch")
    tilelang_ver = _package_version("tilelang")
    mxmaca_home = os.environ.get("MXMACA_HOME") or os.environ.get("MACA_HOME")

    device_name = mx.get("device_name")
    is_c500 = bool(device_name and "c500" in device_name.casefold())

    # Build fingerprint from version-critical facts
    fp_payload = json.dumps(
        {
            "device_name": device_name,
            "maca_version": mx.get("maca_version"),
            "driver_version": mx.get("driver_version"),
            "mxcc_version": mxcc.get("version"),
            "pytorch_version": pytorch_ver,
            "tilelang_version": tilelang_ver,
        },
        ensure_ascii=False,
        sort_keys=True,
    ).encode()
    fingerprint = hashlib.sha256(fp_payload).hexdigest()

    info = EnvInfo(
        is_c500=is_c500,
        device_name=device_name,
        maca_version=mx.get("maca_version"),
        driver_version=mx.get("driver_version"),
        mxcc_version=mxcc.get("version"),
        pytorch_version=pytorch_ver,
        tilelang_version=tilelang_ver,
        mxmaca_home=mxmaca_home,
        fingerprint=fingerprint,
        extra={
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "mx_smi_path": mx.get("mx_smi_path"),
            "mxcc_path": mxcc.get("path"),
        },
    )

    _cached_env = {
        "is_c500": info.is_c500,
        "device_name": info.device_name,
        "maca_version": info.maca_version,
        "driver_version": info.driver_version,
        "mxcc_version": info.mxcc_version,
        "pytorch_version": info.pytorch_version,
        "tilelang_version": info.tilelang_version,
        "mxmaca_home": info.mxmaca_home,
        "fingerprint": info.fingerprint,
        "extra": info.extra,
    }
    return info


def is_mxmaca_env() -> bool:
    """Return ``True`` if the host is a C500 + MXMACA environment."""
    return detect().is_c500


def snapshot() -> dict[str, Any]:
    """Return a JSON-serialisable dict of the current environment facts."""
    info = detect()
    return {
        "schema_version": 1,
        "captured_by": "scripts/env_detector.py",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "is_c500": info.is_c500,
        "device_name": info.device_name,
        "maca_version": info.maca_version,
        "driver_version": info.driver_version,
        "mxcc_version": info.mxcc_version,
        "pytorch_version": info.pytorch_version,
        "tilelang_version": info.tilelang_version,
        "mxmaca_home": info.mxmaca_home,
        "environment_fingerprint": info.fingerprint,
        "extra": info.extra,
    }


def write_snapshot() -> Path:
    """Probe and write ``evals/signals/env-snapshot.json``.  Returns the path."""
    SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    data = snapshot()
    SNAPSHOT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return SNAPSHOT_PATH


def load_snapshot() -> dict[str, Any] | None:
    """Load the most recent environment snapshot, or *None*."""
    if not SNAPSHOT_PATH.exists():
        return None
    try:
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="Print environment facts as JSON"
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Write env-snapshot.json to evals/signals/",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Exit 0 if C500 detected, 1 otherwise (no output)",
    )
    args = parser.parse_args()

    if args.quiet:
        return 0 if is_mxmaca_env() else 1

    if args.snapshot:
        path = write_snapshot()
        print(f"wrote {path}")
        return 0

    info = detect()
    data = snapshot()

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("=== MXMACA Environment Detection ===")
        print(f"  C500 detected:     {info.is_c500}")
        print(f"  Device name:       {info.device_name or '(n/a)'}")
        print(f"  MACA version:      {info.maca_version or '(n/a)'}")
        print(f"  Driver version:    {info.driver_version or '(n/a)'}")
        print(f"  mxcc version:      {info.mxcc_version or '(n/a)'}")
        print(f"  PyTorch version:   {info.pytorch_version or '(n/a)'}")
        print(f"  TileLang version:  {info.tilelang_version or '(n/a)'}")
        print(f"  MXMACA_HOME:       {info.mxmaca_home or '(n/a)'}")
        print(f"  Fingerprint:       {info.fingerprint[:16]}...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
