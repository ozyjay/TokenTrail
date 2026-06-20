# Token Trail

**Token Trail** is an Open Day demo that shows how a language model generates text one token at a time.

Visitors choose a curated prompt, then watch the system break the prompt into tokens, predict possible next tokens, select one, and repeat. Scripted traces remain the guaranteed teaching mode. Ollama can optionally provide short live text generation. A custom Hugging Face Transformers trace server is the preferred planned path for future live token traces.

> Public tagline: **Watch a language model predict text one token at a time.**

---

## Current status

Current app status: **scripted MVP with optional Ollama live text, warm-up, live-mode layout polish, and three prepared traces**.

The current app:

- runs as a local web demo at `http://127.0.0.1:3100`;
- follows the Open Day fixed local service port map;
- exposes a health check at `http://127.0.0.1:3100/health`;
- serves a big-screen UI from `web/`;
- uses scripted token traces from `src/token_trail/traces.py`;
- can optionally use a local Ollama model for short live text generation;
- keeps scripted fallback prompts curated and static;
- includes tests for traces, config, docs, adapters, server routes, and project setup;
- uses PowerShell scripts for local setup, testing, port checks, and launch.

Scripted mode remains the guaranteed fallback for Open Day.

---

## Backend direction

| Backend | Role | Status |
|---|---|---|
| Scripted traces | Mandatory fallback and primary teaching mode | Required |
| Ollama | Simple local live text generation | Working optional path |
| Custom Hugging Face Transformers trace server | Planned live token-trace path | Preferred next spike |
| vLLM | Desktop/GPU experiment if needed | Stretch/deferred |

The HF trace server is **not implemented yet**. It is planned as a separate local service on the reserved model-adapter port.

---

## Project layout

```text
src/
  token_trail/
    adapters/       # Local model backend adapters
    config.py       # Environment-driven runtime config
    ports.py        # Launch-time port checks
    server.py       # Tiny local HTTP server
    traces.py       # Scripted token traces and display helpers
web/
  index.html        # Big-screen UI shell
  app.js            # Token trail animation
  styles.css        # Public-display styling
docs/
  MODEL_BACKENDS.md
  TOKEN_TRAIL_ROADMAP.md
  HF_TRANSFORMERS_TRACE_SERVER_PLAN.md
  SLM_LIVE_TRACE_PLAN.md
  OLLAMA_PHASE_2_GENERATION_PLAN.md
  OLLAMA_WARMUP_PLAN.md
  STAFF_READINESS_CHECKLIST.md
scripts/
  setup.ps1
  test.ps1
  check_ports.ps1
  run.ps1
tests/
```

---

## Requirements

- Python 3.12
- Poetry
- PowerShell 7+
- Optional: Ollama for local live text generation
- Planned only: Hugging Face Transformers/PyTorch for future live trace server

For the Framework Desktop and final rehearsal, use the pinned Python version:

```bash
pyenv install 3.12.13
pyenv local 3.12.13
python --version
```

---

## Ports and local services

| Service | Default URL | Notes |
|---|---|---|
| Token Trail scripted/kiosk app | `http://127.0.0.1:3100` | Current app |
| Health check | `http://127.0.0.1:3100/health` | Staff/launcher readiness check |
| Future Token Trail backend/API | `http://127.0.0.1:8100` | Reserved for later split |
| HF trace server / model adapter | `http://127.0.0.1:8600` | Planned live trace server |
| Ollama | `http://127.0.0.1:11434` | External runtime for live text |
| vLLM OpenAI-compatible server | `http://127.0.0.1:8000/v1` | Stretch/deferred; Token Trail itself must not use 8000 |

Do not change ports randomly for rehearsal or Open Day. If a required port is occupied, the launch scripts should fail clearly.

---

## Useful commands

### Local setup and run

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/setup.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/test.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/check_ports.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/run.ps1
```

Then open:

```text
http://127.0.0.1:3100
```

### Optional HF trace probe

The Hugging Face trace probe uses an optional Poetry group so the main scripted demo stays lightweight. The wrapper installs that group before running the probe:

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --model Qwen/Qwen2.5-0.5B-Instruct --max-new-tokens 24 --top-k 5
```

If you prefer to install the optional group separately:

```bash
poetry install --with hf-trace
```

---

## Environment configuration

The app works without a `.env` file in scripted mode.

For machine-specific settings, copy:

```bash
cp .env.example .env
```

Key settings:

```text
TOKEN_TRAIL_BACKEND=scripted
TOKEN_TRAIL_HOST=127.0.0.1
TOKEN_TRAIL_PORT=3100
TOKEN_TRAIL_BACKEND_PORT=8100
```

Ollama live text settings include:

```text
TOKEN_TRAIL_BACKEND=ollama
TOKEN_TRAIL_OLLAMA_MODEL=qwen3:1.7b
TOKEN_TRAIL_OLLAMA_NUM_PREDICT=96
TOKEN_TRAIL_OLLAMA_TEMPERATURE=0.3
TOKEN_TRAIL_OLLAMA_TIMEOUT_SECONDS=45
TOKEN_TRAIL_OLLAMA_DISABLE_THINKING=true
TOKEN_TRAIL_OLLAMA_WARMUP_ENABLED=true
```

HF trace settings should only be added after the standalone HF trace server spike succeeds.

---

## Public wording

Use:

```text
The model breaks text into tokens, estimates likely next tokens, chooses one, and repeats.
```

Avoid:

```text
The AI is thinking.
```

Also avoid claiming that the demo shows private model reasoning. It shows an observable generation process and, where needed, a simplified or simulated visualisation.

---

## Data and privacy

Default rules:

- do not collect names, emails, phone numbers, or identifiable visitor data;
- do not store visitor prompts by default;
- clear live prompt edits on reset;
- keep logs technical and non-identifying;
- keep scripted fallback prompts curated and static.

---

## Fallback mode

Fallback mode is mandatory.

Fallback should support:

- scripted token traces;
- simulated candidate probabilities;
- replayable curated examples;
- at least three prepared traces;
- a clear label such as:

```text
Prepared demo mode: showing a saved generation trace.
```

Fallback mode should still look intentional and useful, not broken.

---

## Go/no-go criteria

Token Trail is Open Day ready only if:

- a visitor can understand the core idea in under 30 seconds;
- at least three curated prompts run cleanly;
- reset returns to a clean state instantly;
- scripted fallback works without a model;
- the UI is readable on a TV from 2–3 metres away;
- staff can explain the demo with a one-sentence script;
- it can run for 60 minutes without manual debugging;
- it starts from cold boot without developer intervention;
- assigned ports match the Open Day port map;
- launch scripts fail clearly if the configured port is occupied.

---

## Staff script

```text
This shows the basic loop behind language models. The model turns your text into tokens, predicts likely next tokens, chooses one, and repeats.
```

Optional follow-up:

```text
The probabilities are not guarantees. They show likely continuations, and the model can still produce wrong or surprising text.
```

---

## Development roadmap

See:

```text
docs/TOKEN_TRAIL_ROADMAP.md
```

Next concrete build step:

```text
Run the standalone HF Transformers trace server spike from docs/HF_TRANSFORMERS_TRACE_SERVER_PLAN.md.
```

---

## License

TBD.

---

## Acknowledgement

Built as part of the Open Day Demos project for demonstrating AI concepts in an engaging, accurate, and public-friendly way.
