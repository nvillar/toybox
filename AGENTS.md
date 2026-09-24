# Agent guide

**toybox** is a knowledge engine for generating media with agents, from images to full games ([README](README.md)). You are both a user and a maintainer of it. Use what is here, add what you learn, and fix what you find to be wrong.

## Before you start

1. Read `README.md`, then the notes for your task: `notes/patterns/`, the relevant `notes/tools/*.md`, and `notes/pipeline.md` for game work.
2. Check `notes/backlog.md` for related open questions.
3. Check the platform (`notes/platforms.md`) and tool versions (`blender --version`, `unity --version`, `uv tool list`, `ollama --version`, …). If a version differs from a note's `versions`, treat that note as possibly stale.

## Contribute what you learn

Knowledge flows **experiment → tool note / pattern → script**.

- **Experiment, then write.** Run a small, disposable test rather than trusting memory or docs. Log it in `notes/experiments/YYYY-MM-DD-slug.md` ([template](notes/experiments/_template.md)) with exact commands and versions, and add it to the index.
- **Distil.** Fold reusable facts into the relevant `notes/tools/<tool>.md`. When a sequence of steps reliably produces a kind of media, write or extend a pattern in `notes/patterns/`. Link back to the experiments that prove it.
- **Promote helpers.** Scripts that worked and will be reused go in `scripts/`: parameterised, no user-specific paths, a docstring with usage and tested version, and a line in `scripts/README.md`.
- **Fit in, don't sprawl.** Extend an existing note before creating a new one. Follow the existing structure, names and conventions. Propose a new convention only when the old one fails, and then update this guide.
- **Park what you can't resolve** in `notes/backlog.md`.

## Keep it true

Stale or conflicting knowledge is worse than none. When you find a discrepancy (a command that fails, a version that moved on, two notes that disagree, a claim you can disprove):

1. **Verify** with a quick run where you can.
2. **Fix it in place.** Correct the note and update its `last_verified` and `versions`. Don't append a contradiction alongside the old text.
3. **Prune.** Delete superseded recipes, duplicated content and dead links. Merge notes that overlap. Git history keeps the past.
4. **Mark what you can't verify.** Set `status: stale` or tag the claim **(unverified)**, and add a backlog item.
5. **Record the correction** in your experiment log (or a one-line entry in `notes/experiments/README.md`) so others know what changed and why.

Experiment logs are the historical record. Don't rewrite their findings; if a later result overturns one, add a "Superseded by …" line to it.

## Note conventions

Tool notes and patterns start with front matter:

```yaml
---
status: seed | partial | verified | stale
last_verified: YYYY-MM-DD
versions: { blender: 5.2.2 }   # versions the verified content was tested against
---
```

- `seed`: written from docs or prior knowledge; nothing run yet.
- `partial`: some recipes verified.
- `verified`: the core recipes have been run successfully at `versions`.
- `stale`: known or suspected to be out of date.

Tag individual untested claims **(unverified)**. Keep notes concise and operational (*how to do X*, *what breaks*, *what to use instead*) and link to official docs rather than copying them. Keep the status table in `README.md` in sync.

## Working rules

- **Shell first.** Drive tools through their CLI and scripts. MCP servers are optional, not assumed.
- **Install for the CLI.** On macOS prefer Homebrew (e.g. `brew install --cask blender`) or `uv tool install`, so commands land on `PATH`.
- **Native acceleration behind stable interfaces.** Call the capability wrappers in `scripts/gen/`, which choose a backend per platform (MLX on Apple Silicon; CUDA/TensorRT or ROCm elsewhere). Add backends without changing the interface ([platforms](notes/platforms.md)). Preferred on Apple Silicon: MFLUX (images), Stable Audio 3 MLX (SFX/music), Ollama or oMLX (LLMs).
- **Licences matter.** Default to models that allow commercial use (e.g. FLUX.2 Klein 4B, Apache-2.0). Clearly flag non-commercial ones and record licences in provenance.
- **Keep artefacts out.** Generated or bulky output goes in `out/` and third-party checkouts in `sandbox/tools/` (both git-ignored). Real projects and their assets live in separate private repos ([asset storage](notes/tools/asset-storage.md)).
- **No secrets.** Reference API keys by environment variable *name* only.
- **Don't commit or push** unless the user asks.
