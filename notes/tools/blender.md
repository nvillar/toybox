---
status: partial
last_verified: 2026-09-24
versions: { blender: 5.2.2 LTS }
---

# Blender

Role: create and edit 3D assets (modelling, UVs, materials, baking, rigging, animation) and export them for Unity.

For the complete reference-selection, modelling and visual-review loop, see [Selected references → Blender showcase](../patterns/reference-to-blender-showcase.md). This tool note covers individual commands and API findings.

## Installing (macOS)

Prefer Homebrew over downloading the app from blender.org:

```sh
brew install --cask blender
```

You still get `Blender.app`, but the cask also puts a `blender` command on `PATH` (`/opt/homebrew/bin/blender` → Caskroom wrapper), so agents can invoke it reliably from the shell. A manually installed app is only reachable via `/Applications/Blender.app/Contents/MacOS/Blender`, and paths vary between machines. Verified on this machine (5.2.2, 2026-09-23).

Upgrade with `brew upgrade --cask blender`, then re-check notes whose `versions` no longer match.

## Driving it

Blender is fully scriptable through its Python API (`bpy`) and runs headless.

```sh
# one-liner
blender -b --factory-startup --python-expr "import bpy; print(bpy.app.version_string)"

# script with its own arguments (everything after -- is passed to the script)
blender -b --factory-startup --python-exit-code 1 -P scripts/blender/some_script.py -- --out out/thing.glb

# operate on an existing file
blender -b path/to/file.blend --python-exit-code 1 -P script.py
```

- `-b` background (no UI), `-P` run a Python file, `--factory-startup` ignore user prefs/add-ons for reproducibility.
- In the script, read your own args with `sys.argv[sys.argv.index("--") + 1:]`.
- Use `--python-exit-code 1` so script exceptions fail the shell command. Without it, a traceback can still accompany exit code 0 (observed on 5.2.2).

## Verified recipes

- ✅ Headless start and GLB export of a primitive (2026-09-23, 5.2.2):
  ```sh
  blender -b --factory-startup --python-expr \
    "import bpy; bpy.ops.mesh.primitive_monkey_add(); bpy.ops.export_scene.gltf(filepath='/tmp/smoke.glb')"
  ```
  Produced a ~70 KB `.glb`. (The default scene's cube, camera and light were exported too.)

- ✅ Saved-scene Cycles rendering on Metal ([showcase experiment](../experiments/2026-09-23-blender-showcase.md)):
  ```sh
  blender -b out/scene.blend --python-exit-code 1 \
    -P scripts/blender/render_scene.py -- --out out/preview.png \
    --camera "Camera" --width 2560 --height 1920 --samples 192 --device METAL
  ```
  Exact camera name required when supplied. Writes a PNG and sidecar containing camera, device, dimensions, sample count, Blender version, timing and source-scene SHA-256. Does not modify the `.blend`.
- Enable Metal devices through `bpy.context.preferences.addons["cycles"].preferences`, call `get_devices()`, select `device.type == "METAL"`, then set `scene.cycles.device = "GPU"`. The helper fails explicitly if unavailable; its CPU option is **(unverified)**.
- `bpy.data.meshes.new` / `from_pydata` and data-linked objects worked for procedural geometry. Repeated unskinned shapes can share one mesh with object-level material slots. **Copy mesh data before assigning different skin weights** (`obj.data = obj.data.copy()`): vertex weight data is shared with the mesh, even though vertex-group names are object-level. The rig hand-off caught unrelated body parts moving with a limb. Named collections and embedded source texts make the resulting `.blend` inspectable.
- Procedural wood/stone shaders, metallic reflections and transmissive glass were rendered without external textures. Inspect a close-up as well as the full scene; broad vein patterns and coplanar surfaces can hide in the wide shot.
- Convert sRGB/hex colours to linear RGB for shader inputs. Colour management was AgX with Medium High Contrast in the tested scene.

## Diagnostic FBX rig hand-off

Verified with Unity 6000.6.2f1: [experiment and commands](../experiments/2026-09-24-blender-unity-rig-handoff.md). [`export_rig_probe.py`](../../scripts/blender/export_rig_probe.py) exports only the named rig and its descendants, resets the rig object's placement and pose, and bakes a one-second diagnostic bone rotation. It never changes the input `.blend`.

- Choose a **moving mesh witness away from the joint**, plus unaffected head/foot meshes. A symmetric joint's bounding-box centre may not move even when its vertices rotate. Check intended deformation **and** unintended movement.
- Settings: FBX `-Z` forward / `Y` up, `FBX_SCALE_UNITS`, metre units, no leaf bones, no experimental `bake_space_transform`; bake the current take at 24 fps with simplification disabled. With Unity `bakeAxisConversion=true`, measured mapping is `(x, z, y)`, not `(x, z, -y)`. Inspect markers rather than assuming facing.
- With a single scene bake, the take was named after the **scene**, not its active action. The helper names both `HandoffProbe`.
- The tested rig has 16 deform bones and segmented rigid weights, not a production continuous skin. Six decorative curves are converted to unskinned meshes and reported explicitly; this does not bind them for later torso/limb animation.
- Blender shader graphs do not become equivalent Unity materials. The later static transfer below bakes supported colour/normal detail; full visual parity remains separate work.

## Static geometry and procedural surface hand-off

[`export_static_scene.py`](../../scripts/blender/export_static_scene.py) now exports a detailed static environment with baked colour/normal atlases; [experiment and limits](../experiments/2026-09-24-static-scene-unity.md).

- Exclude character/studio collections explicitly. The helper evaluates mesh modifiers, curves and text, then joins by collection and material. It does not transfer rigs, lights or cameras.
- **Preserve procedural coordinates before joining.** Store normalized object-local bounding-box coordinates in a point-domain vector attribute, then use a Shader Attribute node instead of Generated coordinates. Handle unconnected procedural texture Vector inputs too; Noise used implicit Generated coordinates in the tested source. Applying world transforms or joining first changes that coordinate system.
- Triangulate before UV unwrap, tangent-normal baking and export. The original n-gons prevented FBX tangent export; remove genuinely zero-area triangles before comparing engine geometry counts.
- Bake linked Base Color through a temporary Emission output, then restore the Principled output for a tangent-normal bake. Save colour as sRGB, normal as Non-Color. Scalar roughness/metal/transmission/emission factors travel in JSON, not extra constant-colour textures.
- The helper requires metre-scale coordinates, one direct Principled material per object, Generated-coordinate procedural textures and unlinked scalar factors. Guards reject non-metre units, multiple slots, indirect surface outputs, linked scalar factors and explicit non-Generated coordinate outputs. Existing UV image textures and other graph variants are outside its contract, not a verified general-purpose material conversion. Metal is the verified bake device.
- `--planar-material NAME` separates coplanar groups for engine-side planar reflections. Other groups remain collection/material based. Inspect both the complete room and close-up surfaces after import.

## To explore

- Eevee vs Cycles preview quality and speed; Metal Cycles is now exercised.
- Broader `bmesh` modelling; triangulation/subdivision and front-panel normal correction are now exercised in the motion study.
- Applying model-generated textures; broader PBR map baking and arbitrary shader graphs. Procedural colour/normal baking is now verified for the constrained static workflow above.
- Production animation, Humanoid retargeting and closer renderer parity; neither the Generic diagnostic nor the static bake establishes these.
- Geometry Nodes for procedural assets.
- Blender 5.2 compositor API: introspection found `Scene.compositing_node_group`, not `Scene.node_tree`; old glare properties have moved to sockets. Rendering a compositor graph remains **(unverified)**.
- Revisit `Material.use_nodes` / `World.use_nodes` on Blender 6.0; 5.2 emits deprecation warnings.

## First idle/walk study

[Evidence](../experiments/2026-09-24-idle-walk-motion-study.md): a private neutral-limb derivative, all decorative curves converted and rigidly weighted to their intended bones, analytic two-bone legs baked to editable FK keys, 2.4 s idle and 1.2 s walk at 30 fps.

- Derive stance travel from desired translation speed, cycle duration and stance fraction. Stance feet move backward in the in-place clip; adding forward world translation should cancel it. Use a forward knee pole and fail on unreachable targets instead of stretching limbs silently.
- Inspect half-frame samples, not only keys: the first passing study still showed about 0.37 mm of interpolated contact drift. This is a measured tolerance, not exact mathematical foot locking.
- Blender 5.2 layered-action curves are accessible through `action.layers`, strips and channelbags. Set baked-key interpolation explicitly; keep inactive clips via `use_fake_user` and restore the intended action/slot before saving.
- A single baked take per FBX avoids action-selection ambiguity. Half-frame export keys plus Unity `resampleCurves=false` preserved the measured poses; see Unity notes for the resampling failure.
- Curved garment overlays need tessellation **before** projection onto the body. Moving only a large polygon's corners leaves the interior cutting through the coat. Check face winding too: Blender's double-sided rendering can hide faces Unity will cull.
- This remains segmented, flat-footed animation. Heel/toe roll, seamless joints, turns and transitions are separate quality work, not implied by a low drift figure.
