---
status: partial
last_verified: 2026-10-10
versions: { ollama: 0.40.2 }
---

# Local LLMs

Role: cheap, private, scriptable language (and possibly vision) calls *inside* pipeline scripts, e.g. bulk prompt variants, asset naming, captioning or QA of generated images. The orchestrating agent is separate: this is for work the agent delegates to scripts.

A second role is **runtime decisions inside a game**: choosing among a fixed set of options in a single forward pass, for example NPC action selection. See [Decision models](#decision-models-clef).

Caution from HotCards: an LLM silently rewriting or "enriching" image prompts was a **no-go**. It made results harder to control. Keep LLM steps explicit and log their output in asset provenance.

## Ollama (cross-platform, preferred default)

- Runs on macOS (with MLX-format models), Windows and Linux (CUDA, ROCm).
- The local server listens on `http://localhost:11434`. Its native API is `/api/*`, with an OpenAI-compatible API at `/v1/*`.
- This machine: **0.40.2** (checked 2026-10-10; previously 0.34.3), server running. Installed generative models: `qwen3.5:9b-mlx` (8.9 GB), `qwen3.8:27b-mlx` (18 GB) and `qwen3.6:35b-mlx` (21 GB). The `-mlx` tags use MLX acceleration on Apple Silicon. Decision models are listed below.

```sh
ollama list
curl -s localhost:11434/api/version
ollama run qwen3.5:9b-mlx "Give 5 short prompts for retro coin pickup sounds, one per line"
```

## Decision models (Clef)

**Status: partial.** Both models installed and measured on the M4 Max ([experiment](../experiments/2026-10-10-decision-models-ollama.md)). API facts come from the [Ollama model pages](https://ollama.com/library/clef) unless marked as measured.

Cloudflare's **Clef** (27B, from Qwen3.8-27B) and **Clef-Flash** (9B, from Qwen3.5-9B) are Apache-2.0 decision models released 2026-10-01. They don't generate text. Given a `state` and up to 64 named questions, they return **probabilities over the allowed answers** in one non-autoregressive forward pass. Text and image input.

- Requires Ollama ≥ 0.35.1. Tags: `clef-flash:9b` (12 GB on disk here) and `clef:27b` (~18 GB).
- Endpoint: `POST http://localhost:11434/v1/systemone`, body `{model, state, questions, images?, keep_alive?}`. `state` is a string or JSON. `images` are base64 PNG/JPEG/WebP; URLs and data URLs are not accepted.
- Question types:
  - `choice`: 2–26 options in `criteria` (`{option: description | null}`). Returns `choice`, `probabilities` and `confidence`.
  - `noul`: yes/no. Returns P(true).
  - `score`: 2–26 ordered levels (`criteria` array, lowest first). Returns a probability-weighted `score`, plus `legend`, `probabilities` and `confidence`.
- `confidence` measures how concentrated the distribution is, not whether the answer is correct. Ties resolve to the first-listed option, so list the preferred default first.
- There is no temperature parameter. If you want variety, sample from `probabilities` in your own code.
- **Not OpenAI-compatible.** The Ollama Python/JS libraries and `ollama run` don't support decision models yet. Use raw HTTP (stdlib `urllib` is enough) or Cloudflare's `typesafe-sdk` with `TYPESAFE_BASE_URL` pointed at Ollama. The portability convention below doesn't cover this endpoint.
- Without the model pulled, the endpoint answers `{"error":"model \"clef-flash\" not found, try pulling it first"}` (verified 2026-10-10, 0.40.2).
- **Measured latency** (M4 Max, Ollama 0.40.2, ~450–510 input tokens, 3 questions per call):
  - Fresh decision, median: **~0.54 s** (Flash), **~2.1 s** (27B).
  - Cold load: 3.1 s (Flash), 4.7 s (27B).

  The vendor's figures (39 ms / 209 ms) are from unstated hardware and don't transfer to this machine.
- **Measured: outputs are deterministic, and identical requests are cached** (~10 ms). Re-asking an unchanged state is free. For variety, sample from the probabilities yourself.
- **Measured: one call per subject.** Putting several independent subjects into one state with per-subject questions was no faster (Flash about the same as separate calls, 27B ~3× slower) and changed the answers. Earlier subjects' descriptions leak into later ones.
- Sources disagree on context length (64K vs 256K). **(unverified here)**

## oMLX (Apple Silicon only, promising)

- https://github.com/jundot/omlx is an MLX LLM server with continuous batching, a tiered RAM + SSD KV cache, OpenAI/Anthropic-compatible APIs and a menu-bar app.
- Not installed here yet. 🟡 Worth evaluating against Ollama for throughput and long contexts on the 128 GB machine.

## Portability

Scripts should talk to the **OpenAI-compatible HTTP API** and take the base URL and model from environment variables (e.g. `TOYBOX_LLM_BASE_URL`, `TOYBOX_LLM_MODEL`). Then Ollama, oMLX or a hosted API can be swapped without code changes. (Convention proposed, not yet used by any script.)
