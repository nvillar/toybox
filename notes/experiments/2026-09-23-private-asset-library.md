# Private asset library with Git LFS

- **Date:** 2026-09-23
- **Goal:** Preserve media experiments privately without requiring a Unity project or putting project details in this public knowledge repo.
- **Tools & versions:** Git 2.53.0, Git LFS 3.7.1, GitHub CLI 2.98.0; primary macOS arm64 machine. Unity CLI 1.0.0-beta.8 was inspected with `vcs setup --help` only.

## What we did

The user chose a shared private asset library with one folder per project, then explicitly authorized repository creation and the initial asset commit/push. Public `toybox` changes were left uncommitted.

1. Measured the initial experiment: 31.36 MiB, 33 PNGs, 3 JPEG review sheets, 35 JSON files and a detailed Markdown log. Checked every PNG had a provenance sidecar.
2. Created a separate sibling checkout and private GitHub remote. Initialized LFS with `--local` and binary extension patterns before staging. Preserved original relative paths, complete prompts and sidecars.
3. Added private usage and licensing notes. Marked three non-commercial model outputs and the mixed-model comparison sheet research-only; nothing was promoted to an approved shipping directory.
4. Confirmed copied files matched their originals byte-for-byte and checked text for common credential patterns. Inspected the staged content: 36 LFS pointers and 41 regular Git text files.
5. Confirmed the remote was private, committed with the Copilot co-author trailer, ran `git lfs fsck`, and pushed.
6. Cloned from GitHub into a fresh local scratch directory, explicitly pulled LFS content, ran `fsck` and compared SHA-256 hashes for every tracked file. Removed the disposable restore checkout afterward; kept the original scratch assets and the private library checkout.

Commands below substitute generic paths and owner names to avoid exposing the private project:

```sh
ASSET_REPO=../toybox-assets
ASSET_REMOTE=https://github.com/OWNER/toybox-assets.git
git -C "$ASSET_REPO" init -b main
git -C "$ASSET_REPO" lfs install --local
git -C "$ASSET_REPO" lfs track '*.png' '*.jpg' '*.jpeg' '*.webp' '*.exr' \
  '*.blend' '*.glb' '*.fbx' '*.psd' '*.wav' '*.ogg' '*.mp3' '*.flac' '*.mp4' '*.mov'
gh repo create OWNER/toybox-assets --private
gh repo view OWNER/toybox-assets --json isPrivate
git -C "$ASSET_REPO" remote add origin "$ASSET_REMOTE"
# After copying, reviewing and staging the authorized archive:
git -C "$ASSET_REPO" commit -m "Archive initial concept-art experiments with LFS and provenance" \
  -m "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"
git -C "$ASSET_REPO" lfs fsck
git -C "$ASSET_REPO" push -u origin main
GIT_LFS_SKIP_SMUDGE=1 git clone "$ASSET_REMOTE" out/asset-restore
git -C out/asset-restore lfs install --local
git -C out/asset-restore lfs pull
git -C out/asset-restore lfs fsck
```

## What happened

- The private GitHub upload and fresh HTTPS restore succeeded. All 77 tracked files matched the local checkout byte-for-byte, including the 36 actual images rather than just LFS pointers.
- Text metadata stayed in ordinary Git. The archive includes the original detailed log; the public concept-art log, links and helper examples were made generic.
- GitHub's published Free/Pro allowance is currently 10 GiB LFS storage plus 10 GiB monthly downloads per account. Remaining account allowance was not inspected; no spending limits were changed.
- No Unity project, `unity vcs setup`, object storage service or collaborator access was required.

## Learnings

- Folded the operational recipe and current published limits into [asset storage](../tools/asset-storage.md).
- Corrected the earlier per-game-only storage assumption: a private experiment library can precede production repos and cover media that never becomes a game.
- Corrected the assumption that bulk/scratch output needs a bucket immediately: ignored local output is scratch, selected small archives use LFS, and object storage is deferred.
- Privacy applies to prompts, titles, sidecars and review images as well as binaries. Review sheets inherit restrictions from their source images.
- A generic public log can retain timings, tool versions and failure modes without disclosing the creative brief.

## Follow-ups

- [Backlog](../backlog.md): multi-user LFS locking; a Unity-specific setup/merge/sync round-trip; object storage when volume warrants it.
- Check account usage and budget before larger uploads. Verify backup recovery periodically, not just upload success.
