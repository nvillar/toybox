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
