#!/usr/bin/env python3
"""Lightweight C500/MXMACA environment probe for the self-evolution pipeline.

Detects whether the current runtime is a C500+MXMACA environment by probing
mx-smi, mxcc, macainfo, mcTracer, and Python package versions.  Reuses the
non-invasive probing patterns from ``benchmarks/env_capture.py``.

In **deep mode** (``--deep``) also inventories all MACA libraries (with MD5
checksums), MetaX-specific pip packages, and device topology from macainfo.

On non-MXMACA systems all hardware fields are ``None`` and ``is_c500`` is
``False`` — callers should use :func:`is_mxmaca_env` to gate MXMACA-specific
behaviour.

Usage::

    python3 scripts/env_detector.py               # human-readable report
    python3 scripts/env_detector.py --json        # JSON output (basic)
    python3 scripts/env_detector.py --deep --json # JSON with full inventory
    python3 scripts/env_detector.py --snapshot    # write env-snapshot.json
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
# Known MACA tool paths (not always on PATH)
# ---------------------------------------------------------------------------
_KNOWN_MACA_BIN = Path("/opt/maca/bin")
_KNOWN_TILELANG_ROOT = Path("/opt/tilelang-metax")
_KNOWN_DRIVER_BIN = Path("/opt/mxdriver/bin")

# ---------------------------------------------------------------------------
# Cached module-level result — probe once, reuse everywhere
# ---------------------------------------------------------------------------
_cached_env: dict[str, Any] | None = None
_cached_deep: dict[str, Any] | None = None


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
    tilelang_path: str | None = None
    mxmaca_home: str | None = None
    fingerprint: str = ""
    tools: dict[str, dict[str, Any]] = field(default_factory=dict)
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


def _which_any(*names: str) -> str | None:
    """Return the first found path among *names*, checking PATH and known dirs."""
    for name in names:
        p = shutil.which(name)
        if p:
            return p
    for name in names:
        for base in (_KNOWN_MACA_BIN, _KNOWN_DRIVER_BIN):
            candidate = base / name
            if candidate.exists():
                return str(candidate)
    return None


def _run_tool(path: str, *args: str, timeout: int = 15) -> subprocess.CompletedProcess[str] | None:
    """Run a tool safely, returning the CompletedProcess or None on failure."""
    try:
        return subprocess.run(
            [path, *args], text=True, capture_output=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _mx_smi_facts() -> dict[str, Any]:
    """Parse ``mx-smi`` for device name, MACA version, driver version, and GPU metrics.

    Returns nulls when mx-smi is absent or the output layout is unexpected.
    """
    path = shutil.which("mx-smi")
    if not path:
        return {"mx_smi_path": None, "device_name": None, "maca_version": None,
                "driver_version": None}

    result = _run_tool(path, timeout=30)
    if result is None:
        return {"mx_smi_path": path, "device_name": None, "maca_version": None,
                "driver_version": None}

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

    # Driver version (from mx-smi header)
    driver_match = re.search(r"Kernel\s+Mode\s+Driver\s+Version:\s*([0-9.]+)", text)
    driver_version = driver_match.group(1).strip() if driver_match else None

    # GPU utilisation and memory
    gpu_util_match = re.search(r"(\d+)%\s+sGPU-M", text)
    mem_usage_match = re.search(r"(\d+)/(\d+)\s+MiB", text)
    pwr_match = re.search(r"(\d+)W\s*/\s*(\d+)W", text)
    temp_match = re.search(r"(\d+)C\s+P\d", text)

    metrics: dict[str, Any] = {}
    if gpu_util_match:
        metrics["gpu_util_pct"] = int(gpu_util_match.group(1))
    if mem_usage_match:
        metrics["memory_used_mib"] = int(mem_usage_match.group(1))
        metrics["memory_total_mib"] = int(mem_usage_match.group(2))
    if pwr_match:
        metrics["power_w"] = int(pwr_match.group(1))
        metrics["power_cap_w"] = int(pwr_match.group(2))
    if temp_match:
        metrics["temp_c"] = int(temp_match.group(1))

    return {
        "mx_smi_path": path,
        "device_name": device_name,
        "maca_version": maca_version,
        "driver_version": driver_version,
        "metrics": metrics,
    }


def _parse_macainfo() -> dict[str, Any]:
    """Parse ``macainfo`` for device topology (CPU/GPU agents, memory pools)."""
    path = _which_any("macainfo")
    if not path:
        return {"available": False, "error": "macainfo not found"}

    result = _run_tool(path, timeout=15)
    if result is None or result.returncode != 0:
        return {"available": True, "path": path, "error": "macainfo failed"}

    text = result.stdout or ""
    agents: list[dict[str, Any]] = []
    current_agent: dict[str, Any] | None = None

    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("Agent "):
            if current_agent:
                agents.append(current_agent)
            current_agent = {"agent_id": line.rstrip(":")}
        elif current_agent is not None and ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val:
                current_agent[key] = val

    if current_agent:
        agents.append(current_agent)

    return {
        "available": True,
        "path": path,
        "agent_count": len(agents),
        "agents": agents,
    }


def _probe_tilelang() -> dict[str, Any]:
    """Auto-detect TileLang, trying standard locations via sys.path."""
    result: dict[str, Any] = {"available": False, "version": None, "path": None, "source_commit": None}

    # Check if TileLang root exists
    if _KNOWN_TILELANG_ROOT.exists():
        result["path"] = str(_KNOWN_TILELANG_ROOT)
        commit_file = _KNOWN_TILELANG_ROOT / ".git_commit.txt"
        if commit_file.exists():
            result["source_commit"] = commit_file.read_text(encoding="utf-8").strip()

    # Insert TileLang into sys.path before attempting import
    # (os.environ["PYTHONPATH"] changes are ineffective after Python has started)
    saved_path = list(sys.path)
    try:
        if _KNOWN_TILELANG_ROOT.exists():
            sys.path.insert(0, str(_KNOWN_TILELANG_ROOT))

        try:
            import tilelang  # type: ignore[import-untyped]
            result["available"] = True
            result["version"] = getattr(tilelang, "__version__", None)
            result["path"] = str(_KNOWN_TILELANG_ROOT)
        except ImportError:
            pass
    finally:
        sys.path[:] = saved_path

    return result


def _inventory_maca_tools() -> dict[str, dict[str, Any]]:
    """Inventory all discoverable MACA tools with versions."""
    tools: dict[str, dict[str, Any]] = {}

    # Tools on PATH
    for name in ("mx-smi", "mxcc", "mx-diagease", "mx-report"):
        info = _command_version(name)
        tools[name] = {"path": info["path"], "version": info.get("version")}

    # Tools at known paths (not always on PATH)
    known_tools = {
        "mcTracer": _KNOWN_MACA_BIN / "mcTracer",
        "macainfo": _KNOWN_MACA_BIN / "macainfo",
        "mxvs": _KNOWN_MACA_BIN / "mxvs",
        "mcclras": _KNOWN_MACA_BIN / "mcclras",
    }
    for name, tool_path in known_tools.items():
        if tool_path.exists():
            result = _run_tool(str(tool_path), "--help", timeout=10)
            version_line = ""
            if result and (result.stdout or result.stderr):
                # mcTracer prints version like "3.7.1.5-ef9e10e" after "***** Version:"
                text = result.stderr or result.stdout
                # Look for a 4-part version pattern (X.Y.Z.W) near "Version:"
                ver_match = re.search(r"Version:[\s\S]*?([\d]{1,4}\.[\d]{1,4}\.[\d]{1,4}\.[\d]{1,4}(?:-[a-f0-9]+)?)", text)
                version_line = ver_match.group(1) if ver_match else ""
            tools[name] = {"path": str(tool_path), "version": version_line or None}
        else:
            tools[name] = {"path": None, "version": None}

    return tools


def _inventory_maca_libs() -> dict[str, str]:
    """Inventory key MACA shared libraries with MD5 checksums."""
    libs: dict[str, str] = {}
    for lib_dir in ("/opt/maca/lib", "/opt/maca/lib64"):
        p = Path(lib_dir)
        if not p.exists():
            continue
        for lib in sorted(p.glob("libmc*.so")):
            try:
                md5 = hashlib.md5(lib.read_bytes()).hexdigest()
                libs[lib.name] = md5
            except OSError:
                libs[lib.name] = "unreadable"
    return libs


def _inventory_pip_packages() -> list[dict[str, str]]:
    """List MetaX/MXMACA-related pip packages with versions."""
    meta_packages: list[dict[str, str]] = []
    meta_pattern = re.compile(r"metax|maca.tile|mctlass|tilelang|causal.conv|apex|flash.attn|flash.mla|flashinfer|triton|vllm|sglang|xformers|deep.ep|mamba.ssm|sageattention|sparge|spconv|fused.dense|hstu.attn|rotary.emb|xentropy|dropout.layer|torchcodec|cute", re.IGNORECASE)
    try:
        for dist in importlib.metadata.distributions():
            name = dist.metadata.get("Name", "")
            version = dist.metadata.get("Version", "")
            if name and version and meta_pattern.search(name):
                meta_packages.append({"name": name, "version": version})
    except Exception:
        pass
    meta_packages.sort(key=lambda x: x["name"].casefold())
    return meta_packages


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
    tilelang_info = _probe_tilelang()
    tools = _inventory_maca_tools()
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
            "tilelang_version": tilelang_info.get("version"),
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
        tilelang_version=tilelang_info.get("version"),
        tilelang_path=tilelang_info.get("path"),
        mxmaca_home=mxmaca_home,
        fingerprint=fingerprint,
        tools=tools,
        extra={
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "mx_smi_path": mx.get("mx_smi_path"),
            "mx_smi_metrics": mx.get("metrics", {}),
            "mxcc_path": mxcc.get("path"),
            "tilelang_source_commit": tilelang_info.get("source_commit"),
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
        "tilelang_path": info.tilelang_path,
        "mxmaca_home": info.mxmaca_home,
        "fingerprint": info.fingerprint,
        "tools": info.tools,
        "extra": info.extra,
    }
    return info


def is_mxmaca_env() -> bool:
    """Return ``True`` if the host is a C500 + MXMACA environment."""
    return detect().is_c500


def snapshot() -> dict[str, Any]:
    """Return a JSON-serialisable dict of basic environment facts."""
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
        "tilelang_path": info.tilelang_path,
        "mxmaca_home": info.mxmaca_home,
        "environment_fingerprint": info.fingerprint,
        "tools": {k: {"path": v["path"], "version": v["version"]} for k, v in info.tools.items()},
        "extra": info.extra,
    }


def deep_snapshot() -> dict[str, Any]:
    """Return a full environment snapshot including pip packages, MACA libraries,
    and device topology.  Cached after first call."""
    global _cached_deep
    if _cached_deep is not None:
        return _cached_deep

    base = snapshot()
    base["schema_version"] = 2  # deep snapshot uses schema v2
    base["pip_packages"] = _inventory_pip_packages()
    base["maca_libraries"] = _inventory_maca_libs()
    base["macainfo"] = _parse_macainfo()
    base["tilelang"] = _probe_tilelang()

    _cached_deep = base
    return base


def write_snapshot() -> Path:
    """Probe and write ``evals/signals/env-snapshot.json``.  Returns the path."""
    SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    data = snapshot()
    SNAPSHOT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return SNAPSHOT_PATH


def write_deep_snapshot() -> Path:
    """Probe and write a deep snapshot to ``evals/signals/env-snapshot-deep.json``."""
    SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    data = deep_snapshot()
    deep_path = SIGNAL_DIR / "env-snapshot-deep.json"
    deep_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return deep_path


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
        "--deep",
        action="store_true",
        help="Include pip packages, MACA libraries, and macainfo topology",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Write env-snapshot.json to evals/signals/ (use --deep for full inventory)",
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
        if args.deep:
            path = write_deep_snapshot()
        else:
            path = write_snapshot()
        print(f"wrote {path}")
        return 0

    if args.deep:
        data = deep_snapshot()
    else:
        info = detect()
        data = snapshot()

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        info = detect()
        print("=== MXMACA Environment Detection ===")
        print(f"  C500 detected:     {info.is_c500}")
        print(f"  Device name:       {info.device_name or '(n/a)'}")
        print(f"  MACA version:      {info.maca_version or '(n/a)'}")
        print(f"  Driver version:    {info.driver_version or '(n/a)'}")
        print(f"  mxcc version:      {info.mxcc_version or '(n/a)'}")
        print(f"  PyTorch version:   {info.pytorch_version or '(n/a)'}")
        print(f"  TileLang version:  {info.tilelang_version or '(n/a)'}")
        print(f"  TileLang path:     {info.tilelang_path or '(n/a)'}")
        print(f"  MXMACA_HOME:       {info.mxmaca_home or '(n/a)'}")
        print(f"  Fingerprint:       {info.fingerprint[:16]}...")
        print()
        print("  --- MACA Tools ---")
        for name, t in sorted(info.tools.items()):
            status = "✓" if t.get("path") else "✗"
            ver = t.get("version", "")
            if ver and len(ver) > 60:
                ver = ver[:57] + "..."
            print(f"  {status} {name}: {ver or '(version unknown)'}")

        if args.deep:
            d = deep_snapshot()
            print()
            print(f"  --- MACA Libraries ({len(d.get('maca_libraries', {}))} libs) ---")
            for lib, csum in sorted(d.get("maca_libraries", {}).items()):
                print(f"  {lib}: {csum[:16]}...")
            print()
            print(f"  --- MetaX Pip Packages ({len(d.get('pip_packages', []))} pkgs) ---")
            for pkg in d.get("pip_packages", []):
                print(f"  {pkg['name']}=={pkg['version']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
