# Ollama Phase 2 — Live Text Generation Plan

**Project:** Token Trail  
**Status:** Implemented live text path  
**Last updated:** 2026-06-20

---

## Goal

Implement live **text** generation through Ollama while preserving scripted traces as the guaranteed fallback.

Ollama is no longer the preferred path for replayable live token traces. The optional live-trace path is now the custom Hugging Face Transformers trace server described in:

```text
docs/HF_TRANSFORMERS_TRACE_SERVER_PLAN.md
```

---

## Current role of Ollama

Ollama remains useful for:

- local live text generation;
- simple model discovery;
- warm-up and readiness checks;
- quick public demo variation;
- fallback-safe optional local model output.

Ollama should not be treated as the required token-probability backend for Token Trail.

---

## Implemented path

```text
runtime_id + trace_id + optional live prompt
  -> validate selected Ollama runtime
  -> load curated prompt or staff-edited live prompt
  -> call Ollama generate
  -> return generated_text
  -> display paragraph-style live output
  -> fallback to scripted trace on failure
```

---

## Scope

### Included

- Curated prompt to Ollama generation.
- Optional staff-edited prompt for available Ollama runtimes. The same live prompt editor is also used by HF trace mode.
- Runtime-selected Ollama model.
- Live generation endpoint.
- Graceful fallback to scripted traces.
- Timeout handling.
- Warm-up support.
- Unit tests.

### Excluded

- Unsupervised open-ended visitor prompts.
- Chat history.
- Conversations.
- QR integration.
- vLLM generation.
- Real token-probability display.
- Live token-trace replay.
- Multi-user support.

---

## API design

### Endpoint

```text
POST /api/generate-trace
```

### Request

```json
{
  "runtime_id": "ollama:qwen3:4b",
  "trace_id": "robot-university",
  "prompt": "Write a tiny story about a robot at university."
}
```

`prompt` is optional. If omitted, blank, or used with scripted mode, the server uses the selected prepared trace prompt.

### Live response

```json
{
  "mode": "live",
  "runtime_id": "ollama:qwen3:4b",
  "fallback_used": false,
  "generated_text": "A small robot joined orientation and learned to ask better questions."
}
```

### Fallback response

```json
{
  "mode": "scripted-fallback",
  "runtime_id": "ollama:qwen3:4b",
  "fallback_used": true,
  "message": "Live generation unavailable",
  "trace": {}
}
```

---

## Probability display rule

For Ollama live text mode:

```text
Live mode: generated text only
Scripted mode: probability-style bars visible
HF live trace mode: planned future model-derived candidate bars
```

Do **not** claim that Ollama live text mode shows real token probabilities.

---

## Fallback rules

Fallback immediately if:

- Ollama is not running;
- selected model is unavailable;
- timeout occurs;
- response is empty;
- response JSON is invalid;
- runtime is unknown.

The UI must never become stuck.

---

## Public wording

Use:

```text
Live Local Model Mode
```

Use for fallback:

```text
Prepared Demo Mode
```

Avoid:

```text
The AI is thinking.
```

Also avoid claiming that the demo shows private model reasoning.

---

## Open Day rule

```text
Ollama live text is optional.
Scripted trace mode is mandatory.
HF live trace is planned, not required.
```

The demo must still be useful if Ollama is unavailable.
