# Model backends

Token Trail supports two runtime families:

| Runtime | Role |
| --- | --- |
| ModelDeck | Primary live token traces from ready, externally managed Qwen workers |
| Scripted prepared traces | Mandatory deterministic fallback |

Token Trail discovers `qwen-0-5b`, `qwen-1-5b`, and `qwen-3b` through ModelDeck `GET /v1/models`, then requests a native trace through `POST /native/autoregressive/trace`. It does not own worker lifecycle, warm-up, model downloads, or GPU memory.

If the gateway or a configured alias is unavailable, Token Trail starts normally and reports that runtime as unavailable. Scripted mode remains ready.
