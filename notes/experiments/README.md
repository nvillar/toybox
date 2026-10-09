# Experiments

Dated logs of what we tried. Name files `YYYY-MM-DD-short-slug.md` and start from [`_template.md`](_template.md). Newest first.

| Date | Experiment | Outcome |
|------|------------|---------|
| 2026-10-08 | [URP scaffold and unsigned iOS build](2026-10-08-urp-scaffold.md) | 6000.6.5f1 URP/FBX/input/physics checks, native Mac player, unsigned Xcode compile, and LFS-backed cache-free rebuild with no source drift. Signing/device runs remain pending. |
| 2026-10-08 | [Xcode SDK/simulator preflight](2026-10-08-xcode-preflight.md) | Xcode 26.3 (17C529) selected on Sequoia 15.8.1; first-launch complete, SDKs 26.2 and simulator runtime 26.3.1 available. App builds/launches remain unverified. |
| 2026-10-08 | [Unity replacement/module inspection](2026-10-08-unity-installation.md) | Single 6000.6.5f1 arm64 editor, iOS/Web modules, bundled Mac Mono without optional Mac IL2CPP; CLI beta.12 and LFS 3.8.0 available. Xcode and new-version project/build validation pending. |
| 2026-10-07 | [Unity/iOS toolchain preflight](2026-10-07-unity-ios-preflight.md) | Direct editor + Blender FBX/Metal rechecked; iOS module, Xcode and current Git LFS absent. Plain project creation uses Built-in; URP template/package versions differ. Sequoia-compatible Xcode path documented, not built. |
| 2026-09-24 | [Detailed static scene → Unity](2026-09-24-static-scene-unity.md) | Generated-coordinate preservation, 21 colour/normal bakes, 33 grouped meshes, planar reflections and 1.5× locomotion; native and clean-restore acceptance. |
| 2026-09-24 | [Click-to-move native prototype](2026-09-24-click-to-move.md) | Static obstacle navigation, retarget/stop/reset and idle/walk crossfades; 32 native acceptance checks, cache-free rebuild and server-free video review. |
| 2026-09-24 | [Idle/walk motion study](2026-09-24-idle-walk-motion-study.md) | Neutral limbs and all-part binding; grounded in-place clips, Unity curve-resampling fix, real Play Mode preview and four H.264 review videos. |
| 2026-09-24 | [Blender → Unity rig hand-off](2026-09-24-blender-unity-rig-handoff.md) | Fixed shared skin weights; Generic FBX animation, scale/axes, three rendered poses and a reopened Unity scene. Direct editor works without new authentication; CLI stalled. |
| 2026-09-23 | [Procedural Blender showcase](2026-09-23-blender-showcase.md) | Editable private scene and four Metal/Cycles renders; generic renderer with scene-hash provenance. |
| 2026-09-23 | [Private asset library](2026-09-23-private-asset-library.md) | Private GitHub + LFS upload/restore; 77 files matched byte-for-byte. Generic public logs, private project details. |
| 2026-09-23 | [Concept-art exploration](2026-09-23-concept-art.md) | Concept set from Klein 4B in ~7 min; literal simile leakage; fixed-seed comparisons. New pattern + `batch.py`, `contact_sheet.py`. |
| 2026-09-23 | [MLX image and audio generation](2026-09-23-mlx-image-and-audio.md) | MFLUX (Klein 4B, Qwen-Image-2.1) + Stable Audio 3 MLX verified; `scripts/gen` wrappers added. |
| 2026-09-23 | [Environment baseline](2026-09-23-environment-baseline.md) | Blender headless + GLB export works; Unity CLI present. |
