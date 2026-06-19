# Model Backends

Token Trail starts with scripted traces. Live model support should be added only after the visual MVP is understandable and reliable.

---

## Backend priority

| Priority | Backend | Use |
|---|---|---|
| 1 | Scripted traces | Guaranteed fallback and development mode |
| 2 | Ollama | First live SLM path for Framework Desktop testing |
| 3 | vLLM | Optional high-throughput/OpenAI-compatible path after rehearsal testing |

---

## Recommended first model

Start with:

```text
qwen3:4b
```

Why:

- small enough for local Open Day use;
- capable enough for short curated or staff-edited prompts;
- practical for demos where reliability matters more than benchmark performance;
- can be swapped for a smaller fallback such as `qwen3:1.7b` if needed.

---

## Port conventions

Token Trail follows the Open Day fixed local service map.

| Service | Port / URL | Notes |
|---|---|---|
| Token Trail scripted/kiosk app | `http://127.0.0.1:3100` | Current single-process MVP |
| Token Trail health check | `http://127.0.0.1:3100/health` | Staff/launcher readiness check |
| Future Token Trail backend/API | `http://127.0.0.1:8100` | Reserved for later frontend/backend split |
| Shared model adapter | `http://127.0.0.1:8600` | Optional future adapter over Ollama/vLLM/llama.cpp |
| Ollama | `http://127.0.0.1:11434` | External model runtime |
| vLLM OpenAI-compatible server | `http://127.0.0.1:8000/v1` | External model runtime; Token Trail itself must not use 8000 |

---

## Open Day serving rule

Installing both Ollama and vLLM on the Framework Desktop is fine.

Depending on both during the public event is not ideal.

Recommended public setup:

```text
Scripted fallback: always available
Live backend: one active backend only
Default live backend: Ollama
Experimental backend: vLLM
```

---

## Why not vLLM-only at first?

vLLM is a strong serving system, especially for OpenAI-compatible APIs and higher-throughput use. But for Token Trail's early MVP, the main risks are not throughput. The main risks are:

- making token prediction understandable;
- keeping the display readable;
- recovering quickly during a public demo;
- avoiding model-server complexity while several demos run at once.

Use vLLM later if the full booth architecture benefits from one shared OpenAI-compatible local endpoint.

---

## Future adapter shape

Keep backend-specific details behind an adapter so the UI does not care where tokens come from.

```text
Token Trail UI
  -> TokenTrail API
  -> Backend adapter
      -> scripted trace
      -> Ollama
      -> vLLM/OpenAI-compatible endpoint
```

Each adapter should return the same display-friendly structure:

```json
{
  "prompt_tokens": ["Write", "a", "story"],
  "steps": [
    {
      "selected_token": "A",
      "candidates": [
        {"token": "A", "probability": 0.42},
        {"token": "The", "probability": 0.27}
      ],
      "explanation": "Common story openings are likely after this prompt."
    }
  ]
}
```

If the live backend cannot provide real top-k probabilities, the adapter should either:

1. clearly label the display as approximated; or
2. fall back to scripted traces.

---

## Rehearsal test

Before using a live backend publicly, run this together for at least one hour:

- VoiceChanger;
- Token Trail scripted mode on port 3100;
- Token Trail live backend, if enabled;
- any QR/local web server demo;
- TV output;
- browser in kiosk/full-screen mode.

Pass condition:

```text
No crashes, no memory pressure, no port conflicts, clean reset, and fallback works instantly.
```
