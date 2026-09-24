"""Shared helpers for toybox generation wrappers.

Each wrapper (image.py, audio.py) exposes one stable CLI and dispatches to a
platform-specific backend. Backends are registered per platform id; add new
ones (CUDA, ROCm, hosted APIs) without changing the wrapper interface.

Stdlib only; runs on the macOS system Python (3.9+).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import random
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
PLATFORMS_NOTE = "notes/platforms.md"


def detect_platform() -> str:
    """Return a coarse platform id: macos-arm64, <os>-cuda, <os>-rocm, <os>-cpu."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin":
        return "macos-arm64" if machine in ("arm64", "aarch64") else "macos-x86_64"
    os_id = "windows" if system == "windows" else system
    if shutil.which("nvidia-smi"):
        return f"{os_id}-cuda"
    if shutil.which("rocminfo") or shutil.which("rocm-smi") or shutil.which("hipinfo"):
        return f"{os_id}-rocm"
    return f"{os_id}-cpu"


@dataclass
class Backend:
    name: str
    platforms: List[str]
    run: Callable[["Request"], "Result"]
    description: str = ""


@dataclass
class Request:
    capability: str
    prompt: str
    out: Path
    seed: int
    params: Dict[str, object] = field(default_factory=dict)


@dataclass
class Result:
    backend: str
    model: str
    command: List[str]
    license: str
    versions: Dict[str, str] = field(default_factory=dict)


def pick_backend(backends: List[Backend], requested: Optional[str]) -> Backend:
    plat = detect_platform()
    if requested:
        for b in backends:
            if b.name == requested:
                return b
        sys.exit(f"unknown backend {requested!r}; known: {[b.name for b in backends]}")
    for b in backends:
        if plat in b.platforms:
            return b
    sys.exit(
        f"no verified backend for platform {plat!r} yet. "
        f"See {PLATFORMS_NOTE} for candidates, then register one in {Path(sys.argv[0]).name}."
    )


def resolve_seed(seed: Optional[int]) -> int:
    return seed if seed is not None else random.randint(0, 2**31 - 1)


def run_command(cmd: List[str]) -> None:
    print("+", " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        sys.exit(proc.returncode)


def env_path(var: str, default: Path) -> Path:
    value = os.environ.get(var)
    return Path(value).expanduser() if value else default


def git_rev(path: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def write_sidecar(req: Request, res: Result, elapsed_s: float) -> Path:
    """Write <out>.json provenance next to the generated asset."""
    sidecar = req.out.with_suffix(req.out.suffix + ".json")
    data = {
        "capability": req.capability,
        "prompt": req.prompt,
        "seed": req.seed,
        "params": req.params,
        "backend": res.backend,
        "model": res.model,
        "license": res.license,
        "versions": res.versions,
        "platform": detect_platform(),
        "command": res.command,
        "elapsed_s": round(elapsed_s, 2),
        "created": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    sidecar.write_text(json.dumps(data, indent=2) + "\n")
    return sidecar


def generate(backend: Backend, req: Request) -> None:
    req.out.parent.mkdir(parents=True, exist_ok=True)
    if req.out.exists():
        req.out.unlink()
    started = time.monotonic()
    res = backend.run(req)
    elapsed = time.monotonic() - started
    if not req.out.exists():
        sys.exit(f"backend {backend.name} finished but {req.out} was not written")
    sidecar = write_sidecar(req, res, elapsed)
    print(f"wrote {req.out} ({elapsed:.1f}s, seed {req.seed})\nwrote {sidecar}")
