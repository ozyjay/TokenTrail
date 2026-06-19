# Ollama Phase 2 — Live Generation Plan

**Project:** Token Trail  
**Status:** Implemented, with later editable-prompt slice  
**Last updated:** 2026-06-20

---

## Goal

Implement live generation through Ollama while preserving scripted traces as the guaranteed fallback.

The first live path used existing curated trace prompts. A later slice added staff-editable prompt entry only for available local Ollama runtimes. Scripted mode and scripted fallback still use fixed prepared prompts.

```text
runtime_id + trace_id
  -> validate selected Ollama runtime
  -> load curated prompt, optionally overridden by live prompt text
  -> call Ollama generate
  -> map response to display trace
  -> fallback to scripted trace on failure
```

---

## Current Starting Point

Already implemented:

- Ollama model discovery
- Runtime selector UI
- Runtime availability detection
- Health endpoint
- Scripted trace fallback
- Fixed local service ports
- `.env` configuration loading
- No import-time config loading

The runtime selector can already switch between:

```text
Scripted fallback
Ollama model A
Ollama model B
vLLM model A
```

The next step is making Ollama generate real content.

---

## Scope

### Included

- Curated prompt → Ollama generation
- Runtime-selected Ollama model
- Live generation endpoint
- Graceful fallback to scripted traces
- Timeout handling
- Unit tests

### Excluded

- Unsupervised open-ended visitor prompts
- Chat history
- Conversations
- QR integration
- vLLM generation
- Real token probabilities
- Multi-user support

---

## Architecture

Current:

```text
UI
  -> scripted traces
```

Phase 2:

```text
UI
  -> runtime selector
  -> Ollama adapter
  -> local Ollama
  -> generated response
```

Fallback path:

```text
UI
  -> scripted trace
```

---

## API Design

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

### Response

```json
{
  "mode": "live",
  "runtime_id": "ollama:qwen3:4b",
  "fallback_used": false,
  "generated_text": "A small robot joined orientation and learned to ask better questions."
}
```

### Fallback Response

```json
{
  "mode": "scripted-fallback",
  "runtime_id": "ollama:qwen3:4b",
  "fallback_used": true,
  "message": "Live generation unavailable",
  "trace": { }
}
```

---

## Adapter Changes

### File

```text
src/token_trail/adapters/ollama.py
```

Add:

```python
def generate(
    self,
    model: str,
    prompt: str,
    *,
    timeout_seconds: float = 20.0,
    max_tokens: int = 80,
) -> str:
    ...
```

---

## Ollama API

Use:

```text
POST /api/generate
```

Example request:

```json
{
  "model": "qwen3:4b",
  "prompt": "Write a short story about a robot at university.",
  "stream": false,
  "options": {
    "num_predict": 80,
    "temperature": 0.7
  }
}
```

---

## UI Behaviour

### Scripted Mode

Button:

```text
Start Trail
```

### Live Ollama Mode

Button:

```text
Generate Live Trail
```

### Unavailable Runtime

Button:

```text
Show Prepared Trail
```

---

## Display Labels

### Live

```text
Live Local Model Mode
```

### Fallback

```text
Prepared Demo Mode
```

### Failure

```text
Live generation unavailable — showing prepared trace
```

---

## Probability Display

For Phase 2:

Do **not** claim to show real token probabilities.

Options:

### Preferred

```text
Live mode:
Generated text only

Scripted mode:
Probability bars visible
```

### Alternative

Show approximation label:

```text
Probabilities approximated for display
```

The preferred option is simpler and more honest.

---

## Fallback Rules

Fallback immediately if:

- Ollama not running
- Model unavailable
- Timeout
- Empty response
- Invalid JSON
- Unknown runtime

The UI must never become stuck.

---

## Error Handling

| Failure | Behaviour |
|----------|------------|
| Ollama offline | Use scripted fallback |
| Model missing | Use scripted fallback |
| Timeout | Use scripted fallback |
| Bad response | Use scripted fallback |
| Runtime not found | Return HTTP 400 |
| Empty output | Use scripted fallback |

---

## Testing

### Unit Tests

Create:

```text
tests/test_ollama_adapter.py
```

Tests:

```text
test_ollama_generate_posts_expected_payload
test_ollama_generate_returns_response_text
test_ollama_generate_handles_timeout
test_ollama_generate_handles_connection_error
test_ollama_generate_handles_bad_json
test_generation_failure_uses_scripted_fallback
test_generate_trace_returns_live_response
test_unknown_runtime_returns_400
test_server_config_is_not_loaded_at_import_time
```

### Requirements

Unit tests must not require Ollama to be installed.

Use mocked HTTP responses.

---

## Manual Test

```powershell
ollama list

.\scripts\test.ps1

.\scripts\run.ps1
```

Open:

```text
http://127.0.0.1:3100
```

Health:

```text
http://127.0.0.1:3100/health
```

---

## Acceptance Criteria

Phase 2 is complete when:

- Runtime-selected Ollama model generates text
- Curated prompts work
- Available Ollama runtimes can use an edited live prompt
- Failure automatically falls back to scripted mode
- No UI crashes
- Unit tests pass without Ollama installed
- Manual test succeeds with a real local model
- No visitor data is stored
- Health endpoint reports runtime state

---

## Recommended Build Order

### Step 1

Implement:

```python
OllamaAdapter.generate()
```

with tests.

### Step 2

Add:

```text
POST /api/generate-trace
```

### Step 3

Map generated text into a display payload.

### Step 4

Wire UI button to live endpoint.

### Step 5

Add fallback labels.

### Step 6

Test against:

```text
qwen3:4b
qwen3:1.7b
```

---

## Open Day Rule

Scripted traces remain mandatory.

```text
Live generation is optional.
Fallback mode is required.
```

The demo must still be useful if Ollama is unavailable.
