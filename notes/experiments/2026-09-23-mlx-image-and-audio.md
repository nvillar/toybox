# MLX image and audio generation

- **Date:** 2026-09-23
- **Goal:** confirm the preferred Apple Silicon backends (MFLUX, Stable Audio 3 MLX) run from the shell here, and wrap them behind platform-neutral interfaces.
- **Tools & versions:** M4 Max 128 GB, macOS 15.8; mflux 0.18.0 (uv tool) / mlx 0.31.2; Stable Audio 3 repo `779434a` (`optimized/mlx`, mlx 0.32.2); Ollama 0.34.3.
- **Reference:** [nvillar/HotCards](https://github.com/nvillar/HotCards). It uses MFLUX FLUX.2 Klein and Stable Audio 3 Small-SFX through MLX.

## What we did

```sh
# Image: FLUX.2 Klein 4B via MFLUX (weights already in HF cache)
mflux-generate-flux2 --model flux2-klein-4b --prompt "seamless tileable mossy cobblestone texture, top-down, even lighting" \
  --width 512 --height 512 --seed 42 --output /tmp/tex.png

# Audio: official Stable Audio 3 MLX CLI
git clone --depth 1 https://github.com/Stability-AI/stable-audio-3.git sandbox/tools/stable-audio-3
(cd sandbox/tools/stable-audio-3/optimized/mlx && ./install.sh -y --download sm-sfx,sm-music)
./sa3 --prompt "coin pickup, bright chime, retro game" --dit sm-sfx --decoder same-s --seconds 2 --out $PWD/out/sfx_coin.wav
./sa3 --prompt "upbeat chiptune adventure loop 120 BPM" --dit sm-music --decoder same-s --seconds 15 --out $PWD/out/mus.wav

# Then through the new wrappers
python3 scripts/gen/image.py --prompt "…" --width 512 --height 512 --seed 42 --out out/tex_cobble.png
python3 scripts/gen/audio.py --kind sfx --prompt "coin pickup, bright chime, retro game" --seconds 1.5 --out out/sfx_coin.wav
python3 scripts/gen/audio.py --kind music --prompt "calm ambient forest music, soft harp, 90 BPM" --seconds 10 --seed 7 --out out/mus_forest.wav
```

## What happened

- MFLUX Klein 4B at 512²: 4 steps, 5–7 s wall including load, peak MLX memory 10.53 GB. The output was a plausible cobblestone texture. Tiling was not checked.
- `sa3` installed in seconds, since weights were already partly cached from HotCards. Each clip took 0.6–1.6 s wall.
- Output: 44.1 kHz stereo Int16, length exactly `--seconds`. Peak/RMS showed real, non-silent signal.
- The wrappers wrote assets plus `.json` provenance sidecars with seed, command, licence and versions.
- The Stable Audio 3 HF repo also ships `tensorRT/`, `onnx/`, `tflite/` and `cpu-amx/` variants. The TensorRT runtime exposes the same `sa3` CLI, which makes it the obvious NVIDIA backend.

## Learnings

- → [tools/mflux.md](../tools/mflux.md), [tools/stable-audio-3.md](../tools/stable-audio-3.md), [tools/local-llm.md](../tools/local-llm.md), [platforms.md](../platforms.md).
- Pass `sa3` an absolute `--out`; relative paths are written into its own `output/` folder.
- Always pass `--dit`/`--decoder` to `sa3`; otherwise it opens an interactive picker.
- MFLUX 0.18.0 was older than the latest (0.20.0) and HotCards' pin (≥0.19.1), but Klein worked on it. After upgrading to 0.20.0 (`uv tool upgrade mflux`), the Klein 4B recipe re-ran with the same peak memory.
- `ffmpeg` is not installed yet.

## Addendum: Qwen-Image-2.1 (same day)

- `uv tool upgrade mflux` 0.18.0 → 0.20.0 added `mflux-generate-qwen-2.1`.
- Downloaded the weights: `hf download Qwen/Qwen-Image-2.1 --revision 790c926 --exclude "assets/*"` (31 GB, not gated).
- Licence is the **Qwen Research License**: non-commercial only. A commercial licence can be requested from Qwen.
- 512² took 59 s at 20.5 GB peak; 768×512 took 84 s at 21.8 GB. The text in a title logo was rendered correctly.
- Registered in `scripts/gen/image.py` as `--model qwen-image-2.1`. The sidecar records the non-commercial licence.

## Follow-ups

- CUDA / ROCm backends, oMLX evaluation and an MFLUX upgrade, all added to [backlog.md](../backlog.md).
