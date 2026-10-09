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

## Follow-up: camera-facing arcball and visible-direction tests

On the same Unity/URP/Input System versions, a control-focused follow-up exposed a gap in the original undo test: a reversed rotation can still undo perfectly. The correction and expanded tests passed with the same direct-editor command form above, using both `-testPlatform EditMode` and `-testPlatform PlayMode`. Native development builds and both smoke scene paths were rerun; screen captures included the loss/replay HUD.

- Unity camera-local forward is +Z, so a visible-hemisphere arcball uses negative Z with screen X right and Y up. Transform the camera-local delta into world space as `view * delta * inverse(view)`, then apply it to the gesture's initial pose.
- Assert that a point on the **near surface** projects right/up after matching pointer motion, at several camera yaws. Also test rim-roll direction and anchored return independently; merely testing nonzero rotation or undo misses handedness errors.
- Preserve the intended projection profile. A sphere with a cubic shoulder into an equator is not interchangeable with a generic sphere/hyperbola trackball. Test numerical shoulder samples and equatorial roll separately.
- Share projected bounds between visual sphere sizing and input admission; keep pixel thresholds in consistent logical units. Stabilize camera height during an owned gesture so its frozen center does not drift underneath the pointer.
- Cap flick speed, specify minimum sample duration and stale-release cutoff, and ignore stationary drag events. Include these in numeric tests rather than judging only a screenshot.

These checks establish direction and mathematical behavior, not subjective touch-feel acceptance. No project-specific tuning constants or media are published.

## Follow-up: physics evaluation calibration

On the same editor and physics stack, an editor-only PlayMode fixture exercised actual lowering/scoring/loss, repeated placements, and reconstruction of a settled tower from prefab identities, poses and velocities. The command used the earlier direct-editor PlayMode form plus `-testFilter` for the calibration fixture; the complete PlayMode suite and native gameplay smoke also passed.

- Snapshot reconstruction does not restore PhysX contact caches. Wake restored dynamic bodies, rebuild callbacks with ordinary fixed steps, then measure no-placement survival and drift. Do not force sleep or zero velocities to make a fixture pass.
- Support bookkeeping used Unity fixed-time timestamps. Keep the ordinary fixed-update loop for the reference run; manual simulation or accelerated scheduling needs separate equivalence checks.
- A renderer-bounds check immediately after setting an interpolated Rigidbody pose failed. Waiting for a fixed step and rendered frame made the visible bounds and body COM comparable.
- Loaded solver/contact-offset values differed from values assigned in the asset generator. Capture runtime configuration before freezing an experiment baseline; generator code is not proof of persistence.
- Repeated inputs had consistent survival outcomes but some noticeably different resting poses. Paired evaluations need repeated borderline cases and order checks, not an assumption of exact physics replay.
- The ordinary-clock pilot ran near real time. Measure actual trial duration before launching thousands of trials; successful placements with a long observation tail can dominate cost.

These are calibration results for a small corpus, not a general physics quality or snapshot determinism claim. Private results remain in the project repository.

### Accelerated-clock follow-up

Keeping the physics timestep unchanged while increasing `Time.timeScale` substantially reduced wall time in an ordinary-callback PlayMode runner. A generated corpus survived reconstruction and observation at ordinary speed, and successful placement samples survived at both speeds. This was not sufficient evidence of equivalence: repeated borderline placements included a survival/loss disagreement.

Use counterbalanced speed order, repeat both ordinary and accelerated cases, and record distributions rather than expecting a previously failed attempt to always fail again. Keep the full comparison gated when the sample cannot distinguish acceleration bias from ordinary contact/order variability. Restore timing and log-handling settings after the fixture. Expected gameplay timeout errors can be recorded as outcomes, but all other errors/exceptions must still fail the harness.

The corpus test exceeded Unity's default 180-second timeout during normal-speed cross-checks; an explicit bounded `Timeout` attribute allowed the final measurement to complete. A completion marker denotes completed data collection, not scientific acceptance of equivalent behavior. Preserve partial runs separately from completed evidence.

### Separating reset history from speed

A larger prespecified comparison crossed scene reuse/reload, ordinary/accelerated clocks, and counterbalanced order. Reused scenes varied in survival and timeout outcomes; fresh-scene trials agreed across speeds on recorded starting states, first dynamic poses and final positions for every selected case. A further check of the fresh-scene default passed with ordinary fixed callbacks and unchanged timestep. This supports isolated accelerated screening on the tested toolchain, not a universal determinism claim or a proven particular PhysX cache mechanism.

Reload the scene before restoring each independent evaluation state when reset-history sensitivity is observed. Measure total cost including reload and warmup, and confirm marginal/final comparisons at ordinary speed. Keep reused-scene diagnostics distinct from the qualified measurement path.

The larger batch also exercised a genuine gameplay timeout. The fixture's broad ignore setting had not prevented the runner from failing that log path. Replaced it with an explicit expectation for the exact known timeout message, keeping the timeout as a failed placement result and leaving other errors fatal; a dedicated production-timeout test passed.
