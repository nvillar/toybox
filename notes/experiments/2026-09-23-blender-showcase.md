# Procedural Blender showcase and headless Metal rendering

**Rig validation superseded:** the [2026-09-24 hand-off](2026-09-24-blender-unity-rig-handoff.md) caught shared-mesh skin-weight contamination missed by the positive-only articulation check. The private builder is corrected; original renders and scene remain historical artifacts.

- **Date:** 2026-09-23
- **Goal:** Turn selected private concept references into an editable scene and reviewable renders, without embedding project details in the public knowledge repo.
- **Tools & versions:** Blender 5.2.2 LTS, Cycles, Metal; Apple M4 Max, 128 GB unified memory; Python 3.9.6 for orchestration.

## What we did

1. Queried Cycles devices with Blender Python. Both CPU and the 40-core Metal GPU were available; explicitly enabled only Metal and set `scene.cycles.device = "GPU"`.
2. Built original procedural geometry and shader materials with `bpy`. Used named collections, shared sphere meshes with object-level material slots, lathed surfaces, bevelled meshes and bevelled curve paths. Kept the project-specific builder in the private asset library.
3. Saved an editable `.blend`, rendered a small initial image, inspected it, then refined materials, composition and mesh intersections using close-up renders. Generated four final views, not just a single flattering camera.
4. Promoted a generic saved-scene renderer to [`scripts/blender/render_scene.py`](../../scripts/blender/render_scene.py).
5. Archived the final scene, private source, PNGs and sidecars in Git LFS; exposed copies through a loopback-only gallery. Drafts remain local scratch rather than adding every binary revision to LFS.

Generic command; the real source path and camera names are private:

```sh
blender -b out/scene.blend --python-exit-code 1 \
  -P scripts/blender/render_scene.py -- \
  --out out/preview.png --camera "Camera" \
  --width 2560 --height 1920 --samples 192 --device METAL
```

## What happened

- Final scene: 2,323 objects, seven organized collections, four cameras and a 16-bone segmented character armature. The scene and embedded builder are self-contained; no downloaded models or external image textures were needed.
- Rendered two 2560 x 1920 images at 192 samples and two detail images at 128 samples. Exact dimensions were checked against the PNG headers and sidecars.
- Warm render times were 18.80 / 32.80 s for the large views, 12.31 s at 1600 x 2000 and 14.40 s at 2000 x 1600. Initial startup/render was about 79 s at lower settings; likely setup/cache overhead, not a controlled benchmark.
- Reopened the final `.blend`, verified embedded source equality, camera and bone counts, no unpacked image dependencies, and movement of a mesh after rotating its assigned forearm bone.
- Every final image's sidecar records the saved scene's SHA-256. Private copies matched the originals, and gallery images and scene downloads returned successfully over localhost.
- The result is a detailed look-development scene, **not** a production character, completed walk cycle, real-time asset budget or verified Unity import.

## Learnings

- **Test the exact Blender version.** In 5.2, `Scene.node_tree` is absent; introspection found `Scene.compositing_node_group` and socket-driven compositor glare settings. An old `glare_type` property lookup raised `KeyError`. No compositor effect was needed in this scene; this was an API probe, not a verified compositor recipe.
- **Always set `--python-exit-code 1`.** The failed property probe otherwise printed a traceback but exited successfully. Our scene/render commands now make Python failure visible to shell orchestration.
- **Keep the source and the render together.** A scene hash in each render sidecar distinguishes camera changes from accidentally rendering an older `.blend`. Embed a copy of the private builder and navigation notes in the `.blend` as well.
- **Close-ups catch different failures.** Broad material veining and intersecting garment layers can look acceptable in a wide shot; inspect materials, geometry and character separately before the final render.
- **Shared geometry keeps files small.** Repeated decorations can share a mesh while using per-object material slots. Object creation through `bpy.data` avoids repeated selection/context operations.
- **Use linear colours in shaders.** Convert hex/sRGB colour values before assigning shader RGBA inputs; scene colour management is a separate step.
- `Material.use_nodes` and `World.use_nodes` emit Blender 6.0 deprecation warnings on 5.2.2. They still work here; revisit when upgrading.

Reusable details were folded into [Blender](../tools/blender.md). Project identities, art direction, source and images remain private.

## Distillation (2026-09-24)

Promoted the completed sequence into [Selected references → Blender showcase](../patterns/reference-to-blender-showcase.md): freeze the brief, author an editable scene, inspect multiple camera scales, validate the saved artifact and archive selected results with provenance. This documents the existing experiment, not another successful run.

Corrected the concept-art pattern's stale claim that the Blender reference hand-off was entirely unverified. Only the showcase hand-off is now demonstrated; production character work and downstream texture/UI consistency remain open. The animation backlog now separates miniature appearance from a required stop-motion gait.

## Follow-ups

- Production topology, deforming skin and a natural locomotion study; a poseable segmented rig is not enough evidence.
- Unity import, materials/baking, reflection strategy and geometry optimization.
- CPU/CUDA/ROCm runs of the rendering helper; only Metal was exercised here.
