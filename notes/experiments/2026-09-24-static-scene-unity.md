# Detailed static Blender scene in a native Unity prototype

- **Date:** 2026-09-24
- **Goal:** replace a navigation blockout with the original detailed geometry and procedural surface detail, while increasing movement speed by 50%.
- **Tools & versions:** Blender 5.2.2 LTS / Cycles Metal; Unity 6000.6.2f1 built-in renderer / Mono macOS arm64; FFmpeg 9.0.2.

## What we did

Kept the original `.blend` and both earlier experiments unchanged. Exported only the static environment, excluding its posed character and studio. Reused the corrected idle/walk character rather than the showcase's superseded rig.

Promoted [`export_static_scene.py`](../../scripts/blender/export_static_scene.py). It evaluates modifiers, curves and text; converts objects to world-space meshes; groups by collection/material; triangulates; removes zero-area triangles; unwraps textured groups; bakes colour and tangent normals; exports FBX and a manifest with source/exporter/output hashes, surface factors, source bounds and geometry counts.

The important coordinate step is **before joining**: store each object's normalized local bounding-box coordinates in a point-domain `FLOAT_VECTOR` attribute. Connect procedural texture inputs to that attribute instead of `Generated`, including implicit coordinates on unconnected Noise texture inputs. Otherwise the joined object's bounding box changes the material pattern. This is a deliberately constrained helper: metre coordinates, one direct Principled material per object, constant roughness/metal/transmission/emission factors and Generated-coordinate procedural textures. It rejects non-metre units, multiple material slots, indirect surface outputs, linked scalar factors and explicit non-Generated texture-coordinate outputs. Other graph variants, including existing UV image textures, are outside its supported contract.

Generic command shape; actual collection/material selections and paths are in the private archive:

```sh
blender -b "$SOURCE_BLEND" --python-exit-code 1 \
  -P scripts/blender/export_static_scene.py -- \
  --out-dir "$NEW_EXPORT_DIR" --exclude-prefix "$CHARACTER_COLLECTION_PREFIX" \
  --exclude-prefix "$STUDIO_COLLECTION_PREFIX" --planar-material "$MIRROR_MATERIAL" \
  --texture-size 2048
UNITY_EDITOR=/Applications/Unity/Hub/Editor/6000.6.2f1/Unity.app/Contents/MacOS/Unity
"$UNITY_EDITOR" -batchmode -projectPath "$PROJECT" \
  -executeMethod "$SCENE_BUILD_METHOD" -prototypeOut "$BUILD" -logFile "$BUILD_LOG"
"$PLAYER_EXECUTABLE" --prototype-test "$REPORT_DIR" --capture \
  -screen-width 1440 -screen-height 960 -screen-fullscreen 0 -logFile "$PLAYER_LOG"
```

The scene-specific builder and runtime visual treatment stay private. It replaces the blockout in a copy of the saved prototype, checks every imported mesh's triangle count, creates Unity Standard materials from the baked textures and scalar factors, adds simple independent collision proxies, and rebakes navigation. Albedo imports as sRGB; normal maps use the normal-map importer and Mikk tangents.

A realtime cubemap supplies metallic/glass highlights. Two coplanar mirror groups use separate reflected cameras, an oblique clip plane, inverted culling during each render and projective screen-UV sampling. The player appears in those reflections. Mirror surfaces are excluded from reflection cameras to avoid recursive mirrors. Thin emissive effects are excluded only from the coarse cubemap: the first attempt produced broad coloured highlight bands; the effects remain visible in the main camera and planar reflections.

Movement changes from 0.72 to **1.08 m/s**. Keep `authoredWalkSpeed=0.72`; the existing controller then drives the Walk state's multiplier to **1.5**. Changing the authored-speed denominator would incorrectly leave the animation at its old playback rate.

## What happened

| Result | Observed |
|---|---|
| Original static objects retained | 2,241 |
| Grouped imported environment meshes | 33 |
| Imported triangles | 998,167, matching export exactly |
| Baked textures | 21 colour/normal PNGs at 2048² |
| Planar reflection groups | 2 |
| Native movement speed | Maximum 1.080002 m/s |
| Moving animation multiplier | 1.499999 |
| Navigation route | Seven corners around static blockers |
| Runtime acceptance | 33 checks pass, also in a cache-free rebuild of the saved scene |
| Collision / stop checks | Zero body-capsule overlaps; zero explicit-stop drift |
| Native review video | 469 frames, 15.63 s at 30 fps, 1440×960 |

Inspected full-room, focal-object/character and surface-detail screenshots from the native player. Preserved actual modelling detail rather than substituting proxy visuals; collision uses separate simple shapes. The source-only restore does not regenerate geometry, textures or navigation.

The first FBX export warned that n-gons prevented tangent export. Triangulating **before UV/baking/export** removed those warnings and made the geometry count verifiable. Removing 2,876 zero-area triangles did not remove visible surfaces. A frame-fit adjustment also kept the environment below the controls instead of hiding its highest geometry behind the HUD.

A negative unit-scale control (source `scale_length=0.01`) exits nonzero with `Use metre-scale source coordinates before this export`, instead of silently changing navigation dimensions.

## Learnings

- Bake appearance and evaluate the result in the engine; copying material names or diffuse colours is not a shader transfer.
- `EMIT` baking of the source Base Color isolates albedo from lighting and metal response; restore the original Principled output before a tangent-normal bake. Save colour images as sRGB and normal images as Non-Color.
- Grouping static objects reduces renderer count, not triangle count. This transfer preserves nearly a million triangles; it is a fidelity milestone, not an optimization result.
- Keep coplanar mirror surfaces separate when grouping; material-only merging would lose the distinction between reflection planes.
- Realtime transparency and reflection probes are approximations. The imported transmissive detail is present, but not equivalent to Cycles refraction, caustics, area-light transport or AgX colour management.
- Update both target speed and its acceptance measurements while keeping the original clip calibration unchanged. The original movement controller needed no code change for a 1.5× rate.

Distilled into [Blender](../tools/blender.md), [Unity](../tools/unity.md) and the [showcase pattern](../patterns/reference-to-blender-showcase.md).

## Follow-ups

Profile GPU time and memory on target hardware, add LODs/instancing or decimation where appropriate, improve transparent-object sorting and crystal refraction, soften shadows, improve foot planting through turns and compare baked lighting. A human previously confirmed the blockout's walking felt good; the detailed scene still needs hands-on review. No mobile/Windows/WebGL performance or pixel-identical render parity is claimed.
