# Godot vs Unity for agent-driven development: the loop, runtime on Metal, motion maths

- **Date:** 2026-10-17
- **Goal:** choose an engine for a small procedural isometric diorama, where an agent iterates in hundreds of short edit-and-look cycles and the characters' motion is computed (IK, procedural gaits, collision checks) from data rather than played from authored clips. Which engine makes that loop fast, runs it well on Metal, and runs our own per-frame maths fast enough?
- **Tools & versions:** Godot 4.7.2 stable (Homebrew cask, `ed1daf0bf`, run from the editor binary; export templates not installed); Unity 6000.6.5f1 with URP 17.6 (Mono release player); Python 3.12; Apple M4 Max, macOS 15.8.1. All measurements at 1280 × 720.

## What we did

The harness lives in the project that ran it; this log keeps the method and the generic findings.

- **The same scene, built in code in both engines:**
  - a 6 × 5 m room with 300 clutter blocks
  - six characters of 40 blocks in a bone-like hierarchy, animated every frame
  - a sun and six lamps (two with shadows), SSAO, glow, ACES tone mapping, MSAA 4× and an orthographic isometric camera
  - an interior wall that fades while it hides a character, with a raycast every frame
- **The same motion-maths kernel, written identically in Python, GDScript and C#.** Per character per frame: four two-bone reaches, a 40-part forward-kinematics pass and a 40 × 40 overlap check. Checksums agree across languages.
- **One timing script drives both engines from the shell.** It reports medians of 5 runs (3 for sequences); the agent-loop rows are wall time, start to exit.
- **One claim re-checked independently.** A headless Godot script run took 0.13–0.14 s here too:

      godot --headless --path <project> --script probe.gd       # probe.gd: extends SceneTree, computes, quit()

## What happened

### The agent loop (wall time)

| Loop | Godot | Unity |
|---|---|---|
| Run a script or method without the editor UI | **0.14 s** | 4.1 s |
| Edit that script, run it again | **0.14 s** (no compile) | 5.4 s (recompile, domain reload) |
| Run 5 unit tests | **0.14 s** (a plain script; no built-in runner) | 5.3 s (NUnit EditMode, built in) |
| A correctly rendered screenshot | **0.6 s** (a window opens briefly) | 12.7 s (9.3 s player build + 3.4 s run) |
| A screenshot from batch mode, no window | n/a (headless has no renderer) | 5.4 s, **rendered wrong** (see below) |
| Edit a runtime script, then screenshot | **0.6 s** | 12.7 s (rebuild the player) |
| 120-frame PNG sequence | 7.5 s (movie-maker mode, fixed timestep) | 7.7 s (batch editor; rendered wrong) |
| First (cold) player build | n/a (no export templates) | 55 s |

### Runtime on Metal (vsync off, 600 frames after 60 warm-up)

| | Godot (editor binary) | Unity (release Mono player) |
|---|---|---|
| Backend | Metal 3.2, Forward+ | Metal, URP Forward+ |
| Frame time, median | 1.97 ms | **0.58 ms** |
| Frame time, p95 / max | 4.5 / ~13 ms | **0.68 / 1.3 ms** |
| Per-frame script (240 parts animated, 6 raycasts) | 0.07–0.10 ms | **0.03 ms** |
| First frame, caches cleared | **0.72 s** | 3.3 s |
| First frame, warm | **0.30 s** | 2.2 s |

Both use under an eighth of a 60 fps frame (16.7 ms).

### The motion-maths kernel (µs per character per frame)

| Language | µs | vs Python | 6 characters per frame |
|---|---|---|---|
| Python 3.12 (plain floats) | 263 | 1× | 1.6 ms |
| GDScript (typed; engine `Vector3`/`Basis`) | 71 | 3.7× | 0.43 ms |
| C# (Unity player, Mono) | 17 | 15× | 0.10 ms |

**Disk:** Godot is a 349 MB app, and a project is just its text files. Unity is a 19 GB editor install; a nearly empty project's `Library/` is 1.4 GB, and the player is 76 MB.

## Learnings

- **For agent-driven work, the loop dominates: Godot's is 30–40× faster.** Every Unity batch invocation costs 4–5 s before any work, and each C# edit adds compile time and a domain reload. A trustworthy Unity screenshot after a code edit costs about 13 s, against 0.6 s in Godot. Over hundreds of edit-and-look cycles, this matters far more than frame time. → [tools/godot.md](../tools/godot.md), [tools/unity.md](../tools/unity.md)
- **Unity's batch-editor captures rendered this URP scene wrongly.** With both `SingleCameraRequest` and `Camera.Render()`, opaque surfaces came out dark and tinted: no sun, shifted colours. The transparent wall and the built player were correct. Turning off async shader compilation didn't help. SSAO in offscreen editor renders is the likely cause **(unverified)**. Until that's solved, the only trustworthy Unity frames came from a built player. → corrected in [tools/unity.md](../tools/unity.md), which had recorded `SingleCameraRequest` as the fix for wrong colours in an earlier, simpler scene.
- **Godot needs a window to render.** `--headless` has no renderer, so screenshots and movie-maker sequences open a window for a fraction of a second. Unity can render windowless (when it renders right).
- **Unity's runtime is faster and steadier:** about 3× lower median frame time and far fewer spikes. Caveats:
  - Godot ran from the editor binary, not a release export, so the gap may narrow.
  - Godot's GPU timer reads 0 on Metal, so its frame time couldn't be split into CPU and GPU.
  - The scenes match in content, not in every quality setting.

  Both are far inside budget for a scene this size, so for a small diorama runtime speed doesn't decide it.
- **Godot starts faster:** 0.3 s to the first frame warm (Unity 2.2 s), and 0.7 s cold (Unity 3.3 s).
- **Language speed:**
  - C# is about 4× GDScript, and GDScript about 4× plain Python.
  - Six characters' worth of this kernel is 0.43 ms a frame in GDScript. Real solvers do more (reach searches, overlap against a room), so budget several times that.
  - Godot can also run C# (the .NET build) or native code (GDExtension) for hot paths, so GDScript isn't a ceiling.
- **Dithered fades:** one material flag in Godot (`TRANSPARENCY_ALPHA_HASH`). URP Lit has no dither, so it needs Shader Graph or a custom shader; alpha blending was used instead.
- **Setup and scripting:**
  - **Godot:** needed no setup step; scenes and projects are a few text files an agent can write directly.
  - **Unity:** needed an editor script to create materials, the scene and the player settings, because materials made only at runtime risk having their shader variants stripped from a build. It has a built-in test runner (NUnit); Godot needs GUT or gdUnit4, or plain scripts that exit nonzero.

## Follow-ups

- **A second pass on an exported scene:** the same Blender export (glTF for Godot, FBX for Unity) of a room and characters built from primitive blocks, with each block's primitive recorded as glTF extras or FBX custom properties. Measure:
  - import fidelity
  - each engine's built-in two-bone IK
  - navmesh with a moving obstacle, and two agents avoiding each other
  - primitive colliders generated from the blocks, with a timed overlap query each frame

  → [backlog](../backlog.md).
- **Godot with a release export template, and Godot .NET:** frame time and kernel speed. → [backlog](../backlog.md).
- **Confirm the Unity batch-capture cause:** SSAO, or something else. → [backlog](../backlog.md).
