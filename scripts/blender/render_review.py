"""Render review images of a character (or the whole scene): turnaround views and/or chosen frames, auto-framed.

Blender 5.2.2:
  blender -b scene.blend --python-exit-code 1 -P scripts/blender/render_review.py -- \
    --out-dir out/review --views front,side,three_quarter [--frames 1,12,24] [--size 640x800] [--engine EEVEE]
    [--sequence] [--focus Body]

--sequence renders every frame of the scene range from the first view (for turning into a video with ffmpeg).
Adds a ground plane, soft key/fill/rim lights and a neutral background in a throwaway copy; never saves the input.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

VIEWS = {"front": 0, "three_quarter": 35, "side": 90, "back": 180, "three_quarter_back": 145}


def bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        e = o.evaluated_get(dg)
        m = e.to_mesh()
        pts += [e.matrix_world @ v.co for v in m.vertices]
        e.to_mesh_clear()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def setup_stage(engine, size):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE" if engine.upper().startswith("EEVEE") else ("CYCLES" if engine.upper() == "CYCLES" else "BLENDER_WORKBENCH")
    w, h = (int(x) for x in size.split("x"))
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("ReviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.82, 0.80, 0.76, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    sc.world = world
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "ReviewFloor"
    mat = bpy.data.materials.new("ReviewFloor")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.62, 0.58, 0.52, 1)
    floor.data.materials.append(mat)
    for name, rot, energy, size_ in (("Key", (math.radians(50), 0, math.radians(-35)), 3.0, 4.0),
                                     ("Fill", (math.radians(65), 0, math.radians(60)), 1.0, 6.0),
                                     ("Rim", (math.radians(60), 0, math.radians(170)), 1.5, 3.0)):
        light = bpy.data.lights.new(name, "SUN")
        light.energy = energy
        light.angle = math.radians(size_ * 4)
        o = bpy.data.objects.new(name, light)
        o.rotation_euler = rot
        sc.collection.objects.link(o)


def camera_for(view_deg, lo, hi, aspect):
    centre = (lo + hi) / 2
    height = max(hi.z - lo.z, 0.5)
    width = max(hi.x - lo.x, hi.y - lo.y, 0.5)
    cam_data = bpy.data.cameras.new("ReviewCam")
    cam_data.lens = 60
    cam = bpy.data.objects.new("ReviewCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    fov = 2 * math.atan(cam_data.sensor_width / 2 / cam_data.lens)
    span = max(height * 1.15, width * 1.3 / aspect) if aspect < 1 else max(height * 1.15 * aspect, width * 1.3)
    dist = span / (2 * math.tan(fov / 2)) / (1 if aspect >= 1 else aspect) + width * 0.5
    a = math.radians(view_deg)
    # character faces -Y; view 0 = from the front
    cam.location = centre + Vector((math.sin(a) * dist, -math.cos(a) * dist, height * 0.12))
    direction = centre + Vector((0, 0, -height * 0.02)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return cam


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--views", default="front,three_quarter,side")
    ap.add_argument("--frames", default="")
    ap.add_argument("--size", default="640x800")
    ap.add_argument("--engine", default="EEVEE")
    ap.add_argument("--sequence", action="store_true")
    ap.add_argument("--focus", default="", help="comma-separated object names to frame (default: all meshes)")
    ap.add_argument("--action", default="", help="armature action to play (sets the scene range to it)")
    ap.add_argument("--rig", default="Armature")
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])
    a.out_dir.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    if a.action:
        rig = bpy.data.objects[a.rig]
        act = bpy.data.actions[a.action]
        rig.animation_data_create().action = act
        sc.frame_start, sc.frame_end = int(act.frame_range[0]), int(act.frame_range[1])
        shown = set(filter(None, str(act.get("props", "")).split(",")))
        names = {"seat": ("Seat", "SeatBack", "Cube"), "switch": ("Switch", "SwitchWall"), "book": ("Book",)}
        for key, prefixes in names.items():
            for o in sc.objects:
                if o.type == "MESH" and o.name.startswith(prefixes) and o.name not in ("Body",):
                    o.hide_render = key not in shown
    focus = [bpy.data.objects[n] for n in a.focus.split(",") if n] or [o for o in sc.objects if o.type == "MESH"]
    frames = [int(f) for f in a.frames.split(",") if f] or [sc.frame_current]
    # frame over all requested frames so the camera doesn't jump
    los, his = [], []
    for f in (range(sc.frame_start, sc.frame_end + 1, 4) if a.sequence else frames):
        sc.frame_set(f)
        lo, hi = bounds(focus)
        los.append(lo)
        his.append(hi)
    lo = Vector((min(v.x for v in los), min(v.y for v in los), 0.0))
    hi = Vector((max(v.x for v in his), max(v.y for v in his), max(v.z for v in his)))
    setup_stage(a.engine, a.size)
    w, h = (int(x) for x in a.size.split("x"))
    for view in a.views.split(","):
        cam = camera_for(VIEWS[view], lo, hi, w / h)
        sc.camera = cam
        if a.sequence:
            sc.render.filepath = str((a.out_dir / f"{view}_").resolve())
            bpy.ops.render.render(animation=True)
            break
        for f in frames:
            sc.frame_set(f)
            sc.render.filepath = str((a.out_dir / f"{a.action + '_' if a.action else ''}{view}_f{f:03d}.png").resolve())
            bpy.ops.render.render(write_still=True)
    print("rendered to", a.out_dir)


if __name__ == "__main__":
    main()
