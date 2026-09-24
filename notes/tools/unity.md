---
status: partial
last_verified: 2026-09-24
versions: { unity-cli: 1.0.0-beta.8, unity-editor: 6000.6.2f1 }
---

# Unity

Role: assemble assets into a playable game, run it, test it, and build it.

## Driving it

The `unity` CLI (installed at `~/.unity/bin/unity`) wraps Hub/editor management and, together with the **Unity Pipeline** package installed into a project, lets the agent talk to a running editor.

Commands observed in `unity --help` (2026-09-23, 1.0.0-beta.8):

| Area | Commands |
|------|----------|
| Editors | `editors`, `install`, `install-modules`, `modules`, `releases` |
| Projects | `projects`, `templates`, `open`, `close`, `status` |
| Batch work | `run` (batch mode, forwards args), `build`, `test` (Edit/PlayMode, writes report) |
| Live editor | `pipeline install` (adds package to a project), `list` / `command` (execute registered editor commands), `job` (detached commands), `shell` (warm REPL) |
| Agents | `skill install <client>` (installs a Unity CLI agent skill), `mcp` |

Useful global flags: `--json`, `--non-interactive`, `--no-pager`, `--quiet`.

## Verified local batch workflow

The installed editor binary successfully created a project, imported FBX, ran a Generic rig through Animator/Playables, rendered three PNGs, and saved/reopened a scene. No Pipeline package or Unity Cloud project was needed. The existing local editor licence sufficed; no additional account authentication was needed for these commands.

```sh
# Use an editor actually installed on this machine, not merely listed by the CLI.
UNITY_EDITOR=/Applications/Unity/Hub/Editor/6000.6.2f1/Unity.app/Contents/MacOS/Unity
mkdir -p out/unity
"$UNITY_EDITOR" -batchmode -quit -createProject "$PWD/out/unity/RigImportProbe" \
  -logFile "$PWD/out/unity-create.log"
```

Copy a C# editor helper into `Assets/Editor/` and assets into `Assets/`, then use `-projectPath … -executeMethod Class.Method`. The rig helper performs an explicit synchronous import and exits nonzero on failure; see [the complete experiment](../experiments/2026-09-24-blender-unity-rig-handoff.md).

### Animation and image checks

- Built-in FBX import: Generic / Create From This Model, file units enabled, scale 1, axis conversion baked, hierarchy preserved, game-object optimization off, animation compression off. One explicitly looped diagnostic take at 24 fps; `Animator.applyRootMotion=false`.
- Use a manually evaluated `PlayableGraph` connected to the imported `Animator`, then measure bone positions and `SkinnedMeshRenderer.BakeMesh` vertices. This exercises the runtime animation path, not only `AnimationClip.SampleAnimation`.
- **Scaled skins:** in this setup use `BakeMesh(mesh, true)` before `renderer.transform.TransformPoint`. The default overload gave scaled meshes incorrectly shrunken measured bounds; it was a measurement error, not broken FBX geometry.
- **Repeated same-frame renders:** `forceMatrixRecalculationPerRender=true` plus `updateWhenOffscreen=true` refreshed skinned poses for `Camera.Render`. Without forced recalculation, CPU bone/mesh measurements changed but all screenshots were identical. Check the images too.
- Use a `RenderTexture` + `ReadPixels`/PNG for local screenshots. Do **not** pass `-nographics` for this path.
- Raw facing is Blender -Y → Unity -Z with the tested exporter. Correct at the gameplay prefab boundary if a future controller assumes +Z; do not silently rotate the diagnostic instance.
- Imported basic materials are not pink, but Blender procedural shader fidelity, real-time budgets, Humanoid retargeting and locomotion are not established by this probe.

## Live Pipeline workflow (unverified)

`unity pipeline install --project-path <proj>`, `unity open`, `unity status`, `unity command`, `unity test` and `unity build` remain **(unverified)** here. Command discovery is not an end-to-end run.

## Gotchas

- Unity projects generate large `Library/`, `Temp/`, `Logs/`, `obj/` folders — put disposable projects under ignored `out/`. Preserve `Assets/` including `.meta`, `Packages/` and `ProjectSettings/` for selected private archives.
- `unity editors` listed versions that could not actually be located. Only 6000.6.2f1 was verified usable; pin and record the actual editor.
- `unity projects new` failed with a missing parent directory/stale editor version, then stalled with the installed editor. `unity run --editor-path … --timeout 240` also stalled before creating an editor log. We stopped our wrappers and used the binary directly; the cause of the stalls is unresolved.
- The CLI's macOS `--editor-path` expects a `.app` bundle; direct shell execution uses its `Contents/MacOS/Unity` binary. These are different interfaces.
- Do not launch another editor against a project already open elsewhere, and do not stop unrelated editor processes.

## To explore

- Exact C# eval capability of the Pipeline package and its limits.
- Diagnose the CLI startup/authentication flow without requiring cloud services for local editor work.
- GLB import (Unity needs a glTF importer package, e.g. glTFast). (unverified)
- Whether `unity skill install` gives useful guidance for this agent.
