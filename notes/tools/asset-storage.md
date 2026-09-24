---
status: seed
last_verified: 2026-09-23
versions: { unity-cli: 1.0.0-beta.8, git-lfs: 3.7.1 }
---

# Asset storage and collaboration

Role: where game projects and their binary assets (textures, models, audio, video, scenes) live, and how collaborators share them. This is kept separate from this knowledge repo.

## Two tiers

| Tier | What | Where | Visibility |
|------|------|-------|------------|
| Knowledge | Notes, scripts, small fixtures | This repo (`toybox`) | Shareable |
| Game project | Unity project, curated assets, `.blend` sources, provenance sidecars | One **private git repo per game**, binaries in **Git LFS** | Private; invite collaborators |
| Bulk / scratch | Raw generation batches, videos, intermediate renders, builds | **Object storage bucket** (e.g. Cloudflare R2, S3), synced with `rclone` | Private |

Rules:

- Never commit game assets to `toybox`. Its `out/` and `sandbox/` folders are git-ignored scratch space.
- Promote only the assets you have chosen into the game repo. Keep each asset's `.json` provenance sidecar next to it; sidecars are small text and belong in git.
- Record licences in the sidecars. Non-commercial models (e.g. FLUX.2 Klein 9B, Qwen-Image-2.1) must not end up in a shipped build.

## Why git + LFS for game repos

- Agents drive git well, and `gh` handles repos, permissions and pull requests.
- The **`unity vcs`** commands in the Unity CLI understand Unity projects on top of git/LFS (or Unity Version Control):
  - `setup`: create the repo and push a first commit, e.g. `unity vcs setup --vcs github --git-visibility private --git-lfs`.
  - `doctor`: check ignore rules, LFS patterns and pinned packages.
  - `sync` / `switch`: pull or change branch only when no Editor has the project open, then report reimports.
  - `merge-setup` / `conflicts` / `explain` / `resolve`: merge scenes and prefabs with Unity's merge tool (UnityYAMLMerge).
  - `diff` / `summarize` / `affected`: describe changes by Unity object and component, and write PR summaries.
  - `hooks`: integrity checks at commit time.
- `git lfs lock` gives file locking for assets that can't be merged (`.blend`, `.psd`, scenes).
- Artists who don't use git can use **Anchorpoint** (a desktop app built on git/LFS). **(unverified)**

The `unity vcs` details above come from `--help` output (2026-09-23); nothing has been run yet.

## Alternatives

| Option | When to consider | Trade-off |
|--------|------------------|-----------|
| Unity Version Control (UVCS, formerly Plastic SCM) | Many artists, very large repos, Unity-centric team | Hosted by Unity; `cm` CLI; `unity vcs` supports it. Less familiar to agents. |
| Perforce Helix Core | Large teams, AAA-scale binaries | Industry standard, but heavier to run and less agent-friendly. |
| DVC / git-annex | Data-style versioning of large outputs in object storage | Pointer files in git, content in a bucket. More moving parts. |

Pricing and free-tier limits (GitHub LFS storage/bandwidth, R2, UVCS, Perforce) change often. **Check them before choosing (unverified here).**
