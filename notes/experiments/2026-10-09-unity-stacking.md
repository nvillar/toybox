# Unity compound stacking and gesture acceptance

- **Date:** 2026-10-09
- **Goal:** exercise source-derived figures, compound Rigidbody contact, and a real input-module path in a playable scene rather than only a proxy.
- **Tools:** Unity 6000.6.5f1, URP 17.6.0, Input System 1.20.0, Blender 5.2.2 LTS, macOS arm64.

## Method and results

A private project exported evaluated Blender meshes/curves as explicit FBX, with low-complexity authored collision sections and a material sidecar. Visuals and colliders received the same centering transform. The saved Blender file was opened with automatic script execution disabled and was not modified. A generated studio reflection cubemap and URP Complex Lit clearcoat were exercised in a native player.

The export command form was:

```sh
blender -b --factory-startup --disable-autoexec --python-exit-code 1 -P "$EXPORTER"
```

Direct editor tests used `-batchmode -projectPath "$PROJECT" -runTests -testPlatform PlayMode -testResults "$RESULT" -logFile "$LOG"` without `-quit`. Native builds used a project-specific `BuildPipeline.BuildPlayer` entry point. The runtime acceptance launcher used Python `subprocess.run(..., check=True, timeout=60)` through `uv`.

The extended project suite passed 11 EditMode and 10 PlayMode cases. New cases exercised all three source-derived figures on a fixed base, supported scoring, later loss of a scored body, replay, anchored drag-back undo, hold rejection, and **queued touch cancellation followed by a valid tap through the actual UI input module**. Native player captures included the HUD and a scored stack; the older diagnostic scene's smoke path remained available.

These checks establish a first playable path, not a complete pairing/tilt/tall-tower matrix, polished controls, or device performance. Natural falls must not be reclassified as solver bugs merely to force every upright pairing to pass. No assets, figure identities, private paths, or screenshots are published here.

## Corrections and reusable findings

- **A cylinder primitive has a capsule collider.** A wide, shallow platform created with `GameObject.CreatePrimitive(PrimitiveType.Cylinder)` rendered as a disk but collided as a much taller rounded object. Replacing the capsule with a convex MeshCollider using the cylinder's actual mesh removed the invisible support and made the first placement score correctly. Inspect the component, not the rendered primitive.
- **Use Rigidbody poses for kinematic placement.** Moving interpolated kinematic bodies through Transform alone produced rendered poses that snapped back. Writing `Rigidbody.position` / `rotation` and synchronizing before overlap queries fixed held placement and sensor-lowering checks.
- **Scoring is bookkeeping.** Calm supported contact increments a score; it does not freeze bodies, zero motion, change scale, or alter friction. Continue monitoring older released bodies for later loss.
- **Cancellation can deliver pointer-up.** Check the touch phase in the Input System event context rather than assuming every quick pointer-up is a tap. A synthetic Canceled event was verified not to place; the subsequent Began/Ended pair did.
- **Diagnostics must select their scene.** Once the player starts in a new scene, a legacy smoke flag must explicitly load its diagnostic scene. Both paths were run after this change.
- **Clearcoat and reflections are distinct.** Enable `_CLEARCOAT` and configure `_ClearCoatMask` / `_ClearCoatSmoothness` on URP Complex Lit; supply reflection lighting separately. A studio cubemap improved the inspected native frames without changing source geometry. This is not an offline-render parity claim.
- Unity reported one build warning and internal conservative-rasterization shader fallback messages; the final player log was clean. Build acceptance still requires zero errors, and warnings should remain visible.

Distilled into [Unity](../tools/unity.md). Device acceptance, balance sweeps, collider/bevel contact review, material/draw-call consolidation, and human game-feel review remain open.
