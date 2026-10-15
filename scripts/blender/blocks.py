"""Block construction kit: characters and objects built from bevelled blocks mounted on standard interfaces.

Import from a Blender script (Blender 5.2.2):
    sys.path.insert(0, "<toybox>/scripts/blender"); import blocks as bk

Ideas (see notes/experiments/2026-10-14-block-characters.md):
- A block is a generated primitive (rounded box, ellipsoid, cylinder, wedge) with a material; never a hand-made mesh.
- A chassis is a body plan with FIXED proportions: joints, a rig (Humanoid bone names for people) and named sockets
  (grip, seat, sole, head mounts). Clips are authored once per chassis.
- Modules (heads, hair, garments, accessories, tails…) are functions that add blocks to bones of a chassis.
  Character blocks float with small gaps around the joints, and each block is rigidly bound to ONE bone,
  so nothing deforms, bulges or needs weight painting.
- Objects are groups of blocks under an empty placed on a grid (GRID cells, 90-degree turns); surfaces carry a SUB grid.
- Standard heights (seat, table, counter) let one clip per chassis serve every object.
- overlaps() measures how far blocks go into each other or into props: a pass/fail gate, not an eyeball check.
"""
from __future__ import annotations

import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

GRID = 0.25            # room cell (m)
SUB = 0.05             # surface sub-cell (m)
SEAT, SIDE, TABLE, COUNTER = 0.25, 0.375, 0.50, 0.625   # standard surface heights (m), multiples of GRID / 2

# Warm, earthy palette (sRGB). Rooms pick one dominant hue and one accent; the backdrop is a deep complement.
PALETTE = {
    "terracotta": (0.80, 0.42, 0.30), "rust": (0.66, 0.30, 0.20), "mustard": (0.88, 0.65, 0.26), "honey": (0.86, 0.58, 0.30),
    "apricot": (0.95, 0.74, 0.55), "peach": (0.97, 0.82, 0.66), "rose": (0.88, 0.56, 0.52), "plum": (0.42, 0.27, 0.42),
    "sage": (0.64, 0.72, 0.54), "olive": (0.46, 0.52, 0.30), "leaf": (0.36, 0.56, 0.33), "leaf_dark": (0.22, 0.40, 0.26),
    "teal": (0.20, 0.47, 0.48), "teal_deep": (0.10, 0.25, 0.28), "night": (0.08, 0.16, 0.22), "cream": (0.96, 0.90, 0.78),
    "wood_light": (0.84, 0.62, 0.40), "wood": (0.70, 0.46, 0.28), "wood_dark": (0.42, 0.26, 0.17), "ink": (0.12, 0.10, 0.10),
    "skin_a": (0.94, 0.76, 0.62), "skin_b": (0.78, 0.55, 0.40), "skin_c": (0.52, 0.34, 0.24),
    "hair_brown": (0.40, 0.24, 0.14), "hair_dark": (0.16, 0.12, 0.10), "hair_auburn": (0.62, 0.30, 0.16), "hair_grey": (0.74, 0.72, 0.70),
    "ginger": (0.92, 0.58, 0.28), "ginger_dark": (0.72, 0.38, 0.18), "denim": (0.32, 0.42, 0.58), "slate": (0.36, 0.38, 0.42),
    "warm_light": (1.0, 0.80, 0.52),
}

_mats: dict = {}


def lin(c):
    return tuple(x ** 2.2 for x in c)


def mat(colour, rough=0.75, emit=0.0):
    """A flat material from a palette name or an sRGB tuple (cached)."""
    rgb = PALETTE[colour] if isinstance(colour, str) else tuple(colour)
    key = (rgb, rough, emit)
    if key not in _mats:
        m = bpy.data.materials.new(colour if isinstance(colour, str) else "custom")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*lin(rgb), 1)
        b.inputs["Roughness"].default_value = rough
        if emit:
            b.inputs["Emission Color"].default_value = (*lin(rgb), 1)
            b.inputs["Emission Strength"].default_value = emit
        m.diffuse_color = (*lin(rgb), 1)
        _mats[key] = m
    return _mats[key]


# --------------------------------------------------------------------------------------------- blocks

def block(name, shape, centre, size, colour, *, parent=None, bevel=0.25, taper=(1.0, 1.0), rot=(0, 0, 0),
          rough=0.75, emit=0.0, coll=None, segments=None):
    """One block. shape: box | ball | cyl | wedge (4-sided cone) | ring (torus around Z).
    centre/size/rot are in the parent's space (rig space for character blocks). bevel is a fraction of the
    smallest dimension (boxes, cylinders). taper scales the top (+Z) face for boxes and cylinders."""
    sx, sy, sz = size
    bm = bmesh.new()
    if shape == "box":
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            if v.co.z > 0:
                v.co.x *= taper[0]
                v.co.y *= taper[1]
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
        if bevel:
            bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel * min(size), offset_type="OFFSET",
                            segments=segments or 3, profile=0.5, affect="EDGES", clamp_overlap=True)
    elif shape == "ball":
        bmesh.ops.create_uvsphere(bm, u_segments=segments or 28, v_segments=(segments or 28) // 2, radius=0.5)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    elif shape in ("cyl", "wedge"):
        n = 4 if shape == "wedge" else (segments or 28)
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=n, radius1=0.5, radius2=0.5 * taper[0], depth=1.0)
        if shape == "wedge":
            bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 4, 3, "Z"), verts=bm.verts)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
        if bevel and shape == "cyl":
            caps = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6]
            bmesh.ops.bevel(bm, geom=caps, offset=bevel * min(size), offset_type="OFFSET", segments=2, profile=0.5,
                            affect="EDGES", clamp_overlap=True)
    elif shape == "ring":   # size: (outer diameter x, outer diameter y, tube thickness)
        bm.free()
        bpy.ops.mesh.primitive_torus_add(major_radius=0.5 - size[2] / 2 / max(sx, sy), minor_radius=size[2] / 2 / max(sx, sy),
                                         major_segments=32, minor_segments=10)
        tmp = bpy.context.object
        bm = bmesh.new()
        bm.from_mesh(tmp.data)
        bpy.data.objects.remove(tmp)
        bmesh.ops.scale(bm, vec=(sx, sy, max(sx, sy)), verts=bm.verts)
    else:
        raise ValueError(shape)
    m = Matrix.Translation(Vector(centre)) @ Euler(rot).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    if shape in ("box", "cyl", "wedge"):
        me.set_sharp_from_angle(angle=math.radians(35))
    me.materials.append(mat(colour, rough, emit))
    o = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(o)
    if parent is not None:
        o.parent = parent
    return o


def group(name, loc=(0, 0, 0), rot_z_deg=0.0, coll=None):
    """An empty that a set of blocks hangs off (an object's root). Blocks are authored in its local space."""
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.1
    e.location = loc
    e.rotation_euler.z = math.radians(rot_z_deg)
    (coll or bpy.context.scene.collection).objects.link(e)
    return e


def cell(i, j, origin=(0.0, 0.0), w=1, d=1):
    """World XY of the centre of a w x d footprint whose corner cell is (i, j)."""
    return (origin[0] + (i + w / 2) * GRID, origin[1] + (j + d / 2) * GRID)


def sub(top_centre, a, b, z):
    """A point on a surface sub-grid: top_centre is the surface centre (local), a/b are sub-cell offsets."""
    return (top_centre[0] + a * SUB, top_centre[1] + b * SUB, z)


# --------------------------------------------------------------------------------------------- chassis

def _mirror(j):
    out = dict(j)
    for k, v in j.items():
        if k.endswith("_L"):
            out[k[:-2] + "_R"] = (-v[0], v[1], v[2])
    return {k: Vector(v) for k, v in out.items()}


# Human: about 1.30 m and 3.4 heads tall, facing -Y, Z up, the character's left is +X. Fixed proportions.
HUMAN_JOINTS = _mirror({
    "hips": (0, 0, 0.52), "spine": (0, 0, 0.60), "chest": (0, 0, 0.70), "neck": (0, 0, 0.88), "neck_top": (0, 0, 0.91),
    "head_top": (0, 0, 1.30),
    "chest_side_L": (0.05, 0, 0.84), "shoulder_L": (0.19, 0, 0.84), "elbow_L": (0.20, 0.005, 0.685), "wrist_L": (0.205, 0, 0.535),
    "hand_L": (0.205, -0.005, 0.44),
    "hip_L": (0.07, 0, 0.47), "knee_L": (0.07, 0, 0.27), "ankle_L": (0.07, 0.005, 0.08), "ball_L": (0.07, -0.07, 0.03),
    "toe_L": (0.07, -0.13, 0.03),
})
HUMAN_BONES = [  # Unity Humanoid names: name, head joint, tail joint, parent
    ("Hips", "hips", "spine", None), ("Spine", "spine", "chest", "Hips"), ("Chest", "chest", "neck", "Spine"),
    ("Neck", "neck", "neck_top", "Chest"), ("Head", "neck_top", "head_top", "Neck"),
    ("LeftShoulder", "chest_side_L", "shoulder_L", "Chest"), ("LeftUpperArm", "shoulder_L", "elbow_L", "LeftShoulder"),
    ("LeftLowerArm", "elbow_L", "wrist_L", "LeftUpperArm"), ("LeftHand", "wrist_L", "hand_L", "LeftLowerArm"),
    ("RightShoulder", "chest_side_R", "shoulder_R", "Chest"), ("RightUpperArm", "shoulder_R", "elbow_R", "RightShoulder"),
    ("RightLowerArm", "elbow_R", "wrist_R", "RightUpperArm"), ("RightHand", "wrist_R", "hand_R", "RightLowerArm"),
    ("LeftUpperLeg", "hip_L", "knee_L", "Hips"), ("LeftLowerLeg", "knee_L", "ankle_L", "LeftUpperLeg"),
    ("LeftFoot", "ankle_L", "ball_L", "LeftLowerLeg"), ("LeftToes", "ball_L", "toe_L", "LeftFoot"),
    ("RightUpperLeg", "hip_R", "knee_R", "Hips"), ("RightLowerLeg", "knee_R", "ankle_R", "RightUpperLeg"),
    ("RightFoot", "ankle_R", "ball_R", "RightLowerLeg"), ("RightToes", "ball_R", "toe_R", "RightFoot"),
]
HEAD_C, HEAD_SIZE = Vector((0, -0.005, 1.105)), Vector((0.36, 0.33, 0.39))   # head envelope (mounts are relative to it)
HUMAN_SOCKETS = {   # name: (bone, rest point). Poses and props aim at these, never at raw joints.
    "grip_L": ("LeftHand", (0.205, -0.01, 0.48)), "grip_R": ("RightHand", (-0.205, -0.01, 0.48)),
    "seat": ("Hips", (0, 0.0, 0.412)),   # under the thighs when they are level (hip joint minus half a thigh) "sole_L": ("LeftFoot", (0.07, -0.03, 0.0)), "sole_R": ("RightFoot", (-0.07, -0.03, 0.0)),
    "head_top": ("Head", (0, 0.0, 1.30)), "face": ("Head", (0, -0.17, 1.09)),
}

# Cat: about 0.30 m at the shoulder, facing -Y. A generic (non-Humanoid) rig.
CAT_JOINTS = _mirror({
    "hips": (0, 0.11, 0.21), "spine": (0, 0.0, 0.21), "chest": (0, -0.10, 0.22), "neck_top": (0, -0.16, 0.28), "head_top": (0, -0.19, 0.40),
    "fhip_L": (0.055, -0.09, 0.17), "fpaw_L": (0.055, -0.10, 0.035), "ftoe_L": (0.055, -0.15, 0.02),
    "hhip_L": (0.055, 0.10, 0.17), "hpaw_L": (0.055, 0.11, 0.035), "htoe_L": (0.055, 0.06, 0.02),
    "tail0": (0, 0.19, 0.25), "tail1": (0, 0.27, 0.31), "tail2": (0, 0.30, 0.40), "tail3": (0, 0.28, 0.49),
})
CAT_BONES = [
    ("Hips", "hips", "spine", None), ("Spine", "spine", "chest", "Hips"), ("Neck", "chest", "neck_top", "Spine"),
    ("Head", "neck_top", "head_top", "Neck"),
    ("FrontLeg_L", "fhip_L", "fpaw_L", "Spine"), ("FrontPaw_L", "fpaw_L", "ftoe_L", "FrontLeg_L"),
    ("FrontLeg_R", "fhip_R", "fpaw_R", "Spine"), ("FrontPaw_R", "fpaw_R", "ftoe_R", "FrontLeg_R"),
    ("HindLeg_L", "hhip_L", "hpaw_L", "Hips"), ("HindPaw_L", "hpaw_L", "htoe_L", "HindLeg_L"),
    ("HindLeg_R", "hhip_R", "hpaw_R", "Hips"), ("HindPaw_R", "hpaw_R", "htoe_R", "HindLeg_R"),
    ("Tail1", "tail0", "tail1", "Hips"), ("Tail2", "tail1", "tail2", "Tail1"), ("Tail3", "tail2", "tail3", "Tail2"),
]
CAT_SOCKETS = {"lap_rest": ("Hips", (0, 0.05, 0.10)), "head_top": ("Head", (0, -0.20, 0.42))}


def build_rig(name, joints, bones, coll=None):
    arm = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, arm)
    (coll or bpy.context.scene.collection).objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for bname, a, b, parent in bones:
        bone = arm.edit_bones.new(bname)
        bone.head, bone.tail = joints[a], joints[b]
        bone.roll = 0.0
        if parent:
            bone.parent = eb[parent]
            bone.use_connect = (eb[parent].tail - bone.head).length < 1e-5
        eb[bname] = bone
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front = True
    rig.hide_render = True
    return rig


def bind_rigid(rig, obj, bone):
    """Bind a block 100% to one bone: no deformation, Unity-friendly (a skinned mesh with one-bone weights)."""
    obj.parent = rig
    vg = obj.vertex_groups.new(name=bone)
    vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    obj["bone"] = bone


# --------------------------------------------------------------------------------------------- human modules
# Each module adds blocks: add(bone, shape, centre, size, colour_role_or_name, **kw). Colour roles come from the recipe.

def _x(side, x):
    return x if side == "L" else -x


def body_base(add, r):
    """Pelvis, torso and limbs with gaps at every joint. Roles: top, bottom, skin, shoes.
    A skirt replaces the thigh blocks (they would be hidden inside it)."""
    sleeves = r.get("sleeves", "long")
    add("Hips", "box", (0, 0, 0.515), (0.24, 0.165, 0.09), "bottom", bevel=0.3)
    add("Chest", "box", (0, 0, 0.73), (0.27, 0.18, 0.29), "top", bevel=0.25, taper=(1.06, 1.05))
    for s in "LR":
        S = "Left" if s == "L" else "Right"
        add(f"{S}UpperArm", "box", (_x(s, 0.195), 0, 0.765), (0.078, 0.084, 0.13), "top", bevel=0.4)
        add(f"{S}LowerArm", "box", (_x(s, 0.2025), 0.0025, 0.612), (0.07, 0.074, 0.12),
            "top" if sleeves == "long" else "skin", bevel=0.4)
        add(f"{S}Hand", "box", (_x(s, 0.205), -0.006, 0.48), (0.046, 0.074, 0.088), "skin", bevel=0.45, taper=(1.0, 1.08))
        add(f"{S}Hand", "box", (_x(s, 0.192), -0.05, 0.495), (0.03, 0.028, 0.045), "skin", bevel=0.45)   # thumb
        if r.get("bottom") != "skirt":
                add(f"{S}UpperLeg", "box", (_x(s, 0.07), 0, 0.372), (0.105, 0.115, 0.165), "legs", bevel=0.35)
        add(f"{S}LowerLeg", "box", (_x(s, 0.07), 0.003, 0.185), (0.092, 0.10, 0.155), "legs", bevel=0.35)
        add(f"{S}Foot", "box", (_x(s, 0.07), -0.035, 0.04), (0.10, 0.17, 0.08), "shoes", bevel=0.4, taper=(0.92, 0.95))


def top_jumper(add, r):
    add("Chest", "box", (0, 0, 0.598), (0.282, 0.19, 0.035), "top_trim", bevel=0.4)        # ribbed hem
    for s in "LR":
        add(f"{'Left' if s == 'L' else 'Right'}LowerArm", "box", (_x(s, 0.2025), 0.0025, 0.56), (0.076, 0.08, 0.025), "top_trim", bevel=0.4)
    add("Chest", "cyl", (0, 0, 0.885), (0.13, 0.12, 0.03), "top_trim", bevel=0.3)            # roll neck


def top_shirt(add, r):
    for s in "LR":
        add("Chest", "wedge", (_x(s, 0.04), -0.08, 0.86), (0.07, 0.03, 0.05), "top_trim", rot=(0.3, 0, _x(s, -0.5)), bevel=0)
    for k in range(3):
        add("Chest", "ball", (0, -0.093, 0.80 - k * 0.06), (0.014, 0.008, 0.014), "top_trim")


def top_cardigan(add, r):
    add("Chest", "box", (0, -0.088, 0.72), (0.07, 0.012, 0.27), "top_trim", bevel=0.3)        # shirt showing at the front
    for k in range(3):
        add("Chest", "ball", (0.045, -0.093, 0.80 - k * 0.07), (0.016, 0.008, 0.016), "buttons")
    for s in "LR":
        add("Chest", "box", (_x(s, 0.105), -0.07, 0.6), (0.055, 0.04, 0.05), "top", bevel=0.4)   # pockets


def bottom_skirt(add, r):
    add("Hips", "box", (0, 0, 0.41), (0.28, 0.20, 0.26), "bottom", bevel=0.3, taper=(0.86, 0.85))   # to just above the knee


def head_round(add, r):
    add("Head", "ball", tuple(HEAD_C), tuple(HEAD_SIZE), "skin", segments=36)


def head_boxy(add, r):
    add("Head", "box", tuple(HEAD_C), (0.345, 0.31, 0.37), "skin", bevel=0.42, segments=4)


def _face_y(r, x, z):
    """Front surface y of the head envelope at (x, z) (ellipsoid or rounded box)."""
    if r.get("head") == "boxy":
        return HEAD_C.y - 0.155
    a, b, c = HEAD_SIZE / 2
    t = 1 - (x / a) ** 2 - ((z - HEAD_C.z) / c) ** 2
    return HEAD_C.y - b * math.sqrt(max(t, 0.05))


def face_simple(add, r):
    for s in "LR":
        x, z = _x(s, 0.066), 1.105
        add("Head", "ball", (x, _face_y(r, x, z) + 0.004, z), (0.034, 0.022, 0.05), "ink", rough=0.3)
        x2, z2 = _x(s, 0.105), 1.045
        add("Head", "ball", (x2, _face_y(r, x2, z2) + 0.004, z2), (0.05, 0.012, 0.028), "cheek")
    add("Head", "ball", (0, _face_y(r, 0, 1.06) - 0.006, 1.06), (0.04, 0.035, 0.034), "skin")


def glasses(add, r):
    for s in "LR":
        x, z = _x(s, 0.066), 1.105
        add("Head", "ring", (x, _face_y(r, x, z) - 0.012, z), (0.085, 0.085, 0.012), "frames", rot=(math.pi / 2, 0, 0))
    add("Head", "box", (0, _face_y(r, 0, 1.11) - 0.014, 1.112), (0.05, 0.01, 0.01), "frames", bevel=0.3)


def _cap(add, r, extra_back=0.0, low=1.17):
    if r.get("hat"):              # a hat replaces the crown; only the back and sides show
        pass
    elif r.get("head") == "boxy":   # the crown follows the head's shape, or the head's corners poke through
        add("Head", "box", (0, 0.01, 1.215), (0.37, 0.335, 0.20), "hair", bevel=0.45, segments=4)
    else:
        add("Head", "ball", (0, 0.012, 1.17), (0.385, 0.36, 0.30), "hair", segments=32)
    add("Head", "box", (0, 0.105 + extra_back / 2, low + 0.0), (0.30, 0.13 + extra_back, 0.20), "hair", bevel=0.45)


def hair_crop(add, r):
    _cap(add, r)


def hair_bun(add, r):
    _cap(add, r)
    add("Head", "ball", (0, 0.10, 1.31), (0.14, 0.14, 0.13), "hair")
    for s in "LR":
        add("Head", "box", (_x(s, 0.17), -0.06, 1.12), (0.04, 0.07, 0.16), "hair", bevel=0.45)    # side locks


def hair_bob(add, r):
    _cap(add, r, extra_back=0.03, low=1.10)
    add("Head", "box", (0, -0.14, 1.235), (0.31, 0.07, 0.08), "hair", bevel=0.45, rot=(0.15, 0, 0))   # fringe
    top = 1.13 if r.get("hat") else 1.17      # locks hang below a hat's band
    for s in "LR":
        add("Head", "box", (_x(s, 0.17), 0.0, (top + 0.97) / 2), (0.055, 0.22, top - 0.97), "hair", bevel=0.45)


def hat_beanie(add, r):
    add("Head", "ball", (0, 0.0, 1.22), (0.39, 0.37, 0.30), "hat", segments=32)
    add("Head", "cyl", (0, 0.0, 1.20), (0.40, 0.375, 0.06), "hat_trim", bevel=0.3)
    add("Head", "ball", (0, 0.0, 1.385), (0.08, 0.08, 0.08), "hat_trim")


def beard(add, r):
    add("Head", "ball", (0, HEAD_C.y - 0.035, 0.985), (0.33, 0.29, 0.17), "hair", segments=32)   # wraps the jaw


HUMAN_MODULES = {
    "head": {"round": head_round, "boxy": head_boxy}, "face": {"simple": face_simple},
    "hair": {"crop": hair_crop, "bun": hair_bun, "bob": hair_bob, "none": lambda add, r: None},
    "hat": {"beanie": hat_beanie}, "top": {"jumper": top_jumper, "shirt": top_shirt, "cardigan": top_cardigan},
    "bottom": {"trousers": lambda add, r: None, "skirt": bottom_skirt}, "extras": {"glasses": glasses, "beard": beard},
}


# --------------------------------------------------------------------------------------------- cat modules

def cat_body(add, r):
    add("Hips", "box", (0, 0.10, 0.205), (0.20, 0.19, 0.17), "fur", bevel=0.4)
    add("Spine", "box", (0, -0.075, 0.215), (0.19, 0.135, 0.17), "fur", bevel=0.4)
    add("Head", "box", (0, -0.205, 0.335), (0.18, 0.15, 0.145), "fur", bevel=0.45)
    add("Head", "ball", (0, -0.282, 0.31), (0.085, 0.04, 0.055), "fur_light")                       # muzzle
    add("Head", "ball", (0, -0.30, 0.325), (0.022, 0.012, 0.016), "nose")
    for s in "LR":
        add("Head", "wedge", (_x(s, 0.052), -0.19, 0.43), (0.06, 0.05, 0.06), "fur", rot=(0, _x(s, 0.25), 0), bevel=0)
        add("Head", "ball", (_x(s, 0.042), -0.281, 0.355), (0.022, 0.01, 0.032), "ink", rough=0.3)
    for leg, y in (("Front", -0.095), ("Hind", 0.105)):
        for s in "LR":
            add(f"{leg}Leg_{s}", "box", (_x(s, 0.055), y, 0.085), (0.055, 0.06, 0.066), "fur", bevel=0.4)
            add(f"{leg}Paw_{s}", "ball", (_x(s, 0.055), y - 0.012, 0.022), (0.06, 0.075, 0.042), "fur_light")
    for k, (bone, a, b) in enumerate((("Tail1", "tail0", "tail1"), ("Tail2", "tail1", "tail2"), ("Tail3", "tail2", "tail3"))):
        pa, pb = CAT_JOINTS[a], CAT_JOINTS[b]
        d = pb - pa
        rot = d.to_track_quat("Z", "Y").to_euler()
        add(bone, "box", tuple((pa + pb) / 2), (0.045, 0.045, d.length - 0.012), "fur" if k < 2 else "fur_dark",
            bevel=0.45, rot=tuple(rot))


def cat_stripes(add, r):
    for k, y in enumerate((0.03, 0.09, 0.15)):
        add("Hips" if y > 0.0 else "Spine", "box", (0, y, 0.293), (0.15, 0.022, 0.012), "fur_dark", bevel=0.4)
    add("Spine", "box", (0, -0.06, 0.303), (0.14, 0.022, 0.012), "fur_dark", bevel=0.4)
    add("Head", "box", (0, -0.19, 0.41), (0.05, 0.02, 0.01), "fur_dark", bevel=0.4)


CAT_MODULES = {"body": {"cat": cat_body}, "markings": {"stripes": cat_stripes, "none": lambda add, r: None}}

CHASSIS = {
    "human": (HUMAN_JOINTS, HUMAN_BONES, HUMAN_SOCKETS, HUMAN_MODULES, ["head", "face", "hair", "hat", "top", "bottom", "extras"]),
    "cat": (CAT_JOINTS, CAT_BONES, CAT_SOCKETS, CAT_MODULES, ["body", "markings"]),
}


def build_character(name, recipe, coll=None):
    """recipe: {"chassis": "human", "colours": {role: palette name}, <slot>: module name or [names]}.
    Returns the rig; blocks are children bound rigidly to one bone each."""
    joints, bones, sockets, modules, slots = CHASSIS[recipe["chassis"]]
    rig = build_rig(f"{name}_Rig", joints, bones, coll)
    rig["chassis"] = recipe["chassis"]
    colours = {"legs": recipe["colours"].get("bottom"), "top_trim": recipe["colours"].get("top"), "cheek": "rose",
               "frames": "ink", "buttons": "cream", "nose": "rose", **recipe["colours"]}
    count = [0]

    def add(bone, shape, centre, size, role, **kw):
        count[0] += 1
        o = block(f"{name}_{bone}_{count[0]:02d}", shape, centre, size, colours.get(role, role), coll=coll, **kw)
        bind_rigid(rig, o, bone)
        return o

    if recipe["chassis"] == "human":
        body_base(add, recipe)
    for slot in slots:
        names = recipe.get(slot)
        for n in ([names] if isinstance(names, str) else names or []):
            modules[slot][n](add, recipe)
    return rig


# --------------------------------------------------------------------------------------------- posing

def _update():
    bpy.context.view_layer.update()


def aim(rig, bone, direction):
    """Point a bone along a direction in the character's own frame (rig space), keeping its head where the parents put it."""
    _update()
    pb = rig.pose.bones[bone]
    rest = rig.data.bones[bone].matrix_local
    rest_dir = (rest.to_3x3() @ Vector((0, 1, 0))).normalized()
    rot = rest_dir.rotation_difference(Vector(direction).normalized()).to_matrix() @ rest.to_3x3()
    pb.matrix = Matrix.Translation(pb.head) @ rot.to_4x4()
    _update()


def shift(rig, bone, offset):
    """Translate a bone (usually Hips) by an offset in rig space."""
    _update()
    pb = rig.pose.bones[bone]
    m = pb.matrix.copy()
    m.translation += Vector(offset)
    pb.matrix = m
    _update()


def socket(rig, name):
    """World position of a named socket in the current pose."""
    _update()
    sockets = CHASSIS[rig["chassis"]][2]
    bone, rest = sockets[name]
    pb = rig.pose.bones[bone]
    local = rig.data.bones[bone].matrix_local.inverted() @ Vector(rest)
    return rig.matrix_world @ (pb.matrix @ local)


def place_socket(rig, name, world_point):
    """Move the whole character so a socket lands on a world point (e.g. 'seat' on a chair's seat anchor)."""
    rig.location += Vector(world_point) - socket(rig, name)
    _update()


def mount(obj, rig, name, bone=None, local_grip=(0, 0, 0)):
    """Mount a prop so its grip point (in its own space) sits on a socket; it then follows that bone."""
    _update()
    sockets = CHASSIS[rig["chassis"]][2]
    bone = bone or sockets[name][0]
    target = socket(rig, name)
    mw = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    _update()
    obj.matrix_world = Matrix.Translation(target - mw.to_3x3() @ Vector(local_grip)) @ mw.to_3x3().to_4x4()
    _update()


def hold_between(obj, rig, a="grip_L", b="grip_R", face=None):
    """Hold a flat prop (book, tray) between two sockets; its local X runs hand to hand, Y faces `face` (world)."""
    pa, pb = socket(rig, a), socket(rig, b)
    centre = (pa + pb) / 2
    x = (pa - pb).normalized()
    toward = Vector(face) - centre if face is not None else Vector((0, 0, 1))
    y = (toward - toward.dot(x) * x).normalized()
    z = x.cross(y)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = centre
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = CHASSIS[rig["chassis"]][2][a][0]
    _update()
    obj.matrix_world = m
    _update()


# --------------------------------------------------------------------------------------------- checks

def _tree(o, dg):
    e = o.evaluated_get(dg)
    me = e.to_mesh()
    verts = [e.matrix_world @ v.co for v in me.vertices]
    t = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in me.polygons])
    e.to_mesh_clear()
    return t, verts


def _bbox(verts):
    xs, ys, zs = zip(*verts)
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def _joined(a, b):
    """Same rig, and same bone or neighbouring bones with the same material: the overlap reads as one shape
    (hair over a head, trousers at a seated hip), so it is allowed by design."""
    if not (a.get("bone") and b.get("bone") and a.parent is b.parent):
        return False
    if a["bone"] == b["bone"]:
        return True
    bones = a.parent.data.bones
    pa, pb = bones[a["bone"]].parent, bones[b["bone"]].parent
    near = (pa and pa.name == b["bone"]) or (pb and pb.name == a["bone"])
    return bool(near) and a.data.materials[0] == b.data.materials[0]


def overlaps(movers, others, tol=0.004, joined_ok=True):
    """Max depth (m) each mover block goes inside another closed block. Returns [(mover, other, depth)] above tol,
    deepest first. Joined blocks (see _joined) may overlap by design."""
    dg = bpy.context.evaluated_depsgraph_get()
    cache = {o.name: _tree(o, dg) for o in set(movers) | set(others)}
    boxes = {n: _bbox(v) for n, (t, v) in cache.items() if v}
    out = []
    for m in movers:
        tm, vm = cache[m.name]
        if not vm:
            continue
        lo, hi = boxes[m.name]
        for o in others:
            if o is m or (joined_ok and _joined(m, o)):
                continue
            lo2, hi2 = boxes.get(o.name, (None, None))
            if lo2 is None or any(hi[i] < lo2[i] or hi2[i] < lo[i] for i in range(3)):
                continue
            to, _ = cache[o.name]
            depth = 0.0
            for p in vm:
                loc, n, _, dist = to.find_nearest(p, 0.3)
                if loc is not None and n.dot(p - loc) < 0:
                    depth = max(depth, dist)
            if depth > tol:
                out.append((m.name, o.name, depth))
    return sorted(out, key=lambda t: -t[2])
