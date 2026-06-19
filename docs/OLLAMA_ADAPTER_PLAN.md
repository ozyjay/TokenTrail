# Ollama Adapter Implementation Plan

**Project:** Token Trail  
**Status:** Implemented through live generation, warm-up, and editable local prompt slice  
**Last updated:** 2026-06-20

---

## Goal

Add a local Ollama-backed generation path to Token Trail while keeping scripted traces as the guaranteed fallback.

Target flow:

```text
Token Trail UI
  -> Token Trail local server
  -> runtime selector
  -> Ollama adapter
  -> local Ollama API
  -> display-friendly trace
```

The first implementation supported curated prompts only. A later small slice added staff-editable prompt entry for available local Ollama runtimes after reset, timeout, and fallback controls were in place. Scripted mode and scripted fallback remain curated and static.

---

## Current constraints

Token Trail already has:

- scripted traces;
- runtime backend/model selector scaffolding;
- `.env` model lists;
- fixed local port convention;
- `/health`;
- launch-time port checks.

Important local-test lesson:

```text
Do not load runtime config at import time.
```

Config, runtime options, and adapter state should be built during startup or passed into testable functions/classes.

---

## Environment settings

Existing settings:

```env
TOKEN_TRAIL_BACKEND=scripted
TOKEN_TRAIL_OLLAMA_BASE_URL=http://127.0.0.1:11434
TOKEN_TRAIL_OLLAMA_MODEL=qwen3:4b
TOKEN_TRAIL_OLLAMA_MODELS=qwen3:4b,qwen3:1.7b
```

Expected behaviour:

- scripted fallback is always selectable;
- configured Ollama models appear in the runtime selector;
- reachable installed models are marked available;
- missing or unreachable models remain visible but clearly unavailable.

---

## Proposed files

```text
src/token_trail/adapters/
  __init__.py
  base.py
  ollama.py

tests/
  test_ollama_adapter.py
```

Keep the adapter independent from UI code.

---

## Adapter interface

Use one display-friendly shape regardless of backend.

```text
Backend adapter
  -> prompt tokens
  -> generated token steps
  -> selected token text
  -> optional candidate/probability display
  -> source/notes
```

If Ollama cannot provide real candidate probabilities through the selected API path, the UI must either hide probability bars for live mode or clearly label them as approximated. For Open Day, hiding them is safer until real logprobs are available.

---

## Phase 1 — Availability and model discovery

Goal: show whether configured Ollama models are actually usable on the current machine.

Build:

- `OllamaAdapter.is_available()`
- `OllamaAdapter.list_models()`
- `OllamaAdapter.has_model(model_name)`
- short connection timeout
- `/api/runtime` marks Ollama options available/unavailable

Assumed Ollama operations to verify against installed version:

```text
GET  /api/tags       list local models
POST /api/generate   generate from a prompt
```

Tests should use fake responses or monkeypatching. Unit tests must not require Ollama to be installed.

Go/no-go:

```text
App starts cleanly whether Ollama is running, stopped, missing, or missing the selected model.
```

---

## Phase 2 — Curated live generation

Goal: selected Ollama model can generate a short continuation from the selected prompt.

Build endpoint:

```text
POST /api/generate-trace
```

Request shape:

```json
{
  "runtime_id": "ollama:qwen3:4b",
  "trace_id": "robot-university",
  "prompt": "Write a tiny story about a robot at university."
}
```

Required behaviour:

- use the curated prompt from the trace library by default;
- allow an optional edited prompt only for live Ollama generation;
- ignore edited prompt text for scripted mode and scripted fallback;
- keep generation short;
- timeout cleanly;
- return a display-friendly trace;
- fall back to scripted trace if live generation fails;
- do not store visitor prompts by default.

---

## Phase 3 — UI behaviour

Goal: make live vs fallback state obvious.

Build:

- show selected runtime;
- show model availability;
- disable or warn on unavailable models;
- display fallback label when scripted traces are used;
- show a staff-readable error if Ollama times out.

Preferred labels:

```text
Live local model mode
Prepared demo mode: showing a saved generation trace
```

Avoid wording that says the AI is thinking or that the display shows hidden reasoning.

---

## Phase 4 — Open Day hardening

Goal: make Ollama mode safe enough for rehearsal.

Build:

- one-click fallback to scripted mode;
- clear generation timeout;
- `/health` includes runtime and Ollama availability;
- launch warning if `TOKEN_TRAIL_BACKEND=ollama` but Ollama is unreachable;
- logs remain technical and non-identifying;
- reset clears visible state.

Rehearsal test:

```text
Run Token Trail scripted mode, Token Trail Ollama mode, VoiceChanger, TV output, and any other local web demo for 60 minutes.
```

Pass condition:

```text
No crashes, no stuck generation state, no port conflicts, and fallback works instantly.
```

---

## Error handling table

| Condition | Behaviour |
|---|---|
| Ollama not running | Show Ollama models unavailable; keep scripted fallback |
| Model missing | Show model unavailable; do not crash |
| Request timeout | Stop waiting and show fallback |
| Unexpected API response | Treat as adapter error and show fallback |
| Poor model output | Allow reset and curated/scripted retry |

---

## Test plan

Unit tests:

```text
test_ollama_adapter_lists_models
test_ollama_adapter_handles_connection_failure
test_ollama_adapter_handles_timeout
test_ollama_adapter_detects_model_available
test_ollama_generation_maps_to_display_trace
test_generation_failure_uses_scripted_fallback
test_server_config_is_not_loaded_at_import_time
```

Manual test on a real machine:

```powershell
ollama list
.\scripts\test.ps1
.\scripts\run.ps1
```

Open:

```text
http://127.0.0.1:3100
http://127.0.0.1:3100/health
```

---

## First implementation slice

Start here:

```text
OllamaAdapter.list_models()
  -> runtime API marks configured Ollama models available/unavailable
  -> fake-response tests pass
  -> UI shows real availability
```

Only after that works, add live generation.
