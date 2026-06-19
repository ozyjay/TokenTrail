# Token Trail

**Token Trail** is an Open Day demo that shows how a language model generates text one token at a time.

Visitors choose a curated prompt, then watch the system break the prompt into tokens, predict possible next tokens, select one, and repeat. The goal is to make language model generation visible, understandable, and honest without claiming to show hidden model reasoning.

> Public tagline: **Watch a language model predict text one token at a time.**

---

## Current status

Initial scripted visual MVP scaffold with optional Ollama live generation.

The current app:

- uses Poetry, matching the VoiceChanger project style;
- targets Python 3.12, with `.python-version` pinned to `3.12.13` for reproducible Framework Desktop setup;
- runs as a local web demo at `http://127.0.0.1:3100`;
- uses the Open Day fixed local service port map;
- checks its launch port before starting;
- exposes a health check at `http://127.0.0.1:3100/health`;
- serves a big-screen UI from `web/`;
- uses scripted token traces from `src/token_trail/traces.py`;
- can optionally use a local Ollama model for short curated live generation;
- includes tests for traces, config, docs, adapters, and project setup;
- supports Windows PowerShell scripts and Linux/macOS shell scripts.

Scripted mode remains the guaranteed fallback for Open Day.

---

## Purpose

Token Trail is designed for a public university Open Day booth.

It should be:

- quick to understand;
- visible on a large screen;
- safe for mixed-age visitors;
- reliable in a noisy booth environment;
- usable by staff or student ambassadors;
- able to fall back to scripted examples if the live model fails.

This demo explains the basic loop behind LLM text generation:

1. text is split into tokens;
2. the model estimates likely next tokens;
3. one token is selected;
4. the generated token is added to the context;
5. the process repeats.

---

## Project layout

```text
src/
  token_trail/
    __init__.py
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
  DEVELOPMENT_ENVIRONMENTS.md
  MODEL_BACKENDS.md
  OLLAMA_ADAPTER_PLAN.md
scripts/
  setup.ps1
  test.ps1
  check_ports.ps1
  run.ps1
  setup.sh
  test.sh
  check_ports.sh
  run.sh
tests/
```

---

## Requirements

- Python 3.12
- Poetry
- PowerShell on Windows, or Bash on Linux/macOS
- Optional: Ollama for local live generation

For the Framework Desktop and final rehearsal, use the pinned Python version:

```bash
pyenv install 3.12.13
pyenv local 3.12.13
python --version
```

For personal machines, an existing compatible Python 3.12 install should be fine for development.

---

## Ports and local services

Token Trail follows the Open Day fixed local service convention.

| Service | Default URL | Notes |
|---|---|---|
| Token Trail scripted/kiosk app | `http://127.0.0.1:3100` | Current single-process MVP |
| Health check | `http://127.0.0.1:3100/health` | Staff/launcher readiness check |
| Future Token Trail backend/API | `http://127.0.0.1:8100` | Reserved for later frontend/backend split |
| Ollama | `http://127.0.0.1:11434` | External model runtime |
| vLLM OpenAI-compatible server | `http://127.0.0.1:8000/v1` | External model runtime; Token Trail itself must not use port 8000 |

Do not change ports randomly for rehearsal or Open Day. If a required port is occupied, the launch scripts should fail clearly.

---

## Useful commands

### Windows

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/setup.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/test.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/check_ports.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/run.ps1
```

### Linux / macOS

```bash
bash ./scripts/setup.sh
bash ./scripts/test.sh
bash ./scripts/check_ports.sh
bash ./scripts/run.sh
```

Then open:

```text
http://127.0.0.1:3100
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

Values in `.env` are loaded automatically by the local server. Real environment variables take precedence over values in the file.

Future backend values:

```text
TOKEN_TRAIL_BACKEND=ollama
TOKEN_TRAIL_BACKEND=vllm
```

Ollama live generation settings:

```text
TOKEN_TRAIL_OLLAMA_NUM_PREDICT=256
TOKEN_TRAIL_OLLAMA_TEMPERATURE=0.4
TOKEN_TRAIL_OLLAMA_TIMEOUT_SECONDS=20
TOKEN_TRAIL_OLLAMA_DISABLE_THINKING=true
```

These defaults are intended to avoid Qwen3 spending the full token budget on reasoning before producing visible response text.

See:

- `docs/DEVELOPMENT_ENVIRONMENTS.md`
- `docs/MODEL_BACKENDS.md`
- `docs/OLLAMA_ADAPTER_PLAN.md`

---

## What visitors do

Visitors can:

- choose a curated prompt;
- watch token blocks appear step by step;
- compare likely next-token options;
- see the selected token added to the generated text;
- reset and replay the trail.

Example prompt:

```text
Write a short story about a robot at university.
```

---

## What the big screen shows

The large display should make the process obvious from a few metres away.

Suggested panels:

1. **Prompt** — the visitor’s selected or typed prompt.
2. **Tokenised prompt** — the prompt split into visible token blocks.
3. **Next-token prediction** — candidate tokens with probability-style bars.
4. **Selected token** — the token chosen for this step.
5. **Generated text** — the response growing token by token.
6. **Controls** — prompt selection, start, reset, scripted/live mode later.

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
- clear prompts on reset;
- keep logs technical and non-identifying;
- prefer curated prompts over open free text.

If prompt logging is ever enabled, document why, where it is stored, how long it is retained, and what signage is required.

---

## Fallback mode

Fallback mode is mandatory.

Fallback should support:

- scripted token traces;
- simulated candidate probabilities;
- replayable curated examples;
- clear label such as:

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

## Development phases

### Phase 1 — Scripted visual MVP

Goal: prove the public-facing experience without depending on a live model.

Build:

- full-screen UI;
- curated prompt selector;
- token blocks;
- animated next-token steps;
- simulated probability bars;
- reset button;
- replay mode.

### Phase 2 — Local model integration

Goal: connect the visualiser to a real local model where practical.

Build:

- tokenizer adapter;
- model backend adapter;
- streamed generation;
- real or approximated top-k token display;
- graceful timeout handling;
- switch between live and scripted mode.

### Phase 3 — Open Day hardening

Goal: make it reliable for public booth use.

Build:

- kiosk/full-screen launch;
- staff controls;
- visible fallback state;
- prompt clearing;
- packaging/startup scripts;
- demo machine checklist;
- no-terminal reset path.

---

## Repository status

Current status: **scripted MVP with optional Ollama live generation, warm-up, and live-mode layout polish**

Next concrete build step:

```text
Run browser/display rehearsal with docs/STAFF_READINESS_CHECKLIST.md.
```

---

## License

TBD.

---

## Acknowledgement

Built as part of the Open Day Demos project for demonstrating AI concepts in an engaging, accurate, and public-friendly way.
