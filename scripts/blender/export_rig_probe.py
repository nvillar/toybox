"""Export a selected rig and a one-second diagnostic bone animation to FBX.

Blender 5.2.2:
  blender -b source.blend --python-exit-code 1 -P scripts/blender/export_rig_probe.py -- \
    --rig "CharacterRig" --bone "forearm.L" --witness-mesh "Sleeve" --out-dir out/rig-probe

Normalizes the rig's object transform in a disposable process, preserves its
rest pose, and exports only the character. Never overwrites the input .blend.
This is an export diagnostic, not a walk cycle or production-rig conversion.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def unity_vector(value):
    return {"x": value[0], "y": value[2], "z": value[1]}


def bounds(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        evaluated.to_mesh_clear()
    return (
        Vector(tuple(min(p[i] for p in points) for i in range(3))),
        Vector(tuple(max(p[i] for p in points) for i in range(3))),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rig", required=True)
    parser.add_argument("--bone", required=True)
    parser.add_argument("--witness-mesh", required=True,
                        help="Skinned mesh on the animated bone whose bounds centre must move")
    parser.add_argument("--stationary-mesh", action="append", default=[],
                        help="Mesh that must stay fixed during the diagnostic; repeatable")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source = Path(bpy.data.filepath)
    if not source.is_file():
        parser.error("open a saved .blend first")
    output = args.out_dir.resolve()
    if output == source.parent:
        parser.error("use a separate output directory")
    output.mkdir(parents=True, exist_ok=True)
    rig = bpy.data.objects.get(args.rig)
    if rig is None or rig.type != "ARMATURE":
        parser.error(f"armature not found: {args.rig}")
    if args.bone not in rig.pose.bones:
        parser.error(f"bone not found: {args.bone}")
    bone = rig.pose.bones[args.bone]
    if not bone.children:
        parser.error("choose a bone with a child to measure tip displacement")
    tip_name = bone.children[0].name
    children = list(rig.children_recursive)
    unsupported = [o.name for o in children if o.type not in {"MESH", "CURVE", "EMPTY"}]
    if unsupported:
        parser.error(f"unsupported character children: {unsupported}")
    keep = {rig, *children}
    for obj in list(bpy.data.objects):
        if obj not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)
    rig.name = "CharacterRig"
    rig.location = (0, 0, 0)
    rig.rotation_euler = (0, 0, 0)
    rig.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    for obj in children:
        if obj.type == "CURVE":
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.convert(target="MESH")
    meshes = [o for o in rig.children_recursive if o.type == "MESH"]
    skinned = [o for o in meshes if any(m.type == "ARMATURE" and m.object == rig for m in o.modifiers)]
    witness = bpy.data.objects.get(args.witness_mesh)
    if witness not in skinned or witness.vertex_groups.get(args.bone) is None:
        parser.error("witness must be a skinned mesh with a vertex group for the animated bone")
    rigid = [o.name for o in meshes if o not in skinned]
    if rigid:
        print(f"NOTE: {len(rigid)} decorative meshes have no armature modifier; retaining them as rigid geometry.", flush=True)
    rig.animation_data_clear()
    for pose_bone in rig.pose.bones:
        pose_bone.matrix_basis.identity()
    bone.rotation_mode = "XYZ"
    for frame, angle in ((1, 0), (13, .55), (25, 0)):
        bone.rotation_euler = (angle, 0, 0)
        bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone.name)
    rig.animation_data.action.name = "HandoffProbe"
    scene = bpy.context.scene
    # A single baked FBX take uses the scene name, not the active action name.
    scene.name = "HandoffProbe"
    scene.frame_start, scene.frame_end = 1, 25
    scene.render.fps = 24
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    samples = []
    stationary = []
    for name in args.stationary_mesh:
        obj = bpy.data.objects.get(name)
        if obj not in meshes:
            parser.error(f"stationary mesh not found in rig: {name}")
        stationary.append(obj)
    stationary_centers = []
    for frame in (1, 13, 25):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        low, high = bounds([witness])
        samples.append({
            "time": (frame - 1) / 24,
            "tipPosition": unity_vector(rig.matrix_world @ rig.pose.bones[tip_name].head),
            "witnessCenter": unity_vector((low + high) / 2),
        })
        stationary_centers.append([unity_vector(sum(bounds([obj]), Vector()) / 2)
                                   for obj in stationary])
    for index, obj in enumerate(stationary):
        baseline = Vector(tuple(stationary_centers[0][index].values()))
        for sample in stationary_centers[1:]:
            error = (Vector(tuple(sample[index].values())) - baseline).length
            if error > .00001:
                raise RuntimeError(f"stationary mesh {obj.name} moved {error} m; inspect skin weights")
    displacement = (Vector(tuple(samples[1]["tipPosition"].values())) -
                    Vector(tuple(samples[0]["tipPosition"].values()))).length
    if displacement < .02:
        raise RuntimeError(f"diagnostic animation moved the tip only {displacement} metres")
    witness_displacement = (Vector(tuple(samples[1]["witnessCenter"].values())) -
                            Vector(tuple(samples[0]["witnessCenter"].values()))).length
    if witness_displacement < .02:
        raise RuntimeError(f"witness centre moved only {witness_displacement} m; choose a mesh away from the joint")
    scene.frame_set(1)
    low, high = bounds(meshes)
    mesh_bounds = []
    for obj in meshes:
        mesh_low, mesh_high = bounds([obj])
        mesh_bounds.append({
            "name": obj.name,
            "center": unity_vector((mesh_low + mesh_high) / 2),
            "size": {"x": mesh_high.x-mesh_low.x, "y": mesh_high.z-mesh_low.z,
                     "z": mesh_high.y-mesh_low.y},
        })
    expected = {
        "clipName": "HandoffProbe",
        "boneName": args.bone,
        "tipBoneName": tip_name,
        "witnessMeshName": witness.name,
        "boneCount": len(rig.data.bones),
        "boneNames": [b.name for b in rig.data.bones],
        "meshCount": len(meshes),
        "skinnedMeshCount": len(skinned),
        "rigidMeshNames": rigid,
        "duration": 1.0,
        "frameRate": 24,
        "boundsCenter": unity_vector((low + high) / 2),
        "boundsSize": {"x": high.x-low.x, "y": high.z-low.z, "z": high.y-low.y},
        "meshes": mesh_bounds,
        "samples": samples,
        "stationaryMeshNames": [obj.name for obj in stationary],
        "stationaryCenters": stationary_centers[0],
    }
    for name, loc in (("ProbeOrigin", (0,0,0)), ("ProbeRight", (1,0,0)),
                      ("ProbeForward", (0,-1,0)), ("ProbeUp", (0,0,1))):
        obj = bpy.data.objects.new(name, None)
        scene.collection.objects.link(obj)
        obj.parent = rig
        obj.location = loc
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    for obj in rig.children_recursive:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    fbx = output / "rig_probe.fbx"
    bpy.ops.export_scene.fbx(
        filepath=str(fbx), use_selection=True, object_types={"ARMATURE","MESH","EMPTY"},
        global_scale=1, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z", axis_up="Y", bake_space_transform=False,
        add_leaf_bones=False, use_armature_deform_only=True,
        use_mesh_modifiers=True, mesh_smooth_type="FACE",
        bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_use_all_bones=True, bake_anim_force_startend_keying=True,
        bake_anim_step=1, bake_anim_simplify_factor=0, path_mode="AUTO",
    )
    (output / "rig_probe.expected.json").write_text(json.dumps(expected, indent=2) + "\n")
    metadata = {
        "capability": "rig.export.diagnostic", "versions": {"blender": bpy.app.version_string},
        "source_scene": source.name, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "fbx_sha256": hashlib.sha256(fbx.read_bytes()).hexdigest(),
        "expected_sha256": hashlib.sha256((output / "rig_probe.expected.json").read_bytes()).hexdigest(),
        "exporter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "license": scene.get("asset_license", "Not declared; review source rights"),
        "script": "scripts/blender/export_rig_probe.py",
        "bone": args.bone, "witness_mesh": args.witness_mesh,
        "stationary_meshes": args.stationary_mesh,
        "duration_s": 1, "note": "Diagnostic bone motion, not locomotion.",
        "export": {"axis_forward":"-Z","axis_up":"Y","apply_scale_options":"FBX_SCALE_UNITS",
                   "add_leaf_bones":False,"bake_space_transform":False,"animation_simplify":0},
    }
    (output / "rig_probe.fbx.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("RIG_PROBE_EXPORTED", json.dumps({"path":str(fbx),"meshes":len(meshes),
          "skinned_meshes":len(skinned),"bones":len(rig.data.bones),
          "height_m":high.z-low.z,"tip_displacement_m":displacement}), flush=True)


if __name__ == "__main__":
    main()
