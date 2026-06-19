# Ollama Warm-Up Plan

**Project:** Token Trail  
**Status:** Implementation complete; manual rehearsal found live-generation tuning follow-up  
**Last updated:** 2026-06-19

---

## Goal

Reduce first-click latency for live Ollama generation by warming the selected local model before a visitor presses **Generate live trail**.

The public demo should feel responsive, but scripted fallback must remain mandatory.

```text
Runtime selected
  -> warm selected Ollama model
  -> keep model loaded
  -> visitor clicks Generate live trail
  -> generation starts without cold-load delay where practical
```

---

## Why this matters

Cold local model load can make the first live generation feel slow or cause the app to fall back to the prepared trace. Warm-up separates model loading from visitor interaction.

This is especially useful at Open Day because:

- visitors should not wait silently;
- staff need a clear readiness signal;
- live generation should be optional, not a single point of failure;
- scripted fallback must remain available at all times.

---

## Public wording

Use:

```text
Warming local model...
```

```text
Local model ready
```

```text
Live model not warmed — prepared trace still available
```

Avoid:

```text
The AI is thinking
```

Warm-up is a system readiness state, not a claim about private model reasoning.

---

## Phase 1 — Backend-only warm-up method

### Goal

Add the smallest safe backend warm-up primitive.

### Files

```text
src/token_trail/adapters/ollama.py
tests/test_ollama_adapter.py
```

### Implementation

Add:

```python
def warmup(
    self,
    model: str,
    *,
    timeout_seconds: float = 45.0,
    keep_alive: str = "30m",
) -> None:
    ...
```

The method should POST to:

```text
/api/generate
```

Payload:

```json
{
  "model": "qwen3:1.7b",
  "prompt": "/no_think\n\nReply with: ready",
  "stream": false,
  "keep_alive": "30m",
  "options": {
    "num_predict": 2,
    "temperature": 0
  }
}
```

### Behaviour

- Treat any valid JSON response as warm-up success.
- Raise `AdapterError` on timeout, HTTP/URL/OS error, or invalid JSON.
- Do not require real Ollama in tests.

Warm-up does not need a non-empty `response` field because the goal is to load and keep the model resident, not to collect useful generated text.

### Tests

Add tests for:

```text
test_ollama_warmup_posts_expected_payload
test_ollama_warmup_handles_timeout
test_ollama_warmup_handles_bad_json
```

### Go/no-go

Proceed when the test suite passes and no server/UI behaviour has changed.

---

## Phase 2 — Warm-up runtime configuration

### Goal

Make warm-up settings explicit and configurable.

### Files

```text
src/token_trail/config.py
.env.example
tests/test_config.py
```

### Settings

Add:

```env
TOKEN_TRAIL_OLLAMA_WARMUP_ENABLED=true
TOKEN_TRAIL_OLLAMA_WARMUP_TIMEOUT_SECONDS=45
TOKEN_TRAIL_OLLAMA_KEEP_ALIVE=30m
```

### Defaults

Recommended defaults:

```text
warmup_enabled: true
warmup_timeout_seconds: 45.0
keep_alive: 30m
```

### Tests

Add config tests for:

```text
default warm-up settings
environment overrides
.env file overrides
process environment wins over .env
```

### Go/no-go

Proceed when configuration is loaded without affecting scripted mode.

---

## Phase 3 — Server warm-up endpoint

### Goal

Expose a safe endpoint the UI can call after runtime selection.

### File

```text
src/token_trail/server.py
tests/test_server.py
```

### Endpoint

```text
POST /api/runtime/warmup
```

### Request

```json
{
  "runtime_id": "ollama:qwen3:1.7b"
}
```

### Success response

```json
{
  "status": "ready",
  "runtime_id": "ollama:qwen3:1.7b",
  "message": "Local model warmed"
}
```

### Scripted response

```json
{
  "status": "skipped",
  "runtime_id": "scripted:prepared-traces",
  "message": "Scripted runtime does not need warm-up"
}
```

### Disabled response

```json
{
  "status": "skipped",
  "runtime_id": "ollama:qwen3:1.7b",
  "message": "Ollama warm-up disabled"
}
```

### Failure response

```json
{
  "status": "fallback",
  "runtime_id": "ollama:qwen3:1.7b",
  "message": "Could not warm local model; scripted fallback remains available"
}
```

### Behaviour

- Validate `runtime_id` with the existing runtime selection logic.
- Do not crash if warm-up fails.
- Do not switch off scripted fallback.
- Return HTTP 400 for unknown runtime IDs.
- Return a skipped/fallback status for unavailable Ollama models.

### Tests

Add tests for:

```text
test_runtime_warmup_returns_ready_for_available_ollama
test_runtime_warmup_skips_scripted_runtime
test_runtime_warmup_returns_fallback_on_adapter_error
test_runtime_warmup_returns_400_for_unknown_runtime
```

### Go/no-go

Proceed when warm-up failures are visible but never break the app.

---

## Phase 4 — UI warm-up state

### Goal

Warm the selected model before the visitor clicks generate.

### Files

```text
web/app.js
web/styles.css
```

### Behaviour

When an available Ollama runtime is selected:

1. Disable the **Generate live trail** button.
2. Show:

```text
Warming local model...
```

3. Call:

```text
POST /api/runtime/warmup
```

4. On success, show:

```text
Local model ready
```

5. Re-enable the generate button.

6. On failure, show:

```text
Live model not warmed — prepared trace still available
```

7. Re-enable the generate button so the normal live/fallback path can still run.

### Constraints

- Reset must stay usable.
- Scripted mode must not be blocked.
- Do not add open text input.
- Do not store prompts or generated responses.
- Avoid “AI thinking” wording.

### Go/no-go

Proceed when the UI clearly communicates warm-up state and generation still falls back correctly.

---

## Phase 5 — Staff readiness and manual rehearsal

### Goal

Give staff a simple readiness routine.

### Setup checklist

```powershell
ollama list
.\scripts\test.ps1
.\scripts\run.ps1
```

Open:

```text
http://127.0.0.1:3100
```

Then:

1. Select the preferred Ollama runtime.
2. Wait for **Local model ready**.
3. Click **Generate live trail** once.
4. Confirm live text appears.
5. Reset.
6. Switch to scripted mode and confirm prepared trace still works.

### Staff script

```text
This mode uses a local model running on this computer. The first run may take a moment while the model is loaded. If live generation is unavailable, the demo switches to a prepared trace.
```

### Go/no-go

Use live mode only if warm-up and one live generation succeed during setup. Otherwise, run scripted mode.

---

## Recommended implementation order

Do not implement all phases at once.

```text
1. Adapter warmup method and tests
2. Config settings and tests
3. Server endpoint and tests
4. UI warm-up status
5. Staff readiness checklist
```

Each phase should pass tests before moving to the next.

---

## Open Day rule

```text
Live generation is optional.
Fallback mode is required.
```

The demo must still be useful if Ollama is unavailable, slow, or not warmed.

## Current rehearsal note

Local warm-up against Ollama succeeded for the configured Qwen runtime, and the app safely fell back to the prepared trace when live generation returned an empty visible response. Treat warm-up as complete, but keep live mode behind setup verification until generation settings produce a short visible answer during rehearsal.
