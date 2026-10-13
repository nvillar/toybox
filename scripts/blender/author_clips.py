"""Author pose-to-pose clips on a Humanoid-named rig through IK controls, bake to FK, measure contact, export FBX.

Blender 5.2.2:
  blender -b out/authoring-study/character.blend --python-exit-code 1 -P scripts/blender/author_clips.py -- \
    --clips clips.json --out-dir out/authoring-study/clips

How a clip is written (clips.json): a list of key poses, each at a frame, giving only what changes:
  hips: [dx, dy, dz] offset from rest (m) and hips_pitch (deg, + leans forward)
  spine / chest / neck / head: [pitch, yaw, roll] degrees
  foot_L / foot_R / hand_L / hand_R: world targets [x, y, z]; hand_*_rot: [pitch, yaw, roll] degrees
  hold: true duplicates the previous pose (a held moment); ease: "snap" | "smooth" | "linear"
Props (seat, switch, book) come from the same file; contact is measured and the seated height auto-corrected.

Writes per clip: <name>.fbx (single baked take), <name>.json (keys, timing, measurements) and keeps the
baked actions in <out-dir>/clips.blend for rendering. Never overwrites the input .blend.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

LIMBS = {  # IK bone, target name, pole name, pole offset from the joint (world, rest)
    "foot_L": ("LeftLowerLeg", "LeftFoot", Vector((0, -0.6, 0))), "foot_R": ("RightLowerLeg", "RightFoot", Vector((0, -0.6, 0))),
    "hand_L": ("LeftLowerArm", "LeftHand", Vector((0.25, 0.5, 0))), "hand_R": ("RightLowerArm", "RightHand", Vector((-0.25, 0.5, 0))),
}
SPINE = {"spine": "Spine", "chest": "Chest", "neck": "Neck", "head": "Head"}


def add_empty(name, loc, size=0.05):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    e.location = loc
    bpy.context.scene.collection.objects.link(e)
    return e


def setup_controls(rig):
    """IK targets at the rest positions of wrists/ankles, poles in front of knees / behind elbows, rotation followers."""
    ctrl = {}
    for key, (ik_bone, end_bone, pole_off) in LIMBS.items():
        end = rig.data.bones[end_bone]
        target = add_empty(f"CTRL_{key}", rig.matrix_world @ end.head_local)
        target.rotation_mode = "QUATERNION"
        target.rotation_quaternion = (rig.matrix_world @ end.matrix_local).to_quaternion()
        joint = rig.data.bones[ik_bone].head_local
        pole = add_empty(f"POLE_{key}", rig.matrix_world @ joint + pole_off, 0.03)
        pb = rig.pose.bones[ik_bone]
        ik = pb.constraints.new("IK")
        ik.target, ik.pole_target, ik.chain_count = target, pole, 2
        ik.pole_angle = math.radians(-90)
        rot = rig.pose.bones[end_bone].constraints.new("COPY_ROTATION")
        rot.target = target
        ctrl[key] = (target, pole)
    return ctrl


def fix_pole_angles(rig, ctrl):
    """Pick each IK pole angle so the rest pose is unchanged (agents shouldn't guess this per rig)."""
    sc = bpy.context.scene
    for key, (ik_bone, end_bone, _) in LIMBS.items():
        pb = rig.pose.bones[ik_bone]
        ik = pb.constraints["IK"]
        best, best_err = 0.0, 1e9
        for deg in range(-180, 181, 5):
            ik.pole_angle = math.radians(deg)
            sc.frame_set(sc.frame_current)
            bpy.context.view_layer.update()
            err = sum((rig.pose.bones[b].matrix.to_translation() - rig.data.bones[b].matrix_local.to_translation()).length
                      for b in (ik_bone, end_bone)) + abs(rig.pose.bones[ik_bone].matrix.to_euler().y - rig.data.bones[ik_bone].matrix_local.to_euler().y)
            if err < best_err:
                best, best_err = deg, err
        ik.pole_angle = math.radians(best)


def build_props(spec):
    props = {}
    mat = bpy.data.materials.new("Prop")
    mat.diffuse_color = (0.55, 0.38, 0.24, 1)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.42, 0.24, 0.12, 1)
    if "seat" in spec:
        s = spec["seat"]
        x, y, h = s["at"][0], s["at"][1], s["height"]
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h - 0.03))
        seat = bpy.context.object
        seat.name = "Seat"
        seat.scale = (0.46, 0.44, 0.06)
        bpy.ops.object.transform_apply(scale=True)
        seat.data.materials.append(mat)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y + 0.21, h + 0.25))
        back = bpy.context.object
        back.name = "SeatBack"
        back.scale = (0.46, 0.04, 0.5)
        bpy.ops.object.transform_apply(scale=True)
        back.data.materials.append(mat)
        for dx in (-0.2, 0.2):
            for dy in (-0.19, 0.19):
                bpy.ops.mesh.primitive_cube_add(size=1, location=(x + dx, y + dy, (h - 0.06) / 2))
                leg = bpy.context.object
                leg.scale = (0.04, 0.04, h - 0.06)
                bpy.ops.object.transform_apply(scale=True)
                leg.data.materials.append(mat)
        props["seat"] = seat
    if "switch" in spec:
        # A wall to the character's right (-X), facing +X, with the switch plate on it.
        sx, sy, sz = spec["switch"]["at"]
        bpy.ops.mesh.primitive_cube_add(size=1, location=(sx - 0.03, sy, 1.1))
        wall = bpy.context.object
        wall.name = "SwitchWall"
        wall.scale = (0.04, 1.6, 2.2)
        bpy.ops.object.transform_apply(scale=True)
        wm = bpy.data.materials.new("Wall")
        wm.use_nodes = True
        wm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.75, 0.72, 0.66, 1)
        wall.data.materials.append(wm)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(sx + 0.005, sy, sz))
        sw = bpy.context.object
        sw.name = "Switch"
        sw.scale = (0.02, 0.07, 0.11)
        bpy.ops.object.transform_apply(scale=True)
        props["switch"] = sw
    if "book" in spec:
        bpy.ops.mesh.primitive_cube_add(size=1)
        book = bpy.context.object
        book.name = "Book"
        book.scale = (0.22, 0.03, 0.16)
        bpy.ops.object.transform_apply(scale=True)
        bm = bpy.data.materials.new("Book")
        bm.use_nodes = True
        bm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.20, 0.33, 0.30, 1)
        book.data.materials.append(bm)
        book.hide_render = True
        props["book"] = book
    return props


def interp(ease):
    return {"snap": ("BEZIER", "EASE_IN_OUT"), "smooth": ("BEZIER", "AUTO"), "linear": ("LINEAR", "AUTO")}.get(ease, ("BEZIER", "AUTO"))


def key_clip(rig, ctrl, clip, rest):
    """Key the controls for one clip, starting from the rest pose; later keys inherit unspecified channels."""
    sc = bpy.context.scene
    hips = rig.pose.bones["Hips"]
    state = {"hips": [0, 0, 0], "hips_pitch": 0, **{k: [0, 0, 0] for k in SPINE},
             **{k: list(rest[k]) for k in LIMBS}, **{f"{k}_rot": [0, 0, 0] for k in ("hand_L", "hand_R")}}
    objs = [rig] + [o for pair in ctrl.values() for o in pair]
    for o in objs:
        o.animation_data_clear()
    for b in rig.pose.bones:
        b.location, b.rotation_mode = (0, 0, 0), "XYZ"
        b.rotation_euler = (0, 0, 0)
    for pose in clip["keys"]:
        f = pose["frame"]
        if not pose.get("hold"):
            for k, v in pose.items():
                if k in state:
                    state[k] = v
        # hips: location in bone space is awkward; offset in world via the bone's rest frame (Z up, Y back)
        d = Vector(state["hips"])
        hips.location = (rig.data.bones["Hips"].matrix_local.to_3x3().inverted() @ d)
        hips.rotation_euler = Euler((math.radians(state["hips_pitch"]), 0, 0))
        hips.keyframe_insert("location", frame=f)
        hips.keyframe_insert("rotation_euler", frame=f)
        for k, bone in SPINE.items():
            p, y, r = state[k]
            pb = rig.pose.bones[bone]
            pb.rotation_euler = Euler((math.radians(p), math.radians(y), math.radians(r)))   # bone Y runs along the spine: yaw
            pb.keyframe_insert("rotation_euler", frame=f)
        for k, (target, pole) in ctrl.items():
            target.location = Vector(state[k])
            target.keyframe_insert("location", frame=f)
            if k.startswith("hand"):
                base = rest[k + "_quat"]
                rot = Euler([math.radians(a) for a in state[k + "_rot"]]).to_quaternion()
                target.rotation_quaternion = rot @ base
                target.keyframe_insert("rotation_quaternion", frame=f)
        mode, easing = interp(pose.get("ease", "snap"))
        for o in objs:
            if o.animation_data and o.animation_data.action:
                for fc in _fcurves(o.animation_data.action):
                    for kp in fc.keyframe_points:
                        if int(round(kp.co.x)) == f:
                            kp.interpolation = mode
                            kp.easing = easing
                            kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    sc.frame_start, sc.frame_end = clip["keys"][0]["frame"], clip["keys"][-1]["frame"]


def _fcurves(action):
    """Blender 5.x layered actions keep curves in channelbags; older ones expose action.fcurves."""
    if hasattr(action, "layers") and action.layers:
        out = []
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out += list(bag.fcurves)
        return out
    return list(action.fcurves)


def bake(rig, name):
    sc = bpy.context.scene
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.nla.bake(frame_start=sc.frame_start, frame_end=sc.frame_end, only_selected=True, visual_keying=True,
                     clear_constraints=False, use_current_action=False, bake_types={"POSE"})
    bpy.ops.object.mode_set(mode="OBJECT")
    act = rig.animation_data.action
    act.name = name
    act.use_fake_user = True
    return act


def mute_constraints(rig, mute=True):
    for pb in rig.pose.bones:
        for c in pb.constraints:
            c.mute = mute


def body_points(near=None):
    dg = bpy.context.evaluated_depsgraph_get()
    body = bpy.data.objects["Body"].evaluated_get(dg)
    m = body.to_mesh()
    pts = [body.matrix_world @ v.co for v in m.vertices]
    body.to_mesh_clear()
    return pts


def measure(rig, clip, props):
    sc = bpy.context.scene
    out = {}
    # feet planted: max drift of each ankle from the first frame
    feet = {}
    for f in range(sc.frame_start, sc.frame_end + 1):
        sc.frame_set(f)
        for b in ("LeftFoot", "RightFoot"):
            feet.setdefault(b, []).append((rig.matrix_world @ rig.pose.bones[b].head).copy())
    if clip.get("feet_planted", True):
        out["foot_drift_mm"] = round(max(max((p - ps[0]).length for p in ps) for ps in feet.values()) * 1000, 1)
    if "seated_frames" in clip and "seat" in props:
        seat = props["seat"]
        top = max((seat.matrix_world @ v.co).z for v in seat.data.vertices)
        lo_x, hi_x = min((seat.matrix_world @ v.co).x for v in seat.data.vertices), max((seat.matrix_world @ v.co).x for v in seat.data.vertices)
        lo_y, hi_y = min((seat.matrix_world @ v.co).y for v in seat.data.vertices), max((seat.matrix_world @ v.co).y for v in seat.data.vertices)
        gaps = []
        for f in clip["seated_frames"]:
            sc.frame_set(f)
            over = [p.z for p in body_points() if lo_x < p.x < hi_x and lo_y < p.y < hi_y and p.z < top + 0.25]
            gaps.append(min(over) - top if over else None)
        out["seat_gap_mm"] = [round(g * 1000, 1) if g is not None else None for g in gaps]
    if "contact_frame" in clip and "switch" in props:
        sc.frame_set(clip["contact_frame"])
        tip = rig.matrix_world @ rig.pose.bones[clip.get("contact_bone", "RightHand")].tail
        sw = props["switch"]
        centre = sum((sw.matrix_world @ v.co for v in sw.data.vertices), Vector()) / len(sw.data.vertices)
        out["hand_to_switch_mm"] = round((tip - centre).length * 1000, 1)
    return out


def export_fbx(rig, action, path):
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    for c in rig.children:
        c.select_set(True)
    rig.animation_data.action = action
    sc = bpy.context.scene
    sc.name = action.name          # the FBX take is named after the scene, so name it after the clip
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"ARMATURE", "MESH"},
                             axis_forward="-Z", axis_up="Y", apply_scale_options="FBX_SCALE_UNITS",
                             add_leaf_bones=False, use_armature_deform_only=True, bake_anim=True,
                             bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_simplify_factor=0.0, bake_anim_force_startend_keying=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--clips", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])
    spec = json.loads(a.clips.read_text())
    a.out_dir.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    sc.render.fps = spec.get("fps", 30)
    rig = bpy.data.objects["Armature"]
    props = build_props(spec.get("props", {}))
    ctrl = setup_controls(rig)
    fix_pole_angles(rig, ctrl)
    rest = {k: tuple(t.location) for k, (t, _) in ctrl.items()}
    rest.update({f"{k}_quat": ctrl[k][0].rotation_quaternion.copy() for k in ("hand_L", "hand_R")})
    report = {"rest_targets": {k: [round(x, 3) for x in v] for k, v in rest.items() if not k.endswith("quat")}}
    for clip in spec["clips"]:
        name = clip["name"]
        props_visible = set(clip.get("props", []))
        for pname, obj in props.items():
            obj.hide_render = pname not in props_visible
        if "book" in props_visible:
            book = props["book"]
            book.parent = rig
            book.parent_type = "BONE"
            book.parent_bone = clip.get("book_bone", "LeftHand")
            book.location = Vector(clip.get("book_offset", [0.0, 0.08, 0.0]))
            book.rotation_euler = Euler([math.radians(x) for x in clip.get("book_rot", [0, 0, 0])])
        # auto-correct seated height: key, measure the seat gap, shift the seated hips by the gap, re-key (twice)
        for attempt in range(3):
            mute_constraints(rig, False)
            key_clip(rig, ctrl, clip, rest)
            m = measure(rig, clip, props) if "seated_frames" in clip else {}
            gaps = [g for g in m.get("seat_gap_mm", []) if g is not None]
            if not gaps or abs(sum(gaps) / len(gaps)) < 4 or attempt == 2:
                break
            shift = sum(gaps) / len(gaps) / 1000.0
            for pose in clip["keys"]:
                if pose.get("seated"):
                    pose["hips"] = [pose["hips"][0], pose["hips"][1], pose["hips"][2] - shift]
        act = bake(rig, name)
        act["props"] = ",".join(sorted(props_visible))            # renderers show only this clip's props
        mute_constraints(rig, True)
        for pair in ctrl.values():
            for o in pair:
                o.animation_data_clear()
        meas = measure(rig, clip, props)
        export_fbx(rig, act, a.out_dir / f"{name}.fbx")
        report[name] = {"frames": [sc.frame_start, sc.frame_end], "keys": len(clip["keys"]), "measurements": meas}
        print(name, json.dumps(meas))
    bpy.ops.wm.save_as_mainfile(filepath=str((a.out_dir / "clips.blend").resolve()))
    (a.out_dir / "report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
