# Concept-art exploration with local image models

- **Date:** 2026-09-23
- **Goal:** Can local models produce a consistent concept-art set for a new game from a short brief? What workflow should agents follow?
- **Tools & versions:** MFLUX 0.20.0 (mlx 0.32.2); FLUX.2 Klein 4B (Apache-2.0); Qwen-Image-2.1 (Qwen Research License, non-commercial); Pillow 12.3.0 via `uv run`; M4 Max, 128 GB. The assistant has no native image generation. For a cloud model, the user was given a prompt pack to run elsewhere (see below).

## Scope

Test a shared visual style across environments, character studies, motion studies and title art. This public log records the method and findings only. The project premise, title, complete prompts, shot lists and images remain private.

## What we did

1. **Style probe** (Klein 4B, 1344×768, 2 seeds): the diorama framing, nodes, paths and floating slab worked on the first try. The figures looked too realistic.
2. **v1 batch:** 9 Klein shots × seeds 1 and 2, plus 2 Qwen shots (a title card and an environment). The set covered environments, a character turnaround, a motion study and a navigation concept. Commands below use a generic example directory; the actual shot lists are private.
   ```bash
   python3 scripts/gen/batch.py out/concept/example/shots.json --out-dir out/concept/example/v1
   uv run scripts/gen/contact_sheet.py out/concept/example/v1/*klein4b*.png --out out/concept/example/v1/_sheet_klein.jpg --cols 4
   ```
   The v1 style suffix included "…figurines *like hand-painted chess pieces*…".
3. **v2:** replaced the simile with "faceless minimalist sculpted figurines with smooth matte forms and no facial features, each figurine on a small round base". Re-ran 5 shots with the same seeds, plus the Qwen environment with the same seed.
4. **Promoted helpers:** [`scripts/gen/batch.py`](../../scripts/gen/batch.py) (JSON shot list + shared style suffix) and [`scripts/gen/contact_sheet.py`](../../scripts/gen/contact_sheet.py).

Shot lists, images and the detailed project log were initially kept in git-ignored local `out/` storage. They have since been archived in the private asset library, with a fresh-clone restore verified in the [storage experiment](2026-09-23-private-asset-library.md). Public paths above are illustrative.

## What happened

| Run | Model | Time per image (1344×768) | Notes |
|-----|-------|---------------------|-------|
| v1/v2 | Klein 4B | 19–24 s | 18 images in ~6.5 min |
| v1/v2 | Qwen-Image-2.1 | 306–337 s | Peak ~22 GB |

- **v1:** the chess simile leaked literally. Actual chess pieces (pawns, knights) appeared in most scenes, even on the Qwen title card. A character turnaround benefited from its own figure-only style override.
- **v2:** the chess pieces were gone in the reviewed comparisons, the figures became more stylised, and the motion study suggested stop-motion. One ornate interior spilled out into a full room behind the slab.
- **Fixed seeds helped comparison:** the reviewed Klein and Qwen pairs retained broadly similar layouts after changing the style suffix. This is an observation from this batch, not a guarantee that a seed locks composition across prompt changes.
- **Qwen-Image-2.1:** rendered the requested title correctly in the sample. A background landmark became miniature props inside the scene, so spatial relationships still need review. It was ~15× slower than Klein.
- **Cloud comparison:** the user was given a style prompt pack. It describes the style instead of naming the reference game, includes "no chess pieces", and lists the 9 scenes. The comparison is not done yet.

## Learnings

- New pattern: [Concept-art exploration](../patterns/concept-art-exploration.md) (brief → suffix → probe → batch → contact sheet → seed-locked iteration → hand off).
- Prompting gotchas were added to [tools/mflux.md](../tools/mflux.md): similes can leak literally; fixed seeds helped compare style wording in this batch.
- **Correction:** `scripts/gen/image.py` was writing `"versions": {}` in the sidecars. It now asks the interpreter behind the MFLUX console script for the `mflux` and `mlx` versions (verified: `{'mflux': '0.20.0', 'mlx': '0.32.2'}`). Sidecars written before this fix lack versions. This experiment's versions are recorded above.

## Local review gallery

Added [`scripts/gen/gallery.py`](../../scripts/gen/gallery.py), tested with Python 3.9.6 on this Mac. It builds a static page with round/model filters, search, full-size image viewing, prompts, seeds and licence labels. It uses no external fonts, analytics or services.

```bash
# Generic paths/title; the actual gallery and its content remain private.
python3 scripts/gen/gallery.py out/concept/example --out-dir out/gallery/example --title "Concept studies"
python3 -m http.server 8765 --bind 127.0.0.1 --directory out/gallery/example
```

The actual source was the private experiment archive. The generated gallery contained 33 images and 3 review sheets; all copies matched the originals and all 36 HTTP image URLs returned successfully. Checked metadata counts, HTML/script escaping, and rejection of nested or nonempty output directories. Opened the page in the app's browser panel. The server is session-local; the generated HTML and media persist under ignored `out/` and can be reopened without a server. Only the reusable helper and generic instructions belong in public Git.

## Human review and modelling hand-off

Human review selected environment and character references and identified a presentation detail that must not carry into the rigged model. Exact selections and project requirements are recorded in the private project README. The reusable lesson is to record both what to preserve and what to discard before modelling; miniature styling and natural articulated movement are independent choices. A Blender blockout and rigged motion study are proposed, not yet completed.

## Follow-ups (→ [backlog](../backlog.md))

- Compare with cloud image generation using the same brief.
- Use a character turnaround as a Blender modelling reference, then render a turntable in the same style.
- Animate the miniatures: stop-motion-style animation in Blender or Unity, and image-to-video models.
- Keeping the same character across shots without non-commercial reference models.
- Interior framing: try "shallow room section, back wall only, open front" to keep the scene inside the slab.
