# SLM Live Trace Plan

**Project:** Token Trail  
**Status:** Planning  
**Last updated:** 2026-06-19

---

## Goal

Add an optional **SLM Live Trace Mode** that turns a local Ollama model response into the same kind of replayable token trail used by the scripted fallback.

The target behaviour is:

```text
curated prompt
  -> local Ollama generation with logprobs/top_logprobs
  -> convert generated tokens and returned candidate alternatives into trace steps
  -> replay those steps through the existing Token Trail animation
```

This should improve the teaching value without making live generation mandatory.

---

## Current baseline

Token Trail currently has two main display modes:

| Mode | Source | Display |
|---|---|---|
| Scripted trace | Prepared trace data | Token-by-token replay with candidate bars |
| Live local model | Ollama generated text | Paragraph-style generated text |

SLM Live Trace Mode would add a third path:

| Mode | Source | Display |
|---|---|---|
| SLM live trace | Ollama generated text plus returned logprobs/top_logprobs | Token-by-token replay with model-returned candidate bars |

---

## Important terminology

Use **logprobs** or **top returned alternatives**, not "full logits".

The Ollama generate endpoint can return log probability information for generated output tokens when logprobs are enabled. It can also return a limited number of top alternatives per token position. That is enough for a useful public demo, but it is not the same as exposing the full raw logits vector for every vocabulary item.

Recommended public wording:

```text
Live local model trace: candidate tokens from the selected local model.
```

Avoid:

```text
This shows the model's private reasoning.
```

```text
These are all possible next tokens.
```

```text
These probabilities are exact guarantees.
```

---

## Non-goals

Do not build these in the first SLM trace version:

- streaming-first visualisation;
- raw full-logit inspection;
- private reasoning display;
- unsupervised visitor free text;
- prompt or response logging;
- replacement of scripted fallback;
- vLLM support;
- multi-user mode;
- QR/phone control.

---

## Recommended architecture

### Existing live text path

```text
web/app.js
  -> POST /api/generate-trace
  -> OllamaAdapter.generate()
  -> generated_text
  -> paragraph display
```

### Proposed live trace path

```text
web/app.js
  -> POST /api/generate-live-trace
  -> OllamaAdapter.generate_trace()
  -> trace conversion helper
  -> trace-shaped payload
  -> existing token trail replay UI
```

The first implementation should be **non-streaming**:

```text
wait for the full local model response
  -> parse logprobs/top_logprobs
  -> build all trace steps
  -> replay locally in the browser
```

This is simpler, more deterministic, and better for a public booth than animating during model streaming.

---

## Proposed API

### Endpoint

```text
POST /api/generate-live-trace
```

### Request

```json
{
  "runtime_id": "ollama:qwen3:1.7b",
  "trace_id": "robot-university"
}
```

If staff-editable prompts are enabled in the current UI, the endpoint may accept an optional prompt override:

```json
{
  "runtime_id": "ollama:qwen3:1.7b",
  "trace_id": "robot-university",
  "prompt": "Write a short story about a robot at university."
}
```

Prompt overrides must remain non-persistent and resettable.

### Success response

```json
{
  "mode": "live-trace",
  "runtime_id": "ollama:qwen3:1.7b",
  "fallback_used": false,
  "trace": {
    "id": "live-robot-university",
    "title": "Live local model trace",
    "prompt": "Write a short story about a robot at university.",
    "prompt_tokens": ["Write", "a", "short", "story", "..."],
    "steps": [
      {
        "selected_token": "Once",
        "candidates": [
          {"token": "Once", "probability": 0.42},
          {"token": "The", "probability": 0.21},
          {"token": "A", "probability": 0.12}
        ],
        "explanation": "The selected token and alternatives are from the local model response."
      }
    ]
  }
}
```

### Fallback response

Use the existing scripted fallback shape when live trace generation fails:

```json
{
  "mode": "scripted-fallback",
  "runtime_id": "ollama:qwen3:1.7b",
  "fallback_used": true,
  "message": "Live trace unavailable",
  "trace": {}
}
```

---

## Trace conversion rules

For each generated output token returned with logprobs:

1. Use the returned token as `selected_token`.
2. Use `top_logprobs` as candidate alternatives.
3. Ensure the selected token is included in the candidate list.
4. Deduplicate candidates by token text.
5. Convert returned logprobs to display probabilities using a stable softmax over the returned candidate set.
6. Sort candidates from highest to lowest display probability.
7. Limit candidates to a small number, such as 5.
8. Add an explanation that does not claim to show private reasoning.

### Probability display rule

The probability bars are normalised over the returned candidates, not necessarily over the model's full vocabulary.

Recommended label:

```text
Top returned alternatives for this token position.
```

Do not label them as:

```text
All possible next tokens.
```

---

## Proposed data helpers

Add pure conversion helpers before wiring the UI:

```text
src/token_trail/live_trace.py
```

Candidate functions:

```python
def normalise_logprobs(candidates: list[dict]) -> list[dict]:
    ...


def build_live_trace(
    *,
    trace_id: str,
    title: str,
    prompt: str,
    prompt_tokens: list[str],
    response_text: str,
    logprobs: list[dict],
    max_candidates: int = 5,
) -> dict:
    ...
```

Keep these helpers independent of Ollama networking so they are easy to test.

---

## Proposed adapter changes

### File

```text
src/token_trail/adapters/ollama.py
```

Add a new method rather than changing existing `generate()` immediately:

```python
def generate_with_logprobs(
    self,
    model: str,
    prompt: str,
    *,
    timeout_seconds: float,
    max_tokens: int,
    temperature: float,
    disable_thinking: bool,
    top_logprobs: int = 5,
) -> dict:
    ...
```

Payload should include:

```json
{
  "model": "qwen3:1.7b",
  "prompt": "...",
  "stream": false,
  "options": {
    "num_predict": 64,
    "temperature": 0.3,
    "logprobs": true,
    "top_logprobs": 5
  }
}
```

The method should return the parsed response payload, after validating:

- valid JSON;
- non-empty `response`;
- `logprobs` is a list;
- at least one token-level logprob item is present.

If validation fails, raise `AdapterError` and let the server fall back to a scripted trace.

---

## Configuration

Add feature-gated settings:

```env
TOKEN_TRAIL_OLLAMA_LIVE_TRACE_ENABLED=false
TOKEN_TRAIL_OLLAMA_TRACE_TOP_LOGPROBS=5
TOKEN_TRAIL_OLLAMA_TRACE_MAX_TOKENS=64
```

Recommended starting defaults:

| Setting | Default | Why |
|---|---:|---|
| `TOKEN_TRAIL_OLLAMA_LIVE_TRACE_ENABLED` | `false` | Keep existing live text path stable |
| `TOKEN_TRAIL_OLLAMA_TRACE_TOP_LOGPROBS` | `5` | Enough alternatives for teaching display |
| `TOKEN_TRAIL_OLLAMA_TRACE_MAX_TOKENS` | `64` | Keeps replay short and booth-friendly |

---

## UI behaviour

The first UI version can add a small mode choice for available Ollama runtimes:

```text
Live text
Live trace
Prepared trace
```

A simpler first slice is also acceptable:

```text
If live trace enabled and runtime supports it, Generate live trail returns mode=live-trace and reuses the scripted replay UI.
```

### Labels

For live trace mode, show:

```text
Live Local Model Trace
```

In the candidate panel, show a compact note:

```text
Candidate tokens are the top returned alternatives from the selected local model.
```

Footer note remains:

```text
This demo shows an observable generation process. It does not show private model reasoning.
```

---

## Fallback rules

Fallback to the existing prepared trace if:

- Ollama is unavailable;
- the selected model is unavailable;
- logprobs are not returned;
- top alternatives are empty;
- timeout occurs;
- response JSON is invalid;
- trace conversion fails;
- generated trace would be too long or empty.

The UI must never become stuck waiting for live trace generation.

---

## Implementation phases

### Phase A — API capability spike

Goal: confirm the actual installed Ollama version and selected SLM return usable `logprobs` and `top_logprobs`.

Manual check:

```powershell
ollama list
```

Then run a small local request using `stream=false`, `logprobs=true`, and `top_logprobs=5`.

Go/no-go:

- Continue only if the local model returns a `logprobs` array with token entries and top alternatives.
- If not, keep live text mode and scripted trace mode.

### Phase B — Adapter method and tests

Add `generate_with_logprobs()` with mocked HTTP tests.

Tests:

```text
test_generate_with_logprobs_posts_expected_payload
test_generate_with_logprobs_returns_payload
test_generate_with_logprobs_rejects_missing_logprobs
test_generate_with_logprobs_handles_timeout
test_generate_with_logprobs_handles_invalid_json
```

### Phase C — Trace conversion helpers

Add pure helpers for logprob normalisation and trace construction.

Tests:

```text
test_normalise_logprobs_uses_stable_softmax
test_build_live_trace_includes_selected_token
test_build_live_trace_deduplicates_candidates
test_build_live_trace_limits_candidate_count
test_build_live_trace_rejects_empty_steps
```

### Phase D — Server endpoint

Add `POST /api/generate-live-trace` or feature-gate live trace inside `POST /api/generate-trace`.

Preferred first implementation: separate endpoint, because it is easier to test and does not disturb the working live text path.

Tests:

```text
test_generate_live_trace_returns_trace_payload
test_generate_live_trace_falls_back_when_logprobs_missing
test_generate_live_trace_returns_400_for_unknown_runtime
test_generate_live_trace_uses_prompt_override_without_persisting_it
```

### Phase E — UI replay integration

Reuse the existing scripted trace replay code:

```text
receive mode=live-trace
  -> set currentTrace to payload.trace
  -> render prompt tokens
  -> reset generated state
  -> startPreparedTrail()
```

Rename UI wording where needed so this does not say prepared trace when it is a live trace.

### Phase F — Open Day hardening

Add manual rehearsal steps and go/no-go checks.

The demo is ready to use live trace mode only if:

- warm-up succeeds;
- live trace generation succeeds;
- replay completes cleanly;
- fallback still works if Ollama is stopped;
- display remains readable from 2–3 metres.

---

## Recommended next tiny slice

Do not implement all phases at once.

Start with:

```text
Phase A — local API capability spike
```

Then commit a small adapter-only slice if the spike succeeds.

---

## Open Day rule

```text
Scripted trace mode remains mandatory.
SLM live trace mode is optional.
```

If SLM live trace is fragile on the final machine, keep it disabled and use scripted trace plus live text mode.
