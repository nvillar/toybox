"""Flatten a static scene and bake Generated-coordinate colour/normal materials.

Blender 5.2.2: blender -b scene.blend --python-exit-code 1 -P this.py -- \
  --out-dir out/static-scene --exclude-prefix Character --exclude-prefix Studio
Optional --planar-material NAME keeps coplanar mirror surfaces separate.
Supports one Principled material per object, constant surface factors and
Generated-coordinate procedural textures. Does not transfer rigs or lighting.
"""
import argparse
import hashlib
import json
import math
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unity(vector):
    return [float(vector.x), float(vector.z), float(vector.y)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--exclude-prefix", action="append", default=[])
    parser.add_argument("--planar-material", action="append", default=[])
    parser.add_argument("--texture-size", type=int, default=2048)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source = Path(bpy.data.filepath)
    if not source.is_file():
        raise RuntimeError("Open a saved source .blend first")
    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("Choose a new or empty output directory")
    started = time.monotonic()
    scene = bpy.context.scene
    if abs(scene.unit_settings.scale_length - 1) > 1e-6:
        raise RuntimeError("Use metre-scale source coordinates before this export")
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == "METAL"
    if not any(device.use for device in prefs.devices):
        raise RuntimeError("This verified bake requires Metal")
    scene.cycles.device = "GPU"
    scene.render.bake.margin = 8
    scene.render.bake.use_clear = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    originals = list(scene.objects)
    collection = bpy.data.collections.new("Static export")
    scene.collection.children.link(collection)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    materials, records, groups, planes = {}, {}, defaultdict(list), {}
    object_records = []

    def material_copy(original):
        if original.name in materials:
            return materials[original.name]
        material = original.copy()
        material.name = re.sub(r"[^A-Za-z0-9_]", "_", original.name)
        bsdf = next((n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            raise RuntimeError("Unsupported surface: " + original.name)
        target = next((n for n in material.node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
        if target is None or len(target.inputs["Surface"].links) != 1 or target.inputs["Surface"].links[0].from_node != bsdf:
            raise RuntimeError("Expected a direct Principled surface: " + original.name)
        for name in ("Roughness", "Metallic", "Transmission Weight", "Emission Strength", "Emission Color"):
            if bsdf.inputs[name].is_linked:
                raise RuntimeError("Bake does not support linked surface factor: " + name)
        record = {
            "name": material.name, "source": original.name,
            "baseColorLinear": list(bsdf.inputs["Base Color"].default_value),
            "roughness": bsdf.inputs["Roughness"].default_value,
            "metallic": bsdf.inputs["Metallic"].default_value,
            "transmission": bsdf.inputs["Transmission Weight"].default_value,
            "emissionLinear": list(bsdf.inputs["Emission Color"].default_value),
            "emissionStrength": bsdf.inputs["Emission Strength"].default_value,
            "bakeColor": bsdf.inputs["Base Color"].is_linked,
            "bakeNormal": bsdf.inputs["Normal"].is_linked,
        }
        attribute = material.node_tree.nodes.new("ShaderNodeAttribute")
        attribute.attribute_name = "BakeGenerated"
        links = material.node_tree.links
        for node in list(material.node_tree.nodes):
            if node.type == "TEX_COORD":
                for socket in node.outputs:
                    if socket.is_linked and socket.name != "Generated":
                        raise RuntimeError("Only Generated texture coordinates are supported: " + original.name)
                for link in list(node.outputs["Generated"].links):
                    links.new(attribute.outputs["Vector"], link.to_socket)
            elif node.type in {"TEX_NOISE", "TEX_WAVE", "TEX_VORONOI"} and not node.inputs["Vector"].is_linked:
                links.new(attribute.outputs["Vector"], node.inputs["Vector"])
        materials[original.name], records[material.name] = material, record
        return material

    for original in originals:
        if original.type not in {"MESH", "CURVE", "FONT"}:
            continue
        label = original.users_collection[0].name
        if any(label.startswith(prefix) for prefix in args.exclude_prefix):
            continue
        if len(original.material_slots) != 1 or original.material_slots[0].material is None:
            raise RuntimeError("Expected exactly one material: " + original.name)
        original_material = original.material_slots[0].material
        material = material_copy(original_material)
        mesh = bpy.data.meshes.new_from_object(original.evaluated_get(depsgraph),
                                               preserve_all_data_layers=True, depsgraph=depsgraph)
        bounds = [Vector(corner) for corner in original.bound_box]
        low = Vector([min(p[i] for p in bounds) for i in range(3)])
        high = Vector([max(p[i] for p in bounds) for i in range(3)])
        attr = mesh.attributes.new("BakeGenerated", "FLOAT_VECTOR", "POINT")
        for vertex in mesh.vertices:
            attr.data[vertex.index].vector = tuple(
                (vertex.co[i] - low[i]) / (high[i] - low[i]) if high[i] - low[i] > 1e-8 else 0
                for i in range(3))
        mesh.transform(original.matrix_world)
        mesh.materials.clear()
        mesh.materials.append(material)
        mesh.update()
        obj = bpy.data.objects.new(original.name + "_static", mesh)
        collection.objects.link(obj)
        key = (label, material.name)
        if original_material.name in args.planar_material:
            normal = mesh.polygons[0].normal.normalized()
            point = mesh.vertices[mesh.polygons[0].vertices[0]].co
            plane = tuple(round(v, 4) for v in normal) + (round(normal.dot(point), 4),)
            key += plane
            planes[key] = {"point": unity(point), "normal": unity(normal)}
        groups[key].append(obj)
        world = [original.matrix_world @ corner for corner in bounds]
        object_records.append({"name": original.name, "collection": label,
                               "min": unity(Vector([min(p[i] for p in world) for i in range(3)])),
                               "max": unity(Vector([max(p[i] for p in world) for i in range(3)]))})
    for original in originals:
        bpy.data.objects.remove(original, do_unlink=True)
    scene.world.use_nodes = True
    exported = []
    mesh_records = []
    for index, (key, objects) in enumerate(groups.items()):
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        if len(objects) > 1:
            bpy.ops.object.join()
        obj = bpy.context.object
        obj.name = "static_%02d_%s" % (index, key[1])
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        degenerate = [face for face in bm.faces if face.calc_area() <= 1e-12]
        bmesh.ops.delete(bm, geom=degenerate, context="FACES")
        bm.to_mesh(obj.data)
        bm.free()
        material = obj.data.materials[0]
        record = records[material.name]
        obj.data.materials.clear()
        obj.data.materials.append(material)
        if record["bakeColor"] or record["bakeNormal"]:
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.002)
            bpy.ops.object.mode_set(mode="OBJECT")
            bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            target = next(n for n in material.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
            for channel, bake_type in (("color", "EMIT"), ("normal", "NORMAL")):
                if not record["bake" + channel.capitalize()]:
                    continue
                image = bpy.data.images.new(obj.name + "_" + channel, args.texture_size, args.texture_size, alpha=True)
                image.colorspace_settings.name = "sRGB" if channel == "color" else "Non-Color"
                node = material.node_tree.nodes.new("ShaderNodeTexImage")
                node.image = image
                material.node_tree.nodes.active = node
                emission = None
                if channel == "color":
                    emission = material.node_tree.nodes.new("ShaderNodeEmission")
                    socket = bsdf.inputs["Base Color"]
                    material.node_tree.links.new(socket.links[0].from_socket, emission.inputs["Color"])
                    material.node_tree.links.new(emission.outputs[0], target.inputs["Surface"])
                bpy.ops.object.bake(type=bake_type)
                path = output / (image.name + ".png")
                image.filepath_raw, image.file_format = str(path), "PNG"
                image.save()
                obj[channel + "_texture"] = path.name
                material.node_tree.nodes.remove(node)
                if emission is not None:
                    material.node_tree.nodes.remove(emission)
                    material.node_tree.links.new(bsdf.outputs["BSDF"], target.inputs["Surface"])
                bpy.data.images.remove(image)
        mesh_records.append({
            "name": obj.name, "material": material.name, "collection": key[0],
            "sourceObjects": len(objects), "vertices": len(obj.data.vertices),
            "triangles": sum(len(p.vertices)-2 for p in obj.data.polygons),
            "removedDegenerateTriangles": len(degenerate),
            "colorTexture": obj.get("color_texture", ""), "normalTexture": obj.get("normal_texture", ""),
            "mirror": key in planes, "plane": planes.get(key),
        })
        exported.append(obj)
        print("STATIC_GROUP", obj.name, mesh_records[-1]["triangles"], flush=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in exported:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = exported[0]
    fbx = output / "environment.fbx"
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={"MESH"},
                            axis_forward="-Z", axis_up="Y", apply_unit_scale=True,
                            apply_scale_options="FBX_SCALE_UNITS", bake_space_transform=False,
                            use_mesh_modifiers=True, use_tspace=True, bake_anim=False, path_mode="STRIP")
    result = {"blender": bpy.app.version_string, "sourceSha256": sha(source),
              "exporterSha256": sha(Path(__file__).resolve()), "fbxSha256": sha(fbx),
              "textureSize": args.texture_size, "sourceObjects": len(object_records),
              "materials": list(records.values()), "meshes": mesh_records, "objects": object_records,
              "seconds": time.monotonic()-started,
              "files": {path.name: sha(path) for path in sorted(output.iterdir()) if path.is_file()}}
    (output / "environment.json").write_text(json.dumps(result, indent=2)+"\n")
    print("STATIC_EXPORT", len(exported), "meshes", result["seconds"], "seconds", flush=True)


if __name__ == "__main__":
    main()
