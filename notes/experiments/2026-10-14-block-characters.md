# Rigid block characters built by an agent (2026-10-14)

**Question.** Can an agent build characters and furniture reliably, repeatably and composably from scripted Blender primitives, without the per-character tuning that a single skinned "inflated skeleton" mesh (Skin modifier plus automatic weights) needed?

**Technique** (the code lives in the project that uses it; this note keeps the generic findings):
- **Blocks:** bevelled boxes, ellipsoids, cylinders, wedges and rings generated with `bmesh`. There are no hand-made meshes.
- **Body plans with fixed proportions:** a rig plus named **sockets** (grip, seat, sole, head mounts). Unity Humanoid bone names work unchanged.
- **Modules:** functions that add blocks to bones (heads, hair, hats, garments, accessories). A character is a **recipe** of module names and colour roles.
- **Rigid binding:** every block is bound 100% to one bone, with **gaps around the joints**. Nothing deforms, so there's no weight painting, and the result is still a one-bone-weighted skinned mesh that Unity accepts.
- **Grid placement:** objects are groups of blocks placed on a coarse grid, with a finer sub-grid on surfaces, plus standard surface heights.
- **Overlap gate:** for each block, how deep its vertices go inside another closed block (BVH nearest point plus the sign of the normal), filtered by bounding boxes. It's a pass/fail check, not an eyeball check.

**Result.**
- A cluttered isometric room corner and a lineup of three recipes plus a cat were built at about 1 minute per full rebuild, and the scene passes the gate with 0 overlaps. Building it took about 6 iterations, and every fix was a data or parameter change rather than mesh tuning.
- The gate caught every real fit problem before visual review:
  - a figure placed into a wall
  - shins inside a chair whose seat was deeper than the figure's thighs
  - a hand through a mug body
  - a pet under a table
  - tail blocks inside the body

**Lessons.**
- **Contact goes through sockets.** Examples: a seat socket under the level thighs, grip sockets at the palm centres, a prop's own grip point (a mug handle's outer edge). Poses and props aim at sockets, never at raw joints (aiming at the wrist put a hand through a counter).
- **Seat depth is a body-plan standard, not only seat height.** Short-legged figures need shallow seats: the front edge must sit about one thigh length ahead of the seat point.
- **Allow overlaps only where they read as one shape:** the same bone, or neighbouring bones with the same material (trousers at a seated hip). Garments that cover parts replace those blocks rather than hiding them.
- **Modules interact:**
  - a boxy head needs a boxy hair crown, or its corners poke through
  - a hat replaces the crown
  - hair hangs below a hat's band

  Keep those rules inside the modules, not in recipes.
- **Poses may hide blocks** (tucked legs), and hidden blocks are excluded from the gate.
- **Update the view layer** (`bpy.context.view_layer.update()`) before reading `matrix_world` of anything just created or parented. A stale matrix placed an object at the origin.
- **Posing by aiming bones in the character's own frame** (rotate the rest direction onto a target direction, keep the head where the parents put it) is enough for static poses without IK.

## Follow-up (2026-10-15): solving joint gaps over the range of motion

**Method.**
- Give each joint a range of motion: degrees about axes in the character's frame, taken from the poses actually needed.
- Sweep it, turning the joint's subtree of blocks about its pivot in 5–10° steps with everything else at rest.
- Measure the signed clearance between the moving and static blocks in both directions (BVH nearest point plus the sign of the normal).
- Bisect the trim of one block end (the joint's "lever") for the smallest gap that keeps a margin (4 mm) everywhere.
- Cap the visible gap at rest (15% of the block's thickness), so limbs stay coherent.
- Anything that can't meet both is reported, with the angles it can actually reach.

**Findings.**
- **Hand-picked gaps were both too big and too small.** They were 1–3 cm at rest, yet knees, elbows and hips still intersected by about 4 cm at full bend. Shape decides it, not distance.
- **Round parts should turn about their own centre.** A ball head pivoting at its base needed a 25 mm neck gap; pivoting at its centre needs only the margin.
- **Pivots belong at the parent's surface,** with the child's end rounded about the pivot (a hinge cylinder or a ball). Pivots buried inside a body make limbs sweep into it.
- **A part that turns against two neighbours** (a pelvis between thighs) should be rounded about their shared axis, and no deeper than the parts that turn against it.
- **Thickness limits bending.** At deep bends a limb folds onto its neighbour's side whatever the gap; the sweep reports the reachable angle, and the range or the shape has to change.
- **Garments must not span a joint.** A rigid skirt on the hips makes sitting impossible; split it into a panel per thigh.
- **The same sweep works as an acceptance test for add-on parts** (hair, beards, garments) against a body plan's ranges.
- **Furniture standards fall out of the proportions:** seat height (feet reach the floor), maximum seat depth (shins clear the front edge), and table and counter heights from elbow height.

**Revised (same day): plain blocks won.**
- Shaping joints to avoid self-intersection (pivot-centred cylinder and ball caps, with gaps solved over the range of motion) made awkward silhouettes and visible seams where caps met boxes. Plain rounded blocks with small fixed gaps, whose own limbs are allowed to pass into each other at a bend, looked better at diorama distance.
- Keep the clearance sweep as a review aid (render each joint at its extremes), not as a gate.
- Gate what reads as wrong: characters into props, walls or each other.

**Gaps belong only at joints.**
- Details on the same part (eyes, cheeks, stripes, buttons) must sit flush. Floating details look odd.
- Place face details by ray casting the actual head mesh and orienting each to the surface normal, sunk so only a few mm stand proud.
- Check for floating details in both directions (detail to part and part to detail), or a hem that wraps a torso, or a big flat face next to a small detail, gives false readings.
- Where curved blocks cross at shallow angles (hair over a head), use fine tessellation (64 segments). Coarse spheres give zig-zag intersection lines.

## Follow-up (2026-10-17): motion with nothing going into anything, on any frame

**Question.** Characters walk to furniture, sit, get up and pull chairs out, from routines written as data. A route to a dining chair went straight through the chair. How do we prevent that kind of bug in general, rather than case by case?

**Why it happened:**
- the route ignored the piece it was heading for on the last stretch
- the chair's "stand here to sit" spot assumed the chair had already been pulled out
- only still poses were checked

**Method.** One rule, "nothing goes into anything else", applied to motion as it already was to still poses:
- **Check every frame,** at the rendered frame rate, with the same per-object overlap check as still poses, plus the floor. At 0.1 s samples a cat's tail swept into a cushion between two frames; at 24 fps it was caught.
- **Rigid blocks make that cheap.** Each block is bound wholly to one bone, so its shape (vertices and BVH tree in its own space) can be built once and placed each frame by one transform: the armature's world matrix × the pose bone's matrix × the bone's rest matrix inverted × the armature's inverse world matrix × the object's world matrix. That matched Blender's evaluated meshes to under a micron. A frame against about 280 room objects took ~40 ms before culling by distance.
- **The planner gets no exemptions.** Routes run between clear points; the last bit up to a seat or a shelf is planned in the body's real shape. Close to things the planner tries a short menu of moves: walk straight on and turn; set off on an arc; turn, then step back; step along, then across. It keeps the first that clears every frame.
- **Moves are few and general:**
  - a walk or trot along a path
  - small steps between two stances (turning on the spot, sidesteps, steps back)
  - an animal pivoting on the spot
  - a change of posture: two solved poses blended about one stance, feet on the floor in both kept planted, and a lean on the way
  - a piece sliding, a hand on it
- **Pieces that move say so.** A dining chair declares how far it slides and where a hand takes it. When there's no room to stand in front of a seat, sit down or get up, the character goes beside the chair, takes it from above, steps back with it, sits and scoots in as far as there's room. The same rule leaves a chair at a round table alone and pulls one out from a counter.

**Lessons.**
- **The motion check found problems nobody had looked for:**
  - a trot sinking planted paws up to 40 mm into the floor on turns (one-bone legs can't shorten, and the body was kept level)
  - a cat's tail sweeping up through a low table as she stood up
  - a hand's straight path to a grip passing through the chair post
- **A hand takes a grip from above:** it rises, moves over, then settles. Stand far enough out that the hanging hands clear the piece, not a shoulder's width.
- **Fit an animal's body to its planted legs.** Solve its height, pitch and roll (Gauss-Newton, with a small penalty on tilt) so each planted leg reaches its paw's spot exactly; the neck takes the tilt back so the head stays steady. A trotting diagonal pair is met exactly; four planted legs are met as nearly as they can be.
- **One floor rule for every limb:** a leg in the air, or a tail, that would reach below the floor reaches further along or lies along the floor. Applying it to planted legs instead made them slide; fix the body instead.
- **Walk maps need the body's real shape from above:**
  - a body that turns freely (a person) keeps a clear circle: the walkway, or its own reach, whichever is wider
  - a long narrow body (an animal) is its outline facing one of eight ways, turning between them on the spot, so it still passes gaps lengthwise
- **Measure the body's reach while it moves** (arms and legs swinging through a stride), not at rest.
- **Skip a frame's 3D check only where the walk map vouches for the whole body** at that position and facing. "Near the ends of the route" was a guess, and it left gaps neither check covered.
- **Search order matters for speed.** Check the end of a walk first, where most ways in fail. Don't pose frames the walk map vouches for. Planning went from 55 s to about 4 s an action.
- **Conventions, tolerances and motion numbers:**
  - one facing convention for characters, paths and arcs (two opposite sign conventions had crept in, joined by minus signs)
  - one floor tolerance for every check (they had drifted to 6, 8 and 12 mm, and the loosest hid the trot's dips)
  - motion timings kept as data, next to the poses
- **Before changing a convention, snapshot every move:** record bone positions over time, refactor, compare. The motion stayed identical to 0.01 mm.

**Not solved yet:** characters don't avoid each other; the check catches collisions, but routines were hand-timed to keep characters apart. Engine crowd avoidance is a candidate ([Godot vs Unity](2026-10-17-godot-vs-unity.md)).
