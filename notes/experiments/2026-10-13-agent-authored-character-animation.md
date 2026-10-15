# Agent-authored stylised character and pose-to-pose animation

- **Date:** 2026-10-13
- **Goal:** Can an agent, driving Blender from scripts only, build a gently stylised character with a Unity-Humanoid-compatible rig and author believable pose-to-pose clips (sit down, seated reading idle, stand up, press a wall switch)? And how much of the work is mechanical vs judgement?
- **Tools & versions:** Blender 5.2.2 LTS (headless, Eevee renders), Unity 6000.6.5f1 (batch mode), FFmpeg, macOS 15.8.1 / M4 Max.

## What we did

1. **Character:** [`build_stylised_character.py`](../../scripts/blender/build_stylised_character.py).
   - The body is a joint graph with per-joint radii → Skin modifier → **symmetrize** → Subdivision. Proportions are parameters: height, heads-tall, build.
   - Head, eyes, nose and hair are separate smooth meshes, rigidly bound to the Head bone.
   - A 21-bone deform rig uses **Unity Humanoid names**, facing −Y, feet at Z=0, with automatic weights.
   - Clothing seams are cut with `bisect_plane` before material assignment.
2. **Clips:** [`author_clips.py`](../../scripts/blender/author_clips.py) with [`examples/sit_read_press.json`](../../scripts/blender/examples/sit_read_press.json).
   - Each clip is a short list of **key poses written as data**: hips offset and pitch, spine/chest/neck/head rotations, world targets for feet and hands, and hand rotation offsets.
   - Easing is `snap` (ease in-out), `smooth` or `linear`; `hold` repeats the previous pose.
   - Two-bone IK with pole targets is set up automatically; the pole angles are found by search so the rest pose is unchanged.
   - The script keys the controls, bakes to FK with `nla.bake(visual_keying=True)`, mutes the constraints, and exports one FBX take per clip.
   - **Contact is measured and corrected in the loop:** the seat gap (the seated hips height is auto-corrected from the measured gap), foot drift, and fingertip-to-target distance.
3. **Review:** [`render_review.py`](../../scripts/blender/render_review.py).
   - Auto-framed turnaround or key-frame renders, or a full sequence.
   - Per-action prop visibility, read from a custom property on the action.
   - FFmpeg makes the review videos.
4. **Unity:** [`HumanoidImportProbe.cs`](../../scripts/unity/HumanoidImportProbe.cs) imports the FBX as Humanoid and reports avatar validity, bone mapping and clips.

```sh
blender -b --factory-startup --python-exit-code 1 -P scripts/blender/build_stylised_character.py -- --out out/authoring-study/character.blend
blender -b out/authoring-study/character.blend --python-exit-code 1 -P scripts/blender/author_clips.py -- \
  --clips scripts/blender/examples/sit_read_press.json --out-dir out/authoring-study/clips
blender -b out/authoring-study/clips/clips.blend --python-exit-code 1 -P scripts/blender/render_review.py -- \
  --out-dir out/authoring-study/clips/review --action sit_down --views three_quarter --frames 1,8,16,22,27,32 --focus Body
"$UNITY_EDITOR" -batchmode -projectPath "$PROJECT" -executeMethod HumanoidImportProbe.Run -probeDir Assets/Probe \
  -probeOut "$PWD/out/authoring-study/humanoid_report.json" -logFile "$PWD/out/authoring-study/humanoid.log"
```

## What happened

| Clip | Frames (30 fps) | Keys | Measured contact |
|---|---|---|---|
| sit down | 40 | 7 | hips sink 6.7 mm into the seat (acceptable as a cushion); feet slide forward deliberately in the settle |
| seated reading | 120 (loop) | 7 | feet 0 mm drift; seat −6.7 mm; book anchored to the chest, hands on its edges, page turn |
| stand up | 44 | 8 | seat −6.7 mm at the start; feet step back deliberately before the push |
| press switch | 54 | 9 | fingertip 7.1 mm from the switch centre at contact; feet 0.3 mm drift |

**Unity 6000.6.5f1:** all four FBX import as a valid Humanoid avatar (`isHuman`), with all 21 bones mapped by name automatically and every clip flagged `humanMotion`.

**Iterations** (each judged from rendered contact sheets read by the agent):
- **Character, 4:** torso too thin from the side; neck and floating head; seams jagged; a branch-node bulge fixed by symmetrize.
- **Clips, about 6:**
  - the wall occluded the reach
  - wrong hand-rotation axis (156 mm miss, then 26, then 7 mm)
  - feet needed to slide forward for a natural seated pose
  - the book was parented to the bone *tail*, so it sat at face height

## Learnings

- **Agents can author stylised pose-to-pose animation through IK targets written as data.** Static key poses plus easing are tractable. Measuring contact and auto-correcting in the loop removes the most error-prone part, exact heights.
- **The agent must look at renders.** Every visual problem above was invisible in the numbers (occlusion, a floating book, cramped legs). Contact sheets read by the agent caught them; video confirms the timing.
- **Skin-modifier hulls are asymmetric at branch joints.** Build, then `mesh.symmetrize(POSITIVE_X)` before subdividing.
- **Skin radius axes map to the vertex frame** (x→X, y→Y for a vertical chain). Branch nodes (hips, chest) still lose depth, so give torso radii extra depth.
- **Parenting an object to a bone (`parent_type='BONE'`) places it at the bone's tail.** Offsets are from the tail, in bone space (Y along the bone).
- **For vertical spine bones, the second Euler component is yaw (twist).** For world-space hand-target offsets, rotate about the axis you actually mean (sideways pointing = world Y).
- **Unity Humanoid requires unique names for transforms mapped to human bones.** A mesh object named `Head` next to a `Head` bone fails avatar creation ("Ambiguous Transform"). Name meshes e.g. `HeadMesh`.
- **The FBX take is named after the scene.** Set `scene.name` to the clip name before export, or every take is called "Scene".
- **Review videos for in-app or web viewers:** concatenating clips with `-f concat -c copy` and no `+faststart` played fine in FFmpeg but showed **black in the user's viewer**. Re-encode the joined video (`concat` filter, `libx264 -profile:v main`, `yuv420p`, `-movflags +faststart`) and offer a GIF fallback.
- **Foot drift can be a feature.** Sitting needs a deliberate foot slide forward, and standing up a step back. Measure drift only where feet should be planted.

**Not yet established:**
- quality as judged by a human
- retargeting onto other proportions
- runtime IK
- locomotion
- fingers (hands are mittens)
- facial expression
- cats

## Review round 1 (user)

Verdict: "looks good and promising". Two artefacts, both fixed in the method:

1. **"Not fully sitting, pivoting on its thighs."** The seat-gap check took the lowest body point over the seat, which was the thighs at the front edge. It reported contact while the pelvis hovered. Now:
   - the check measures **under the pelvis** (within 12 cm of the Hips joint) and separately reports the deepest penetration
   - the hips sit further back on the seat
   - the seat height suits the character's short stylised legs: **0.41 m for a knee height of about 0.43 m**. At 0.45 m the thighs hung over the front edge.

   Result: pelvis 3.8 mm above the seat; thighs compress 15 mm.
2. **"Book in an odd position vs the hands."** The book was attached to the chest while the hands were placed independently. Now it's **held**:
   - placed automatically between the palms at the clip's first frame, facing the head
   - carried by the left hand, so the right hand can turn pages

Also: resting hands moved onto the thighs after the hips moved back.

**Lessons:**
- Measure contact at the body part that should carry the weight, not at the nearest point.
- Seat heights must suit the character's proportions. This is exactly why anchors should be relative to the character.
- A prop that is held should be driven by the hands holding it, not placed independently.

## Follow-up fixes (2026-10-14, from a room mockup)

- **Feet:** at diorama distance, thin tapering feet read as dark lumps and pinched ankles look like pins. Feet are now longer, wider and thicker at the ankle, with chunky rounded toes, and the soles are flattened to Z=0 after subdivision.
- **IK pole offsets must follow the rig's facing.** The poles were offset in world directions, so a character rotated 180° had its knee poles behind it: twisted legs and feet. Offsets are now transformed by the rig's rotation.
- **Imported Euler-keyed actions need matching rotation modes.** A freshly built rig defaults to quaternions, so Euler-keyed clips silently apply only locations: the character sinks into the seat with straight limbs. Set `pose_bone.rotation_mode = "XYZ"` before assigning. In Blender 5, also assign `animation_data.action_slot` for actions loaded from another file.

## Follow-ups

- Human review of the clips. Then a shared-rig study: a second adult (different proportions) and a child on the same clips, with runtime hip/foot/hand IK in Unity.
- A two-key "use" library (press, twist, pull) generated from anchor height.
- Upper-body activity layers as masked overrides on sitting and standing bases.
