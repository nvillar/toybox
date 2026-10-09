# URP scaffold, native player, and unsigned iOS build

- **Date:** 2026-10-08
- **Goal:** establish a reproducible URP/Blender workflow on the replacement editor and separate compilation evidence from physical-device acceptance.
- **Tools & versions:** macOS Sequoia 15.8.1 arm64; Unity 6000.6.5f1; URP 17.6.0; Input System 1.20.0; Test Framework 1.8.0; uGUI 2.6.0; Blender 5.2.2 LTS; Xcode 26.3 (17C529), iOS SDK 26.2; Apple Git 2.50.1; Git LFS 3.8.0; uv 0.10.3.

## What we did

Created a disposable project with the actual editor and its installed URP archive:

```sh
EDITOR=/Applications/Unity/Hub/Editor/6000.6.5f1/Unity.app/Contents/MacOS/Unity
TEMPLATE=/Applications/Unity/Hub/Editor/6000.6.5f1/Unity.app/Contents/Resources/PackageManager/ProjectTemplates/com.unity.template.urp-blank-17.2.1.tgz
PROJECT="$PWD/out/unity/2026-10-08-scaffold/UrpProbe"
mkdir -p "$(dirname "$PROJECT")"
"$EDITOR" -batchmode -quit -createProject "$PROJECT" \
  -cloneFromTemplate "$TEMPLATE" \
  -logFile "$PWD/out/unity/2026-10-08-scaffold/create.log"
```

Promoted the exercised command to [`scripts/unity/create_urp.sh`](../../scripts/unity/create_urp.sh) and ran it against a second fresh disposable directory:

```sh
bash scripts/unity/create_urp.sh "$EDITOR" "$TEMPLATE" \
  "$PWD/out/unity/2026-10-08-scaffold/HelperProbe" \
  "$PWD/out/unity/2026-10-08-scaffold/helper-create.log"
```

The helper refuses an existing destination. It does not create a Cloud project or use the separate Unity CLI.

In a private project, generated a small multi-mesh Blender fixture, kept its editable source outside `Assets/`, and exported FBX with metre units, `FBX_SCALE_UNITS`, `-Z` forward / `Y` up, and no animation. Unity imported with scale 1, file units and baked axis conversion enabled, and no imported materials. Authored URP materials and compound primitive collision geometry independently.

Added EditMode and PlayMode checks plus native build/smoke entry points. Project-specific helper names, assets, and source paths stay private. The exercised batch forms were:

```sh
# PROJECT is the private checkout; RESULT and LOG are ignored output paths.
"$EDITOR" -batchmode -projectPath "$PROJECT" -buildTarget StandaloneOSX \
  -runTests -testPlatform EditMode -testResults "$RESULT" -logFile "$LOG"
# Same form with -testPlatform PlayMode for scene/input/physics/render checks.
# For builds: -batchmode -quit -buildTarget StandaloneOSX (or iOS)
#             -executeMethod <project's build entry point>
```

The generated iOS project used IL2CPP/ARM64, Metal, deployment minimum 26.0, and both device families. From the private project root:

```sh
xcodebuild -quiet -project Builds/iOS/Unity-iPhone.xcodeproj \
  -scheme Unity-iPhone -configuration Debug -sdk iphoneos \
  -destination 'generic/platform=iOS' \
  -derivedDataPath Builds/DerivedData CODE_SIGNING_ALLOWED=NO
```

Uploaded two binary assets through repo-local LFS, then cloned the private remote into a new ignored scratch directory with `GIT_LFS_SKIP_SMUDGE=1`. Ran `git lfs install --local`, `git lfs pull`, and `git lfs fsck`; compared SHA-256 for every tracked file. Repeated tests, desktop build/run, and iOS export with no project Library cache.

## What happened

- Both URP creation paths succeeded. Archive version **17.2.1** contained URP **17.6.0**. Input System resolved from the archive's 1.19.0 to **1.20.0**. Commit the generated manifest and lockfile, not guessed versions.
- The imported mesh bounds and facing matched the authored fixture. There was no dependency on invoking Blender during a clone's Unity import.
- **11 EditMode and 5 PlayMode cases passed**, including synthetic mouse/touch events through `InputSystemUIInputModule`, physics raycasts, UI clicks, release/reset, and portrait/landscape URP captures. These are not physical touchscreen events.
- The macOS Mono development player built, captured its actual HUD, settled a released Rigidbody, reset it, and exited successfully under a 60-second launcher limit. Its final runtime log was clean.
- iOS export and desktop build had **zero Unity build errors/warnings**. Xcode compiled and linked an unsigned device app. Built Info.plist values matched deployment/device-family/orientation requirements.
- Xcode warned about deprecated APIs in Unity-generated native code, deprecated `UIRequiresFullScreen`, build-script output declarations, and the missing final App Store icon. No generated engine code was patched to hide these warnings.
- Final remote restore: **112 tracked files matched byte-for-byte**, including both LFS payloads. Cache-free tests, desktop build/smoke, and iOS export passed with **no tracked-source drift**.
- No signing, physical-device run, simulator app run, browser build, or distribution acceptance was performed. Private assets/captures were not published here.

## Learnings

- Plain `-createProject` is not a URP request. Use `-cloneFromTemplate` explicitly; [helper](../../scripts/unity/create_urp.sh) now captures that contract.
- Omit `-quit` for `-runTests`; let the test runner finish and inspect its XML. Keep graphics enabled for image evidence.
- Persistent settings need editor serialization, not only runtime setters. For the 60 Hz timestep, set `Time.fixedDeltaTime`, mark the loaded TimeManager dirty, and save. The current serialized timestep is rational rather than a plain float; assigning `SerializedProperty.floatValue` did not change it.
- `supportsSoftShadows` is read-only in the current URP asset API; editor tooling used its serialized `m_SoftShadowsSupported` field.
- A first `RenderPipeline.StandardRequest` capture showed incorrect material colors. Using `UniversalRenderPipeline.SingleCameraRequest` and separating captures by a frame produced correct inspected images. Camera requests omit a screen-space overlay HUD; the native `ScreenCapture.CaptureScreenshot` path includes it.
- Disable unused renderer post-process data when all post-processing is intentionally off. Retaining it with stripped effect shaders produced runtime warnings; removing it avoided those warnings without enabling unnecessary effects.
- Batch tests have no focused Game view. Temporarily allow background input and `AllDeviceInputAlwaysGoesToGameView`, then restore settings. Queue actual `MouseState`/`TouchState` events instead of claiming input coverage from direct handler calls.
- `DEVELOPMENT_BUILD` now produces a deprecation warning. Use `Debug.isDebugBuild` for a development-only runtime probe. The first native probe timed out; the final diagnostic path also enables `Application.runInBackground` only while running that probe, so focus changes cannot pause acceptance.
- iPhone/iPad orientation needs both plist and runtime policy: Unity's generated app delegate asks its root view controller for supported orientations. UIKit's device idiom avoids guessing tablet identity from model-name strings. Unsigned linking establishes native-helper integration, not rotation/window behavior.
- A first clean import normalized the iOS automatic-graphics-API flag. Keeping Unity's normalized setting and validating the effective API list as Metal-only eliminated that source drift.
- Unity-generated YAML contains trailing spaces after empty fields. Preserve serialization rather than hand-reformatting it; check authored source normally.

Distilled into [Unity](../tools/unity.md), [Blender](../tools/blender.md), [asset storage](../tools/asset-storage.md), and [platform readiness](../platforms.md).

## Follow-ups

Physical iPhone/iPad signing and acceptance, native rotation/window/safe-area behavior, touch feel, lifecycle interruptions, and sustained device performance remain in [the backlog](../backlog.md). The CLI/Pipeline, rig-animation recipes on this replacement editor, and Web target remain unverified.
