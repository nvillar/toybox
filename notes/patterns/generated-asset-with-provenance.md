---
status: verified
last_verified: 2026-09-23
versions: { mflux: 0.20.0, stable-audio-3: 779434a }
---

# Generated asset with provenance

The base pattern for every generated 2D or audio asset: generate through a capability wrapper so the output is reproducible and its licence is known.

**Produces:** an image (PNG) or audio clip (44.1 kHz stereo WAV), plus `<file>.json` recording the prompt, seed, params, backend, model, licence, versions, platform, exact command and timing.

## Steps

```sh
python3 scripts/gen/image.py --prompt "seamless mossy cobblestone texture, top-down" \
  --width 1024 --height 1024 --seed 42 --out out/tex_cobble.png
python3 scripts/gen/audio.py --kind sfx --prompt "coin pickup, bright chime, retro game" \
  --seconds 1.5 --out out/sfx_coin.wav
```

- Use type-prefixed `snake_case` names (`tex_`, `sky_`, `sfx_`, `mus_`, …). See [pipeline](../pipeline.md).
- Pass `--seed` to reproduce an asset exactly. To explore variations, omit it; the chosen seed is still recorded.

## Checks

- Images: view the PNG. For textures, tile it 2×2 to check seams (not yet scripted).
- Audio: `afinfo out/sfx_coin.wav` for format and duration; listen with `afplay`.
- The sidecar's `license` is acceptable for the intended use.

## Pitfalls

- The default models are commercially usable (FLUX.2 Klein 4B: Apache-2.0; Stable Audio 3: Stability AI Community License, which has conditions). Overriding `--model` may switch to a non-commercial licence. The sidecar records it.
- Keep generated assets out of this repo. Curate them into a private project repo ([asset storage](../tools/asset-storage.md)).

## Evidence

- [2026-09-23 MLX image and audio generation](../experiments/2026-09-23-mlx-image-and-audio.md)
