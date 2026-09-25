# Click-to-move with a native Unity player

- **Date:** 2026-09-24
- **Goal:** turn the measured in-place clips into controllable navigation, with obstacle routing, turning and idle/walk crossfades.
- **Tools & versions:** Unity editor 6000.6.2f1, built-in renderer and AI module, Mono macOS arm64 player; FFmpeg 9.0.2; macOS 15.8 on M4 Max.

## What we did

Started a separate disposable project from the previous experiment's pinned Packages/ProjectSettings and two FBX files. Kept the original showcase and motion study unchanged. The small room, scene builder, acceptance probe, sources, screenshots and video are private; the reusable controller is [`ClickToMove.cs`](../../scripts/unity/ClickToMove.cs).

1. Collected floor/blocker colliders with `UnityEngine.AI.NavMeshBuilder.CollectSources`, baked a `NavMeshData` asset with `BuildNavMeshData`, and registered it at runtime before the player starts. No AI Navigation package, Pipeline package or new authentication was required.
2. Used a 0.38 m agent radius, 1.75 m height, 0.72 m/s speed, 2 m/s² acceleration, 240 degrees/s turning and 0.04 m stopping distance. The visual child keeps the established 180-degree Y facing correction.
3. Raycast the nearest floor **or blocker**, then require floor layer, a navigation sample within 0.08 m and a complete agent path. Rejected commands show a reason and do not replace an active destination. Render the route and destination marker.
4. Built Idle/Walk Animator states with 0.16/0.18 s fixed-duration crossfades, no exit-time requirement. `MoveBlend` is actual velocity divided by authored walk speed; `WalkRate` adjusts the walking state's playback, not the whole Animator. Root motion is off.
5. Built and exercised the native player, not just editor sampling. The runtime probe calls the same screen-ray method as mouse input, measures navigation and real Animator states, and captures the player window including GUI. It does not synthesize OS mouse/keyboard events.
6. Copied only Assets, Packages and ProjectSettings to a cache-free directory, rebuilt the **saved** scene without rerunning scene generation or the navigation bake, and repeated the native acceptance sequence.

The private builder exposes these exact entry points. The paths below are intentionally generic placeholders for the private project/output.

```sh
UNITY_EDITOR=/Applications/Unity/Hub/Editor/6000.6.2f1/Unity.app/Contents/MacOS/Unity
"$UNITY_EDITOR" -batchmode -projectPath "$PROJECT" \
  -executeMethod BuildPrototype.Run -prototypeOut "$BUILD" -logFile "$BUILD_LOG"
# Rebuild the saved scene from a source-only restore, without regenerating it:
"$UNITY_EDITOR" -batchmode -projectPath "$RESTORED_PROJECT" \
  -executeMethod BuildPrototype.BuildSaved -prototypeOut "$RESTORED_BUILD" -logFile "$RESTORE_LOG"
"$PLAYER_EXECUTABLE" --prototype-test "$REPORT_DIR" --capture \
  -screen-width 1440 -screen-height 960 -screen-fullscreen 0 -logFile "$PLAYER_LOG"
ffmpeg -hide_banner -loglevel error -framerate 30 -i "$REPORT_DIR/frames/%05d.png" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart "$REVIEW_VIDEO"
```

Both editor methods exit explicitly; do not add `-nographics` to capture runs. A normal player launch without `--prototype-test` accepts mouse/keyboard input and does not run scripted movement.

## What happened

Both the original and cache-free native builds passed **32 acceptance checks**. The final release build reported zero errors/warnings. The recorded sequence contains 420 frames, 14 s at 30 fps, 1440×960 H.264.

| Observation | Final native run |
|---|---|
| Reachable route around central blocker | Four path corners; 5.90 m total measured travel across the sequence |
| Maximum speed | 0.720001 m/s |
| Arrival error | 0 m reported at settled destination; required <0.08 m |
| Explicit stop | Zero drift/speed; Idle and no transition after 0.6 s |
| Largest per-frame displacement | 0.024 m at 30 fps; no old preview reset |
| Static collisions | Zero overlap samples for a 0.36 m body capsule |
| Vertical position | Root at 0.02 m from voxelized navigation; lowest measured sole 0.00848 m |
| Visible floor top | 0.006 m; required soles no more than 0.002 m below it |
| Animator | Idle, Walk and transitions observed in actual player frames |

Checks also cover HUD/background/offscreen/obstacle clicks, insufficient edge clearance, invalid retarget preserving the old path, an actual disconnected NavMesh island rejecting its partial path, retarget while moving, and movement after both Stop and Reset.

Failed iterations were useful negative evidence: `ResetPath()` alone left residual motion; a separate pass with translation fixed still failed the 0.6 s idle guard. Explicitly stop the agent and clear velocity, and avoid stacking float-parameter damping on top of state crossfades. The final controller drives the transition parameter directly and keeps the outgoing state's clock running at zero movement speed.

## Learnings

- Create `NavMeshPath` in `Start`/`Awake`, **not in a MonoBehaviour field initializer**. The first build logged a native API initialization exception during serialization, yet returned `BuildResult.Succeeded` with a nonzero error count. Reject either a failed result **or any reported build errors**.
- A `.asset` extension does not guarantee text: this baked navigation asset is binary. Track the selected binary file with LFS, leaving scene YAML, materials, controllers and `.meta` files in normal Git.
- Capture selected screenshots at `WaitForEndOfFrame`. A queued `CaptureScreenshot` followed immediately by a move command captured the next moving frame, not the intended idle image.
- Save the generated scene and navigation data; a fresh-import build of those assets is a different, necessary check from rerunning the generator.
- Static HTML with relative MP4/PNG links works as a server-free review. The native `.app` stays in ignored local output; the private source archive makes it rebuildable.

Reusable setup and limitations are folded into [the Unity note](../tools/unity.md).

## Follow-ups

This is flat-floor navigation, not production locomotion or a game loop. Numeric clearance does not establish convincing foot planting: voxel height, acceleration and turns still need contact/turn polish. No slopes, moving blockers, multiple agents, foot IK, guards, interaction goals, audio, WebGL/Windows builds or distribution signing were tested. The input-ray path is covered, but a human mouse/keyboard usability pass remains distinct from scripted acceptance.
