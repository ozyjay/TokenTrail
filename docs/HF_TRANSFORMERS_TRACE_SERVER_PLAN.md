# Hugging Face Transformers Trace Server Plan

**Project:** Token Trail  
**Status:** Preferred planned path for SLM live trace  
**Last updated:** 2026-06-20

---

## Goal

Build an optional local Hugging Face Transformers trace server that returns Token Trail-shaped trace JSON from a small local language model.

This replaces the earlier Ollama/vLLM-first live-trace direction.

Current backend roles:

| Backend | Role |
|---|---|
| Scripted traces | Mandatory fallback and primary teaching mode |
| Ollama | Simple local live text mode |
| Hugging Face Transformers server | Preferred planned path for live token traces |
| vLLM | Stretch/deferred desktop experiment |

---

## Why pivot

Ollama live text works, but local logprob probing did not return the token alternatives needed for a replayable trace on the tested Qwen3 models.

vLLM has strong logprob support, but it is a heavier serving stack and is not the best default for a local laptop or public-booth workflow.

A custom Hugging Face Transformers server gives Token Trail direct control over the generated token IDs, per-step prediction scores, top returned alternatives, trace conversion, and fallback behaviour.

---

## Target architecture

```text
Token Trail web UI
  -> Token Trail local app on port 3100
  -> optional HF trace client
  -> HF trace server on port 8600
  -> small local Transformers model
  -> trace-shaped JSON
  -> existing token replay UI
```

The HF trace server should be a separate process. Token Trail must still run without it.

---

## HF server API

### Endpoint

```text
POST /api/trace
```

### Request shape

```json
{
  "prompt": "Write one sentence about a robot at university.",
  "max_new_tokens": 48,
  "top_k": 5,
  "temperature": 0.3
}
```

### Response shape

```json
{
  "mode": "hf-live-trace",
  "model": "Qwen/Qwen2.5-1.5B-Instruct",
  "prompt": "Write one sentence about a robot at university.",
  "prompt_tokens": ["Write", " one", " sentence", " ..."],
  "steps": [
    {
      "selected_token": "A",
      "candidates": [
        {"token": "A", "probability": 0.31},
        {"token": "The", "probability": 0.22}
      ],
      "explanation": "Top returned alternatives from the local model for this token position."
    }
  ]
}
```

---

## Generation approach

The spike should use `transformers` generation with:

- `return_dict_in_generate=True`
- `output_scores=True`
- short `max_new_tokens`
- small `top_k`
- one short prompt at a time

For each generated token, take the matching score vector, apply softmax, select the top returned alternatives, and build a Token Trail step.

Use `output_logits=True` only if processed generation scores are not sufficient for display. For a public demo, processed scores are usually preferable because they match the decoding settings used for generation.

---

## Trace conversion rules

For each generated token:

1. Decode the selected token ID.
2. Compute display probabilities from the returned score vector.
3. Select a small top-k candidate list.
4. Ensure the selected token is present.
5. Deduplicate candidate token text.
6. Sort candidates by display probability.
7. Add a public-safe explanation.
8. Reject empty or excessively long traces.

Label bars as:

```text
Top returned alternatives for this token position.
```

Do not label them as:

```text
All possible next tokens.
```

---

## Configuration after spike succeeds

Add these only after the standalone server spike works:

```env
TOKEN_TRAIL_HF_TRACE_ENABLED=false
TOKEN_TRAIL_HF_TRACE_URL=http://127.0.0.1:8600/api/trace
TOKEN_TRAIL_HF_TRACE_MODEL=Qwen/Qwen2.5-1.5B-Instruct
TOKEN_TRAIL_HF_TRACE_TOP_K=5
TOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS=48
```

HF live trace should be disabled by default until rehearsed on the final machine.

---

## Suggested first models

Start small:

```text
Qwen/Qwen2.5-0.5B-Instruct
Qwen/Qwen2.5-1.5B-Instruct
Qwen/Qwen2.5-3B-Instruct
```

Choose reliability and clear short output over model quality.

---

## Implementation phases

### Phase A — Standalone server spike

Create a tiny local HF trace server or one-off probe that loads one small model and returns trace-shaped JSON.

Go/no-go:

- generated text appears;
- steps are non-empty;
- each step has candidate alternatives;
- response time is acceptable for a booth demo;
- memory use is acceptable on the target machine.

### Phase B — Pure trace helpers

Add helpers for score-to-candidate conversion and trace construction.

### Phase C — Server MVP

Run a small local service on port 8600 with one `/api/trace` endpoint.

### Phase D — Token Trail client

Add a Token Trail-side client with timeout handling and scripted fallback on every error.

### Phase E — UI integration

Reuse the existing scripted replay UI for `hf-live-trace` payloads.

### Phase F — Rehearsal and go/no-go

Use HF live trace only if it starts cleanly, generates a trace, replays cleanly, and falls back instantly when the server is stopped.

---

## Open Day rule

```text
Scripted trace mode remains mandatory.
HF live trace mode is optional.
Ollama live text mode remains available.
```

If the HF trace path is fragile, keep it disabled and run scripted trace plus Ollama live text mode.
