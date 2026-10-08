# Unity replacement and module inspection

- **Date:** 2026-10-08
- **Goal:** Confirm an editor replacement and distinguish optional build backends from bundled player support.
- **Tools & versions:** Unity Editor 6000.6.5f1 arm64, Unity CLI 1.0.0-beta.12, Apple Git 2.50.1, Git LFS 3.8.0, GitHub CLI 2.101.0.

## What we did

Inspected the user's completed installation; no software or global configuration was changed.

```sh
ls -1 /Applications/Unity/Hub/Editor
/Applications/Unity/Hub/Editor/6000.6.5f1/Unity.app/Contents/MacOS/Unity -version
file /Applications/Unity/Hub/Editor/6000.6.5f1/Unity.app/Contents/MacOS/Unity
ls -1 /Applications/Unity/Hub/Editor/6000.6.5f1/PlaybackEngines
unity --version
git --version
git lfs version
gh --version
xcode-select -p
xcodebuild -version
find /Applications -maxdepth 1 -type d -name 'Xcode*.app' -print
mdfind 'kMDItemCFBundleIdentifier == "com.apple.dt.Xcode"'
```

Inspected module selection and Mac player variants:

```sh
uv run --no-project python - <<'PY'
import json
from pathlib import Path
root = Path('/Applications/Unity/Hub/Editor/6000.6.5f1')
for m in json.loads((root/'modules.json').read_text()):
    if m.get('id') in ('ios', 'webgl', 'mac-mono', 'mac-il2cpp'):
        print(json.dumps({k:m.get(k) for k in ('id','name','selected','destination')}))
mac = root/'PlaybackEngines/MacStandaloneSupport'
print('Mac engine contents:', ', '.join(sorted(p.name for p in mac.iterdir())))
variations = mac/'Variations'
if variations.exists():
    print('Mac variations:', ', '.join(sorted(p.name for p in variations.iterdir())))
PY
```

## What happened

- Only **6000.6.5f1** remained in the Hub editor directory; its executable returned that version and was native arm64.
- `iOSSupport`, `WebGLSupport`, and `MacStandaloneSupport` were present.
- Module metadata used the UI name **Web Build Support** for ID `webgl` and directory `WebGLSupport`. iOS and Web were selected.
- **Mac Build Support (IL2CPP)**, ID `mac-il2cpp`, was not selected. Nevertheless, MacStandaloneSupport contained Mono development/release players for arm64, x64, and universal architectures. Do not infer Mac IL2CPP installation from that directory alone.
- Git LFS **3.8.0** was now executable, correcting the current-readiness gap from the previous day's inspection. No upload/restore was performed.
- Xcode was not found in the inspected application locations or Spotlight query; Command Line Tools remained selected and `xcodebuild -version` failed.
- No project was created or migrated. Editor-side target detection, imports, rendering, native builds, and the newer CLI's project commands remain **(unverified)** on these versions.

## Learnings

Updated [Unity](../tools/unity.md), [platform readiness](../platforms.md), and [asset storage](../tools/asset-storage.md). Preserve historical experiment versions; installation inspection does not revalidate old gameplay/build recipes.

## Follow-ups

[Backlog](../backlog.md): repeat the Blender/URP preflight on the replacement editor, configure full Xcode for iOS, and repeat an LFS restore before claiming current end-to-end readiness.
