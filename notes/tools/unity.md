---
status: seed
last_verified: 2026-09-23
versions: { unity-cli: 1.0.0-beta.8, editors: [6000.7.0b1, 6000.3.24f1, 6000.0.84f1, …] }
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

## Workflow (to verify)

1. Create a project from a template (`unity templates …`). (unverified)
2. `unity pipeline install --project-path <proj>` to add the Pipeline package.
3. `unity open <proj>`, then `unity status` to see the connected editor.
4. `unity command` (no args) to list available editor commands; look for a C# eval / execute command. (unverified)
5. Import assets by copying into `Assets/` and triggering a refresh via a command. (unverified)
6. `unity test <proj>` and `unity build <proj>` for the feedback loop and output.

## Gotchas

- Unity projects generate large `Library/`, `Temp/`, `Logs/`, `obj/` folders — keep projects under `sandbox/` or ensure they're git-ignored.
- Many editors are installed; pin the version per project and record it.

## To explore

- Exact C# eval capability of the Pipeline package and its limits.
- Headless screenshot / frame capture for visual feedback.
- GLB import (Unity needs a glTF importer package, e.g. glTFast). (unverified)
- Whether `unity skill install` gives useful guidance for this agent.
