"""Render a saved Blender scene with an explicit camera and compute device.

Blender 5.2.2 LTS:
  blender -b scene.blend --python-exit-code 1 -P scripts/blender/render_scene.py -- \
    --out out/preview.png --camera "Camera" --width 1600 --height 1200 \
    --samples 64 --device METAL

Writes a PNG and a render-provenance sidecar without changing the saved scene.
METAL and CPU are supported selections; METAL is verified on this Mac.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--camera", help="Exact camera object name; otherwise use the scene camera")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--device", choices=("METAL", "CPU"), default="METAL")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if min(args.width, args.height, args.samples) < 1:
        parser.error("width, height and samples must be positive")
    if not bpy.data.filepath:
        parser.error("open a saved .blend file before running this script")
    scene = bpy.context.scene
    if args.camera:
        camera = scene.objects.get(args.camera)
        if camera is None or camera.type != "CAMERA":
            parser.error(f"camera not found: {args.camera}")
        scene.camera = camera
    if scene.camera is None:
        parser.error("scene has no active camera")
    scene.render.engine = "CYCLES"
    devices = []
    if args.device == "METAL":
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = args.device
        prefs.get_devices()
        for device in prefs.devices:
            device.use = device.type == args.device
            if device.use:
                devices.append(device.name)
        if not devices:
            parser.error("no Metal device found; explicitly choose --device CPU if appropriate")
        scene.cycles.device = "GPU"
    else:
        scene.cycles.device = "CPU"
        devices = ["CPU"]
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    args.out = args.out.resolve()
    if args.out.suffix.lower() != ".png":
        parser.error("--out must use the .png extension")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(args.out)
    started = time.monotonic()
    bpy.ops.render.render(write_still=True)
    source = Path(bpy.data.filepath)
    sidecar = {
        "capability": "scene.render",
        "backend": f"blender-cycles-{args.device.lower()}",
        "model": "Blender scene",
        "license": scene.get("asset_license", "Not declared; review scene and source-asset licences"),
        "prompt": scene.get("provenance", "Rendered from a saved Blender scene"),
        "versions": {"blender": bpy.app.version_string},
        "scene": source.name,
        "scene_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "params": {"camera": scene.camera.name, "width": args.width, "height": args.height,
                   "samples": args.samples, "devices": devices},
        "elapsed_s": round(time.monotonic() - started, 2),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    args.out.with_suffix(".png.json").write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"wrote {args.out} ({sidecar['elapsed_s']}s)", flush=True)


if __name__ == "__main__":
    main()
