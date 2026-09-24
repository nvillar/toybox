---
status: partial
last_verified: 2026-09-23
versions: { mflux: 0.20.0, mlx: 0.32.2 }
---

# MFLUX

Role: **preferred image generation / editing backend on Apple Silicon.** An MLX port of FLUX-family and other diffusion models with a CLI per model family.

Wrapper: [`scripts/gen/image.py`](../../scripts/gen/image.py) (backend `mflux`). Capability overview: [image-generation.md](image-generation.md).

## Install

```sh
uv tool install mflux --with hf-transfer    # puts mflux-* commands in ~/.local/bin
uv tool upgrade mflux
```

This machine: **0.20.0** (upgraded from 0.18.0 on 2026-09-23; HotCards pins `mflux>=0.19.1`). 0.20.0 adds Qwen-Image-2.1 (`mflux-generate-qwen-2.1`) and Krea 2. Weights download to the Hugging Face cache (`~/.cache/huggingface/hub`) on first use. Klein 4B is ~15 GB, 9B / 9B-KV are ~49 GB each, and Qwen-Image-2.1 is ~31 GB. All are cached here.

## Models

| Model (`--model`) | Licence | Use |
|-------------------|---------|-----|
| `flux2-klein-4b` | Apache-2.0 | **Default.** Fast; fine to ship in a game. |
| `flux2-klein-9b` | FLUX Non-Commercial | Text-to-image, slower. Not for shipped commercial assets. |
| `flux2-klein-9b-kv` | FLUX Non-Commercial | Reference-image / edit mode (`mflux-generate-flux2-edit`). |
| `flux2-klein-base-*` | as above | Undistilled bases (more steps). |
| `qwen-image-2.1` (`mflux-generate-qwen-2.1`) | **Qwen Research License, non-commercial** | 7.1B DiT with a Qwen3-VL text encoder. **Excellent in-image text** (logos, titles, signage). ~10× slower than Klein 4B. |

Other families available through `mflux-generate-*`: Qwen Image 1.x (+edit), Krea 2, Z-Image (turbo), FIBO, Kontext, ERNIE, Ideogram, depth/ControlNet/fill/redux, SeedVR2 upscaling, LoRA training (`mflux-train`). None tested here yet.

## Verified recipes

- ✅ Text-to-image, 512×512, Klein 4B (2026-09-23, M4 Max, 0.18.0 and 0.20.0): ~5–9 s wall including load, 4 steps, **peak MLX memory 10.53 GB**.
  ```sh
  mflux-generate-flux2 --model flux2-klein-4b --prompt "seamless tileable mossy cobblestone texture, top-down, even lighting" \
    --width 512 --height 512 --seed 42 --output out/tex.png
  ```
  The result looked like a plausible cobblestone texture. It was not checked for seamless tiling.
- ✅ Qwen-Image-2.1 text-to-image (2026-09-23, M4 Max, mflux 0.20.0). Defaults: 40 steps, no guidance, bf16.
  - 512×512: **59 s**, peak **20.5 GB**.
  - 768×512: **84 s**, peak **21.8 GB**.
  - It rendered a pixel-art "TOYBOX" title logo with every letter correct.
  - `mflux-generate-qwen-2.1` defaults to this model, so the wrapper does not pass `--model`. `-q 8` / `-q 4` quantization is available, but untested here.
  ```sh
  python3 scripts/gen/image.py --model qwen-image-2.1 --prompt 'pixel-art game title logo reading "TOYBOX" …' \
    --width 768 --height 512 --seed 7 --out out/title.png
  ```

## Learnings carried over from HotCards

From [nvillar/HotCards](https://github.com/nvillar/HotCards), `evals/DECISION.md`, measured on this class of machine:

- Klein 4B took ~11.2–11.6 s per render. Regular 9B took ~30.7–32.1 s, with no consistent quality gain for authoring. This is why 4B is the default.
- Reference-guided generation and editing use `Flux2KleinEdit` with the 9B KV model. HotCards accepts up to two references, passed in order and referred to in the prompt as "image 1" and "image 2".
- Sending the author's description straight to MFLUX, plus a fixed style suffix, worked. Adding hidden role instructions or having an LLM rewrite the prompt was a **no-go**.
- Getting the same object from a new viewpoint was unreliable with references, so don't rely on it for consistency across views.
- Inside one process, run MLX/Metal work (MFLUX and Stable Audio) one at a time through a single inference boundary. Our wrappers start a separate process per call.

## Prompting gotchas (verified 2026-09-23, [concept-art exploration](../experiments/2026-09-23-concept-art.md))

- **Similes leak literally.** "figurines like hand-painted chess pieces" put chess pieces into most scenes, in both Klein and Qwen. Klein runs at guidance 1.0 with no negative prompt, so remove the simile and describe the attribute itself.
- **Fixed seeds helped style comparisons:** the reviewed Klein 4B and Qwen-Image-2.1 pairs kept broadly similar layouts after suffix changes. This is not a guarantee of composition consistency.
- Qwen-Image-2.1 sometimes moved a background landmark inside the scene as miniature props; inspect spatial relationships, not just object presence.
- Timing at 1344×768: Klein 4B 19–24 s; Qwen-Image-2.1 306–337 s.
- `scripts/gen/image.py` now records the `mflux` and `mlx` versions in each sidecar. Earlier sidecars have `"versions": {}`.

## To explore

- Tileable / seamless textures: prompt-only vs post-processing (offset + inpaint via `mflux-generate-fill`).
- PBR map derivation (depth → normal via `mflux-save-depth`?).
- Transparent sprites (FIBO edit RMBG / background removal).
- Qwen-Image-2.1: `-q 8` speed/quality, img2img (`--image`), true CFG with `--negative-prompt`. Is a commercial licence from Qwen worth it for title/UI text?
