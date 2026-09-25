---
status: verified
last_verified: 2026-09-24
versions: { blender: 5.2.2 LTS }
---

# Selected references → Blender showcase

Turn a reviewed concept set into an editable 3D scene, using a render-and-review loop rather than treating the first successful render as completion. Verified once on macOS/Metal; production animation and engine integration are outside this pattern.

**Produces:** a private project-specific Python builder, a self-contained `.blend`, several PNG views with scene-hash provenance, and a local review gallery. Geometry and materials are authored through `bpy`; this is **not automatic image-to-mesh reconstruction**. Reference licences and project rights still apply.

## Steps

1. **Freeze the visual brief.** Record the exact selected images and what to preserve, change or omit. Separate appearance from function: a display stand is not part of a walking character, and a miniature appearance does not require stepped animation. Keep the brief and reference paths private.
2. **Build a small representative scene.** Establish camera, proportions and the focal object before multiplying detail. Use meshes for flat or clipped components, lathed profiles for rotational forms, and bevelled curves for rails, cables and ornament. Share repeated unskinned mesh data where appropriate; copy data before assigning different skin bindings. Use object-level material slots when instances need different materials. Keep the builder parameterised and project-specific.
3. **Make the deliverable editable.** Organize named collections and cameras. Keep procedural materials in the scene, embed the builder and navigation notes as Blender text blocks, and preserve the standalone source in private Git. A `.blend` is the editable source, not just an intermediate on the way to a PNG.
4. **Render, inspect and revise.** Start with a small draft; then inspect a wide composition, a focal-object close-up, a material/detail view and a character view where relevant. Fix geometry and materials before increasing resolution. Re-render all final views from the same saved scene revision.
5. **Reopen and check the saved file.** Verify the named cameras and expected objects, embedded source agreement, and external dependencies. If a rig is claimed, rotate a bone and verify its intended mesh moves **while unrelated body parts stay still**. The original positive-only check missed shared-weight contamination, caught in the hand-off experiment. This establishes articulation only, not good deformation or a natural walk cycle.
6. **Archive the selected result.** Preserve the builder, `.blend`, images and sidecars in the private asset library. Record the scene hash in each render sidecar; archive only selected milestones, leaving disposable drafts in local scratch. Commit/push the completed cycle under the repository's checkpoint policy.

The existing renderer provides the draft/final loop once the project's builder has saved a scene. Camera names below are examples; use the exact names in the saved file.

```sh
blender -b out/scene.blend --python-exit-code 1 \
  -P scripts/blender/render_scene.py -- --out out/review/draft.png \
  --camera "Wide" --width 1200 --height 900 --samples 24 --device METAL

# After reviewing, revising and saving the scene:
blender -b out/scene.blend --python-exit-code 1 \
  -P scripts/blender/render_scene.py -- --out out/review/final/wide.png \
  --camera "Wide" --width 2560 --height 1920 --samples 192 --device METAL

blender -b out/scene.blend --python-exit-code 1 \
  -P scripts/blender/render_scene.py -- --out out/review/final/detail.png \
  --camera "Detail" --width 2000 --height 1600 --samples 128 --device METAL

python3 scripts/gen/gallery.py out/review/final \
  --out-dir out/gallery/scene-review --title "Scene review"
```

Choose a new or empty gallery output directory. Prefer opening and presenting its `index.html` directly, without a server; keep the HTML and relative media files together. Only if serving is genuinely required, serve that directory on `127.0.0.1`, never the private repository root.

## Checks

- The scene reads at the intended viewing distance; close-ups also hold up. In the experiment, wide views hid oversized material veins and intersecting garment layers.
- No accidental presentation props remain attached to articulated objects; contact with the floor is inspected rather than inferred from a rig's existence.
- Every final render has the intended dimensions and camera, and its sidecar's `scene_sha256` matches the archived `.blend`. Keep source/scene hashes and licence information with the result.
- Reopening the saved `.blend` works without relying on the original live Blender session. The tested scene required no external image textures; other projects may need packed or explicitly managed dependencies.
- Limitations are explicit: poseable is not animation-ready; rendered is not game-ready; no missing textures is not proof of all asset rights.

## Pitfalls

- **Use geometry where control matters.** A procedural approach worked well for repeated architectural and decorative forms. The same experiment's segmented character remained a look-development model; do not infer that detailed environment generation solves anatomy, skinning or natural motion.
- **A render is a diagnostic, not a reward.** Add close-up cameras early. Raising sample counts cannot fix intersections, proportions or excessively broad texture patterns.
- **Fail visibly.** Pass `--python-exit-code 1`; otherwise Blender can print a Python traceback and still return success. Select Metal explicitly and fail if unavailable rather than silently changing the compute backend.
- **Test the installed API.** Blender 5.2 changed compositor access; use small API probes rather than copying older snippets unchanged. See [Blender notes](../tools/blender.md).
- **Do not generalize warm timings.** First-run overhead was substantial; the experiment was not a controlled benchmark.
- **Do not infer engine compatibility.** Shader baking, geometry budgets, character skinning and Unity import remain separate experiments.

## Evidence

- [Concept-art exploration](../experiments/2026-09-23-concept-art.md): selected references and human review.
- [Procedural Blender showcase](../experiments/2026-09-23-blender-showcase.md): construction, iteration, saved-scene checks and Metal renders.
- [Private asset library](../experiments/2026-09-23-private-asset-library.md): storage and restoration.
- [Rig hand-off](../experiments/2026-09-24-blender-unity-rig-handoff.md): corrected shared skin weights and added negative controls before Unity import.
