---
status: partial
last_verified: 2026-09-23
versions: { ollama: 0.34.3 }
---

# Local LLMs

Role: cheap, private, scriptable language (and possibly vision) calls *inside* pipeline scripts, e.g. bulk prompt variants, asset naming, captioning or QA of generated images. The orchestrating agent is separate: this is for work the agent delegates to scripts.

Caution from HotCards: an LLM silently rewriting or "enriching" image prompts was a **no-go**. It made results harder to control. Keep LLM steps explicit and log their output in asset provenance.

## Ollama (cross-platform, preferred default)

- Runs on macOS (with MLX-format models), Windows and Linux (CUDA, ROCm).
- The local server listens on `http://localhost:11434`. Its native API is `/api/*`, with an OpenAI-compatible API at `/v1/*`.
- This machine: **0.34.3**, server running. Installed models: `qwen3.5:9b-mlx` (8.9 GB), `qwen3.8:27b-mlx` (18 GB) and `qwen3.6:35b-mlx` (21 GB). The `-mlx` tags use MLX acceleration on Apple Silicon.

```sh
ollama list
curl -s localhost:11434/api/version
ollama run qwen3.5:9b-mlx "Give 5 short prompts for retro coin pickup sounds, one per line"
```

## oMLX (Apple Silicon only, promising)

- https://github.com/jundot/omlx is an MLX LLM server with continuous batching, a tiered RAM + SSD KV cache, OpenAI/Anthropic-compatible APIs and a menu-bar app.
- Not installed here yet. 🟡 Worth evaluating against Ollama for throughput and long contexts on the 128 GB machine.

## Portability

Scripts should talk to the **OpenAI-compatible HTTP API** and take the base URL and model from environment variables (e.g. `TOYBOX_LLM_BASE_URL`, `TOYBOX_LLM_MODEL`). Then Ollama, oMLX or a hosted API can be swapped without code changes. (Convention proposed, not yet used by any script.)
