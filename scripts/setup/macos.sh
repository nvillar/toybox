#!/usr/bin/env bash
# Set up the toybox toolchain on an Apple Silicon Mac.
# Idempotent: skips anything already installed. Tested 2026-09-23 on M4 Max / macOS 15.
#
# Usage: scripts/setup/macos.sh
#
# Installs:
#   - Blender (Homebrew cask, gives `blender` on PATH)
#   - uv, ffmpeg (Homebrew)
#   - MFLUX (uv tool) for MLX image generation
#   - Stable Audio 3 official MLX CLI into sandbox/tools/stable-audio-3 (sm-sfx + sm-music weights)
# Not installed here (install manually if wanted): Unity Hub / unity CLI, Ollama, oMLX.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if [[ "$(uname -s)/$(uname -m)" != "Darwin/arm64" ]]; then
  echo "This script targets Apple Silicon macOS. See notes/platforms.md for other platforms." >&2
  exit 1
fi

command -v brew >/dev/null || { echo "Homebrew required: https://brew.sh" >&2; exit 1; }

brew list --cask blender >/dev/null 2>&1 || brew install --cask blender
command -v uv >/dev/null || brew install uv
command -v ffmpeg >/dev/null || brew install ffmpeg

command -v mflux-generate-flux2 >/dev/null || uv tool install mflux --with hf-transfer

SA3_DIR="$REPO_ROOT/sandbox/tools/stable-audio-3"
if [[ ! -d "$SA3_DIR" ]]; then
  mkdir -p "$(dirname "$SA3_DIR")"
  git clone --depth 1 https://github.com/Stability-AI/stable-audio-3.git "$SA3_DIR"
fi
(cd "$SA3_DIR/optimized/mlx" && ./install.sh -y --download sm-sfx,sm-music)

echo
echo "Done. Smoke tests:"
echo "  python3 scripts/gen/image.py --prompt 'test' --width 512 --height 512 --out out/test.png"
echo "  python3 scripts/gen/audio.py --kind sfx --prompt 'coin pickup' --out out/test.wav"
