---
status: partial
last_verified: 2026-09-23
versions: { blender: 5.2.2 LTS }
---

# Blender

Role: create and edit 3D assets (modelling, UVs, materials, baking, rigging, animation) and export them for Unity.

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
- `bpy.data.meshes.new` / `from_pydata` and data-linked objects worked for procedural geometry. Repeated shapes can share one mesh with object-level material slots. Named collections and embedded source texts make the resulting `.blend` inspectable.
- Procedural wood/stone shaders, metallic reflections and transmissive glass were rendered without external textures. Inspect a close-up as well as the full scene; broad vein patterns and coplanar surfaces can hide in the wide shot.
- Convert sRGB/hex colours to linear RGB for shader inputs. Colour management was AgX with Medium High Contrast in the tested scene.

## To explore

- Eevee vs Cycles preview quality and speed; Metal Cycles is now exercised.
- `bmesh` workflows (unverified here).
- Applying generated textures to materials and baking PBR maps.
- Export settings for Unity: scale, axes, apply modifiers, animations. (unverified)
- Geometry Nodes for procedural assets.
- Blender 5.2 compositor API: introspection found `Scene.compositing_node_group`, not `Scene.node_tree`; old glare properties have moved to sockets. Rendering a compositor graph remains **(unverified)**.
- Revisit `Material.use_nodes` / `World.use_nodes` on Blender 6.0; 5.2 emits deprecation warnings.
