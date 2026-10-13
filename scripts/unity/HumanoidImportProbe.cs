// Import FBX characters as Unity Humanoid and report whether the avatar is valid, which bones mapped, and the clips.
//
// Unity 6000.6.5f1, direct editor batch mode (no Pipeline package needed):
//   cp scripts/unity/HumanoidImportProbe.cs <project>/Assets/Editor/
//   cp out/authoring-study/clips/*.fbx <project>/Assets/Probe/
//   "$UNITY_EDITOR" -batchmode -quit -projectPath <project> -executeMethod HumanoidImportProbe.Run \
//       -probeDir Assets/Probe -probeOut <abs path>/humanoid_report.json -logFile <abs path>/humanoid.log
//
// Exits nonzero if any model fails to produce a valid human avatar.
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class HumanoidImportProbe
{
    static string Arg(string name, string fallback)
    {
        var args = System.Environment.GetCommandLineArgs();
        var i = System.Array.IndexOf(args, name);
        return i >= 0 && i + 1 < args.Length ? args[i + 1] : fallback;
    }

    public static void Run()
    {
        var dir = Arg("-probeDir", "Assets/Probe");
        var outPath = Arg("-probeOut", "humanoid_report.json");
        var report = new List<string>();
        var ok = true;
        foreach (var path in Directory.GetFiles(dir, "*.fbx").Select(p => p.Replace('\\', '/')))
        {
            var importer = (ModelImporter)AssetImporter.GetAtPath(path);
            importer.animationType = ModelImporterAnimationType.Human;
            importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            importer.resampleCurves = false;
            importer.animationCompression = ModelImporterAnimationCompression.Off;
            importer.SaveAndReimport();
            var assets = AssetDatabase.LoadAllAssetsAtPath(path);
            var avatar = assets.OfType<Avatar>().FirstOrDefault();
            var clips = assets.OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")).ToList();
            var mapped = importer.humanDescription.human?.Select(h => $"\"{h.humanName}\":\"{h.boneName}\"") ?? Enumerable.Empty<string>();
            var valid = avatar != null && avatar.isValid && avatar.isHuman;
            ok &= valid;
            report.Add("{" + $"\"file\":\"{Path.GetFileName(path)}\",\"avatarValid\":{(avatar != null && avatar.isValid).ToString().ToLower()}," +
                       $"\"isHuman\":{(avatar != null && avatar.isHuman).ToString().ToLower()},\"mappedBones\":{mapped.Count()}," +
                       $"\"clips\":[{string.Join(",", clips.Select(c => $"{{\"name\":\"{c.name}\",\"length\":{c.length:0.000},\"humanMotion\":{c.humanMotion.ToString().ToLower()}}}"))}]," +
                       $"\"mapping\":{{{string.Join(",", mapped)}}}" + "}");
            Debug.Log($"HumanoidImportProbe {path}: valid={valid} clips={clips.Count}");
        }
        File.WriteAllText(outPath, "[\n" + string.Join(",\n", report) + "\n]\n");
        EditorApplication.Exit(ok && report.Count > 0 ? 0 : 1);
    }
}
