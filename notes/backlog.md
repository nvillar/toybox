# Backlog

Open questions and next experiments. Move items into an experiment log when you pick them up; delete or strike them when resolved (link the log).

## Next experiments

- [ ] **Blender → Unity round-trip**: generate a mesh with bpy, export GLB, import into a fresh Unity project, place it in a scene, capture a screenshot.
- [ ] **Unity CLI basics**: create a project, install the Pipeline package, open it, list `unity command` tools, find and try C# eval.
- [ ] **Headless Blender preview render** so the agent can inspect models visually.
- [ ] **First texture in Blender**: generate a tileable texture with `scripts/gen/image.py`, apply it to a mesh, check seams by 2×2 tiling, export GLB.
- [ ] **SFX into Unity**: generate a handful of UI/pickup sounds with `scripts/gen/audio.py`, normalise with `ffmpeg`, play them from Unity.
- [ ] **NVIDIA backend for images**: diffusers `Flux2KleinPipeline` (or ComfyUI API) with FLUX.2 Klein 4B on a Windows/Linux CUDA box; register in `scripts/gen/image.py`.
- [ ] **NVIDIA backend for audio**: Stable Audio 3 TensorRT `sa3` on Linux (and try Windows/WSL2); register in `scripts/gen/audio.py`.
- [ ] **AMD ROCm backends**: same as above on PyTorch ROCm; try Stable Audio 3 ONNX exports.
- [ ] **oMLX vs Ollama** on the M4 Max: throughput, memory, API compatibility.
- [ ] **Image edit / references** via `mflux-generate-flux2-edit` (9B KV, non-commercial) and a commercial-safe alternative.
- [ ] **Qwen-Image-2.1** via MFLUX 0.20.0: finish download, test, register in `scripts/gen/image.py` flagged non-commercial.
- [ ] **Private game repo via `unity vcs`**: create a throwaway Unity project, run `unity vcs setup --vcs github --git-visibility private --git-lfs`, then `unity vcs doctor` and `merge-setup`. Push a generated texture + WAV (with sidecars), clone elsewhere, `unity vcs sync`. Record LFS patterns, locking, and GitHub LFS quota behaviour in [tools/asset-storage.md](tools/asset-storage.md).
- [ ] **Bulk storage**: try `rclone` to a private R2/S3 bucket for raw generation batches; decide the promotion flow into the game repo.
- [ ] Install `ffmpeg` (`brew install ffmpeg`, or run `scripts/setup/macos.sh`). Not present yet.
- [ ] **Tiny vertical slice**: one scene, one controllable object, one generated model, one texture, one sound, one test.

## Open questions

- Voice / TTS: which model, on which backends?
- Is the Stability AI Community License acceptable for the games we want to ship? (Revenue thresholds apply.)
- Can multiple MLX jobs (image + audio + LLM) run concurrently in separate processes without contention problems, given 128 GB unified memory?
- Provenance: per-asset sidecars are now the default. Do we also want a project-level manifest?
- Where should Unity projects live — in this repo under `sandbox/`, or separate repos?
- What does "publishing" mean for us first: a desktop build, WebGL on a page, or a store?
