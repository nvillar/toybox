# Environment baseline

- **Date:** 2026-09-23
- **Goal:** confirm which tools are available and that the agent can drive them from the shell.
- **Tools & versions:** Blender 5.2.2 LTS (Homebrew cask, `/opt/homebrew/bin/blender`), unity CLI 1.0.0-beta.8 (`~/.unity/bin/unity`), macOS arm64.

## What we did

```sh
blender --version
blender -b --factory-startup --python-expr \
  "import bpy; bpy.ops.mesh.primitive_monkey_add(); bpy.ops.export_scene.gltf(filepath='/tmp/toybox_smoke.glb'); print('OK', bpy.app.version_string)"

unity --version
unity --help
unity pipeline --help
unity command --help
unity status
unity editors --json
```

## What happened

- Blender ran headless and wrote a ~70 KB GLB.
- `unity editors` lists several arm64 editors, including 6000.7.0b1, 6000.3.24f1, 6000.0.84f1 and others.
- `unity status` showed no connected editors (none were open).
- The `unity` CLI exposes `pipeline install`, `command`, `job`, `shell`, `run`, `test`, `build`, and `skill install`.

## Learnings

- Blender driving is straightforward → [tools/blender.md](../tools/blender.md).
- The Unity live-editor workflow depends on the Pipeline package being installed in a project → [tools/unity.md](../tools/unity.md).

## Follow-ups

- Exercise the Unity Pipeline and C# eval end-to-end (see backlog).
