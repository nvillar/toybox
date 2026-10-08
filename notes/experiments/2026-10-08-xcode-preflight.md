# Xcode SDK and simulator discovery on Sequoia

- **Date:** 2026-10-08
- **Goal:** Verify full Xcode installation and distinguish SDK availability from simulator and application readiness.
- **Tools & versions:** macOS Sequoia 15.8.1; Xcode 26.3 (17C529); iPhoneOS/iPhoneSimulator SDKs 26.2; simulator runtime reporting version 26.3.1 (23D8133).

## What we did

After the user's installation, ran read-only diagnostics. Did not change developer selection, install components, accept licences, inspect signing identities, or boot a simulator.

```sh
find /Applications -maxdepth 1 -type d -name 'Xcode*.app' -print
xcode-select -p
xcodebuild -version
sw_vers -productVersion
xcodebuild -checkFirstLaunchStatus
xcrun --sdk iphoneos --show-sdk-version
xcrun --sdk iphoneos --show-sdk-path
xcrun --sdk iphonesimulator --show-sdk-version
xcrun simctl list runtimes --json | uv run --no-project python -c \
  'import json,sys; data=json.load(sys.stdin); print(json.dumps([{k:r.get(k) for k in ("name","version","buildversion","isAvailable")} for r in data["runtimes"]], indent=2))'
```

## What happened

- `/Applications/Xcode.app` is installed; `/Applications/Xcode.app/Contents/Developer` was already the selected developer directory.
- `xcodebuild -version` returned **26.3**, build **17C529**. macOS remained **15.8.1**.
- `xcodebuild -checkFirstLaunchStatus` exited successfully with no output.
- Both device and simulator SDK queries returned **26.2**. The device SDK path resolves inside this Xcode installation to `iPhoneOS26.2.sdk`.
- `simctl` listed **iOS 26.3**, version **26.3.1**, build **23D8133**, with `isAvailable: true`. Preserve the reported name and version separately; neither is the SDK version.
- No Unity export, Xcode compilation, simulator launch, signing, or physical-device build was attempted. Those remain **(unverified)**.

## Learnings

Full Xcode and SDK discovery are now exercised on Sequoia, rather than only supported by documentation. SDKs, simulator runtimes, the host OS, and deployment minimums are separate versioned components. A successful discovery check is not an end-to-end app build.

Updated [Unity](../tools/unity.md), [platform readiness](../platforms.md), and the README status table. This supersedes the missing-Xcode readiness finding in the earlier [installation inspection](2026-10-08-unity-installation.md), not its historical observations.

## Follow-ups

[Backlog](../backlog.md): a real Unity iOS export, compilation, signing, and physical iPhone/iPad run; separate simulator build/launch if required.
