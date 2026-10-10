# Clef decision models through Ollama

- **Date:** 2026-10-10
- **Goal:** Can local decision models (Clef, Clef-Flash) drive runtime choices such as NPC action selection, and how fast are they on this machine?
- **Tools & versions:** Ollama 0.40.2, `clef-flash:9b`, `clef:27b`, uv 0.10.3 / CPython 3.12, macOS 15.8.1, M4 Max 128 GB.

## What we did

```sh
ollama pull clef-flash:9b   # 12 GB
ollama pull clef:27b        # 18 GB
```

A private stdlib-Python harness posted to `http://localhost:11434/v1/systemone`:

- **Scenes:** 6 small household situations × 3 characters (two humans and a pet).
- **Per call:** the character's persona, the room and its own perception/memory as JSON `state`, plus three questions:
  - a `choice` over 5–6 legal actions
  - an "interrupt current activity?" `noul`
  - a 4-level irritation `score`
- **Repeats:** each call 5 times.
- **Comparisons:** both humans got identical action lists, so their distributions could be compared with Jensen–Shannon divergence. A persona-swap test and an all-characters-in-one-call variant were also run.

Project specifics stay in the private game repo.

## What happened

| | Clef-Flash 9B | Clef 27B |
|---|---|---|
| Cold load | 3.1 s | 4.7 s |
| Fresh call, median | ~0.54 s | ~2.1 s |
| Identical repeat | ~10 ms | ~12 ms |
| 3 subjects × 3 questions in one call | ~1.7 s | ~6.0 s |

- **Deterministic:** all 5 repeats were identical, and repeats were served from a cache.
- **Plausible choices:** both models made sensible, context-dependent choices. Examples: a cold-averse character closes the window; a pet leaves a draft; a considerate character yields an occupied seat; a "claimed" object is left alone.
- **History is noticed but doesn't change strategy:** history raised irritation scores, but neither model switched away from a repeatedly failing action. Both kept picking the same fix.
- **27B separated personas more** in 3 of 5 comparable scenes.
- **Persona text was a weak lever.** Swapping only the persona barely moved most distributions; situational text dominated.
- **Batching changed answers:** combining subjects in one call agreed with the per-subject choice in as few as 0 of 3 cases.

### Follow-up: what drives latency (Clef 27B)

With a unique suffix on each request to defeat the cache, latency scaled with input tokens (0.56 s at 197 tokens, 4.4 s at 1,237), and every question's text added to those tokens. This fits a compute-bound single forward pass: about 2 × 27B × tokens, at the M4 Max's effective throughput. A datacenter GPU is roughly 30× faster, which accounts for the vendor's ~200 ms. Prefix reuse across calls was inconsistent and remains unverified.

## Learnings

- Folded into [tools/local-llm.md](../tools/local-llm.md#decision-models-clef): measured latency, caching and determinism, one call per subject. Also corrected the stale Ollama version (0.34.3 → 0.40.2).
- Vendor latency figures don't transfer to Apple Silicon. Measure on the target machine.
- Treat the model as a judgment layer. Escalation, cooldowns and variety belong in the surrounding simulation.

## Follow-ups

- Persona placement (in the state vs in the question instructions) and its effect on separation.
- Image input for perception: same API, `images` array.
- Concurrency: whether parallel requests to one loaded model overlap or queue.
