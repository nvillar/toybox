# Scripts

Reusable helpers that link tools together. Only scripts that have actually worked belong here.

| Folder | Contents | How it runs |
|--------|----------|-------------|
| `gen/` | Capability wrappers with a stable interface and platform-specific backends | `python3 scripts/gen/<capability>.py …` |
| `setup/` | Per-platform toolchain setup | `scripts/setup/<platform>.sh` |
| `blender/` | `bpy` scripts | `blender -b --factory-startup -P scripts/blender/<script>.py -- <args>` |
| `unity/` | C# editor helpers for direct batch mode; Pipeline candidates | See [notes/tools/unity.md](../notes/tools/unity.md) |

Conventions:

- Parameterise via CLI args; no hard-coded user paths. Tool locations come from `PATH` or `TOYBOX_*` environment variables, falling back to `sandbox/tools/…`.
- Start each script with a short docstring: purpose, usage, tool version it was tested with.
- Write outputs to `out/` by default.
- Generation wrappers: stdlib-only Python (runs on macOS system Python 3.9), always resolve and record a seed, and write an `<out>.json` provenance sidecar.
- Backends are registered per platform id; only register ones that have been run. See [notes/platforms.md](../notes/platforms.md).
- List each script below.

## Index

| Script | Purpose | Backends (verified) |
|--------|---------|---------------------|
| [`gen/image.py`](gen/image.py) | Text-to-image (textures, backgrounds, sprites) | `mflux` (macos-arm64) |
| [`gen/audio.py`](gen/audio.py) | SFX / music from text | `sa3-mlx` (macos-arm64) |
| [`gen/batch.py`](gen/batch.py) | Batch images from a JSON shot list with a shared style suffix (concept sets, variations) | via `image.py` |
| [`gen/contact_sheet.py`](gen/contact_sheet.py) | Tile images into a labelled JPEG for review (`uv run`, Pillow) | — |
| [`gen/gallery.py`](gen/gallery.py) | Build a local image gallery with round/model filters, full-size viewing and provenance (stdlib Python) | — |
| [`gen/toybox_gen.py`](gen/toybox_gen.py) | Shared: platform detection, backend selection, seeds, provenance | — |
| [`blender/render_scene.py`](blender/render_scene.py) | Render a saved scene/camera to PNG with scene-hash provenance | Cycles / Metal, Blender 5.2.2 |
| [`blender/export_rig_probe.py`](blender/export_rig_probe.py) | Character-only FBX diagnostic, moving/stationary mesh guards and expected measurements | Blender 5.2.2 |
| [`unity/RigImportProbe.cs`](unity/RigImportProbe.cs) | Import FBX, check Generic Animator/skin/axes, capture poses and save/reopen a scene | Unity 6000.6.2f1, built-in renderer, macOS |
| [`unity/AnimationStudy.cs`](unity/AnimationStudy.cs) | Compare idle/walk bones and all mesh bounds, measure world-space foot contacts, render loops and check real Play Mode; requires `RigImportProbe.cs` | Unity 6000.6.2f1, built-in renderer, macOS |
| [`unity/StudyLocomotion.cs`](unity/StudyLocomotion.cs) | Constant-speed, camera-follow study preview with a four-cycle position reset; not a player controller | Unity 6000.6.2f1 |
| [`setup/macos.sh`](setup/macos.sh) | Install Blender, uv, ffmpeg, MFLUX, Stable Audio 3 MLX on Apple Silicon | — |
