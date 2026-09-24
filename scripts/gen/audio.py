#!/usr/bin/env python3
"""Generate a sound effect or music clip from a prompt.

Stable interface; the backend is chosen per platform (see notes/platforms.md).

Usage:
  python3 scripts/gen/audio.py --kind sfx   --prompt "coin pickup, bright chime" --seconds 2  --out out/sfx_coin.wav
  python3 scripts/gen/audio.py --kind music --prompt "chiptune adventure 120 BPM" --seconds 30 --out out/mus_theme.wav

Writes a 44.1 kHz stereo 16-bit WAV plus <out>.json provenance.

Backends:
  sa3-mlx (macos-arm64) - Stability AI's official Stable Audio 3 MLX CLI (`sa3`).
    Tested 2026-09-23 on M4 Max with sm-sfx / sm-music + same-s decoder.
    Location: $TOYBOX_SA3_MLX or sandbox/tools/stable-audio-3/optimized/mlx/sa3
    (install: scripts/setup/macos.sh).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toybox_gen import (  # noqa: E402
    REPO_ROOT,
    Backend,
    Request,
    Result,
    env_path,
    generate,
    git_rev,
    pick_backend,
    resolve_seed,
    run_command,
)

SA3_DEFAULT = REPO_ROOT / "sandbox/tools/stable-audio-3/optimized/mlx/sa3"
SA3_DIT = {"sfx": "sm-sfx", "music": "sm-music"}
SA3_LICENSE = "Stability AI Community License (T5Gemma: Gemma Terms of Use)"


def _run_sa3_mlx(req: Request) -> Result:
    sa3 = env_path("TOYBOX_SA3_MLX", SA3_DEFAULT)
    if not sa3.exists():
        sys.exit(f"sa3 not found at {sa3}; run scripts/setup/macos.sh or set TOYBOX_SA3_MLX")
    dit = str(req.params.get("dit") or SA3_DIT[str(req.params["kind"])])
    decoder = "same-l" if dit == "medium" else "same-s"
    cmd = [
        str(sa3),
        "--prompt", req.prompt,
        "--dit", dit,
        "--decoder", decoder,
        "--seconds", str(req.params["seconds"]),
        "--seed", str(req.seed),
        "--out", str(req.out),
    ]
    if req.params.get("steps"):
        cmd += ["--steps", str(req.params["steps"])]
    run_command(cmd)
    return Result(
        backend="sa3-mlx",
        model=f"stable-audio-3 {dit} + {decoder}",
        command=cmd,
        license=SA3_LICENSE,
        versions={"stable-audio-3": git_rev(sa3.parent)},
    )


BACKENDS = [
    Backend("sa3-mlx", ["macos-arm64"], _run_sa3_mlx, "Stable Audio 3 official MLX runtime"),
]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kind", choices=sorted(SA3_DIT), required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--seconds", type=float, default=2.0)
    p.add_argument("--seed", type=int)
    p.add_argument("--steps", type=int, help="backend default if omitted")
    p.add_argument("--dit", choices=["sm-sfx", "sm-music", "medium"], help="override model choice")
    p.add_argument("--backend", help="force a backend: " + ", ".join(b.name for b in BACKENDS))
    a = p.parse_args()

    req = Request(
        capability=f"audio.{a.kind}",
        prompt=a.prompt,
        out=a.out.resolve(),
        seed=resolve_seed(a.seed),
        params={"kind": a.kind, "seconds": a.seconds, "steps": a.steps, "dit": a.dit},
    )
    generate(pick_backend(BACKENDS, a.backend), req)


if __name__ == "__main__":
    main()
