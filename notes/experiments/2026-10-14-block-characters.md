# Block characters and objects (2026-10-14)

**Question.** Can an agent build characters and furniture reliably, repeatably and composably from scripted Blender
primitives, without the per-character tuning a single skinned "inflated skeleton" mesh needed?

**Approach** (`scripts/blender/blocks.py`):
- **Blocks:** bevelled boxes, ellipsoids, cylinders, wedges and rings generated with bmesh. There are no hand-made meshes.
- **Chassis:** a body plan with **fixed proportions**, a rig and named **sockets**. The human chassis is about 1.30 m and 3.4 heads tall, with Unity Humanoid bone names; the cat chassis uses a generic rig.
- **Modules:** functions that add blocks to bones (head shapes, hair, hats, garments, glasses, a beard, cat body and markings). A character is a **recipe** of module names and colour roles.
- **Floating joints:** gaps between the blocks around each joint, with every block **rigidly bound to one bone**. Nothing deforms, so there's no weight painting.
- **Grid:** objects are groups of blocks on a 0.25 m grid, with a 5 cm sub-grid on surfaces. Standard surface heights are set: seat 0.25 m, side 0.375 m, table 0.5 m, counter 0.625 m.
- **Overlap gate:** `overlaps()` measures how deep a block goes inside another closed block (BVH nearest point plus the normal's sign). Blocks on the same bone, or neighbouring blocks with the same material, may overlap by design.

**Result.**
- A cluttered room corner and a lineup of three recipes plus a cat were built in about 1 minute per full rebuild, and the scene passes the gate with 0 overlaps. Building it took about 6 iterations, and every fix was a data or parameter change.
- The gate caught every real fit problem before review:
  - a figure placed into a wall (an object's matrix was read before the scene updated)
  - shins inside a chair whose seat was deeper than the chassis' thighs
  - a hand through a mug body
  - a cat under a table
  - tail blocks inside the body

**Lessons.**
- **Seat depth is a chassis standard, not only seat height.** Short-legged figures need shallow seats: the front edge must sit about one thigh length ahead of the seat point.
- **Contact goes through sockets.** Examples: a `seat` socket under the level thighs, `grip` sockets at the palm centres, a prop's own grip point (a mug handle's outer edge). Poses and props aim at sockets, never at raw joints.
- **Allow overlaps only where they read as one shape:** the same bone, or neighbouring bones with the same material (trousers at a seated hip). A skirt replaces the thigh blocks rather than hiding them.
- **Modules interact:**
  - a boxy head needs a boxy hair crown, or its corners poke through
  - a hat replaces the crown
  - hair locks hang below a hat's band

  Keep those rules inside the modules, not in recipes.
- **Poses can hide blocks** (a cat's tucked hind legs), and hidden blocks are excluded from the gate.
- **Update the view layer** before reading `matrix_world` of anything just created or parented.
