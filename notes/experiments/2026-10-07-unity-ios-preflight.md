# Unity and iOS toolchain preflight on Sequoia

- **Date:** 2026-10-07
- **Goal:** Distinguish an installed desktop editor from an iOS-ready toolchain, and recheck the Blender hand-off before scaffolding a new project.
- **Tools & versions:** macOS 15.8.1 arm64; Blender 5.2.2 LTS; Unity Editor 6000.6.2f1 arm64; Hub 3.21.3; Unity CLI 1.0.0-beta.8; Apple Git 2.50.1; GitHub CLI 2.101.0; uv 0.10.3. Git LFS and full Xcode were unavailable in this environment.

## What we did

Read the existing Blender, Unity, storage, and platform notes. Inspected the actual executables and installed module directories; did not install software, change the selected developer directory, inspect signing credentials, or upgrade any project.

```sh
sw_vers
uname -m
blender --version
unity --version
uv --version
uv tool list
git --version
git lfs version
gh --version
xcode-select -p
xcodebuild -version
xcrun --sdk iphoneos --show-sdk-version

UNITY_ROOT=/Applications/Unity/Hub/Editor/6000.6.2f1
UNITY_EDITOR="$UNITY_ROOT/Unity.app/Contents/MacOS/Unity"
"$UNITY_EDITOR" -version
file "$UNITY_EDITOR"
ls "$UNITY_ROOT/PlaybackEngines"
ls "$UNITY_ROOT/Unity.app/Contents/Resources/PackageManager/ProjectTemplates"
```

Created a disposable project in ignored `out/`, using the editor directly:

```sh
mkdir -p out/unity/2026-10-07-preflight
"$UNITY_EDITOR" -batchmode -quit \
  -createProject "$PWD/out/unity/2026-10-07-preflight/ToolchainProbe" \
  -logFile "$PWD/out/unity/2026-10-07-preflight/create.log"
```

Saved the following disposable script as `out/unity/2026-10-07-preflight/export_probe.py`:

```python
import pathlib
import sys

import bpy

out = pathlib.Path(sys.argv[sys.argv.index("--") + 1]).resolve()
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 1.0
bpy.ops.mesh.primitive_cube_add(size=1)
obj = bpy.context.object
obj.name = "ScaleProbe"
obj.dimensions = (1, 2, 3)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.export_scene.fbx(
    filepath=str(out),
    use_selection=True,
    object_types={"MESH"},
    axis_forward="-Z",
    axis_up="Y",
    apply_scale_options="FBX_SCALE_UNITS",
    bake_space_transform=False,
    add_leaf_bones=False,
    bake_anim=False,
)
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "METAL"
prefs.get_devices()
devices = [device.name for device in prefs.devices if device.type == "METAL"]
assert devices, "No Metal device available"
assert out.stat().st_size > 0, "FBX export is empty"
print("PREFLIGHT Blender:", bpy.app.version_string, "Metal:", devices)
```

Saved this helper in the disposable project's `Assets/Editor/ToolchainProbe.cs`:

```csharp
using System;
using System.IO;
using UnityEditor;
using UnityEngine;

public static class ToolchainProbe
{
    [Serializable]
    private sealed class Report
    {
        public string editor;
        public string graphics;
        public string renderPipeline;
        public Vector3 importedSize;
        public bool macBuildSupport;
        public bool iosBuildSupport;
    }

    public static void Run()
    {
        const string path = "Assets/ScaleProbe.fbx";
        AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        var importer = AssetImporter.GetAtPath(path) as ModelImporter;
        if (importer == null)
            throw new InvalidOperationException("Missing FBX ModelImporter");
        importer.globalScale = 1;
        importer.useFileScale = true;
        importer.bakeAxisConversion = true;
        importer.SaveAndReimport();

        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        var instance = UnityEngine.Object.Instantiate(asset);
        var renderers = instance.GetComponentsInChildren<Renderer>();
        if (renderers.Length == 0)
            throw new InvalidOperationException("Imported FBX has no renderers");
        var bounds = renderers[0].bounds;
        foreach (var renderer in renderers)
            bounds.Encapsulate(renderer.bounds);
        if (Vector3.Distance(bounds.size, new Vector3(1, 3, 2)) > 0.001f)
            throw new InvalidOperationException("Incorrect imported dimensions: " + bounds.size);

        var pipeline = UnityEngine.Rendering.GraphicsSettings.defaultRenderPipeline;
        var report = new Report
        {
            editor = Application.unityVersion,
            graphics = SystemInfo.graphicsDeviceType.ToString(),
            renderPipeline = pipeline == null ? "Built-in" : pipeline.GetType().Name,
            importedSize = bounds.size,
            macBuildSupport = BuildPipeline.IsBuildTargetSupported(
                BuildTargetGroup.Standalone, BuildTarget.StandaloneOSX),
            iosBuildSupport = BuildPipeline.IsBuildTargetSupported(
                BuildTargetGroup.iOS, BuildTarget.iOS),
        };
        if (report.graphics != "Metal" || !report.macBuildSupport)
            throw new InvalidOperationException("Expected Metal and macOS build support");
        string json = JsonUtility.ToJson(report, true);
        File.WriteAllText(Path.Combine(Application.dataPath, "../preflight.json"), json);
        Debug.Log("PREFLIGHT " + json);
        UnityEngine.Object.DestroyImmediate(instance);
    }
}
```

Ran the export and import checks:

```sh
blender -b --factory-startup --python-exit-code 1 \
  -P out/unity/2026-10-07-preflight/export_probe.py \
  -- out/unity/2026-10-07-preflight/ToolchainProbe/Assets/ScaleProbe.fbx
"$UNITY_EDITOR" -batchmode -quit \
  -projectPath "$PWD/out/unity/2026-10-07-preflight/ToolchainProbe" \
  -executeMethod ToolchainProbe.Run \
  -logFile "$PWD/out/unity/2026-10-07-preflight/import.log"
uv run --no-project python -m json.tool \
  out/unity/2026-10-07-preflight/ToolchainProbe/preflight.json
```

Also inspected the bundled URP template's JSON manifests with Python `tarfile`, without extracting it into a production project. Consulted the official release API and Apple compatibility/submission pages, not just search-result summaries.

## What happened

- Editor project creation and scripted FBX import completed successfully. Blender reported the Apple M4 Max Metal device. Unity reported `Metal`, `Built-in`, imported dimensions `(1, 3, 2.000000238418579)`, `macBuildSupport: true`, and `iosBuildSupport: false`.
- The existing licence allowed local batch work. Logs also contained `Access token is unavailable; failed to update`; successful local execution is not evidence of cloud authentication. No new licence/login step was needed for this probe.
- `PlaybackEngines` is beside `Unity.app` in this Hub installation, not inside its `Contents`. It contained `MacStandaloneSupport` and `WebGLSupport`, not iOS support. The `ios` entry in `modules.json` described an available download, not an installed module; `selected` was false.
- Plain `-createProject` produced a Built-in project. A separate `com.unity.template.urp-blank-17.2.1.tgz` was installed. Its template version is **not** the URP package version: its manifest specified URP **17.6.0**, Input System **1.19.0**, Test Framework **1.8.0**, and uGUI **2.6.0**. These belong to the inspected editor; do not assume a different patch ships identical dependencies.
- Only Command Line Tools were selected; full Xcode and the iPhoneOS SDK were not found. Desktop editor success did not establish iOS readiness.
- `git lfs version` failed and Homebrew reported no Git LFS formula installed. The [September upload/restore experiment](2026-09-23-private-asset-library.md) remains valid historical evidence, not proof that LFS is installed today.
- The Unity release API listed **6000.6.4f1**, dated 2026-10-01, as `SUPPORTED` and **6000.3.25f1** as `LTS`. Neither was installed or tested in this experiment. Blender's official 5.2 directory listed **5.2.2** as the newest patch.

### Published iOS compatibility, not a completed build

[Apple's Xcode table](https://developer.apple.com/xcode/system-requirements/) lists **Xcode 26.3** with the **iOS 26.2 SDK** as compatible with macOS Sequoia **15.6** through its specified Tahoe range. Xcode **26.4.1** requires macOS **26.2**; Xcode **27** requires macOS **26.6** or later. Thus "install latest Xcode" is not a valid Sequoia setup recipe.

[Unity 6.6](https://docs.unity3d.com/6000.6/Documentation/Manual/ios-requirements-and-compatibility.html) documents Xcode 16 or later. Actual Unity/Xcode build compatibility, signing, and device behavior remain **(unverified)** here. Apple's [submission page](https://developer.apple.com/app-store/submitting/) announces an **iOS/iPadOS 27 SDK** minimum from **April 2027**. SDK requirements are distinct from an app's deployment minimum; recheck at distribution time.

Other sources: [Unity supported releases](https://services.api.unity.com/unity/editor/release/v1/releases?limit=8&version=6000.6), [LTS releases](https://services.api.unity.com/unity/editor/release/v1/releases?limit=5&stream=LTS), [Blender downloads](https://download.blender.org/release/Blender5.2/).

## Learnings

- Added preflight gates and the template/package distinction to [Unity](../tools/unity.md).
- Rechecked the Blender FBX scale contract; did not claim rendering, production asset fidelity, or URP/iOS validation.
- Updated [asset storage](../tools/asset-storage.md) to require a current LFS executable check instead of assuming historical installation persists.
- Updated the platform profile and status table. No project identity, private asset, or raw machine log is included.

## Follow-ups

- [Backlog](../backlog.md): explicit URP scaffold/render/clean-clone check; iOS export and signed physical-device build on a Sequoia-compatible Xcode; restore LFS before binary work.
- Keep the Unity CLI startup issue open: this experiment used the editor directly and did not diagnose the wrapper.
- Disposable project, scripts, FBX, and logs can be removed after recording the result; the minimal reproduction is above.
