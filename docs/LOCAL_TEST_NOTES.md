# Local Test Notes

This file records local setup or test issues found while running Token Trail on real development machines.

---

## 2026-06-19 — Runtime model selection local fix

**Status:** fixed locally and pushed

**Context:** Runtime selection was added so the app can choose between scripted traces, Ollama models, and vLLM models without editing code.

**Observed issue:** During local testing, the runtime model configuration needed to support multiple selectable installed models, not only a single default model per backend.

**Fix captured in repo:**

- `RuntimeConfig` now carries both the selected model and the configured selectable model list for Ollama and vLLM.
- `TOKEN_TRAIL_OLLAMA_MODELS` and `TOKEN_TRAIL_VLLM_MODELS` are comma-separated lists used to populate runtime options.
- Duplicate model names are de-duplicated while preserving order.
- Tests now clear and cover the model-list environment variables so local `.env` or shell settings do not mask failures.

**Example `.env` values:**

```env
TOKEN_TRAIL_OLLAMA_MODEL=qwen3:4b
TOKEN_TRAIL_OLLAMA_MODELS=qwen3:4b,qwen3:1.7b

TOKEN_TRAIL_VLLM_MODEL=Qwen/Qwen3-4B
TOKEN_TRAIL_VLLM_MODELS=Qwen/Qwen3-4B
```

**Why this matters:** Different development machines and the Framework Desktop may already have different local models installed. Token Trail should let staff or developers choose from configured installed models at runtime rather than requiring code edits.

**Follow-up:** When the live Ollama adapter is implemented, replace or supplement configured model lists with live discovery from `ollama list` / Ollama API where practical. Keep scripted traces as the guaranteed fallback.

---

## Local testing rule

When a local machine fix is needed:

1. Push the code fix.
2. Add a short note here with the symptom, fix, and follow-up.
3. If it affects setup, ports, or runtime selection, update `.env.example` and the README.
4. If it affects Open Day operation, update the relevant project source-of-truth document as well.
