"""Build a gently stylised humanoid test character with a Unity-Humanoid-named deform rig.

Blender 5.2.2:
  blender -b --factory-startup --python-exit-code 1 -P scripts/blender/build_stylised_character.py -- \
    --out out/authoring-study/character.blend [--height 1.68] [--heads 5.5] [--build 1.0] [--palette warm]

The body is generated from a joint graph with per-joint radii (Skin modifier + subdivision), so proportions are
parameters, not sculpting. Head, eyes, nose and hair are separate smooth meshes rigidly bound to the Head bone.
Bones use Unity Humanoid names (Hips, Spine, Chest, Neck, Head, LeftUpperArm…) in a clean parent chain, deform-only,
character facing -Y, feet at Z=0, metres. A small JSON sidecar records proportions and bone lengths.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PALETTES = {
    "warm": {"skin": (0.86, 0.66, 0.52), "shirt": (0.78, 0.42, 0.30), "trousers": (0.24, 0.27, 0.36),
             "shoes": (0.20, 0.15, 0.12), "hair": (0.22, 0.14, 0.09), "eyes": (0.05, 0.04, 0.04)},
    "cool": {"skin": (0.80, 0.62, 0.50), "shirt": (0.33, 0.52, 0.48), "trousers": (0.38, 0.30, 0.24),
             "shoes": (0.15, 0.13, 0.12), "hair": (0.10, 0.08, 0.07), "eyes": (0.05, 0.04, 0.04)},
}


def joints(height: float, heads: float, build: float) -> dict:
    """Joint positions for a figure facing -Y with Z up; the character's left is +X.
    Body joints are authored for a 1.68 m figure and scale with height; shoulder/hip width scale with build;
    the head block (and so the neck) follows the heads-tall parameter."""
    s = height / 1.68
    head_h = height / heads
    neck_top = height - head_h * 0.86
    base = {
        "hips": (0, 0, 0.84), "spine": (0, 0, 0.97), "chest": (0, 0, 1.10),
        "shoulder_L": (0.19, 0, None), "elbow_L": (0.225, 0.01, 0.99), "wrist_L": (0.24, -0.01, 0.79),
        "hand_L": (0.245, -0.015, 0.69), "thumb_L": (0.21, -0.055, 0.74),
        "hip_L": (0.095, 0, 0.80), "knee_L": (0.10, -0.01, 0.43), "ankle_L": (0.10, 0.02, 0.085),
        "ball_L": (0.10, -0.11, 0.047), "toe_L": (0.10, -0.215, 0.047),
    }
    out = {"neck_top": Vector((0, 0, neck_top)), "neck": Vector((0, 0, neck_top - 0.05 * s))}
    for k, (x, y, z) in base.items():
        z = (neck_top - 0.08 * s) if z is None else z * s
        wide = build if k.startswith(("shoulder", "hip", "elbow", "wrist", "hand", "thumb")) else 1.0
        out[k] = Vector((x * s * wide, y * s, z))
        if k.endswith("_L"):
            out[k[:-2] + "_R"] = Vector((-out[k].x, out[k].y, out[k].z))
    out["head_centre"] = Vector((0, -0.01 * s, height - head_h * 0.5))
    out["head_top"] = Vector((0, 0, height))
    out["head_h"] = head_h
    return out


RADII = {"hips": 0.145, "spine": 0.13, "chest": 0.15, "neck": 0.062, "neck_top": 0.06,
         "shoulder": 0.068, "elbow": 0.052, "wrist": 0.044, "hand": 0.064, "thumb": 0.028,
         "hip": 0.09, "knee": 0.064, "ankle": 0.058, "ball": 0.07, "toe": 0.062}

EDGES = [("hips", "spine"), ("spine", "chest"), ("chest", "neck"), ("neck", "neck_top"),
         ("chest", "shoulder_L"), ("shoulder_L", "elbow_L"), ("elbow_L", "wrist_L"), ("wrist_L", "hand_L"), ("wrist_L", "thumb_L"),
         ("chest", "shoulder_R"), ("shoulder_R", "elbow_R"), ("elbow_R", "wrist_R"), ("wrist_R", "hand_R"), ("wrist_R", "thumb_R"),
         ("hips", "hip_L"), ("hip_L", "knee_L"), ("knee_L", "ankle_L"), ("ankle_L", "ball_L"), ("ball_L", "toe_L"),
         ("hips", "hip_R"), ("hip_R", "knee_R"), ("knee_R", "ankle_R"), ("ankle_R", "ball_R"), ("ball_R", "toe_R")]

BONES = [  # name, head joint, tail joint, parent
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


def material(name, rgb, rough=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*[c ** 2.2 for c in rgb], 1.0)   # sRGB-ish → linear
    bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*[c ** 2.2 for c in rgb], 1.0)
    return m


def build_body(j, mats):
    names = sorted({a for e in EDGES for a in e})
    idx = {n: i for i, n in enumerate(names)}
    mesh = bpy.data.meshes.new("BodyMesh")
    mesh.from_pydata([j[n] for n in names], [(idx[a], idx[b]) for a, b in EDGES], [])
    body = bpy.data.objects.new("Body", mesh)
    bpy.context.collection.objects.link(body)
    skin = body.modifiers.new("Skin", "SKIN")
    skin.use_smooth_shade = True
    for n, i in idx.items():
        r = RADII[n.rsplit("_", 1)[0]] if n.endswith(("_L", "_R")) else RADII[n]
        sv = mesh.skin_vertices[0].data[i]
        torso = n in ("hips", "chest", "spine")
        sv.radius = (r * (1.18 if torso else 1.0), r * (1.35 if torso else 1.0))   # branch nodes shrink depth; compensate
        if n == "hips":
            sv.use_root = True
    sub = body.modifiers.new("Subdivision", "SUBSURF")
    sub.levels = sub.render_levels = 2
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    bpy.ops.object.modifier_apply(modifier="Skin")
    # Skin hulls at branch joints come out asymmetric; mirror the character's left (+X) half onto the right.
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.symmetrize(direction="POSITIVE_X")
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.modifier_apply(modifier="Subdivision")
    bpy.ops.object.shade_smooth()
    for v in body.data.vertices:          # chunky shoes with flat soles resting on the floor
        if v.co.z < 0.0:
            v.co.z = 0.0
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(body.data)
    for z in (j["ankle_L"].z + 0.035, j["hips"].z + 0.02, j["wrist_L"].z + 0.02, j["neck"].z - 0.005):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1))
    bm.to_mesh(body.data)
    bm.free()
    # Materials by region: shoes below the ankle, trousers up to the hips, skin on hands/neck, shirt elsewhere.
    for key in ("shirt", "trousers", "shoes", "skin"):
        body.data.materials.append(mats[key])
    order = {"shirt": 0, "trousers": 1, "shoes": 2, "skin": 3}
    wrist_z = j["wrist_L"].z
    for p in body.data.polygons:
        c = p.center
        if c.z < j["ankle_L"].z + 0.035:
            p.material_index = order["shoes"]
        elif abs(c.x) > j["shoulder_L"].x * 0.9 and c.z < wrist_z + 0.02:
            p.material_index = order["skin"]
        elif c.z > j["neck"].z - 0.005 and abs(c.x) < 0.09:
            p.material_index = order["skin"]
        elif c.z < j["hips"].z + 0.02:
            p.material_index = order["trousers"]
        else:
            p.material_index = order["shirt"]
    return body


def build_head(j, mats, height):
    h = j["head_h"]
    parts = []
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=h * 0.5, location=j["head_centre"])
    head = bpy.context.object
    head.name = "HeadMesh"   # must not share a name with the Head bone (Unity Humanoid needs unique names)
    head.scale = (1.0, 0.95, 1.05)
    head.data.materials.append(mats["skin"])
    parts.append(head)
    for side in (1, -1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=h * 0.045,
                                             location=j["head_centre"] + Vector((side * h * 0.17, -h * 0.45, h * 0.03)))
        eye = bpy.context.object
        eye.name = f"Eye{'L' if side > 0 else 'R'}"
        eye.scale = (1.0, 0.6, 1.3)
        eye.data.materials.append(mats["eyes"])
        parts.append(eye)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=h * 0.06,
                                         location=j["head_centre"] + Vector((0, -h * 0.49, -h * 0.07)))
    nose = bpy.context.object
    nose.name = "Nose"
    nose.data.materials.append(mats["skin"])
    parts.append(nose)
    # Hair: an upper cap slightly larger than the head, cut below the ears at the back.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=h * 0.53, location=j["head_centre"] + Vector((0, h * 0.03, h * 0.04)))
    hair = bpy.context.object
    hair.name = "Hair"
    hair.scale = (1.02, 0.98, 1.0)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    kill = [v for v in bm.verts if v.co.z < (0.16 * h if v.co.y < -0.2 * h else -0.18 * h)]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(hair.data)
    bm.free()
    hair.data.materials.append(mats["hair"])
    solid = hair.modifiers.new("Solidify", "SOLIDIFY")
    solid.thickness = 0.01
    parts.append(hair)
    for p in parts:
        bpy.context.view_layer.objects.active = p
        bpy.ops.object.select_all(action="DESELECT")
        p.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        for m in list(p.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.ops.object.shade_smooth()
    return parts


def build_rig(j):
    j = dict(j)
    for side, sx in (("L", 1), ("R", -1)):
        j[f"chest_side_{side}"] = Vector((sx * 0.05, 0, j[f"shoulder_{side}"].z - 0.01))
    arm = bpy.data.armatures.new("Armature")
    rig = bpy.data.objects.new("Armature", arm)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for name, a, b, parent in BONES:
        bone = arm.edit_bones.new(name)
        bone.head, bone.tail = j[a], j[b]
        bone.use_deform = True
        if parent:
            bone.parent = eb[parent]
            bone.use_connect = (eb[parent].tail - bone.head).length < 1e-5
        eb[name] = bone
    # Roll: knees and elbows bend predictably (X axis as the hinge for limbs).
    for b in arm.edit_bones:
        b.roll = 0.0
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def bind(rig, body, head_parts):
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    for p in head_parts:
        vg = p.vertex_groups.new(name="Head")
        vg.add(list(range(len(p.data.vertices))), 1.0, "REPLACE")
        p.parent = rig
        mod = p.modifiers.new("Armature", "ARMATURE")
        mod.object = rig
    return body


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--height", type=float, default=1.68)
    ap.add_argument("--heads", type=float, default=5.5)
    ap.add_argument("--build", type=float, default=1.0, help="width multiplier for shoulders/hips")
    ap.add_argument("--palette", default="warm", choices=list(PALETTES))
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    j = joints(a.height, a.heads, a.build)
    mats = {k: material(k.capitalize(), v, 0.8 if k in ("trousers", "shirt") else 0.5) for k, v in PALETTES[a.palette].items()}
    body = build_body(j, mats)
    head_parts = build_head(j, mats, a.height)
    rig = build_rig(j)
    bind(rig, body, head_parts)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(a.out.resolve()))
    meta = {"height": a.height, "heads": a.heads, "build": a.build, "palette": a.palette,
            "bones": {b.name: round(b.length, 4) for b in rig.data.bones},
            "body_vertices": len(body.data.vertices), "blender": bpy.app.version_string}
    a.out.with_suffix(".json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
