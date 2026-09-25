# Backlog

Open questions and next experiments. Move items into an experiment log when you pick them up; delete or strike them when resolved (link the log).

## Next experiments

- [x] **Blender → Unity rig hand-off**: FBX Generic import, Animator/Playables, scale/axis/skin checks and screenshots ([experiment](experiments/2026-09-24-blender-unity-rig-handoff.md)). This is one-way, not a Unity-to-Blender round trip.
- [ ] **GLB into Unity**: add a glTF importer in a disposable project and compare simple textured assets with FBX.
- [ ] **Unity CLI basics**: create a project, install the Pipeline package, open it, list `unity command` tools, find and try C# eval.
- [ ] **Unity CLI startup**: investigate stalled `projects new` / `run` and listed-but-unlocatable editors. Direct editor batch mode is verified; do not assume cloud authentication is needed for local asset checks.
- [x] **Headless Blender preview render**: Cycles/Metal with explicit camera and scene-hash sidecar ([experiment](experiments/2026-09-23-blender-showcase.md)).
- [ ] **First texture in Blender**: generate a tileable texture with `scripts/gen/image.py`, apply it to a mesh, check seams by 2×2 tiling, export GLB.
- [ ] **SFX into Unity**: generate a handful of UI/pickup sounds with `scripts/gen/audio.py`, normalise with `ffmpeg`, play them from Unity.
- [ ] **NVIDIA backend for images**: diffusers `Flux2KleinPipeline` (or ComfyUI API) with FLUX.2 Klein 4B on a Windows/Linux CUDA box; register in `scripts/gen/image.py`.
- [ ] **NVIDIA backend for audio**: Stable Audio 3 TensorRT `sa3` on Linux (and try Windows/WSL2); register in `scripts/gen/audio.py`.
- [ ] **AMD ROCm backends**: same as above on PyTorch ROCm; try Stable Audio 3 ONNX exports.
- [ ] **oMLX vs Ollama** on the M4 Max: throughput, memory, API compatibility.
- [ ] **Image edit / references** via `mflux-generate-flux2-edit` (9B KV, non-commercial) and a commercial-safe alternative.
- [ ] **Commercial-safe in-image text**: find a shippable alternative to Qwen-Image-2.1 for titles/UI text (or overlay real fonts), and compare.
- [ ] **Private game repo via `unity vcs`**: create a throwaway Unity project, run `unity vcs setup --vcs github --git-visibility private --git-lfs`, then `unity vcs doctor` and `merge-setup`. Push a generated texture + WAV (with sidecars), clone elsewhere, `unity vcs sync`. Record LFS patterns, locking, and GitHub LFS quota behaviour in [tools/asset-storage.md](tools/asset-storage.md).
- [ ] **Multi-user LFS locking**: test lock/unlock and competing edits to a disposable binary with two collaborators. Private-library upload/restore is [verified](experiments/2026-09-23-private-asset-library.md); shared access and locking are not.
- [ ] **Bulk storage (deferred)**: try `rclone` to a private R2/S3 bucket when large batches or video justify it. Small selected experiments now live in the private LFS library; disposable runs stay local.
- [x] Install `ffmpeg`: Homebrew 9.0.2; four H.264 motion-review loops encoded and inspected ([experiment](experiments/2026-09-24-idle-walk-motion-study.md)).
- [ ] **Tiny vertical slice**: one scene, one controllable object, one generated model, one texture, one sound, one test.
- [x] **First idle/walk study**: neutral limbs, all 54 pieces skinned, half-frame floor/contact measurements, +Z Unity parent convention and constant-speed Play Mode preview ([experiment](experiments/2026-09-24-idle-walk-motion-study.md)).
- [ ] **Concept → production model**: production shoulder/hip topology, heel/toe roll, less mechanical weight transfer, idle/walk transitions and turning. The verified first walk is flat-footed and segmented, not production animation.
- [ ] **Player control**: build on measured 0.72 m/s in-place walk; coordinate clip speed with translation, add input/collision and transitions. The study preview is straight-line and automatically resets after four cycles, not navigation.
- [ ] **Blender → Unity appearance**: bake procedural materials, compare lighting, and optimize mesh/renderer counts; successful rig import does not establish visual parity or game-ready budgets.
- [ ] **Miniature animation**: test natural articulated locomotion independently of any deliberately stepped/stop-motion treatment; visual scale does not dictate movement style. Also survey local image-to-video models (licences, MLX/CUDA backends).
- [ ] **Local vs cloud concept art**: run the same brief and suffix through a cloud image model and compare quality, consistency and terms.
- [ ] **Character consistency across shots** with commercial-safe models (Klein 9B-kv reference editing is non-commercial).

## Open questions

- Voice / TTS: which model, on which backends?
- Is the Stability AI Community License acceptable for the games we want to ship? (Revenue thresholds apply.)
- Can multiple MLX jobs (image + audio + LLM) run concurrently in separate processes without contention problems, given 128 GB unified memory?
- Provenance: per-asset sidecars are now the default. Do we also want a project-level manifest?
- What does "publishing" mean for us first: a desktop build, WebGL on a page, or a store?
