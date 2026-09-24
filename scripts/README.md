# Scripts

Reusable helpers that link tools together. Only scripts that have actually worked belong here.

| Folder | Contents | How it runs |
|--------|----------|-------------|
| `gen/` | Capability wrappers with a stable interface and platform-specific backends | `python3 scripts/gen/<capability>.py …` |
| `setup/` | Per-platform toolchain setup | `scripts/setup/<platform>.sh` |
| `blender/` | `bpy` scripts | `blender -b --factory-startup -P scripts/blender/<script>.py -- <args>` |
| `unity/` | C# editor scripts / snippets for the Pipeline package | See [notes/tools/unity.md](../notes/tools/unity.md) |

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
| [`gen/toybox_gen.py`](gen/toybox_gen.py) | Shared: platform detection, backend selection, seeds, provenance | — |
| [`setup/macos.sh`](setup/macos.sh) | Install Blender, uv, ffmpeg, MFLUX, Stable Audio 3 MLX on Apple Silicon | — |
