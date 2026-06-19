# Token Trail Roadmap

**Project:** Token Trail  
**Status:** Active build roadmap  
**Last updated:** 2026-06-19

---

## Purpose

This roadmap tracks the remaining Token Trail work from current working prototype to Open Day-ready public demo.

Token Trail should explain language-model generation clearly, visibly, and honestly. It should remain useful even if live generation is unavailable.

```text
Primary teaching mode: scripted token trail
Optional live mode: local Ollama generation
Planned educational upgrade: SLM live trace mode
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
- optional live local generation;
- warm-up path for available local Ollama runtimes;
- live-mode paragraph layout;
- scripted fallback for failed live generation;
- three prepared scripted traces;
- environment-driven configuration;
- launch and test scripts;
- tests for config, server routes, adapters, traces, runtime selection, and setup.

Recent live-generation findings:

- live generation works with local Ollama;
- Qwen-style reasoning can consume token budget unless thinking is disabled or constrained;
- first run can be slow if the model is cold, so warm-up is useful;
- live text mode is readable but less educational than a replayable token trail;
- Ollama logprobs/top-logprobs support makes an SLM live trace worth planning, but it should be proven on the actual local model before implementation.

---

## Phase summary

| Phase | Name | Status | Main outcome |
|---|---|---|---|
| 0 | Repository and local-service foundation | Done | Repeatable local app on fixed Open Day ports |
| 1 | Scripted visual MVP | Mostly done | Public-facing token trail without live model dependency |
| 2 | Ollama live generation | Working, needs polish | Runtime-selected local model can generate text |
| 3 | Warm-up and reliability | Done | Model is warmed before visitor interaction |
| 4 | Live-mode UI polish | Basic pass done | Live output is readable and clearly labelled |
| 5 | SLM live trace planning | Planned / spike next | Convert model logprobs/top alternatives into replayable token trails |
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

### Remaining polish

- Add at least one or two more strong curated traces if needed.
- Improve text sizing for TV viewing.
- Ensure the explanation panel reads clearly from 2–3 metres.
- Confirm reset is instant and visually obvious.

### Go/no-go

This phase is good enough when a visitor can understand the core idea in under 30 seconds with no live model running.

---

## Phase 2 — Ollama live generation

### Goal

Allow a selected local Ollama model to generate short text from a curated prompt.

### Status

Working, needs polish.

### Delivered

- Ollama adapter.
- Installed model discovery.
- Runtime availability display.
- `POST /api/generate-trace` route.
- Runtime-selected live generation.
- Configurable generation settings:
  - `TOKEN_TRAIL_OLLAMA_NUM_PREDICT`
  - `TOKEN_TRAIL_OLLAMA_TEMPERATURE`
  - `TOKEN_TRAIL_OLLAMA_TIMEOUT_SECONDS`
  - `TOKEN_TRAIL_OLLAMA_DISABLE_THINKING`
- Scripted fallback when generation fails.

### Remaining polish

- Verify preferred model for the actual demo machine.
- Tune token budget and temperature for short readable output.
- Keep live output concise enough for the display.
- Avoid showing or implying private reasoning.
- If staff prompt editing is kept, ensure it is wired through intentionally, resettable, constrained, and non-persistent.

### Go/no-go

Live mode is usable only if it reliably returns a short visible answer during setup. If not, use scripted mode.

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

### Required public wording

Use:

```text
Warming local model...
```

```text
Local model ready
```

Avoid:

```text
The AI is thinking
```

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

### Remaining polish

- Confirm generated text remains readable from 2–3 metres on the final TV.
- Confirm long live output does not overflow awkwardly.
- Confirm reset returns to the scripted/default layout every time.

### Go/no-go

A live response should be readable on the TV without scrolling or developer intervention.

---

## Phase 5 — SLM live trace mode

### Goal

Improve the teaching value by turning a local SLM response into a replayable token trail using returned logprobs/top alternatives.

### Status

Planned / spike next.

### Supporting doc

```text
docs/SLM_LIVE_TRACE_PLAN.md
```

### Target behaviour

```text
curated prompt
  -> local Ollama generation with logprobs/top_logprobs
  -> convert generated tokens and top returned alternatives into trace steps
  -> replay using the existing token trail animation
```

### Why this matters

Current live text mode proves that a local model can generate a response, but it does not show the token-by-token trail. SLM live trace mode would bring live generation closer to the scripted teaching experience while keeping fallback intact.

### Constraints

- Non-streaming first.
- Do not claim to show private reasoning.
- Do not claim top returned alternatives are every possible next token.
- Do not require SLM live trace for Open Day.
- Keep scripted fallback mandatory.
- Feature-gate this until proven on the final machine.

### First tiny step

Run the API capability spike from `docs/SLM_LIVE_TRACE_PLAN.md` and confirm the selected local model returns usable `logprobs` and `top_logprobs`.

### Go/no-go

Proceed only if the actual installed Ollama version and selected local model return stable enough logprob data for a clear public replay. Otherwise, keep live text mode plus scripted traces.

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

```powershell
ollama list
.\scripts\test.ps1
.\scripts\check_ports.ps1
.\scripts\run.ps1
```

Then verify:

1. Scripted trace starts and resets cleanly.
2. Live runtime availability is shown accurately.
3. Warm-up status appears for live runtime.
4. Live generation either works or falls back cleanly.
5. The display is readable from 2–3 metres.
6. Staff can explain the demo in one sentence.

### Staff script

```text
This shows the basic loop behind language models. The model turns text into tokens, predicts likely next tokens, chooses one, and repeats.
```

Optional live-mode note:

```text
This mode uses a local model running on this computer. If live generation is unavailable, the demo switches to a prepared trace.
```

Optional SLM live trace note:

```text
This mode builds a token trail from the top returned alternatives of a local model. It still does not show private model reasoning.
```

### Go/no-go

Run live mode only if it works reliably during setup. Otherwise, run prepared trace mode.

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
- live mode as a required dependency.

---

## Immediate next steps

### Next small implementation step

```text
Run Phase A — API capability spike from docs/SLM_LIVE_TRACE_PLAN.md.
```

### Then

```text
If the spike succeeds, add adapter-only generate_with_logprobs() and tests.
If the spike fails, keep SLM live trace disabled and continue Open Day hardening.
```

### Always preserve

```text
Scripted fallback remains mandatory.
Live generation remains optional.
SLM live trace remains optional until proven reliable.
```
