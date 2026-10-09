---
status: partial
last_verified: 2026-10-09
versions: { unity-cli: 1.0.0-beta.12, unity-editor: 6000.6.5f1, xcode: "26.3 (17C529)" }
---

# Unity

Role: assemble assets into a playable game, run it, test it, and build it.

**Current installation:** [6000.6.5f1 arm64](../experiments/2026-10-08-unity-installation.md) is the only editor in the Hub directory. iOS and Web modules are present. Mac Mono players are bundled even with optional **Mac Build Support (IL2CPP)** unselected. Hub's **Web Build Support** still uses module ID `webgl` and directory `WebGLSupport`. A [current URP scaffold experiment](../experiments/2026-10-08-urp-scaffold.md) now verifies project creation, static FBX import, mouse/touch routing, physics, rendering, native Mac build/run, unsigned iOS compilation, and a cache-free remote restore. The animation/navigation recipes below retain their **6000.6.2f1** scope. CLI beta.12 is present; CLI help observations retain their original beta.8 scope.

## Driving it

The `unity` CLI (installed at `~/.unity/bin/unity`) wraps Hub/editor management and, together with the **Unity Pipeline** package installed into a project, lets the agent talk to a running editor.

Commands observed in `unity --help` (2026-09-23, 1.0.0-beta.8):

| Area | Commands |
|------|----------|
| Editors | `editors`, `install`, `install-modules`, `modules`, `releases` |
| Projects | `projects`, `templates`, `open`, `close`, `status` |
| Batch work | `run` (batch mode, forwards args), `build`, `test` (Edit/PlayMode, writes report) |
| Live editor | `pipeline install` (adds package to a project), `list` / `command` (execute registered editor commands), `job` (detached commands), `shell` (warm REPL) |
| Agents | `skill install <client>` (installs a Unity CLI agent skill), `mcp` |

Useful global flags: `--json`, `--non-interactive`, `--no-pager`, `--quiet`.

## Verified local batch workflow

The 6000.6.2f1 editor binary successfully created a project, imported FBX, ran a Generic rig through Animator/Playables, rendered three PNGs, and saved/reopened a scene. No Pipeline package or Unity Cloud project was needed. The existing local editor licence sufficed at that time; no additional account authentication was needed for these commands.

```sh
# Historical tested version; substitute an installed editor and revalidate.
UNITY_EDITOR=/Applications/Unity/Hub/Editor/6000.6.2f1/Unity.app/Contents/MacOS/Unity
mkdir -p out/unity
"$UNITY_EDITOR" -batchmode -quit -createProject "$PWD/out/unity/RigImportProbe" \
  -logFile "$PWD/out/unity-create.log"
```

Copy a C# editor helper into `Assets/Editor/` and assets into `Assets/`, then use `-projectPath … -executeMethod Class.Method`. The rig helper performs an explicit synchronous import and exits nonzero on failure; see [the complete experiment](../experiments/2026-09-24-blender-unity-rig-handoff.md).

### Scaffold and platform preflight

[Rechecked on 2026-10-07](../experiments/2026-10-07-unity-ios-preflight.md): the native 6000.6.2f1 editor created a project, compiled a helper, and imported an asymmetric Blender FBX with the expected metre dimensions under Metal. These are local checks, not proof that a shipping target is ready.

- `unity --version` reports the separate CLI version; invoke the actual editor with `-version` to identify the compiler/importer in use.
- **Choose the render pipeline explicitly.** Plain `-createProject` produced Built-in, not URP. Use `-createProject <new-path> -cloneFromTemplate <archive>`; [`create_urp.sh`](../../scripts/unity/create_urp.sh) is verified on 6000.6.5f1. The 3D URP archive is version `17.2.1`, but its manifest pins URP `17.6.0`. Input System resolved to 1.20.0 from a 1.19.0 template entry. Commit the generated manifest and lockfile; do not infer rendering-package versions from archive names.
- Installed modules in this Hub layout are under `/Applications/Unity/Hub/Editor/<version>/PlaybackEngines`, beside `Unity.app`. An entry in `modules.json` may describe an available download rather than an installed component. Use `BuildPipeline.IsBuildTargetSupported` as an editor-side check; macOS was true and iOS false.
- The licence at that preflight allowed batch work even though a token-refresh error appeared in the log. Do not infer cloud authentication from local success, or ignore a future licence failure.
- For VS Code, Microsoft's [Unity extension](https://code.visualstudio.com/docs/other/unity) uses `com.unity.ide.visualstudio` 2.0.20 or later, not the legacy VS Code Editor package. This authoring integration is **(unverified)** here; a PATH-visible .NET SDK is not required for the editor's own C# compiler.

### Current URP, tests, and native-player checks

Verified on **6000.6.5f1 / URP 17.6.0**: [commands, failures, and corrections](../experiments/2026-10-08-urp-scaffold.md).

- Separate runtime, editor, and test assemblies. Run `-runTests -testPlatform EditMode` or `PlayMode` with explicit result/log paths, **without `-quit`**. Check XML counts/results; a batch exit is not enough.
- For batch Input System tests, temporarily select `AllDeviceInputAlwaysGoesToGameView` and allow background processing; restore the previous settings afterward. Queue real `MouseState`/`TouchState` events and exercise UI/physics raycasters rather than only invoking handlers.
- Persist a fixed timestep through the actual TimeManager object: `Time.fixedDeltaTime = 1f / 60f`, mark it dirty, save, then reopen to verify. This version serializes rational time; setting the property's `floatValue` did not change it.
- Use `UniversalRenderPipeline.SingleCameraRequest` with a RenderTexture for URP camera captures; inspect pixels, not just hashes. The initial StandardRequest path produced wrong material colors. Camera captures do not include a screen-space overlay HUD; capture the real native frame separately with `ScreenCapture`.
- When post-processing is deliberately unused, clear the renderer's `postProcessData`; keeping stripped effect references produced avoidable runtime warnings.
- Use `Debug.isDebugBuild` for development-only runtime diagnostics; `DEVELOPMENT_BUILD` is deprecated here. A command-driven native probe should enable background execution for its duration and have an external timeout.
- A remote clone with restored LFS assets passed tests, Mac build/run, and iOS export without a project Library cache or source changes. Preserve Unity's normalized iOS automatic-graphics flag and assert the effective API list is Metal-only instead of repeatedly forcing a setting that the importer rewrites.

### Compound physics and input cancellation

[Verified with source-derived figures on 6000.6.5f1](../experiments/2026-10-09-unity-stacking.md):

- Unity's cylinder primitive carries a **capsule** collider. For a wide, shallow platform, replace it with collision geometry matching the disk; otherwise invisible support can sit far above the visible surface.
- Set interpolated kinematic poses through `Rigidbody.position` / `rotation`, and synchronize transforms before geometry queries. Transform-only placement snapped back in the experiment.
- Test a queued `TouchPhase.Canceled` through the real UI module; a pointer-up callback alone does not prove a valid tap. Suppress placement on cancellation, focus loss, or resize.
- Preserve independent smoke scene selection when changing the default build scene. A new gameplay entry point must not silently invalidate an older diagnostic command.
- URP Complex Lit clearcoat needs its keyword/mask/smoothness configured; reflection lighting is separate. Native frame review remains necessary even when shader compilation succeeds.
- For a camera-facing arcball with screen X right/Y up, Unity's near hemisphere is camera-local **negative Z**. Conjugate the local quaternion delta by camera rotation. Test projected near-surface motion in the pointer direction at several camera yaws, plus rim roll; drag-back undo alone also passes for reversed controls.
- A tuned spherical/cubic-shoulder/equator projection differs from a generic sphere/hyperbola trackball. Preserve its curve, logical-pixel bounds, flick sampling and decay independently. Use shared projected bounds for visible/input spheres and pause camera-height tracking during an owned gesture. [Follow-up evidence](../experiments/2026-10-09-unity-stacking.md#follow-up-camera-facing-arcball-and-visible-direction-tests).
- For physics evaluations, record loaded runtime settings rather than assuming generator assignments persisted. Rehydrate saved poses with contact warmup and a no-placement survival/drift check; do not force stability. Preserve fixed-time bookkeeping when calibrating acceleration, and measure repeatability and wall time before a large matrix. [Calibration evidence](../experiments/2026-10-09-unity-stacking.md#follow-up-physics-evaluation-calibration).

### iOS on a Sequoia host (unsigned compile verified)

Unity needs **iOS Build Support for the exact editor** to export an Xcode project, then **full Xcode** to compile the application locally ([Unity setup](https://docs.unity3d.com/6000.6/Documentation/Manual/ios-environment-setup.html)). Command Line Tools alone are insufficient. Unity 6000.6.5f1 and Xcode 26.3 (17C529) on Sequoia 15.8.1 now [export and compile an unsigned IL2CPP/ARM64 app](../experiments/2026-10-08-urp-scaffold.md), using SDK 26.2 with deployment minimum 26.0. Signing and device launches remain unverified.

- For unsigned device compilation, use `xcodebuild -project <export>/Unity-iPhone.xcodeproj -scheme Unity-iPhone -configuration Debug -sdk iphoneos -destination 'generic/platform=iOS' -derivedDataPath <ignored-path> CODE_SIGNING_ALLOWED=NO`. Inspect the compiled app's Info.plist, not only Unity's settings.
- Device-family orientation policies may need both Info.plist and runtime `Screen` settings: Unity's generated view controller supplies its own orientation mask. A small UIKit device-idiom helper was linked successfully; physical rotation/window behavior remains **(unverified)**.
- Current Xcode warnings include Unity-generated deprecated iOS APIs, `UIRequiresFullScreen`, a script phase without outputs, and a missing final store icon. Do not confuse a successful unsigned compile with distribution readiness.

- As checked 2026-10-07, [Apple's compatibility table](https://developer.apple.com/xcode/system-requirements/) lists **Xcode 26.3 / iOS 26.2 SDK** as compatible with Sequoia **15.6+** within its stated OS range. Xcode 26.4.1 requires macOS 26.2; Xcode 27 requires macOS 26.6+. Use a versioned download rather than prescribing "latest Xcode."
- Keep the host OS, Xcode, SDK, simulator runtime, and deployment minimum separate. The local SDKs report **26.2** while the available simulator runtime is named **iOS 26.3** and reports version **26.3.1**. Do not infer one version from another. A newer SDK can build for an older supported deployment minimum.
- Check `xcode-select -p`, `xcodebuild -version`, `xcodebuild -checkFirstLaunchStatus`, and `xcrun --sdk iphoneos --show-sdk-version`. Inspect `xcrun simctl list runtimes --json` for runtime versions and `isAvailable`. These discovery commands are verified; runtime availability alone is not a successful simulator launch.
- If needed, use a per-command `DEVELOPER_DIR=/Applications/<actual-Xcode-name>.app/Contents/Developer` instead of changing other projects' global developer selection. In the latest probe the correct Xcode was already selected, so no override or global change was necessary.
- Check [App Store submission requirements](https://developer.apple.com/app-store/submitting/) at release time. Apple announces an iOS/iPadOS **27 SDK** minimum from **April 2027**; a Sequoia-compatible local setup is not an indefinite publishing guarantee.
- Confirm a real IL2CPP/Metal build on both intended device families before claiming mobile support. Simulator, desktop, editor tests, and catalogue metadata do not establish physical-device behavior.

### Animation and image checks

- Built-in FBX import: Generic / Create From This Model, file units enabled, scale 1, axis conversion baked, hierarchy preserved, game-object optimization off, animation compression off. One explicitly looped diagnostic take at 24 fps; `Animator.applyRootMotion=false`.
- Use a manually evaluated `PlayableGraph` connected to the imported `Animator`, then measure bone positions and `SkinnedMeshRenderer.BakeMesh` vertices. This exercises the runtime animation path, not only `AnimationClip.SampleAnimation`.
- **Scaled skins:** in this setup use `BakeMesh(mesh, true)` before `renderer.transform.TransformPoint`. The default overload gave scaled meshes incorrectly shrunken measured bounds; it was a measurement error, not broken FBX geometry.
- **Repeated same-frame renders:** `forceMatrixRecalculationPerRender=true` plus `updateWhenOffscreen=true` refreshed skinned poses for `Camera.Render`. Without forced recalculation, CPU bone/mesh measurements changed but all screenshots were identical. Check the images too.
- Use a `RenderTexture` + `ReadPixels`/PNG for local screenshots. Do **not** pass `-nographics` for this path.
- Raw facing is Blender -Y → Unity -Z with the tested exporter. Correct at the gameplay prefab boundary if a future controller assumes +Z; do not silently rotate the diagnostic instance.
- Imported basic materials are not pink, but Blender procedural shader fidelity, real-time budgets, Humanoid retargeting and locomotion are not established by this probe.

## Live Pipeline workflow (unverified)

`unity pipeline install --project-path <proj>`, `unity open`, `unity status`, `unity command`, `unity test` and `unity build` remain **(unverified)** here. Command discovery is not an end-to-end run.

## Measured locomotion study

[`AnimationStudy.cs`](../../scripts/unity/AnimationStudy.cs) reuses the diagnostic helper's bounds, hashing and screenshot functions. Supply `idle.fbx`, `walk.fbx` and matching measurements in a disposable project; copy both editor helpers to `Assets/Editor/` and [`StudyLocomotion.cs`](../../scripts/unity/StudyLocomotion.cs) outside it. [Experiment and commands](../experiments/2026-09-24-idle-walk-motion-study.md).

- **Preserve sampled curves deliberately.** With compression off but default `resampleCurves=true`, half-frame walk poses differed from Blender by up to 3.76 mm. Denser FBX keys alone did not help. Turning resampling off reduced maximum observed bone error to about 0.002 mm. This is one measured Generic workflow, not a universal recommendation for all animation import.
- The visual child rotates 180 degrees around Y; its parent moves forward along +Z at 0.72 m/s with root motion off. Bone comparisons are made back in visual-local space; contact measurements are world-space.
- Check every bone and every mesh's bounds at keys **and between keys**. Measure each stance against its first world-space foot position, not just consecutive frames; otherwise cumulative drift can hide.
- Verify the saved scene separately in real Play Mode. `AnimationStudy.VerifyPlayback` enters Play Mode, survives the domain reload with `SessionState`, checks speed/camera follow and one four-cycle preview reset, writes a report, then exits. Omit `-quit` for that command.
- Front and side renders expose different problems. An overlapping tiled floor caused depth artifacts; one planar mesh with two material submeshes avoided them. A changed PNG hash proves change, not visual correctness.
- All 54 parts are now skinned in the motion derivative. The study still does not establish continuous topology, natural heel/toe mechanics, blends, turning, player input or collision behaviour. The preview deliberately resets position after four cycles and is not a gameplay controller.

## Click-to-move and native builds

[`ClickToMove.cs`](../../scripts/unity/ClickToMove.cs) is a separate runtime controller, not an extension of the looping study preview. Verified with a flat, static NavMesh and the existing Generic clips in a native macOS arm64 player. [Experiment, commands and limits](../experiments/2026-09-24-click-to-move.md).

- Put the script outside `Assets/Editor`. Supply a `NavMeshAgent` on registered navigation, a camera, a visual-child Animator and a click mask including **both floor and blocking colliders**. It uses legacy `UnityEngine.Input` (the tested project's `activeInputHandler` is 0). Left-click moves; right-click/Space stops; R resets; Esc quits the player.
- `floorLayer` defaults to 8; wire your actual floor layer. `blockedScreenRect` is a top-left-origin GUI rectangle. Optional `LineRenderer route` and `Transform targetMarker` display a path/goal. The hosting UI should show `Status`, including rejection reasons.
- Use `NavMeshBuilder.CollectSources` / `BuildNavMeshData` from the built-in AI module for a small procedural room. Save the returned data asset; add it with `NavMesh.AddNavMeshData` before agents start and remove that instance on disable. No extra AI Navigation package was needed for this narrow workflow.
- Reject distant samples and incomplete paths, not just points outside the NavMesh. An isolated but valid navigation surface can produce a partial path. Invalid retargets should preserve an existing route.
- Animator contract: float `MoveBlend` reflects actual speed / `authoredWalkSpeed` (default 0.72 m/s). Idle → Walk when >0.07, Walk → Idle when <0.04; fixed-duration transitions of 0.16/0.18 s, no exit time. Bind **only Walk's** speed multiplier to float `WalkRate` (default 1). Root motion stays off. The transitions do the smoothing; additional parameter damping delayed stop recovery in the experiment.
- `ResetPath` alone did not meet the stop guard. Set `isStopped=true`, clear velocity, then reset the path; resume explicitly on a successful destination. Keep the outgoing animation clock running during a stationary crossfade.
- Initialize `NavMeshPath` in `Start` or `Awake`, not a component field initializer: its native allocation fails during Unity serialization. Check **both** `BuildResult.Succeeded` and `summary.totalErrors == 0`; the initial build returned success despite a logged serialization error.
- Native build: `BuildPipeline.BuildPlayer` targeting `StandaloneOSX`, Mono backend, MacStandaloneSupport installed. A cache-free rebuild of the saved scene also passed the runtime probe. This is a local build, not signed/notarized distribution.
- The runtime acceptance probe exercises the same screen-ray method as pointer input, plus real navigation/Animator evaluation. It is not an OS-level mouse/keyboard test. Contact, natural turning, dynamic blockers and other platforms remain open.

## Detailed static scene transfer

A [later experiment](../experiments/2026-09-24-static-scene-unity.md) replaces blockout visuals with a baked Blender environment: 2,241 static objects grouped into 33 meshes, 998,167 triangles and 21 2K textures. Engine import checks each mesh's triangle count against the export manifest; native navigation and a cache-free saved-scene rebuild pass.

- Import static FBX normals and calculate Mikk tangents. Set colour textures to sRGB; use `TextureImporterType.NormalMap` for tangent normals. Set Standard material roughness via smoothness = 1 − roughness and keep metallic/emission factors explicit.
- Keep geometry for display separate from collision proxies. Decorative topology and small floor details should not automatically become navigation geometry.
- A realtime reflection probe supports metallic highlights; planar mirrors need their own reflected camera/texture. The tested private implementation separates two coplanar groups, clips at the mirror plane and excludes mirror surfaces from reflection rendering. These are one-bounce reflections, not recursive ray tracing.
- Highly emissive thin effects made broad highlight bands in the coarse cubemap. Excluding those effects from that probe improved the result; they remain in the main view and planar reflections. This is an intentional realtime approximation.
- Transparent Standard materials retain visible glass/crystal geometry but not Cycles refraction or caustics. Grouping transparent geometry can also limit sorting; do not claim offline-render parity.
- For a 50% movement increase, set agent speed to 1.08 m/s and retain `authoredWalkSpeed=0.72`; observed `WalkRate` is 1.5. The existing controller already supports this without changing clip calibration.

## Gotchas

- Unity projects generate large `Library/`, `Temp/`, `Logs/`, `obj/` folders — put disposable projects under ignored `out/`. Preserve `Assets/` including `.meta`, `Packages/` and `ProjectSettings/` for selected private archives.
- Inspect `.asset` files before archiving: baked `NavMeshData` was binary even though nearby materials/controllers/scenes were YAML. Put that binary in LFS without globally treating all `.asset` or `.meta` files as binary.
- CLI beta.8's `unity editors` listed versions that could not actually be located. Only 6000.6.2f1 was verified for project work at that time; pin and record the actual editor. The current installation is listed above.
- `unity projects new` failed with a missing parent directory/stale editor version, then stalled with the installed editor. `unity run --editor-path … --timeout 240` also stalled before creating an editor log. We stopped our wrappers and used the binary directly; the cause of the stalls is unresolved.
- The CLI's macOS `--editor-path` expects a `.app` bundle; direct shell execution uses its `Contents/MacOS/Unity` binary. These are different interfaces.
- Do not launch another editor against a project already open elsewhere, and do not stop unrelated editor processes.

## To explore

- Exact C# eval capability of the Pipeline package and its limits.
- Diagnose the CLI startup/authentication flow without requiring cloud services for local editor work.
- GLB import (Unity needs a glTF importer package, e.g. glTFast). (unverified)
- Whether `unity skill install` gives useful guidance for this agent.
