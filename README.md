# Token Trail

Token Trail is an Open Day demo that replays next-token choices and their probabilities. Its primary live backend is the externally managed [ModelDeck](../ModelDeck/README.md) gateway; prepared replay remains a separate, explicit mode.

## Runtime modes

| Runtime | Purpose | Availability |
| --- | --- | --- |
| `modeldeck:<alias>` | Live token traces from a configured ModelDeck demo route | Primary when the route is ready |
| `scripted:prepared-traces` | Curated deterministic traces | Always available |

The active “2026 OpenDay Demo” set exposes the public aliases `qwen-0-5b`, `qwen-1-5b` and `qwen-3b`. Token Trail reads `GET /v1/models`, keeps those aliases in gateway order and uses each route's `ready` field without assuming its worker is running. It sends bounded requests to `POST /native/autoregressive/trace` through the server-side adapter. ModelDeck owns route configuration, physical model selection, lifecycle and GPU memory; Token Trail never starts, warms, stops or downloads models and has no cloud fallback.

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

Open the ModelDeck management UI at <http://127.0.0.1:3600>, select the required worker for the active demo set and start it there. Then start Token Trail:

```powershell
pwsh -NoProfile -File ./scripts/run.ps1
```

Open <http://127.0.0.1:3100>. The runtime selector shows all three public aliases and their current readiness. If a configured route is not ready, Token Trail directs the operator to ModelDeck's Workers view. It does not silently switch aliases or substitute prepared output. To use prepared content, explicitly select “Prepared replay mode”.

Stop Token Trail without affecting ModelDeck or unrelated Python processes:

```powershell
pwsh -NoProfile -File ./scripts/stop.ps1
```

## Configuration

Copy `.env.example` to `.env` for machine-specific overrides. The normal live configuration is:

```dotenv
TOKEN_TRAIL_MODEL_CONFIG_PATH=config/models.json
TOKEN_TRAIL_BACKEND=modeldeck
TOKEN_TRAIL_MODELDECK_ENABLED=true
TOKEN_TRAIL_MODELDECK_URL=http://127.0.0.1:8600
TOKEN_TRAILS_MODEL=qwen-1-5b
TOKEN_TRAIL_MODELDECK_MODELS=qwen-0-5b,qwen-1-5b,qwen-3b
TOKEN_TRAIL_MODELDECK_INSTRUCTIONS_FILE=config/instructions/modeldeck_default.txt
```

The fixed hidden instruction keeps public responses short and suitable for the demo. Token Trail sends it as a system message while retaining the staff-entered prompt as the visible prompt.

For live traces, Token Trail preserves ModelDeck's generated tokens, probabilities, returned alternatives, timing/metrics, complete prompt token metadata and user-prompt token metadata. The public prompt view uses only `user_prompt_tokens`; complete prompt tokens can contain hidden instructions or chat-template markers and are never rendered. Invalid or misaligned metadata, including model-control markers leaked into generated tokens or alternatives, is treated as `invalid_worker_trace_metadata` and is not shown as a successful trace.

Each browser request supplies a bounded request ID. Resetting during generation aborts the browser request and forwards cancellation through ModelDeck's stable `POST /v1/requests/{request_id}/cancel` route. ModelDeck's structured `local_provider_unavailable` response is shown as a local readiness state. There is no cloud inference or model download path.

## Behaviour and privacy

- Live output is trimmed to the first complete sentence after at least eight generated steps.
- Once a trail starts, visitors can pause and scrub backwards or forwards through its generated tokens.
- Candidate bars are top returned alternatives from the local model, not private reasoning.
- Gateway, route, local readiness, cancellation and invalid-metadata states are reported distinctly without presenting prepared output as a live result.
- Visitor prompts and generated responses are not stored by default.

## Verification

```powershell
pwsh -NoProfile -File ./scripts/test.ps1
```
