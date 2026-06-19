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
- scripted fallback for failed live generation;
- environment-driven configuration;
- launch and test scripts;
- tests for config, server routes, adapters, traces, runtime selection, and setup.

Recent live-generation findings:

- live generation works with local Ollama;
- Qwen-style reasoning can consume token budget unless thinking is disabled or constrained;
- first run can be slow if the model is cold;
- live output needs a better paragraph layout than the large token-trace headline style.

---

## Phase summary

| Phase | Name | Status | Main outcome |
|---|---|---|---|
| 0 | Repository and local-service foundation | Done | Repeatable local app on fixed Open Day ports |
| 1 | Scripted visual MVP | Mostly done | Public-facing token trail without live model dependency |
| 2 | Curated Ollama live generation | Working, needs polish | Runtime-selected local model can generate text |
| 3 | Warm-up and reliability | Done | Model is warmed before visitor interaction |
| 4 | Live-mode UI polish | Basic pass done | Live output is readable and clearly labelled |
| 5 | Educational visualisation improvements | Later | Better explanation without overclaiming real internals |
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
- Prompt display.
- Tokenised prompt display.
- Candidate-token rows with simulated probability bars.
- Selected-token animation.
- Generated-text panel.
- Reset and replay.
- Prepared trace fallback.

### Remaining polish

- Add at least one or two more strong curated traces.
- Improve text sizing for TV viewing.
- Ensure the explanation panel reads clearly from 2–3 metres.
- Confirm reset is instant and visually obvious.

### Go/no-go

This phase is good enough when a visitor can understand the core idea in under 30 seconds with no live model running.

---

## Phase 2 — Curated Ollama live generation

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

### Build sequence

1. Add backend-only `OllamaAdapter.warmup()`.
2. Add warm-up config.
3. Add `POST /api/runtime/warmup`.
4. Add UI warm-up state.
5. Add staff readiness checklist.

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

### Build

- Use a different layout for live text than scripted token animation.
- Treat live output as paragraph text, not a giant token headline.
- Add clear live-mode label:

```text
Live Local Model Mode
```

- Hide or deemphasise simulated probability bars during live-only response display.
- Preserve scripted trace UI for the teaching mode.
- Ensure long generated text wraps cleanly and does not overflow the panel.

### Go/no-go

A live response should be readable on the TV without scrolling or developer intervention.

---

## Phase 5 — Educational visualisation improvements

### Goal

Improve the teaching value while staying honest about what is real, simulated, or simplified.

### Status

Later.

### Candidate improvements

- More curated traces.
- Better token explanation copy.
- A simple “why this token?” panel for scripted mode.
- Clear labels for simulated probabilities.
- Optional side-by-side comparison:

```text
Prepared trace mode: shows candidate tokens and simulated probabilities.
Live local model mode: shows generated text from a local model.
```

### Deferred unless clearly needed

- Real top-k token probabilities.
- Token-by-token live streaming visualisation.
- vLLM backend.
- Open-ended visitor prompts.
- QR/phone control.
- Multi-user mode.

### Go/no-go

Only add educational features that make the demo clearer from a booth distance and do not make it fragile.

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
- No open free text unless explicitly supervised and constrained.

### Rehearsal checklist

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

### Go/no-go

Run live mode only if it works reliably during setup. Otherwise, run prepared trace mode.

---

## What not to build yet

Do not prioritise these until the core demo is stable:

- open-ended visitor text input;
- visitor prompt logging;
- QR/phone control;
- multi-user crowd mode;
- real private reasoning display;
- claims that the model understands like a person;
- claims that probabilities are exact unless they really are;
- live mode as a required dependency.

---

## Immediate next steps

### Next small implementation step

```text
Run staff readiness and manual rehearsal.
```

### Then

```text
Continue Open Day hardening.
```

### Always preserve

```text
Scripted fallback remains mandatory.
Live generation remains optional.
```
