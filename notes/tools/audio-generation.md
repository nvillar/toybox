---
status: partial
last_verified: 2026-09-23
---

# Audio generation

Role: sound effects, ambience, music, and voice.

**Interface:** [`scripts/gen/audio.py`](../../scripts/gen/audio.py): `--kind sfx|music --prompt --seconds --seed --out`. It writes a 44.1 kHz stereo WAV plus a `.json` provenance file. Backends by platform: see [platforms.md](../platforms.md).

| Platform | Backend | Status |
|----------|---------|--------|
| macOS Apple Silicon | [Stable Audio 3](stable-audio-3.md) MLX `sa3` (sm-sfx, sm-music) | ✅ |
| NVIDIA Linux | Stable Audio 3 TensorRT `sa3` (same CLI) | 🟡 |
| NVIDIA / AMD via PyTorch | `stable-audio-3` library | ❓ |
| Voice / TTS | not yet chosen | ❓ |

## Needs by asset type

| Asset | Requirements | Notes |
|-------|--------------|-------|
| SFX (UI, impacts, pickups) | Short, tight onsets, variations | Generate several seeds per event; Unity can randomise. |
| Ambience | Long, seamless loops | Loop points must be clean (crossfade / zero crossing). |
| Music | Loopable, consistent mood | SA3 accepts BPM in the prompt; inpainting may help build loops. |
| Voice / barks | Consistent character voice | Consent and licensing matter for voice cloning. |

## Post-processing (likely via `ffmpeg`, not yet installed here)

- Trim silence, normalise loudness, convert to OGG for Unity if needed.
- Make loops seamless.
- Give the agent feedback: duration, peak/LUFS measurements, spectrogram images.

## Evaluation criteria

Quality · controllability (duration, loopability, seed) · latency · **licence for commercial game use** · scriptability from the shell.
