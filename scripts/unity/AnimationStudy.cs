// Unity 6000.6.2f1, built-in renderer. Copy this and RigImportProbe.cs to Assets/Editor.
// <editor> -batchmode -quit -projectPath <disposable-project>
//   -executeMethod AnimationStudy.Run -studyAssets Assets/Study -probeOut <absolute-directory>
// Expects idle/walk.fbx and matching .expected.json with per-sample bones, mesh bounds and feet.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

public static class AnimationStudy
{
    [Serializable] public class Foot
    {
        public string name;
        public bool planted;
        public Vector3 center;
        public float floor;
    }
    [Serializable] public class Sample
    {
        public float time;
        public Vector3[] bones;
        public RigImportProbe.MeshMeasurement[] meshes;
        public Foot[] feet;
    }
    [Serializable] public class Expected
    {
        public string clipName, fbxSha256;
        public string[] boneNames;
        public float duration, frameRate, speed;
        public int meshCount;
        public Sample[] samples;
    }
    [Serializable] public class Result
    {
        public string clip, modelSha256, expectedSha256;
        public int sampleCount, meshCount, boneCount;
        public float duration, speed, maxBoneError, maxMeshError, maxContactSlip, maxContactDrift, maxContactHeight;
        public string worstBone;
        public float worstBoneTime;
        public float minFloor = float.MaxValue;
        public float loopError;
        public float[] maxFootLift = new float[2];
        public List<string> frameHashes = new List<string>();
    }
    [Serializable] public class Report
    {
        public bool passed;
        public string unityVersion;
        public List<Result> clips = new List<Result>();
        public List<string> failures = new List<string>();
    }

    static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    static Material MaterialAsset(string folder, string name, Color color)
    {
        string path = folder + "/" + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (material == null)
        {
            material = new Material(Shader.Find("Standard"));
            AssetDatabase.CreateAsset(material, path);
        }
        material.color = color;
        material.SetFloat("_Glossiness", .18f);
        return material;
    }

    static Camera Studio(string folder)
    {
        var groundMat = MaterialAsset(folder, "StudioFloor", new Color(.26f, .32f, .28f));
        var tileMat = MaterialAsset(folder, "StudioTile", new Color(.32f, .38f, .33f));
        var ground = new GameObject("Half-metre checker floor");
        ground.name = "Ground plane";
        var vertices = new List<Vector3>();
        var triangles = new[] { new List<int>(), new List<int>() };
        for (int x = -4; x < 4; x++)
            for (int z = -4; z < 12; z++)
            {
                int start = vertices.Count;
                vertices.AddRange(new[] { new Vector3(x*.5f, 0, z*.5f), new Vector3(x*.5f, 0, (z+1)*.5f),
                    new Vector3((x+1)*.5f, 0, (z+1)*.5f), new Vector3((x+1)*.5f, 0, z*.5f) });
                triangles[(x+z+16)%2].AddRange(new[] { start, start+1, start+2, start, start+2, start+3 });
            }
        string meshPath = folder + "/StudioFloorMesh.asset";
        var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
        if (mesh == null)
        {
            mesh = new Mesh();
            AssetDatabase.CreateAsset(mesh, meshPath);
        }
        mesh.Clear();
        mesh.SetVertices(vertices);
        mesh.subMeshCount = 2;
        for (int i = 0; i < 2; i++) mesh.SetTriangles(triangles[i], i);
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        EditorUtility.SetDirty(mesh);
        ground.AddComponent<MeshFilter>().sharedMesh = mesh;
        var floorRenderer = ground.AddComponent<MeshRenderer>();
        floorRenderer.sharedMaterials = new[] { groundMat, tileMat };
        floorRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(.52f, .55f, .54f);
        QualitySettings.shadows = ShadowQuality.All;
        QualitySettings.shadowDistance = 30;
        var light = new GameObject("Key").AddComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 1.1f;
        light.shadows = LightShadows.Soft;
        light.shadowBias = .05f;
        light.shadowNormalBias = .2f;
        light.transform.rotation = Quaternion.Euler(40, -25, 0);
        var fill = new GameObject("Fill").AddComponent<Light>();
        fill.type = LightType.Directional;
        fill.intensity = .5f;
        fill.transform.rotation = Quaternion.Euler(25, 145, 0);
        var camera = new GameObject("Study camera").AddComponent<Camera>();
        camera.orthographic = true;
        camera.orthographicSize = 1.1f;
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(.10f, .14f, .12f);
        camera.nearClipPlane = .01f;
        camera.farClipPlane = 50;
        return camera;
    }

    static void FrameCamera(Camera camera, Vector3 position, bool side)
    {
        var target = position + Vector3.up*.85f;
        camera.transform.position = target + (side ? new Vector3(4, .15f, 0) : new Vector3(2.8f, 1.1f, 4));
        camera.transform.LookAt(target);
    }

    static void VerifyClip(string folder, string stem, string output, Report report)
    {
        var modelPath = folder + "/" + stem + ".fbx";
        var expectedPath = folder + "/" + stem + ".expected.json";
        var expected = JsonUtility.FromJson<Expected>(File.ReadAllText(expectedPath));
        var result = new Result {
            clip = expected.clipName, speed = expected.speed,
            modelSha256 = RigImportProbe.FileHash(modelPath),
            expectedSha256 = RigImportProbe.FileHash(expectedPath)
        };
        report.clips.Add(result);
        Require(result.modelSha256 == expected.fbxSha256, "Model hash differs from Blender measurements");
        Require(expected.samples.Length >= 3 && expected.samples[0].time == 0, "Missing sampled animation");
        var importer = AssetImporter.GetAtPath(modelPath) as ModelImporter;
        Require(importer != null, "Model importer missing");
        importer.animationType = ModelImporterAnimationType.Generic;
        importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
        importer.importAnimation = true;
        importer.animationCompression = ModelImporterAnimationCompression.Off;
        importer.resampleCurves = false;
        importer.optimizeGameObjects = false;
        importer.preserveHierarchy = true;
        importer.globalScale = 1;
        importer.useFileScale = true;
        importer.bakeAxisConversion = true;
        importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
        var settings = importer.defaultClipAnimations;
        Require(settings.Length == 1, "Expected a single named take per model");
        settings[0].loopTime = true;
        importer.clipAnimations = settings;
        importer.SaveAndReimport();
        var clip = AssetDatabase.LoadAllAssetsAtPath(modelPath).OfType<AnimationClip>()
            .Single(c => !c.name.StartsWith("__preview__"));
        Require(clip.name == expected.clipName && Mathf.Abs(clip.length-expected.duration) < .001f &&
            Mathf.Abs(clip.frameRate-expected.frameRate) < .001f, "Clip identity, duration or sample rate changed");
        result.duration = clip.length;
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var root = new GameObject("Locomotion root (+Z forward)");
        var model = UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(modelPath), root.transform);
        model.name = "Visual (-Z asset corrected to +Z)";
        model.transform.localRotation = Quaternion.Euler(0, 180, 0);
        var animator = model.GetComponent<Animator>();
        Require(animator != null && animator.avatar != null && animator.avatar.isValid && !animator.avatar.isHuman,
            "Expected valid Generic avatar");
        animator.applyRootMotion = false;
        animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
        var skins = model.GetComponentsInChildren<SkinnedMeshRenderer>();
        var renderers = model.GetComponentsInChildren<Renderer>();
        Require(skins.Length == expected.meshCount && skins.Length == renderers.Length,
            "Every mesh, including decorative geometry, must be skinned");
        foreach (var skin in skins)
        {
            skin.updateWhenOffscreen = true;
            skin.forceMatrixRecalculationPerRender = true;
            Require(skin.bones.All(b => b != null) && skin.bones.Length == skin.sharedMesh.bindposes.Length,
                "Invalid skin bones/bindposes: " + skin.name);
        }
        var transforms = expected.boneNames.Select(name => RigImportProbe.Find(model, name)).ToArray();
        var meshMap = renderers.ToDictionary(r => r.name);
        result.meshCount = renderers.Length;
        result.boneCount = transforms.Length;
        var previousContact = new Vector3?[2];
        var contactAnchor = new Vector3?[2];
        var firstBones = new Vector3[transforms.Length];
        var camera = Studio(folder);
        var frames = Path.Combine(output, stem);
        Directory.CreateDirectory(frames);
        var graph = PlayableGraph.Create("Locomotion verification");
        try
        {
            graph.SetTimeUpdateMode(DirectorUpdateMode.Manual);
            var playable = AnimationClipPlayable.Create(graph, clip);
            playable.SetApplyFootIK(false);
            var animationOutput = AnimationPlayableOutput.Create(graph, "Character", animator);
            animationOutput.SetSourcePlayable(playable);
            graph.Play();
            for (int i = 0; i < expected.samples.Length; i++)
            {
                var sample = expected.samples[i];
                root.transform.position = Vector3.forward * expected.speed * sample.time;
                playable.SetTime(sample.time);
                graph.Evaluate(0);
                for (int b = 0; b < transforms.Length; b++)
                {
                    var local = model.transform.InverseTransformPoint(transforms[b].position);
                    float error = Vector3.Distance(local, sample.bones[b]);
                    if (error > result.maxBoneError)
                    {
                        result.maxBoneError = error;
                        result.worstBone = expected.boneNames[b];
                        result.worstBoneTime = sample.time;
                    }
                    if (i == 0) firstBones[b] = local;
                    if (i == expected.samples.Length-1)
                        result.loopError = Mathf.Max(result.loopError, Vector3.Distance(firstBones[b], local));
                }
                var measured = meshMap.ToDictionary(pair => pair.Key, pair => RigImportProbe.MeshBounds(pair.Value));
                foreach (var reference in sample.meshes)
                {
                    var bounds = measured[reference.name];
                    result.maxMeshError = Mathf.Max(result.maxMeshError,
                        Vector3.Distance(model.transform.InverseTransformPoint(bounds.center), reference.center),
                        Vector3.Distance(bounds.size, reference.size));
                    result.minFloor = Mathf.Min(result.minFloor, bounds.min.y);
                }
                for (int f = 0; f < sample.feet.Length; f++)
                {
                    var foot = sample.feet[f];
                    var bounds = measured[foot.name];
                    result.maxFootLift[f] = Mathf.Max(result.maxFootLift[f], bounds.min.y);
                    if (foot.planted)
                    {
                        if (!contactAnchor[f].HasValue) contactAnchor[f] = bounds.center;
                        result.maxContactDrift = Mathf.Max(result.maxContactDrift,
                            Vector3.Distance(contactAnchor[f].Value, bounds.center));
                        result.maxContactHeight = Mathf.Max(result.maxContactHeight, Mathf.Abs(bounds.min.y));
                        if (previousContact[f].HasValue)
                            result.maxContactSlip = Mathf.Max(result.maxContactSlip,
                                Vector3.Distance(previousContact[f].Value, bounds.center));
                        previousContact[f] = bounds.center;
                    }
                    else { previousContact[f] = null; contactAnchor[f] = null; }
                }
                result.sampleCount++;
                if (i % 2 == 0 && i < expected.samples.Length-1)
                {
                    FrameCamera(camera, root.transform.position, false);
                    string path = Path.Combine(frames, "front_" + (i/2).ToString("D3") + ".png");
                    RigImportProbe.Screenshot(camera, path);
                    result.frameHashes.Add(RigImportProbe.FileHash(path));
                    FrameCamera(camera, root.transform.position, true);
                    RigImportProbe.Screenshot(camera, Path.Combine(frames, "side_" + (i/2).ToString("D3") + ".png"));
                }
            }
            Require(result.maxBoneError < .003f && result.maxMeshError < .005f,
                "Blender/Unity mismatch: bones=" + result.maxBoneError + ", meshes=" + result.maxMeshError);
            Require(result.minFloor > -.002f && result.maxContactHeight < .002f &&
                result.maxContactSlip < .003f && result.maxContactDrift < .003f && result.loopError < .001f,
                "Grounding/loop failure: floor=" + result.minFloor + ", contact=" + result.maxContactHeight +
                ", slip=" + result.maxContactSlip + ", drift=" + result.maxContactDrift + ", loop=" + result.loopError);
            Require(result.frameHashes.Distinct().Count() > result.frameHashes.Count/2, "Rendered animation is frozen");
            if (expected.speed > 0) Require(result.maxFootLift.All(h => h > .07f), "Both feet must clear the floor");
        }
        finally { graph.Destroy(); }
        var controllerPath = folder + "/" + stem + ".controller";
        var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(controllerPath);
        if (controller == null) controller = AnimatorController.CreateAnimatorControllerAtPath(controllerPath);
        var machine = controller.layers[0].stateMachine;
        foreach (var state in machine.states) machine.RemoveState(state.state);
        controller.AddMotion(clip);
        animator.runtimeAnimatorController = controller;
        root.transform.position = Vector3.zero;
        FrameCamera(camera, Vector3.zero, false);
        var playback = root.AddComponent<StudyLocomotion>();
        playback.speed = expected.speed;
        playback.duration = expected.duration;
        playback.previewCamera = camera;
        AssetDatabase.SaveAssets();
        string scenePath = folder + "/" + stem + ".unity";
        Require(EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), scenePath),
            "Scene save failed");
        EditorSceneManager.OpenScene(scenePath);
        var restored = UnityEngine.Object.FindFirstObjectByType<Animator>();
        Require(restored != null && restored.runtimeAnimatorController != null &&
            restored.runtimeAnimatorController.animationClips.Contains(clip), "Saved controller did not restore");
    }

    [Serializable] class PlaybackResult
    {
        public bool passed;
        public string unityVersion, error;
        public float seconds, maxCameraDrift, maxSpeedError, normalizedAnimationTime;
        public int updates, wraps;
    }
    static PlaybackResult playback;
    static Vector3 previousPosition, cameraOffset;
    static float previousTime;

    // Run without -quit: this exits after inspecting a real Play Mode loop and its preview wrap.
    public static void VerifyPlayback()
    {
        var folder = RigImportProbe.Arg("-studyAssets");
        EditorSceneManager.OpenScene(folder + "/walk.unity");
        SessionState.SetBool("toybox.motionPlayback", true);
        EditorApplication.EnterPlaymode();
    }

    [InitializeOnLoadMethod]
    static void ResumePlaybackCheck()
    {
        if (SessionState.GetBool("toybox.motionPlayback", false))
            EditorApplication.update += CheckPlayback;
    }

    static void CheckPlayback()
    {
        if (!EditorApplication.isPlaying) return;
        if (playback == null) playback = new PlaybackResult { unityVersion = Application.unityVersion };
        try
        {
            var driver = UnityEngine.Object.FindFirstObjectByType<StudyLocomotion>();
            Require(driver != null && driver.enabled && driver.previewCamera != null, "Missing active preview driver/camera");
            float time = Time.timeSinceLevelLoad;
            if (time <= previousTime) return;
            var position = driver.transform.position;
            var offset = driver.previewCamera.transform.position-position;
            if (playback.updates == 0) cameraOffset = offset;
            else
            {
                var displacement = position-previousPosition;
                if (displacement.z < -driver.speed*driver.duration*2) playback.wraps++;
                else playback.maxSpeedError = Mathf.Max(playback.maxSpeedError,
                    Mathf.Abs(displacement.z/(time-previousTime)-driver.speed));
                playback.maxCameraDrift = Mathf.Max(playback.maxCameraDrift, Vector3.Distance(offset, cameraOffset));
            }
            previousTime = time;
            previousPosition = position;
            playback.updates++;
            playback.seconds = time;
            if (time < driver.duration*4+.4f) return;
            var animator = driver.GetComponentInChildren<Animator>();
            playback.normalizedAnimationTime = animator.GetCurrentAnimatorStateInfo(0).normalizedTime;
            Require(playback.updates > 20 && playback.wraps == 1 && playback.maxSpeedError < .02f &&
                playback.maxCameraDrift < .002f && playback.normalizedAnimationTime > 4,
                "Play Mode speed, camera follow, loop wrap or Animator failed");
            playback.passed = true;
        }
        catch (Exception error) { playback.error = error.ToString(); Debug.LogException(error); }
        SessionState.SetBool("toybox.motionPlayback", false);
        EditorApplication.update -= CheckPlayback;
        var output = Path.GetFullPath(RigImportProbe.Arg("-probeOut"));
        Directory.CreateDirectory(output);
        File.WriteAllText(Path.Combine(output, "playback_report.json"), JsonUtility.ToJson(playback, true));
        EditorApplication.Exit(playback.passed ? 0 : 1);
    }

    public static void Run()
    {
        var output = Path.GetFullPath(RigImportProbe.Arg("-probeOut"));
        Directory.CreateDirectory(output);
        var report = new Report { unityVersion = Application.unityVersion };
        int exitCode = 1;
        try
        {
            string folder = RigImportProbe.Arg("-studyAssets");
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (string stem in new[] { "idle", "walk" }) VerifyClip(folder, stem, output, report);
            report.passed = true;
            exitCode = 0;
            Debug.Log("ANIMATION_STUDY_PASSED");
        }
        catch (Exception error)
        {
            report.failures.Add(error.ToString());
            Debug.LogException(error);
        }
        finally
        {
            File.WriteAllText(Path.Combine(output, "animation_report.json"), JsonUtility.ToJson(report, true));
            EditorApplication.Exit(exitCode);
        }
    }
}
