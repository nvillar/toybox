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

## Import, IK, navigation, physics (verified 2026-10-17)

[Second pass](../experiments/2026-10-17-godot-vs-unity.md#second-pass-a-real-export-engine-ik-navigation-and-colliders):
- **glTF from Blender imports right with no work:**
  - skinned meshes, each bound to one bone as in Blender
  - an orthographic camera stays orthographic
  - colours match Blender's renders
  - Blender `(x, y, z)` becomes Godot `(x, z, -y)`
  - extras arrive as node metadata
- **`TwoBoneIK3D` does nothing, silently, without a pole node.** Its solved pose can only be read inside the skeleton's `skeleton_updated` signal. Its documentation is thin.
- **Navigation:**
  - a navmesh bake took 27–50 ms; a rebake after a moved obstacle runs async in wall-clock time (30–54 ms)
  - with the simulation faster than real time and an obstacle moving, one agent never arrived (3 of 3 runs); in real time it was fine
  - avoidance let agents touch, with up to 3 mm overlap in real time
- **Physics overlap queries:** 0.4–0.8 µs each uncapped, or 0.4 µs reusing query objects. Under real-time pacing they measure ~10× slower because the CPU idles between frames, so time them uncapped.
- **GDScript gotchas:** type inference on Variants, and lambdas capture locals by value.
- **A script error leaves the process running.** Wrap agent runs in a timeout; macOS has no `timeout`, so use `perl -e 'alarm shift; exec @ARGV' <seconds> <command…>`.

## To explore

- A release export template's frame time, and Godot .NET ([backlog](../backlog.md)).
- Navigation in a simulation running faster than real time with moving obstacles: is the async rebake the cause?
