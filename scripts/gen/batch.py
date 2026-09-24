#!/usr/bin/env python3
"""Generate a batch of images from a JSON shot list (concept art, texture sets, variations).

Each shot's prompt is combined with a shared style suffix, so a set stays visually
consistent. Every image goes through scripts/gen/image.py, so the per-platform
backend and the provenance sidecars apply. Existing outputs are skipped unless
--force is given, so a batch can be extended or re-run cheaply.

Usage:
  python3 scripts/gen/batch.py SPEC.json --out-dir out/concept/example [--only id1,id2] [--force] [--dry-run]

Spec format:
  {
    "style": "shared style suffix appended to every prompt",
    "defaults": {"width": 1344, "height": 768, "model": "flux2-klein-4b", "seeds": [1, 2]},
    "shots": [
      {"id": "scene", "prompt": "subject description", "seeds": [3], "model": "qwen-image-2.1",
       "width": 1024, "height": 1024, "style": false}
    ]
  }
Per-shot keys override defaults. "style": false skips the suffix; a string replaces it.
Outputs: <out-dir>/<id>_<model>_s<seed>.png (+ .json sidecar).

Tested 2026-09-23 on macOS arm64 (mflux backend).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

IMAGE_PY = Path(__file__).resolve().parent / "image.py"
MODEL_TAGS = {"flux2-klein-4b": "klein4b", "flux2-klein-9b": "klein9b", "qwen-image-2.1": "qwen21"}


def build_prompt(shot: dict, style: str) -> str:
    shot_style = shot.get("style", True)
    if shot_style is False:
        return shot["prompt"]
    suffix = shot_style if isinstance(shot_style, str) else style
    return f"{shot['prompt']}, {suffix}" if suffix else shot["prompt"]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("spec", type=Path)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--only", help="comma-separated shot ids")
    p.add_argument("--force", action="store_true", help="regenerate existing outputs")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    spec = json.loads(a.spec.read_text())
    defaults = spec.get("defaults", {})
    only = set(a.only.split(",")) if a.only else None
    jobs = []
    for shot in spec["shots"]:
        if only and shot["id"] not in only:
            continue
        cfg = {**defaults, **shot}
        model = cfg.get("model", "flux2-klein-4b")
        for seed in cfg.get("seeds", [1]):
            out = a.out_dir / f"{shot['id']}_{MODEL_TAGS.get(model, model)}_s{seed}.png"
            jobs.append((shot, cfg, model, seed, out))

    for i, (shot, cfg, model, seed, out) in enumerate(jobs, 1):
        label = f"[{i}/{len(jobs)}] {out.name}"
        if out.exists() and not a.force:
            print(f"{label}: exists, skipping")
            continue
        cmd = [
            sys.executable, str(IMAGE_PY),
            "--prompt", build_prompt(shot, spec.get("style", "")),
            "--width", str(cfg.get("width", 1024)),
            "--height", str(cfg.get("height", 1024)),
            "--model", model,
            "--seed", str(seed),
            "--out", str(out),
        ]
        if cfg.get("steps"):
            cmd += ["--steps", str(cfg["steps"])]
        print(label, flush=True)
        if a.dry_run:
            print("  " + " ".join(cmd[2:]))
            continue
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if proc.returncode != 0:
            print(proc.stdout[-2000:], file=sys.stderr)
            sys.exit(f"{label}: failed")
        print("  " + next((ln for ln in proc.stdout.splitlines() if ln.startswith("wrote")), "done"), flush=True)


if __name__ == "__main__":
    main()
