---
status: partial
last_verified: 2026-09-23
versions: { git: 2.53.0, git-lfs: 3.7.1, gh: 2.98.0, unity-cli: 1.0.0-beta.8 }
---

# Asset storage and collaboration

Role: where private media experiments, game projects and binary assets live. A private GitHub + Git LFS library has been created, uploaded and restored on macOS; Unity-specific workflows, locking and object storage remain unverified. Evidence: [private asset-library experiment](../experiments/2026-09-23-private-asset-library.md).

## Storage convention

| Store | What belongs there | Status |
|-------|--------------------|--------|
| Public `toybox` | Generic methods, measurements, scripts, intentional non-project fixtures | In use |
| Private `toybox-assets` | Selected media experiments, full briefs and prompts, sources, review sheets, provenance; one folder per project | GitHub + Git LFS upload/restore verified |
| Private per-game repo | Unity project and approved assets when a game enters production | Planned; no Unity project needed to start the asset library |
| Local `out/` | Disposable batches, intermediate renders and builds | Scratch, not a backup |
| Private object storage | Large archives or video batches that outgrow practical LFS use | Deferred; R2/S3 + `rclone` are candidates |

The library's local checkout is a sibling of `toybox`, not a nested repository. Discover or ask for its path on another machine; never assume this Mac's absolute path.

```text
projects/<project>/
  README.md
  experiments/<date>-<experiment>/   # selected runs, shot lists, review sheets
  sources/                         # editable originals when available
  approved/                        # explicitly selected, rights-reviewed assets
```

- Archive deliberately. A complete small experiment is useful evidence; do not auto-upload every generation. The initial archive was 31.36 MiB.
- Preserve each `<asset>.json` sidecar and the original shot list. Keep text in regular Git; binary formats in `.gitattributes` use LFS. Do not fabricate missing provenance or rewrite historical paths.
- `experiments/` is not a shipping allowlist. Review model terms and depicted content before promotion; permissive model licensing alone is not blanket clearance.
- Mark non-commercial outputs **and derived contact sheets** as research-only. Keep them out of `approved/` and game builds unless suitable rights are obtained. Private storage does not waive licence terms.
- When promoting to a game repo, copy the approved asset with its sidecar and record the library commit and source path. Do not make the entire experimental library a build dependency.
- Keep project names, briefs, prompts, screenshots and asset links out of public logs; record generic findings instead.
- Collaborators get repository access, not per-folder access. Split private repos when projects need different audiences.
- No model weights, tool caches, Unity `Library/`, builds or credentials. Keep Unity `.meta`, scenes and prefabs in regular Git rather than a blanket binary LFS rule.

## Verified CLI workflow

Plain `git`, `git lfs` and `gh` suffice; Unity is not a prerequisite. Create a private remote only after user approval:

```sh
# Example values: replace OWNER and choose an unused local directory.
ASSET_REPO=../toybox-assets
ASSET_REMOTE=https://github.com/OWNER/toybox-assets.git
mkdir "$ASSET_REPO"
git -C "$ASSET_REPO" init -b main
git -C "$ASSET_REPO" lfs install --local
git -C "$ASSET_REPO" lfs track '*.png' '*.jpg' '*.jpeg' '*.webp' '*.exr' \
  '*.blend' '*.glb' '*.fbx' '*.psd' '*.wav' '*.ogg' '*.mp3' '*.flac' '*.mp4' '*.mov'
gh repo create OWNER/toybox-assets --private
git -C "$ASSET_REPO" remote add origin "$ASSET_REMOTE"
```

Add ignore rules and private project documentation before staging. Copy selected files, stage `.gitattributes` with them, and inspect `git lfs ls-files` plus the staged diff. Confirm the remote is private before an authorized commit/push. Use `--local` to avoid changing global Git settings. Lower-case extensions are the convention; add LFS patterns for other formats before their first commit.

Verify remote restoration, not merely a successful push:

```sh
# Use a fresh, unused destination.
GIT_LFS_SKIP_SMUDGE=1 git clone "$ASSET_REMOTE" out/asset-restore
git -C out/asset-restore lfs install --local
git -C out/asset-restore lfs pull
git -C out/asset-restore lfs fsck
```

Compare restored files' SHA-256 hashes with the originals. A pointer-only clone is not a restored asset archive. The experiment restored all 77 repository files byte-for-byte, including 36 LFS binaries.

## Capacity and costs

Documentation checked 2026-09-23; these are **published limits, not a measurement of this account's remaining allowance**:

- [GitHub LFS billing](https://docs.github.com/en/billing/concepts/product-billing/git-lfs): Free/Pro includes 10 GiB storage and 10 GiB monthly download bandwidth **per account**, shared across repos. Team/Enterprise Cloud includes 250 GiB of each.
- [Per-file limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage): Free/Pro 2 GB, Team 4 GB, Enterprise Cloud 5 GB.
- Every distinct binary revision consumes its full size; downloads, including CI, use the owner's bandwidth. Deleting a file or rewriting Git history does not automatically reclaim remote LFS storage ([removal details](https://docs.github.com/en/repositories/working-with-files/managing-large-files/removing-files-from-git-large-file-storage)).
- Check account usage and set an appropriate LFS budget in GitHub Billing before scaling. A $0 budget blocks overages rather than providing unlimited free storage. No budget or billing settings were changed in this experiment.
- Defer a second storage service while assets are small. Revisit for large videos, frequent revisions of large source files, or expensive download volume. Paid LFS rates and R2/S3 costs must be checked when needed.

## Unity collaboration (help-only; unverified)

- Agents drive git well, and `gh` handles repos, permissions and pull requests.
- The **`unity vcs`** commands in the Unity CLI understand Unity projects on top of git/LFS (or Unity Version Control):
  - `setup`: create the repo and push a first commit, e.g. `unity vcs setup --vcs github --git-visibility private --git-lfs`.
  - `doctor`: check ignore rules, LFS patterns and pinned packages.
  - `sync` / `switch`: pull or change branch only when no Editor has the project open, then report reimports.
  - `merge-setup` / `conflicts` / `explain` / `resolve`: merge scenes and prefabs with Unity's merge tool (UnityYAMLMerge).
  - `diff` / `summarize` / `affected`: describe changes by Unity object and component, and write PR summaries.
  - `hooks`: integrity checks at commit time.
- `git lfs lock` is a candidate for non-mergeable source assets (`.blend`, `.psd`); server locking and multi-user conflict behaviour have not been tested. Keep Unity YAML scenes/prefabs mergeable by default.
- Artists who don't use git can use **Anchorpoint** (a desktop app built on git/LFS). **(unverified)**

The `unity vcs` details above come from `--help` output (2026-09-23), not an end-to-end Unity run. `setup` normally commits and pushes; `--no-initial-commit` skips that step. Do not run it without the appropriate user authorization.

## Alternatives

| Option | When to consider | Trade-off |
|--------|------------------|-----------|
| Unity Version Control (UVCS, formerly Plastic SCM) | Many artists, very large repos, Unity-centric team | Hosted by Unity; `cm` CLI; `unity vcs` supports it. Less familiar to agents. |
| Perforce Helix Core | Large teams, AAA-scale binaries | Industry standard, but heavier to run and less agent-friendly. |
| DVC / git-annex | Data-style versioning of large outputs in object storage | Pointer files in git, content in a bucket. More moving parts. |

R2, UVCS and Perforce pricing and workflows remain **(unverified)**.
