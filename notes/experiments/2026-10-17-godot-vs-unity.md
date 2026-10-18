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

## Second pass: a real export, engine IK, navigation and colliders

**Method.**
- **One Blender export for both engines:** a room of about 400 rigid blocks and two characters (52 blocks on 21 and 15 bones), as glTF for Godot and as FBX for Unity, with toybox's verified settings.
- **Primitives travel with the blocks:** each block's primitive (shape, size, centre, rotation) goes as glTF extras or FBX custom properties.
- **Nothing of the project's own was ported.** Each engine got a few lines of script per check:
  - **Godot:** run headless with `--fixed-fps 60` for timings, and in real time for navigation.
  - **Unity:** a `-batchmode -nographics` player with a fixed timestep.

| | Godot 4.7.2 (glTF) | Unity 6.6 (FBX) |
|---|---|---|
| Import: blocks and metadata | all blocks; extras kept as node metadata | all blocks; custom properties kept (as `Vector4` and strings) |
| Import: orthographic camera | stays orthographic | arrives **perspective** |
| Import: materials | match Blender | **darker and over-saturated** |
| Rigid binding | every block on exactly one bone | the same |
| Turning a bone moves its blocks | matches Blender | matches (skinned vertices equal bone × bind pose exactly) |
| Colliders built from the primitives vs mesh bounds | worst 0.54 mm | worst 0.54 mm |
| Built-in two-bone IK onto a target | `TwoBoneIK3D`, ~10 lines, wrist within 2.5 mm | Animation Rigging `TwoBoneIKConstraint` (built in), ~13 lines, wrist within 2.5 mm |
| Navmesh bake (2.5 cm cells) | 27 ms (50 ms in real time) | 6.4 ms |
| Rebake after an obstacle slides 0.25 m | 30 ms async (54 ms in real time) | 7 ms async; carving also available |
| Two agents swap places, real time | both arrive; touch with up to 3 mm overlap | both arrive; about 1 mm apart; the same every run |
| The same, simulation faster than real time | **one agent never arrives (3 of 3 runs); 2.7 cm overlap** | identical to real time |
| Building colliders from the primitives | ~325 shapes in 3 ms | ~325 shapes in 14 ms |
| Overlap queries, uncapped | 0.4–0.8 µs a query | 0.36 µs a query |
| Turnaround per check | 0.6 s | ~8 s (5 s player build + 2.7 s run) |

**Learnings.**
- **On the core jobs the engines are equal and add no error:** binding, bones moving their blocks, collider fit and IK accuracy matched to the millimetre.
- **Import fidelity favours glTF into Godot.** Unity's FBX lost the orthographic camera, and colours came out darker and over-saturated, which looks like sRGB values read as linear **(unverified)**. Unity's glTF importer (glTFast) wasn't tested.
- **Engine IK solves to the wrist bone, not the grip.** If contact is defined at a grip point further along the hand, offset the IK target by it (here 7.6 cm).
- **Unity's navigation is faster and deterministic by default.** Godot's agents got stuck when the simulation ran faster than real time and an obstacle moved. The third pass found the cause and two fixes (below): with synchronous navigation, Godot is deterministic at any speed too.
- **Neither engine's avoidance keeps a clear gap** between agents: Godot's touch, Unity's stay about 1 mm apart. Pad agent radii, or check contact separately.
- **"Nothing goes into anything" as engine queries is cheap:** about 0.02–0.04 ms a frame for two 40-block characters against a room, in either engine.
- **Measure tiny timings uncapped.** Under real-time pacing, the same Godot query loop measured 7–8 µs a query instead of under 1 µs: the CPU idles between frames.
- **Agree on what counts as floor.** A thin rug made characters' feet "overlap" in both engines until each collider builder applied the same rule, by height: anything whose top is at most 3 cm counts as floor. Ship the rule (its threshold) with the export, not a name list.
- **Script errors don't end the process** in either engine, so an agent's runs need a timeout. macOS has no `timeout` command; this works:

      perl -e 'alarm shift; exec @ARGV' <seconds> <command…>

Engine-specific gotchas are in [tools/godot.md](../tools/godot.md) and [tools/unity.md](../tools/unity.md).

## Follow-ups

- **Godot with a release export template, and Godot .NET:** frame time and kernel speed. → [backlog](../backlog.md).
- **Unity with glTFast instead of FBX:** does it fix the camera and colours? → [backlog](../backlog.md).
- **Crowds:** more than two agents, and agents of different sizes squeezing past furniture. → [backlog](../backlog.md).

## Third pass: Godot navigation faster than real time

**Method.** The same two agents swap places while an obstacle (a chair) slides 0.25 m, routed four ways:
- **async:** Godot's navmesh, rebaked on a thread when the chair stops (the second pass)
- **norebake:** never rebaked
- **sync:** rebaked on the main thread, then every agent routes again
- **grid:** a walk map of the project's own: clear raster points per body size from physics shape queries, rebuilt when the chair stops, routed with `AStarGrid2D`; Godot's avoidance still separates the agents

Each runs twice fast-forwarded (headless `--fixed-fps 60`: 75–1200× real time) and twice in real time, with Godot's default threaded navigation and with synchronous navigation (set through an `override.cfg`).

| Way | Threaded (default), fast | Threaded, real time | Synchronous, fast and real time |
|---|---|---|---|
| async | an agent never arrives; 27 mm overlap | arrive, times vary | fast: an agent never arrives; real time: arrive |
| norebake | an agent never arrives | an agent never arrives, or nobody moves | an agent never arrives |
| sync | 2.53 / 3.22 s | 2.52–2.53 / 3.22 s | **2.52 / 3.22 s, every run** |
| grid | 2.83 / 3.05 s | 2.83–2.88 / 3.05–3.10 s | **2.83 / 3.05 s, every run** |

A rebuild after the obstacle moves takes about 25 ms for the navmesh and 2 ms for the grid. Agents ended between 3 mm overlapping and 0.2 mm apart.

**Learnings.**
- **The cause is Godot's navigation threading, not the rebake.** By default the navigation server updates maps and regions asynchronously, and computes avoidance on several threads, so results land in wall-clock time. A simulation running ahead of the clock routes and avoids with stale data. Never rebaking fails the same way: the obstacle moves into the agent's way and the map never learns of it.
- **For a simulation that fast-forwards or replays, make navigation synchronous.** Every run was identical at any speed with these settings in `project.godot`:

      navigation/world/map_use_async_iterations=false
      navigation/world/region_use_async_iterations=false
      navigation/avoidance/thread_model/avoidance_use_multiple_threads=false

  Then either rebake on the main thread and have agents route again when something moves, or route on a walk map of your own and use Godot only for avoidance.
- **A silent start-up race with threaded navigation.** A navmesh baked in the same frame as setting the map's cell size can leave the map empty, with no warning. Agents that ask for a route before the map has the mesh get an empty path, and don't ask again until the map changes; in some real-time runs nobody moved at all. Wait until the map answers a route query (`NavigationServer3D.map_get_path` not empty) before giving agents targets. Synchronous navigation is ready after one frame.
- **`NavigationAgent3D` computes avoidance only while it has a navigation target.** When steering by your own route, set `target_position` to the goal anyway.
- **`override.cfg` next to `project.godot` overrides project settings** for a test run without editing the project.
- **Confirm the Unity batch-capture cause:** SSAO, or something else. → [backlog](../backlog.md).
