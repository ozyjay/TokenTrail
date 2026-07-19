# Model backends

Token Trail supports two runtime families:

| Runtime | Role |
| --- | --- |
| ModelDeck | Primary live token traces from a configured, externally managed demo route |
| Prepared replay | Explicit deterministic fallback mode |

Token Trail discovers the configured public aliases `qwen-0-5b`, `qwen-1-5b` and `qwen-3b` through ModelDeck `GET /v1/models`, preserving gateway order and the advertised `ready` state. It requests native traces through `POST /native/autoregressive/trace`. It does not know deployment IDs or worker ports, and does not own lifecycle, warm-up, model downloads or GPU memory.

If the gateway or a configured alias is unavailable, Token Trail starts normally and reports that runtime as unavailable. Scripted mode remains ready.
