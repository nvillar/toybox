---
status: partial
last_verified: 2026-09-23
versions: { stable-audio-3: 779434a (optimized/mlx), mlx: 0.32.2 }
---

# Stable Audio 3

Role: **sound effects and music**, text-to-audio plus audio-to-audio variation and inpainting. The Small-SFX and Small-Music models are proven on this Mac (and in HotCards).

Wrapper: [`scripts/gen/audio.py`](../../scripts/gen/audio.py) (backend `sa3-mlx`). Capability overview: [audio-generation.md](audio-generation.md).

## Models

| `--dit` | Params | Decoder | Max length | Use |
|---------|--------|---------|-----------|-----|
| `sm-sfx` | 433M | `same-s` | 120 s | Sound effects |
| `sm-music` | 433M | `same-s` | 120 s | Music |
| `medium` | 1.4B | `same-l` | 380 s | Higher-quality music (slower) |

Output: 44.1 kHz stereo 16-bit WAV. Licence: **Stability AI Community License** (commercial use has conditions, see https://stability.ai/license). The T5Gemma text encoder is under the Gemma Terms of Use. Weights come from `stabilityai/stable-audio-3-optimized` on Hugging Face, which was not gated when checked on 2026-09-23. HotCards' README says to accept the terms and sign in.

## Install (Apple Silicon)

The official repo ships a pure-MLX CLI, `sa3` (no PyTorch needed at runtime):

```sh
git clone --depth 1 https://github.com/Stability-AI/stable-audio-3.git sandbox/tools/stable-audio-3
cd sandbox/tools/stable-audio-3/optimized/mlx
./install.sh -y --download sm-sfx,sm-music    # uv venv + weights (skips ones already cached)
```

Or run `scripts/setup/macos.sh`. The wrapper looks for `sa3` at `$TOYBOX_SA3_MLX`, falling back to the path above.

## Verified recipes

✅ 2026-09-23, M4 Max:

```sh
./sa3 --prompt "coin pickup, bright chime, retro game" --dit sm-sfx --decoder same-s --seconds 2 --out /abs/sfx_coin.wav
./sa3 --prompt "upbeat chiptune adventure loop 120 BPM" --dit sm-music --decoder same-s --seconds 15 --out /abs/mus.wav
```

- Wall time was ~0.6–1.6 s per clip, including model load.
- Output length matched `--seconds` exactly, and the clips were not silent.
- Use absolute `--out` paths: relative ones are written under the sa3 project's `output/` folder.
- `--seed` makes results reproducible. If you omit it, sa3 picks one and prints it; the wrapper always passes one.
- Always pass `--dit` and `--decoder`. Without them, sa3 opens an interactive picker.

Other modes (not yet tested here): `--init-audio IN.wav --init-noise-level 0.4–0.8` (variation), `--inpaint-range "S,E"`, `--cfg 3.0 --negative-prompt …`, `--lora file.safetensors`. There is also a Gradio UI (`./sa3-gradio`) and an MLX LoRA trainer.

## Other platforms

- **NVIDIA:** `optimized/tensorRT/` provides the same `sa3` CLI and flags. It targets Linux, downloads prebuilt engines per GPU architecture or builds them from ONNX (~30 min). Upstream reports ~30 ms per 30 s clip on H100. 🟡 Not run here. Windows is untested (possibly via WSL2).
- **CUDA via PyTorch:** the `stable-audio-3` Python library (`StableAudioModel.from_pretrained("small-sfx")`) and the older `stable-audio-tools`. `medium` needs Flash Attention 2.
- **AMD / other:** the HF repo ships `onnx/` and `tflite/` exports, and the upstream README says support for more hardware is "coming soon". ❓
- **CPU:** the small models are designed to run on CPU.

## HotCards notes

HotCards vendors an MIT-licensed subset of the official MLX code (`src/hotcards/vendor/stable_audio_3_mlx`) and runs Small-SFX in-process with pingpong sampling, 8 steps, cfg 1.0, and durations of 1–30 s. For toybox, calling the official `sa3` CLI is simpler and avoids vendoring.
