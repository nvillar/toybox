#!/usr/bin/env python3
"""Generate an image (texture, background, sprite, concept) from a prompt.

Stable interface; the backend is chosen per platform (see notes/platforms.md).

Usage:
  python3 scripts/gen/image.py --prompt "mossy cobblestone, tileable" \
      --width 1024 --height 1024 --out out/tex_cobble.png [--seed 42] [--model flux2-klein-4b]

Writes the image plus <out>.json provenance.

Backends:
  mflux (macos-arm64) - MFLUX. FLUX.2 Klein via `mflux-generate-flux2`;
    Qwen-Image-2.1 (non-commercial) via `mflux-generate-qwen-2.1`.
    Tested 2026-09-23 with mflux 0.20.0 (mlx 0.32.2) on M4 Max.
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toybox_gen import Backend, Request, Result, generate, pick_backend, resolve_seed, run_command  # noqa: E402

MFLUX_LICENSES = {
    "flux2-klein-4b": "Apache-2.0",
    "flux2-klein-base-4b": "Apache-2.0",
    "flux2-klein-9b": "FLUX Non-Commercial",
    "flux2-klein-9b-kv": "FLUX Non-Commercial",
    "flux2-klein-base-9b": "FLUX Non-Commercial",
    "qwen-image-2.1": "Qwen Research License (non-commercial)",
}
MFLUX_COMMANDS = {"qwen-image-2.1": "mflux-generate-qwen-2.1"}


def _package_versions(exe: str, packages: list[str]) -> dict[str, str]:
    """Ask the interpreter behind a console script (its shebang) for package versions."""
    try:
        with open(exe, "rb") as f:
            first = f.readline().decode(errors="replace").strip()
        if not first.startswith("#!"):
            raise ValueError("console script has no interpreter shebang")
        interpreter = shlex.split(first[2:].strip())
        if not interpreter:
            raise ValueError("console script has an empty interpreter shebang")
        code = (
            "import importlib.metadata as m, json\n"
            f"print(json.dumps({{p: m.version(p) for p in {packages!r}}}))"
        )
        out = subprocess.run(
            [*interpreter, "-c", code], capture_output=True, text=True, timeout=30, check=True
        )
        versions = json.loads(out.stdout)
        if not isinstance(versions, dict) or any(
            not isinstance(versions.get(package), str) for package in packages
        ):
            raise ValueError("interpreter returned invalid package versions")
        return versions
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"warning: could not record package versions for {exe}: {error}", file=sys.stderr)
        return {}


def _run_mflux(req: Request) -> Result:
    model = str(req.params["model"])
    command = MFLUX_COMMANDS.get(model, "mflux-generate-flux2")
    exe = shutil.which(command)
    if not exe:
        sys.exit(f"{command} not found; install/upgrade with: uv tool install --upgrade mflux --with hf-transfer")
    cmd = [exe] + (["--model", model] if command == "mflux-generate-flux2" else [])
    cmd += [
        "--prompt", req.prompt,
        "--width", str(req.params["width"]),
        "--height", str(req.params["height"]),
        "--seed", str(req.seed),
        "--output", str(req.out),
    ]
    if req.params.get("steps"):
        cmd += ["--steps", str(req.params["steps"])]
    if req.params.get("quantize"):
        cmd += ["--quantize", str(req.params["quantize"])]
    run_command(cmd)
    return Result(
        backend="mflux",
        model=model,
        command=cmd,
        license=MFLUX_LICENSES.get(model, "unknown - check model card"),
        versions=_package_versions(exe, ["mflux", "mlx"]),
    )


BACKENDS = [
    Backend("mflux", ["macos-arm64"], _run_mflux, "MFLUX (MLX) FLUX.2 Klein"),
]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prompt", required=True)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=1024)
    p.add_argument("--seed", type=int)
    p.add_argument("--steps", type=int, help="backend default if omitted")
    p.add_argument(
        "--model",
        default="flux2-klein-4b",
        help="flux2-klein-4b (default, Apache-2.0), flux2-klein-9b, qwen-image-2.1 (both non-commercial)",
    )
    p.add_argument("--quantize", type=int, choices=[3, 4, 5, 6, 8])
    p.add_argument("--backend", help="force a backend: " + ", ".join(b.name for b in BACKENDS))
    a = p.parse_args()

    req = Request(
        capability="image.generate",
        prompt=a.prompt,
        out=a.out.resolve(),
        seed=resolve_seed(a.seed),
        params={"width": a.width, "height": a.height, "steps": a.steps, "model": a.model, "quantize": a.quantize},
    )
    generate(pick_backend(BACKENDS, a.backend), req)


if __name__ == "__main__":
    main()
