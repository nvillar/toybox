---
status: partial
last_verified: 2026-09-23
versions: { mflux: 0.20.0, mlx: 0.32.2, models: [flux2-klein-4b, qwen-image-2.1] }
---

# Concept-art exploration

The first step for any new game, setting or look. Turn a short creative brief into a reviewable set of concept images, then use the picks to set the style for everything downstream (3D models, textures, UI).

**Produces:** a folder of PNGs with provenance sidecars, one contact sheet per round, and a short list of picks (shot id + seed). Klein 4B's model licence is Apache-2.0; this is not blanket clearance for depicted content or third-party rights. Qwen-Image-2.1 has a non-commercial research licence: keep its outputs separate and review the terms for the intended use, including prototypes.

## Steps

1. **Write a brief** (5 lines): the premise, the reference *qualities* (materials, scale, camera, lighting, palette, mood), the core objects and characters, a few locations, and one "signature" moment (e.g. *miniatures coming to life*).
2. **Write one style suffix** that describes those qualities literally. Every shot shares it, and it is what keeps the set consistent. See the prompting rules below.
3. **Probe the style:** run 1 shot × 2 seeds at the target aspect ratio (Klein 4B at 1344×768 takes ~20 s per image). Fix the suffix before scaling up.
4. **Write a shot list** (JSON) covering the range: key locations, the protagonist, the signature moment, a menu or world map, a character turnaround, and a title card. Give turnarounds their own style (figure only, plain background).
5. **Batch it:**
   ```bash
   python3 scripts/gen/batch.py out/concept/<game>/shots.json --out-dir out/concept/<game>/v1
   ```
   Klein takes ~20 s per image at 1344×768, so 9 shots × 2 seeds is about 6–7 min. Qwen-Image-2.1 takes ~5 min per image at that size, so keep it for text shots.
6. **Contact sheet:**
   ```bash
   uv run scripts/gen/contact_sheet.py out/concept/<game>/v1/*klein4b*.png \
       --out out/concept/<game>/v1/_sheet.jpg --cols 4 --title "<game> v1"
   ```
   The agent views the sheet inline (one image instead of 18), and the human reviews the same file.
   For browsing full-size images and their prompts, build a local gallery from the experiment folder:
   ```bash
   python3 scripts/gen/gallery.py out/concept/example --out-dir out/gallery/example --title "Concept studies"
   python3 -m http.server 8765 --bind 127.0.0.1 --directory out/gallery/example
   ```
   Open `http://127.0.0.1:8765/`. The output directory must be new or empty and separate from the source. The gallery copies images and embeds sidecar metadata; it does not modify the archive. Keep it in ignored local output, bind only to loopback, and serve only the generated gallery directory, never the repository root. It also opens directly from `index.html` without a server. Missing sidecars are flagged for rights review, not assumed permissive.
7. **Review and iterate:** write down which shots and seeds to keep, and diagnose the failures. Repeated failures suggest checking the shared suffix first; isolated ones suggest checking the shot prompt. Re-run into `v2/` **with the same seeds** to reduce variation. The reviewed Klein 4B and Qwen-Image-2.1 pairs kept broadly similar layouts after suffix changes, but seeds do not guarantee composition. Put v1 and v2 side by side on one contact sheet.
8. **Archive and hand off:** preserve selected rounds, shot lists, picks and full briefs in the private asset library ([storage](../tools/asset-storage.md)), not here. Selected references have now guided an editable [Blender showcase](reference-to-blender-showcase.md); production character modelling and reuse of the suffix for downstream texture/UI sets remain unverified. Promote only selected, rights-reviewed assets to a game's private production repo.
   Record human selections by exact image path, model and seed, plus explicit exceptions to the reference (for example, removing display bases to allow articulated locomotion). Separate visual style from animation requirements; a sculpted miniature look does not imply rigid movement or stepped timing. Keep these project-specific decisions beside the private assets rather than changing the original prompts or publishing the brief.

## Prompting rules (Klein 4B)

- **Describe the reference style; don't name it.** Write "tabletop miniature diorama, faceless sculpted figurines on round bases, board of nodes connected by engraved paths", not the name of a game or studio. This is safer for IP, and it works better.
- **Similes leak literally.** "Figurines *like hand-painted chess pieces*" put actual chess pieces in every scene. Klein is distilled (guidance 1.0) and has no negative prompt, so the only fix is to drop the simile. Say what the thing *is*.
- **Spell out the negatives as positive attributes.** "faceless, smooth matte forms, no facial features" turned realistic miniatures into stylised figurines.
- **Frame the diorama explicitly** ("a floating square slab with cut-away edges on a plain dark background"). Interior scenes with strong architecture (e.g. a hall of mirrors) still tend to spill past the slab into a full room.
- **Motion in stills:** "stop-motion animation still, subtle motion blur on the moving piece, light cone from a tiny flashlight" sells the "brought to life" idea.
- **Text:** read generated text back rather than trusting the prompt. Qwen-Image-2.1 rendered the sampled title correctly (non-commercial); overlay a real font when exact text is required.

## Checks

- Contact sheet: is the style consistent across all shots? Does the style show up in every shot without shot-specific wording?
- No stray objects coming from the suffix (a repeated artefact across shots means the suffix is at fault).
- Title text is spelled correctly (read it back).
- Each sidecar records the model, licence, seed and full prompt.

## Pitfalls

- Qwen-Image-2.1 rendered the sampled title correctly, but took ~15× longer than Klein at 1344×768. It still made spatial errors; the non-commercial licence applies.
- Cloud image models (if available) are a good second opinion. Give them the same brief and suffix, and record their terms before using any output.
- Consistency *across* shots (the same character every time) is not solved by prompting alone. Reference editing (Klein 9B-kv) is non-commercial. Treat the character in concept art as indicative, and the Blender model as canonical.

## Evidence

- [2026-09-23 concept-art exploration](../experiments/2026-09-23-concept-art.md)
