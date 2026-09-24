// Copy to Assets/Editor in a disposable built-in-renderer Unity project.
// Unity 6000.6.2f1: <editor> -batchmode -quit -projectPath <project>
//   -executeMethod RigImportProbe.Run
//   -probeModel Assets/Probe/rig_probe.fbx
//   -probeExpected Assets/Probe/rig_probe.expected.json -probeOut <absolute-directory>
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

public static class RigImportProbe
{
    [Serializable] public class Sample
    {
        public float time;
        public Vector3 tipPosition;
        public Vector3 witnessCenter;
    }

    [Serializable] public class Expected
    {
        public string clipName, boneName, tipBoneName, witnessMeshName;
        public int boneCount, meshCount, skinnedMeshCount;
        public string[] boneNames, rigidMeshNames, stationaryMeshNames;
        public Vector3[] stationaryCenters;
        public float duration, frameRate;
        public Vector3 boundsCenter, boundsSize;
        public Sample[] samples;
        public MeshMeasurement[] meshes;
    }

    [Serializable] public class MeshMeasurement
    {
        public string name;
        public Vector3 center, size;
    }

    [Serializable] public class Report
    {
        public bool passed;
        public string unityVersion, model, modelSha256, expectedSha256, clip, avatarType;
        public int meshCount, skinnedMeshCount, boneCount;
        public float duration, frameRate, maxTipError, maxWitnessError, loopTipError;
        public Vector3 boundsCenter, boundsSize, upMarker, forwardMarker, rightMarker;
        public List<Sample> samples = new List<Sample>();
        public List<MeshMeasurement> meshes = new List<MeshMeasurement>();
        public List<string> screenshotSha256 = new List<string>();
        public List<string> checks = new List<string>();
        public List<string> failures = new List<string>();
    }

    static string Arg(string key)
    {
        var args = Environment.GetCommandLineArgs();
        var index = Array.IndexOf(args, key);
        if (index < 0 || index + 1 >= args.Length)
            throw new ArgumentException("Missing argument " + key);
        return args[index + 1];
    }

    static string FileHash(string path)
    {
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant();
    }

    static void Check(bool condition, string message, Report report)
    {
        if (!condition) throw new InvalidOperationException(message);
        report.checks.Add(message);
    }

    static Transform Find(GameObject instance, string name)
    {
        var matches = instance.GetComponentsInChildren<Transform>(true).Where(t => t.name == name).ToArray();
        if (matches.Length != 1) throw new InvalidOperationException("Expected one transform named " + name + ", got " + matches.Length);
        return matches[0];
    }

    static Bounds MeshBounds(Renderer renderer)
    {
        var baked = new Mesh();
        var skin = renderer as SkinnedMeshRenderer;
        Mesh mesh;
        if (skin != null)
        {
            // Include renderer scale before transforming the baked vertices to world space.
            skin.BakeMesh(baked, true);
            mesh = baked;
        }
        else mesh = renderer.GetComponent<MeshFilter>().sharedMesh;
        var vertices = mesh.vertices;
        if (vertices.Length == 0) throw new InvalidOperationException("Empty mesh: " + renderer.name);
        var bounds = new Bounds(renderer.transform.TransformPoint(vertices[0]), Vector3.zero);
        foreach (var vertex in vertices) bounds.Encapsulate(renderer.transform.TransformPoint(vertex));
        UnityEngine.Object.DestroyImmediate(baked);
        return bounds;
    }

    static Bounds AllBounds(Renderer[] renderers)
    {
        var bounds = MeshBounds(renderers[0]);
        foreach (var renderer in renderers.Skip(1)) bounds.Encapsulate(MeshBounds(renderer));
        return bounds;
    }

    static Camera MakeStudio(Bounds bounds)
    {
        var ground = GameObject.CreatePrimitive(PrimitiveType.Cube);
        ground.name = "Diagnostic floor";
        ground.transform.position = new Vector3(0, bounds.min.y - .026f, 0);
        ground.transform.localScale = new Vector3(5, .05f, 5);
        const string materialPath = "Assets/Probe/DiagnosticFloor.mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
        if (material == null)
        {
            material = new Material(Shader.Find("Standard"));
            AssetDatabase.CreateAsset(material, materialPath);
        }
        material.color = new Color(.22f, .26f, .25f);
        ground.GetComponent<Renderer>().sharedMaterial = material;
        RenderSettings.ambientLight = new Color(.42f, .42f, .42f);
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
        var key = new GameObject("Diagnostic key").AddComponent<Light>();
        key.type = LightType.Directional;
        key.intensity = 1.3f;
        key.transform.rotation = Quaternion.Euler(40, -30, 0);
        var fill = new GameObject("Diagnostic fill").AddComponent<Light>();
        fill.type = LightType.Directional;
        fill.intensity = .55f;
        fill.transform.rotation = Quaternion.Euler(30, 140, 0);
        var camera = new GameObject("Diagnostic camera").AddComponent<Camera>();
        camera.transform.position = bounds.center + new Vector3(-2.5f, 1.2f, -3.5f);
        camera.transform.LookAt(bounds.center);
        camera.orthographic = true;
        camera.orthographicSize = bounds.size.y * .7f;
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(.10f, .13f, .12f);
        camera.nearClipPlane = .01f;
        camera.farClipPlane = 30;
        return camera;
    }

    static void Screenshot(Camera camera, string path)
    {
        var target = new RenderTexture(1000, 1000, 24, RenderTextureFormat.ARGB32);
        var previous = RenderTexture.active;
        var texture = new Texture2D(1000, 1000, TextureFormat.RGB24, false);
        try
        {
            camera.targetTexture = target;
            camera.Render();
            RenderTexture.active = target;
            texture.ReadPixels(new Rect(0, 0, 1000, 1000), 0, 0);
            texture.Apply();
            File.WriteAllBytes(path, texture.EncodeToPNG());
        }
        finally
        {
            camera.targetTexture = null;
            RenderTexture.active = previous;
            target.Release();
            UnityEngine.Object.DestroyImmediate(target);
            UnityEngine.Object.DestroyImmediate(texture);
        }
    }

    public static void Run()
    {
        string output = Path.GetFullPath(Arg("-probeOut"));
        Directory.CreateDirectory(output);
        var report = new Report { unityVersion = Application.unityVersion };
        PlayableGraph graph = default;
        int exitCode = 1;
        try
        {
            var modelPath = Arg("-probeModel");
            var expected = JsonUtility.FromJson<Expected>(File.ReadAllText(Arg("-probeExpected")));
            report.model = modelPath;
            report.modelSha256 = FileHash(modelPath);
            report.expectedSha256 = FileHash(Arg("-probeExpected"));
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var importer = AssetImporter.GetAtPath(modelPath) as ModelImporter;
            if (importer == null) throw new InvalidOperationException("No model importer for " + modelPath);
            importer.animationType = ModelImporterAnimationType.Generic;
            importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            importer.importAnimation = true;
            importer.animationCompression = ModelImporterAnimationCompression.Off;
            importer.optimizeGameObjects = false;
            importer.preserveHierarchy = true;
            importer.globalScale = 1;
            importer.useFileScale = true;
            importer.bakeAxisConversion = true;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            var clipSettings = importer.defaultClipAnimations;
            Check(clipSettings.Length == 1, "Exactly one source animation take", report);
            clipSettings[0].loopTime = true;
            importer.clipAnimations = clipSettings;
            importer.SaveAndReimport();
            var clips = AssetDatabase.LoadAllAssetsAtPath(modelPath).OfType<AnimationClip>()
                .Where(c => !c.name.StartsWith("__preview__")).ToArray();
            Check(clips.Length == 1, "Exactly one imported animation clip", report);
            var clip = clips[0];
            report.clip = clip.name;
            report.duration = clip.length;
            report.frameRate = clip.frameRate;
            Check(clip.name.Contains(expected.clipName), "Diagnostic clip name preserved", report);
            Check(Mathf.Abs(clip.length - expected.duration) < .02f, "Clip duration preserved within 20 ms", report);
            Check(Mathf.Abs(clip.frameRate - expected.frameRate) < .01f, "Animation frame rate preserved", report);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            Check(prefab != null, "Model prefab exists", report);
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var instance = UnityEngine.Object.Instantiate(prefab);
            instance.name = "Imported character";
            instance.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            instance.transform.localScale = Vector3.one;
            var animator = instance.GetComponent<Animator>();
            Check(animator != null && animator.avatar != null && animator.avatar.isValid, "Valid imported avatar", report);
            Check(!animator.avatar.isHuman, "Generic rig, not an assumed Humanoid mapping", report);
            report.avatarType = "Generic";
            animator.applyRootMotion = false;
            animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            foreach (var name in expected.boneNames) Find(instance, name);
            report.boneCount = expected.boneNames.Length;
            Check(report.boneCount == expected.boneCount, "All expected bone transforms preserved", report);
            var renderers = instance.GetComponentsInChildren<Renderer>();
            var skins = instance.GetComponentsInChildren<SkinnedMeshRenderer>();
            report.meshCount = renderers.Length;
            report.skinnedMeshCount = skins.Length;
            Check(renderers.Length == expected.meshCount, "All mesh objects imported", report);
            Check(skins.Length == expected.skinnedMeshCount, "All skinned mesh objects imported", report);
            foreach (var skin in skins)
            {
                skin.updateWhenOffscreen = true;
                // Several manual camera renders occur without advancing the editor frame.
                skin.forceMatrixRecalculationPerRender = true;
                Check(skin.bones.Length > 0 && skin.bones.All(b => b != null), "Skin bones bound: " + skin.name, report);
                Check(skin.sharedMesh.bindposes.Length == skin.bones.Length, "Bind-pose count matches: " + skin.name, report);
            }
            var origin = Find(instance, "ProbeOrigin").position;
            report.upMarker = Find(instance, "ProbeUp").position - origin;
            report.forwardMarker = Find(instance, "ProbeForward").position - origin;
            report.rightMarker = Find(instance, "ProbeRight").position - origin;
            Check(Vector3.Distance(report.upMarker, Vector3.up) < .001f, "One metre Blender +Z becomes Unity +Y", report);
            Check(Vector3.Distance(report.forwardMarker, Vector3.back) < .001f, "Blender -Y faces Unity -Z (raw FBX import)", report);
            Check(Vector3.Distance(report.rightMarker, Vector3.right) < .001f, "Blender +X becomes Unity +X", report);
            graph = PlayableGraph.Create("Import animation verification");
            graph.SetTimeUpdateMode(DirectorUpdateMode.Manual);
            var playable = AnimationClipPlayable.Create(graph, clip);
            playable.SetApplyFootIK(false);
            var animationOutput = AnimationPlayableOutput.Create(graph, "Character", animator);
            animationOutput.SetSourcePlayable(playable);
            graph.Play();
            var witness = renderers.Single(r => r.name == expected.witnessMeshName);
            Camera camera = null;
            for (int i = 0; i < expected.samples.Length; i++)
            {
                var sample = expected.samples[i];
                playable.SetTime(sample.time);
                graph.Evaluate(0);
                var actual = new Sample {
                    time = sample.time, tipPosition = Find(instance, expected.tipBoneName).position,
                    witnessCenter = MeshBounds(witness).center
                };
                report.samples.Add(actual);
                report.maxTipError = Mathf.Max(report.maxTipError, Vector3.Distance(actual.tipPosition, sample.tipPosition));
                report.maxWitnessError = Mathf.Max(report.maxWitnessError, Vector3.Distance(actual.witnessCenter, sample.witnessCenter));
                for (int j = 0; j < expected.stationaryMeshNames.Length; j++)
                {
                    var fixedMesh = renderers.Single(r => r.name == expected.stationaryMeshNames[j]);
                    Check(Vector3.Distance(MeshBounds(fixedMesh).center, expected.stationaryCenters[j]) < .001f,
                        "Stationary mesh stays fixed: " + fixedMesh.name + " at " + sample.time, report);
                }
                if (i == 0)
                {
                    foreach (var renderer in renderers)
                    {
                        var measured = MeshBounds(renderer);
                        report.meshes.Add(new MeshMeasurement {
                            name = renderer.name, center = measured.center, size = measured.size
                        });
                    }
                    foreach (var measured in report.meshes)
                    {
                        var reference = expected.meshes.Single(m => m.name == measured.name);
                        Check(Vector3.Distance(measured.center, reference.center) < .01f &&
                            Vector3.Distance(measured.size, reference.size) < .01f,
                            "Rest mesh bounds agree within 1 cm: " + measured.name, report);
                    }
                    var bounds = AllBounds(renderers);
                    report.boundsCenter = bounds.center; report.boundsSize = bounds.size;
                    Check(Vector3.Distance(bounds.size, expected.boundsSize) < .01f, "Rest bounds size agrees with Blender within 1 cm", report);
                    Check(Vector3.Distance(bounds.center, expected.boundsCenter) < .01f, "Rest bounds centre agrees with Blender within 1 cm", report);
                    camera = MakeStudio(bounds);
                }
                var screenshot = Path.Combine(output, "unity_pose_" + i + ".png");
                Screenshot(camera, screenshot);
                report.screenshotSha256.Add(FileHash(screenshot));
            }
            Check(report.maxTipError < .01f, "Animated bone positions agree with Blender within 1 cm", report);
            Check(report.maxWitnessError < .01f, "Animated skinned-mesh bounds agree with Blender within 1 cm", report);
            Check(Vector3.Distance(report.samples[0].tipPosition, report.samples[1].tipPosition) > .02f,
                "Animator/Playables moves the diagnostic limb by more than 2 cm", report);
            Check(Vector3.Distance(report.samples[0].witnessCenter, report.samples[1].witnessCenter) > .02f,
                "Animator/Playables deforms the witness mesh by more than 2 cm", report);
            report.loopTipError = Vector3.Distance(report.samples[0].tipPosition, report.samples[2].tipPosition);
            Check(report.loopTipError < .001f, "Animation endpoints return within 1 mm", report);
            Check(report.screenshotSha256[0] != report.screenshotSha256[1],
                "Rendered diagnostic poses are visibly different", report);
            foreach (var renderer in renderers)
                Check(renderer.sharedMaterials.All(m => m != null && m.shader != null &&
                    m.shader.name != "Hidden/InternalErrorShader"), "Usable imported materials: " + renderer.name, report);
            const string controllerPath = "Assets/Probe/Diagnostic.controller";
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(controllerPath);
            if (controller == null)
                controller = AnimatorController.CreateAnimatorControllerAtPath(controllerPath);
            var stateMachine = controller.layers[0].stateMachine;
            foreach (var child in stateMachine.states) stateMachine.RemoveState(child.state);
            controller.AddMotion(clip);
            graph.Destroy();
            animator.runtimeAnimatorController = controller;
            AssetDatabase.SaveAssets();
            const string scenePath = "Assets/Probe/ImportProbe.unity";
            Check(EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), scenePath),
                "Diagnostic scene saved", report);
            EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);
            var restored = UnityEngine.Object.FindFirstObjectByType<Animator>();
            Check(restored != null && restored.avatar != null && restored.avatar.isValid &&
                restored.runtimeAnimatorController != null &&
                restored.runtimeAnimatorController.animationClips.Contains(clip),
                "Reopened scene preserves the avatar and controller clip", report);
            report.passed = true;
            exitCode = 0;
            Debug.Log("RIG_IMPORT_PROBE_PASSED");
        }
        catch (Exception error)
        {
            report.failures.Add(error.ToString());
            Debug.LogException(error);
        }
        finally
        {
            if (graph.IsValid()) graph.Destroy();
            File.WriteAllText(Path.Combine(output, "unity_report.json"), JsonUtility.ToJson(report, true));
            EditorApplication.Exit(exitCode);
        }
    }
}
