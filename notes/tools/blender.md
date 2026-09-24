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
blender -b --factory-startup -P scripts/blender/some_script.py -- --out out/thing.glb

# operate on an existing file
blender -b path/to/file.blend -P script.py
```

- `-b` background (no UI), `-P` run a Python file, `--factory-startup` ignore user prefs/add-ons for reproducibility.
- In the script, read your own args with `sys.argv[sys.argv.index("--") + 1:]`.

## Verified recipes

- ✅ Headless start and GLB export of a primitive (2026-09-23, 5.2.2):
  ```sh
  blender -b --factory-startup --python-expr \
    "import bpy; bpy.ops.mesh.primitive_monkey_add(); bpy.ops.export_scene.gltf(filepath='/tmp/smoke.glb')"
  ```
  Produced a ~70 KB `.glb`. (The default scene's cube, camera and light were exported too.)

## To explore

- Headless preview renders (Eevee vs Cycles, speed) so the agent can look at results.
- Prefer `bpy.data` / `bmesh` over `bpy.ops` where possible — ops depend on context. (unverified for 5.x specifics)
- Applying generated textures to materials and baking PBR maps.
- Export settings for Unity: scale, axes, apply modifiers, animations. (unverified)
- Geometry Nodes for procedural assets.
