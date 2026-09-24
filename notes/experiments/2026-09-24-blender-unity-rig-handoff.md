# Blender to Unity: diagnostic rig and animation hand-off

- **Date:** 2026-09-24
- **Goal:** Verify a small character-only export before spending effort on natural locomotion or player control.
- **Tools & versions:** Blender 5.2.2 LTS; Unity editor 6000.6.2f1; Unity CLI 1.0.0-beta.8; macOS 15.8, Apple M4 Max.

## What we did

Exported a private segmented character with one one-second forearm rotation, not a walk cycle. Compared Blender measurements with the imported Generic rig through Unity Animator/Playables, captured three actual Unity camera renders, and saved/reopened a diagnostic scene.

Promoted [`export_rig_probe.py`](../../scripts/blender/export_rig_probe.py) and [`RigImportProbe.cs`](../../scripts/unity/RigImportProbe.cs). Commands below use generic source/mesh names; exact private inputs and original commands are archived with the assets.

```sh
blender -b out/source.blend --python-exit-code 1 \
  -P scripts/blender/export_rig_probe.py -- \
  --rig CharacterRig --bone forearm.L --witness-mesh Sleeve \
  --stationary-mesh Head --stationary-mesh Shoe --out-dir out/rig-probe/export

UNITY_EDITOR=/Applications/Unity/Hub/Editor/6000.6.2f1/Unity.app/Contents/MacOS/Unity
mkdir -p out/unity
"$UNITY_EDITOR" -batchmode -quit -createProject "$PWD/out/unity/RigImportProbe" \
  -logFile "$PWD/out/unity-create.log"
mkdir -p out/unity/RigImportProbe/Assets/Editor out/unity/RigImportProbe/Assets/Probe
cp scripts/unity/RigImportProbe.cs out/unity/RigImportProbe/Assets/Editor/
cp out/rig-probe/export/rig_probe.fbx out/rig-probe/export/rig_probe.expected.json \
  out/unity/RigImportProbe/Assets/Probe/
"$UNITY_EDITOR" -batchmode -quit -projectPath "$PWD/out/unity/RigImportProbe" \
  -executeMethod RigImportProbe.Run -probeModel Assets/Probe/rig_probe.fbx \
  -probeExpected Assets/Probe/rig_probe.expected.json \
  -probeOut "$PWD/out/rig-probe/unity" -logFile "$PWD/out/rig-probe-unity.log"
```

Use a disposable built-in-renderer project, not one open in another editor. Do not use `-nographics`: this experiment requires a graphics context. The helper replaces its diagnostic scene/controller, writes hashes and a JSON report, and exits nonzero on failure.

## What happened

| Measurement | Result |
|-------------|--------|
| Skeleton / geometry | 16 bones, 54 meshes, 48 skins; Generic avatar valid |
| Animation | One `HandoffProbe` clip, 1.00000012 s, 24 fps |
| Scale | 1.694 m character height; one-metre markers retained |
| Axes | Blender +Z → Unity +Y, +X → +X, -Y → -Z |
| Motion | Tip moved 0.13675 m; moving mesh centre also moved > 0.02 m |
| Cross-tool agreement | Maximum sampled tip error 0.000000223 m; mesh-centre error 0.000000311 m |
| Negative controls | Unrelated head/foot meshes stayed within 1 mm in Unity |
| Loop endpoints | Tip error 0; first/last PNG hashes identical, midpoint different |
| Persistence | Scene reopened with valid avatar and controller clip |

The final run passed 234 checks. Those errors are observations for this asset at three sample times, not a general precision guarantee. Acceptance thresholds were 1 cm for animated positions and per-mesh rest bounds, 1 mm for marker/end-point/stationary checks, and 20 ms for duration.

Basic material colours imported and screenshots show the intended limb movement. This is **not** production skinning, natural walking, full scene import, shader fidelity, Humanoid retargeting or a playable game. Six decorative curves were converted to rigid meshes; their binding needs attention before full-body animation.

## Learnings

- **Shared mesh data contaminated skin weights.** Different object-level vertex-group assignments reused mesh-level deform data. An unrelated head part moved with a forearm. Copying each skinned part's mesh before binding fixed it. The original scene failed the new stationary-mesh guard; the corrected derivative passed. Historical renders/scenes were preserved, not silently replaced.
- **A positive-only rig check is insufficient.** Confirm expected movement and non-movement. Choose a witness away from the joint: a rotating symmetric elbow mesh had a stationary bounds centre.
- **Check both sides of the coordinate conversion.** The proposed `(x, z, -y)` mapping was wrong for the tested Blender/Unity settings. Measured `(x, z, y)` and raw -Z-facing are now documented; controller-facing correction is separate.
- **Single baked FBX take names follow the scene.** Naming only the Blender action produced an imported `Scene` clip. Naming the scene too produced `HandoffProbe`.
- **Measurement APIs can mislead.** Default `BakeMesh` followed by `TransformPoint` gave shrunken bounds for scaled skins. `BakeMesh(mesh, true)` matched all Blender mesh bounds; this was not an export failure.
- **CPU motion does not guarantee fresh screenshots.** Multiple same-frame camera renders initially captured identical images despite correct changing bone/mesh measurements. Forced skin matrix recalculation per render fixed it.
- **Local editor work does not require Unity Cloud setup.** `unity projects new` and `unity run` stalled before useful editor work; `--editor-path` expects a macOS `.app`, not its binary. The directly invoked installed editor worked with its existing licence and no new sign-in. The CLI stall's cause remains unresolved, not attributed conclusively to authentication.
- **Editor listings are not installation proof.** Older versions listed by the CLI could not be located. The earlier Unity note was corrected to the editor actually exercised.

Distilled into [Blender](../tools/blender.md), [Unity](../tools/unity.md), the [showcase pattern](../patterns/reference-to-blender-showcase.md), pipeline/platform status and script index. Project-specific sources, FBX, previews, hashes and the minimal Unity project remain in the private library; caches and intermediate failures remain local.

## Follow-ups

Tracked in [backlog](../backlog.md): neutral rest pose and production binding; in-place idle/walk and foot-contact checks; explicit prefab facing and code-driven player control; material baking/optimization; GLB import and CLI/Pipeline investigation.
