---
status: partial
last_verified: 2026-09-23
---

# Platforms and acceleration

We develop on one machine but want the pipeline to be portable. Each **capability** (image generation, audio generation, local LLM, …) has a stable interface — the wrappers in [`scripts/gen/`](../scripts/gen/) — and one or more **backends** per platform. Prefer the fastest native backend on each platform (MLX on Apple Silicon, CUDA/TensorRT on NVIDIA, ROCm on AMD) rather than a lowest-common-denominator runtime.

## Primary development machine

| | |
|---|---|
| Machine | Apple M4 Max, 128 GB unified memory |
| OS | macOS 15.8 (arm64) |
| Accelerator | Metal / MLX |
| Platform id (`scripts/gen`) | `macos-arm64` |

Unified memory means GPU models share RAM with everything else (Blender, Unity, the agent). Observed peaks so far: FLUX.2 Klein 4B ~10.5 GB at 512², Qwen-Image-2.1 ~20–22 GB at 512²–768×512, Stable Audio 3 small ~2 GB (upstream benchmark). Local LLMs add their weight size (e.g. 9–21 GB for the installed Ollama models).

## Backend matrix

✅ verified here · 🟡 proven elsewhere / documented upstream, not yet run by us · ❓ candidate, needs research

| Capability | macOS Apple Silicon | Windows / Linux + NVIDIA | Linux / Windows + AMD | Fallback |
|------------|---------------------|---------------------------|------------------------|----------|
| Image gen / edit | ✅ **MFLUX** (FLUX.2 Klein; Qwen-Image-2.1) — [tools/mflux.md](tools/mflux.md) | ❓ diffusers `Flux2KleinPipeline` on PyTorch CUDA; ❓ ComfyUI (HTTP API) | ❓ diffusers or ComfyUI on PyTorch ROCm (Linux mature; Windows ROCm newer) | Hosted image APIs |
| SFX / music | ✅ **Stable Audio 3 MLX** (`sa3`) — [tools/stable-audio-3.md](tools/stable-audio-3.md) | 🟡 Stable Audio 3 **TensorRT** `sa3` (same CLI flags, Linux; Windows via WSL2 ❓); 🟡 `stable-audio-3` PyTorch lib (CUDA) | ❓ `stable-audio-3` PyTorch on ROCm; ❓ ONNX exports via onnxruntime (MIGraphX / DirectML) | 🟡 Small models on CPU (TFLite/LiteRT runtime upstream) |
| Local LLM | ✅ **Ollama** (MLX models); 🟡 **oMLX** (Apple Silicon only) — [tools/local-llm.md](tools/local-llm.md) | 🟡 Ollama (CUDA) | 🟡 Ollama (ROCm) | Hosted LLM APIs |
| 3D modelling | ✅ Blender (Metal) | 🟡 Blender (CUDA/OptiX) | 🟡 Blender (HIP) | Blender CPU |
| Game engine | 🟡 Unity | 🟡 Unity | 🟡 Unity | — |

The same Hugging Face weights generally work across backends (e.g. `black-forest-labs/FLUX.2-klein-4B`; `stabilityai/stable-audio-3-optimized` ships `MLX/`, `tensorRT/`, `onnx/`, `tflite/` and `cpu-amx/` variants), so switching platform changes the runtime, not the model. Check licences per model, not per backend.

## Adding a backend

1. Get it working by hand on the target platform; write an experiment log.
2. Register it in the relevant wrapper's `BACKENDS` list with the platform ids it supports (`scripts/gen/toybox_gen.py::detect_platform` defines them: `macos-arm64`, `<os>-cuda`, `<os>-rocm`, `<os>-cpu`).
3. Keep the wrapper's CLI flags and output format unchanged; map them onto the backend's own flags.
4. Update this matrix and the tool note.

Only register backends that have actually been run. Put candidates in this table and in [backlog.md](backlog.md) instead.
