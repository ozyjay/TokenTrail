# Token Trail

Token Trail is an Open Day demo that replays next-token choices and their probabilities. Its primary live backend is the externally managed [ModelDeck](../ModelDeck/README.md) gateway; scripted prepared traces remain the guaranteed fallback.

## Runtime modes

| Runtime | Purpose | Availability |
| --- | --- | --- |
| `modeldeck:<alias>` | Live token traces from a ready ModelDeck Qwen worker | Primary when the alias is ready |
| `scripted:prepared-traces` | Curated deterministic traces | Always available |

The configured aliases are `qwen-0-5b`, `qwen-1-5b`, and `qwen-3b`. ModelDeck owns model discovery, loading, warm-up, process isolation, and GPU memory. Token Trail only reads `GET /v1/models` and sends generation requests to `POST /native/autoregressive/trace`; it never starts, warms, stops, or downloads models.

## Setup and run

Poetry is required. Install it once with `pipx`, then restart PowerShell so the updated `PATH` is loaded:

```powershell
pipx install poetry
poetry --version
```

Install Token Trail's Python environment:

```powershell
pwsh -NoProfile -File ./scripts/setup.ps1
```

Start ModelDeck separately and make the required Qwen workers ready using its operator console or management API. Then start this demo:

```powershell
pwsh -NoProfile -File ./scripts/run.ps1
```

Open <http://127.0.0.1:3100>. If ModelDeck is unreachable or an alias has no ready worker, that runtime is shown as unavailable and the scripted mode remains usable.

## Configuration

Copy `.env.example` to `.env` for machine-specific overrides. The normal live configuration is:

```dotenv
TOKEN_TRAIL_MODEL_CONFIG_PATH=config/models.json
TOKEN_TRAIL_BACKEND=modeldeck
TOKEN_TRAIL_MODELDECK_ENABLED=true
TOKEN_TRAIL_MODELDECK_URL=http://127.0.0.1:8600
TOKEN_TRAIL_MODELDECK_MODEL=qwen-1-5b
TOKEN_TRAIL_MODELDECK_MODELS=qwen-0-5b,qwen-1-5b,qwen-3b
TOKEN_TRAIL_MODELDECK_INSTRUCTIONS_FILE=config/instructions/modeldeck_default.txt
```

The fixed hidden instruction keeps public responses short and suitable for the demo. Token Trail sends it as a system message while retaining the staff-entered prompt as the visible prompt.

ModelDeck protocol v1 returns prompt token IDs rather than decoded prompt-token strings. Token Trail displays those IDs in angle brackets after generation; generated tokens and candidate bars use the exact decoded tokens and probabilities returned by the worker.

## Behaviour and privacy

- Live output is trimmed to the first complete sentence after at least eight generated steps.
- Candidate bars are top returned alternatives from the local model, not private reasoning.
- A failed, slow, malformed, or incomplete live trace falls back to the selected prepared trace.
- Visitor prompts and generated responses are not stored by default.

## Verification

```powershell
pwsh -NoProfile -File ./scripts/test.ps1
```
