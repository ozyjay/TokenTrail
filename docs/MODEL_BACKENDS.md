# Model Backends

**Status:** Updated for optional HF Transformers trace server  
**Last updated:** 2026-06-20

Token Trail starts with scripted traces. Live model support should remain optional and should be added only when it improves the public explanation without weakening fallback reliability.

---

## Backend priority

| Priority | Backend | Use | Status |
|---|---|---|---|
| 1 | Scripted traces | Guaranteed fallback and primary teaching mode | Required |
| 2 | Ollama | Simple local live text generation | Working path |
| 3 | Custom Hugging Face Transformers trace server | Optional live token-trace path using generated token IDs and scores | Working optional path, rehearsal-gated |
| 4 | vLLM | Optional desktop/GPU experiment if HF trace server is too slow | Stretch/deferred |

---

## Current decision

Use this architecture:

```text
Scripted fallback: always available
Ollama: optional live text mode
HF Transformers trace server: optional live token-trace mode
vLLM: stretch/deferred
```

Do not depend on the HF trace server or vLLM during the public event unless they pass rehearsal on the final machine.

---

## Recommended first live-text model

For Ollama live text, start with:

```text
qwen3:1.7b
```

or:

```text
qwen3:4b
```

Use whichever is more reliable on the final machine. Ollama is for short live text, not the preferred live token-trace path.

---

## Recommended first trace-server models

For the custom HF trace server, start smaller than the Ollama live text path:

```text
Qwen/Qwen2.5-0.5B-Instruct
Qwen/Qwen2.5-1.5B-Instruct
Qwen/Qwen2.5-3B-Instruct
```

The goal is not maximum model quality. The goal is a short, reliable, replayable token trail.

---

## Port conventions

Token Trail follows the Open Day fixed local service map.

| Service | Port / URL | Notes |
|---|---|---|
| Token Trail scripted/kiosk app | `http://127.0.0.1:3100` | Current single-process app |
| Token Trail health check | `http://127.0.0.1:3100/health` | Staff/launcher readiness check |
| Future Token Trail backend/API | `http://127.0.0.1:8100` | Reserved for later frontend/backend split |
| HF trace server / shared model adapter | `http://127.0.0.1:8600` | Optional live trace adapter |
| Ollama | `http://127.0.0.1:11434` | External model runtime for live text |
| vLLM OpenAI-compatible server | `http://127.0.0.1:8000/v1` | Stretch/deferred; Token Trail itself must not use 8000 |

---

## Why not vLLM first?

vLLM is a strong serving system, especially for high-throughput and OpenAI-compatible APIs. But Token Trail needs one short, inspectable trace at a time. The main risks are public-demo reliability, clear explanation, and easy fallback, not throughput.

Use vLLM later only if:

- the RTX desktop is the final demo machine;
- the setup is stable under rehearsal;
- the HF trace server is too slow;
- vLLM gives a clear benefit for live token traces.

---

## Why HF Transformers for live traces?

A custom HF trace server can directly return the display shape Token Trail needs:

```json
{
  "prompt_tokens": ["Write", " a", " story"],
  "steps": [
    {
      "selected_token": "A",
      "candidates": [
        {"token": "A", "probability": 0.42},
        {"token": "The", "probability": 0.27}
      ],
      "explanation": "Top returned alternatives from the local model for this token position."
    }
  ]
}
```

This is simpler for Token Trail than trying to force Ollama or vLLM into the exact teaching format.

HF trace mode accepts the current edited live prompt from the Token Trail UI. After generation, the UI should display the HF server's returned `prompt_tokens`, because those are model-tokenised pieces rather than the temporary word-split preview used while typing.

---

## Fallback rule

If a live backend cannot provide a reliable, clear display:

1. fall back to scripted traces;
2. label the mode honestly;
3. keep reset instant;
4. do not store visitor prompts or responses.

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
