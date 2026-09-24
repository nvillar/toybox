---
status: partial
last_verified: 2026-09-23
---

# Image generation

Role: textures, PBR maps, backgrounds, skyboxes, sprites, UI art, concept art.

**Interface:** [`scripts/gen/image.py`](../../scripts/gen/image.py): `--prompt --width --height --seed --model --out`. It writes a PNG plus a `.json` provenance file. Backends by platform: see [platforms.md](../platforms.md).

| Platform | Backend | Status |
|----------|---------|--------|
| macOS Apple Silicon | [MFLUX](mflux.md), FLUX.2 Klein 4B default; Qwen-Image-2.1 for in-image text (non-commercial) | ✅ |
| NVIDIA (Win/Linux) | diffusers `Flux2KleinPipeline` or ComfyUI, same HF weights | ❓ |
| AMD ROCm | diffusers / ComfyUI on PyTorch ROCm | ❓ |

## Needs by asset type

| Asset | Requirements | Notes |
|-------|--------------|-------|
| Tileable textures | Seamless edges, power-of-two, consistent scale | Check seams by tiling 2×2 in a preview. |
| PBR maps | Albedo + normal, roughness, metallic, AO | Derive data maps from albedo/depth, or bake in Blender. Data maps are linear, not sRGB. |
| Skyboxes | Equirectangular 2:1 or 6-face cubemap, ideally HDR | Pole distortion and seams are the typical failure. |
| Backgrounds / parallax | Layered, transparent edges | Needs alpha or background removal. |
| Sprites / UI / icons | Transparent background, consistent style | Style consistency across a set is the hard part. A fixed style suffix helped in HotCards. |
| Titles, logos, signage | Legible, correctly spelled text | Qwen-Image-2.1 spells text reliably. Non-commercial, so use it for prototypes or get a licence. |
| Concept art | Fast iteration | Feeds the design brief and Blender reference. |

## Evaluation criteria

Quality for the asset type · controllability (seed, size, tiling, alpha, references) · speed · memory · **licence for commercial game use** · scriptability from the shell.
