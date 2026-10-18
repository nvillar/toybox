---
status: partial
last_verified: 2026-10-17
versions: { godot: 4.7.2.stable (Homebrew cask) }
---

# Godot

Role: a candidate engine for assembling, running and testing games. It's being compared with [Unity](unity.md) for agent-driven work ([experiment](../experiments/2026-10-17-godot-vs-unity.md)).

**Installation:** `brew install --cask godot` puts `godot` on `PATH` (`/opt/homebrew/bin/godot`; `godot --version` prints `4.7.2.stable.official.ed1daf0bf`). Export templates (about 1 GB) are a separate download and aren't installed yet, so release exports are unverified.

## Driving it from the shell (verified)

- **Run a script without the editor UI:** about 0.14 s from start to exit, including engine start-up. There's no compile step, so an edit-and-rerun costs the same.

      godot --headless --path <project> --script <file>.gd

  The script extends `SceneTree`, does its work in `_init()` and calls `quit()` (`quit(1)` to fail a check). A `project.godot` file must exist at `--path`; an empty one is enough for a probe.
- **Rendering needs a window.** `--headless` has no renderer. Screenshots and frame sequences open a window for a fraction of a second: about 0.6 s for a correct screenshot after an edit.
- **Frame sequences:** movie-maker mode renders PNGs at a fixed timestep. 120 frames at 1280 × 720 took 7.5 s.
- **Tests:** there's no built-in runner. Use plain scripts that print and exit nonzero on failure, or add GUT or gdUnit4 **(unverified here)**.
- **Projects are text files:** `project.godot`, `.tscn` scenes, `.gd` scripts. An agent can write them directly, with no editor-side setup step. The `.godot/` folder is the import cache; keep it out of version control.

## Runtime notes (Metal, verified)

- Forward+ on Metal 3.2. A small diorama (about 550 blocks, 7 lights, SSAO, glow, MSAA 4×) ran at 1.97 ms median per frame from the editor binary, with a warm first frame in 0.30 s.
- The GPU timer reads 0 on Metal, so CPU and GPU frame time can't be told apart there.
- GDScript, typed and using engine `Vector3`/`Basis`, ran a motion-maths kernel 3.7× faster than plain Python and about 4× slower than C# in a Unity player. For hot paths use the .NET build (C#) or GDExtension **(neither verified here)**.
- **Dithered transparency** (fading a wall that hides a character) is one material setting: `TRANSPARENCY_ALPHA_HASH`.

## To explore

- Import a Blender glTF with skinned meshes and custom properties (extras), and a release export template's frame time ([backlog](../backlog.md)).
- Built-in two-bone IK, NavigationServer with avoidance and moving obstacles, and physics overlap queries on primitive colliders.
