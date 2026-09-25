# In-place idle/walk, measured contacts and Unity playback

- **Date:** 2026-09-24
- **Goal:** Progress from a diagnostic limb motion to an editable first walk study before player control.
- **Tools:** Blender 5.2.2 LTS, Unity 6000.6.2f1 (built-in renderer), FFmpeg 9.0.2, macOS 15.8 / M4 Max.

## What we did

Created a private derivative of the previously tested character rather than overwriting its showcase. Prepared neutral limbs, grounded the soles, bound six previously rigid decorative parts and authored a 2.4 s idle plus 1.2 s in-place walk at 30 fps. Analytic two-bone leg poses use a forward knee pole; all results are editable FK keys, not a live procedural runtime rig.

The first walk uses 0.72 m/s translation and a 62% stance phase. Stance feet travel backward at the matching speed; swing feet follow a smooth trajectory with about 9.5 cm clearance. Pelvis sway/bob and counter-swinging arms are restrained. Flat-footed contacts are intentional for this first study, **not a claim of finished natural locomotion**.

Project-specific Blender source and measurements stay private. Generic Unity helpers are [`AnimationStudy.cs`](../../scripts/unity/AnimationStudy.cs), [`StudyLocomotion.cs`](../../scripts/unity/StudyLocomotion.cs), and the existing [`RigImportProbe.cs`](../../scripts/unity/RigImportProbe.cs), whose small shared utilities were exposed internally rather than copied.

Commands below begin after private source export; input files are `idle.fbx`, `walk.fbx` and their `.expected.json` measurements. A disposable project is created/copied using the [verified editor workflow](../tools/unity.md).

```sh
mkdir -p out/unity/MotionStudy/Assets/Editor out/unity/MotionStudy/Assets/Study
cp scripts/unity/AnimationStudy.cs scripts/unity/RigImportProbe.cs out/unity/MotionStudy/Assets/Editor/
cp scripts/unity/StudyLocomotion.cs out/unity/MotionStudy/Assets/Study/
# Copy the four exported input files into Assets/Study, then:
UNITY_EDITOR=/Applications/Unity/Hub/Editor/6000.6.2f1/Unity.app/Contents/MacOS/Unity
"$UNITY_EDITOR" -batchmode -quit -projectPath "$PWD/out/unity/MotionStudy" \
  -executeMethod AnimationStudy.Run -studyAssets Assets/Study \
  -probeOut "$PWD/out/motion-study/unity-final" -logFile "$PWD/out/motion-study/unity-final.log"
"$UNITY_EDITOR" -batchmode -projectPath "$PWD/out/unity/MotionStudy" \
  -executeMethod AnimationStudy.VerifyPlayback -studyAssets Assets/Study \
  -probeOut "$PWD/out/motion-study/unity-final" -logFile "$PWD/out/motion-study/playback.log"
```

The second command intentionally omits `-quit`: the helper enters real Play Mode and exits after its checks. Neither command uses `-nographics`, a new Unity sign-in, a cloud project or the Pipeline package.

## What happened

| Measurement | Idle | Walk |
|-------------|------|------|
| Duration / fps | 2.4 s / 30 | 1.2 s / 30 |
| Sampled times, including half frames and both endpoints | 145 | 73 |
| Bones / skinned meshes | 16 / 54 | 16 / 54 |
| Maximum bone mismatch with Blender | ~0.0013 mm | ~0.0020 mm |
| Maximum mesh-bounds mismatch | <0.003 mm | <0.003 mm |
| Maximum world-space stance drift | <0.001 mm | ~0.371 mm |
| Lowest foot excursion below nominal floor | <0.001 mm | ~0.366 mm |
| Swing clearance | Stationary | ~94.9 mm, both feet |

Thresholds: 3 mm bone mismatch, 5 mm mesh-bound mismatch, 3 mm stance drift, 2 mm floor/contact excursion, 1 mm loop error, at least 70 mm swing clearance. The thresholds were not relaxed to accept initial failures. Measurements are for this asset and sampled times, not guarantees over all continuous times or assets.

The saved project was copied without caches and passed again. Real Play Mode advanced beyond four cycles, moved at the expected speed, kept the camera offset and performed exactly one deliberate preview reset. This checks automatic straight-line playback, not input, turns or navigation. The separate idle and walk scenes do not yet blend clips.

A negative control changed only the commanded walk speed to 0.85 m/s in a disposable copy. The contact guard rejected it with about 95.3 mm stance drift and a nonzero exit; the fixture was restored afterward.

Four 1000-square H.264/yuv420p clips show front/side views at real time: 72 frames per idle view and 36 per walk view. FFmpeg was missing, so installed with `brew install ffmpeg`, then verified as 9.0.2. Example:

```sh
ffmpeg -hide_banner -loglevel error -framerate 30 \
  -i out/motion-study/unity-final/walk/front_%03d.png \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart \
  out/motion-study/review/walk-front.mp4
ffprobe -v error -show_entries stream=codec_name,width,height,nb_frames,r_frame_rate:format=duration \
  -of json out/motion-study/review/walk-front.mp4
```

Exclude the duplicated endpoint from video loops. The character's pose loops, but the world checkerboard shifts with travel and resets on replay; these are short review clips, not seamless environment footage.

## Corrections discovered through iteration

- An initial leg target exceeded its fixed segment lengths. Reduced pelvis height within the intended cautious gait instead of silently stretching bones.
- Default Unity curve resampling caused a 3.76 mm half-frame bone mismatch even with compression off. Exporting half-frame keys alone did not fix it; `resampleCurves=false` preserved them and reduced mismatch to micrometre-scale observations. This is why testing only authored keys is insufficient.
- Side views exposed floating garment panels. Tessellating before projection fixed interior/body intersections. Blender showed backfaces that Unity culled; explicit outward face winding restored the missing front panels rather than masking the issue with a double-sided shader.
- Overlaid floor geometry produced distracting depth patterns; a single two-material checker mesh fixed the review stage.
- Mathematical contact checks and attractive stills are complementary, not substitutes for motion review. The walk remains visibly segmented and flat-footed; heel/toe roll and production joints are unresolved.

Distilled into [Blender](../tools/blender.md), [Unity](../tools/unity.md), the [pipeline](../pipeline.md), script index and backlog. Selected videos, sources, `.blend`, FBX, expected measurements, reports and a minimal Unity project are privately archived. Raw frame sequences, intermediate failures and `Library/` stay in ignored scratch.

## Follow-ups

Human motion review; heel/toe roll and weight transfer; shoulder/hip topology; transitions and turns; then player input, collision and speed/clip coordination. These remain explicit backlog items.
