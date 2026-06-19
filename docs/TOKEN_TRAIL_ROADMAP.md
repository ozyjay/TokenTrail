# Token Trail Roadmap

**Project:** Token Trail  
**Status:** Active build roadmap  
**Last updated:** 2026-06-20

---

## Purpose

This roadmap tracks the remaining Token Trail work from current working prototype to Open Day-ready public demo.

Token Trail should explain language-model generation clearly, visibly, and honestly. It should remain useful even if live generation is unavailable.

```text
Primary teaching mode: scripted token trail
Optional live mode: local Ollama text generation
Planned educational upgrade: custom HF Transformers live trace server
Mandatory fallback: prepared trace replay
```

---

## Current status

Token Trail currently has:

- a local web UI on the reserved Token Trail port;
- curated scripted traces;
- token blocks and simulated candidate probabilities;
- runtime selector;
- Ollama model discovery;
- optional live local text generation;
- warm-up path for available local Ollama runtimes;
- live-mode paragraph layout;
- scripted fallback for failed live generation;
- three prepared scripted traces;
- environment-driven configuration;
- launch and test scripts;
- tests for config, server routes, adapters, traces, runtime selection, and setup.

Recent backend decisions:

- Ollama remains the simple live text path.
- Ollama logprob probing did not produce usable live trace data on the tested Qwen3 models.
- vLLM remains a stretch/deferred desktop experiment because it is heavier than needed for the local laptop workflow.
- A custom HF Transformers trace server is now the preferred planned path for replayable SLM token trails.

---

## Phase summary

| Phase | Name | Status | Main outcome |
|---|---|---|---|
| 0 | Repository and local-service foundation | Done | Repeatable local app on fixed Open Day ports |
| 1 | Scripted visual MVP | Mostly done | Public-facing token trail without live model dependency |
| 2 | Ollama live text generation | Working, needs polish | Runtime-selected local model can generate short text |
| 3 | Warm-up and reliability | Done | Model is warmed before visitor interaction |
| 4 | Live-mode UI polish | Basic pass done | Live output is readable and clearly labelled |
| 5 | HF Transformers live trace server | Planned / spike next | Convert local model scores into replayable token trails |
| 6 | Open Day hardening | Final rehearsal phase | Staff-ready, resettable, reliable booth demo |

---

## Phase 0 — Repository and local-service foundation

### Goal

Create a maintainable local demo repo that follows the Open Day port map and can run reliably on Windows and development machines.

### Status

Done.

### Delivered

- Poetry project scaffold.
- Python 3.12 target.
- Fixed local service ports.
- `.env.example` configuration.
- PowerShell and shell scripts.
- Port preflight checks.
- Tests and project setup checks.

### Keep stable

- Token Trail app port: `3100`.
- Future backend/API port: `8100`.
- HF trace server / model adapter port: `8600`.
- Ollama external runtime: `11434`.
- Do not move Token Trail to port `8000`.

---

## Phase 1 — Scripted visual MVP

### Goal

Prove the public-facing explanation without depending on a live model.

### Status

Mostly done.

### Delivered

- Curated trace selector.
- Three prepared scripted traces.
- Prompt display.
- Tokenised prompt display.
- Candidate-token rows with simulated probability bars.
- Selected-token animation.
- Generated-text panel.
- Reset and replay.
- Prepared trace fallback.

### Go/no-go

This phase is good enough when a visitor can understand the core idea in under 30 seconds with no live model running.

---

## Phase 2 — Ollama live text generation

### Goal

Allow a selected local Ollama model to generate short text from a curated or staff-edited prompt.

### Status

Working, needs polish.

### Delivered

- Ollama adapter.
- Installed model discovery.
- Runtime availability display.
- `POST /api/generate-trace` route.
- Runtime-selected live generation.
- Configurable generation settings.
- Scripted fallback when generation fails.

### Scope boundary

Ollama is now treated as the **live text** backend, not the preferred live token-trace backend.

### Go/no-go

Live text mode is usable only if it reliably returns a short visible answer during setup. If not, use scripted mode.

---

## Phase 3 — Warm-up and reliability

### Goal

Warm the selected local model before visitor interaction, so the first visitor click does not pay the cold-load cost.

### Status

Done.

### Supporting doc

```text
docs/OLLAMA_WARMUP_PLAN.md
```

### Delivered

- Backend-only `OllamaAdapter.warmup()`.
- Warm-up config.
- `POST /api/runtime/warmup`.
- UI warm-up state.
- Staff-facing warm-up wording.

### Go/no-go

The app must never become stuck because warm-up fails. Warm-up failure should leave scripted fallback available.

---

## Phase 4 — Live-mode UI polish

### Goal

Make live generation look intentional and readable, not like a broken or oversized scripted trace.

### Status

Basic pass done.

### Delivered

- Different layout for live text than scripted token animation.
- Live output treated as paragraph text.
- Clear live-mode explanation.
- Candidate-token panel replaced with an honest live-mode placeholder.
- Scripted trace UI preserved for the teaching mode.

### Go/no-go

A live response should be readable on the TV without scrolling or developer intervention.

---

## Phase 5 — Custom HF Transformers live trace server

### Goal

Improve the teaching value by turning a local model response into a replayable token trail using generated token IDs and per-step scores from Hugging Face Transformers.

### Status

Planned / spike next.

### Supporting docs

```text
docs/HF_TRANSFORMERS_TRACE_SERVER_PLAN.md
docs/SLM_LIVE_TRACE_PLAN.md
```

### Target behaviour

```text
curated prompt
  -> local HF trace server on port 8600
  -> generate with return_dict_in_generate=True and output_scores=True
  -> convert generated token IDs and top returned alternatives into trace steps
  -> replay using the existing token trail animation
```

### Constraints

- Non-streaming first.
- Do not claim to show private reasoning.
- Do not claim top returned alternatives are every possible next token.
- Do not require HF live trace for Open Day.
- Keep scripted fallback mandatory.
- Feature-gate this until proven on the final machine.

### First tiny step

Run a standalone HF trace server spike. Continue only if a small model returns trace-shaped JSON with non-empty steps in acceptable time on the target machine.

### Go/no-go

Proceed only if the actual local machine can produce a clear short trace reliably. Otherwise, keep HF live trace disabled and use scripted traces plus Ollama live text.

---

## Phase 6 — Open Day hardening

### Goal

Make the demo reliable for public booth operation by non-developer staff.

### Status

Final rehearsal phase.

### Required build items

- One-click reset path.
- Staff-readable readiness status.
- Scripted fallback always available.
- Clean startup from cold boot.
- Clear launcher failure if a port is occupied.
- Kiosk/full-screen instructions.
- Staff script.
- Go/no-go checklist.
- No visitor data storage.
- No unsupervised open free text.

### Rehearsal checklist

Detailed staff checklist:

```text
docs/STAFF_READINESS_CHECKLIST.md
```

### Staff script

```text
This shows the basic loop behind language models. The model turns text into tokens, predicts likely next tokens, chooses one, and repeats.
```

Optional HF live trace note:

```text
This mode builds a token trail from top returned alternatives from a local model. It still does not show private model reasoning.
```

### Go/no-go

Run live modes only if they work reliably during setup. Otherwise, run prepared trace mode.

---

## What not to build yet

Do not prioritise these until the core demo is stable:

- unsupervised open-ended visitor text input;
- visitor prompt logging;
- QR/phone control;
- multi-user crowd mode;
- real private reasoning display;
- claims that the model understands like a person;
- claims that top returned alternatives are the full set of possible next tokens;
- any live backend as a required dependency.

---

## Immediate next steps

### Next small implementation step

```text
Run Phase A — standalone HF trace server spike from docs/HF_TRANSFORMERS_TRACE_SERVER_PLAN.md.
```

### Then

```text
If the spike succeeds, add pure trace conversion helpers and tests.
If the spike fails, keep HF live trace disabled and continue Open Day hardening.
```

### Always preserve

```text
Scripted fallback remains mandatory.
Ollama live text remains optional.
HF live trace remains optional until proven reliable.
```
