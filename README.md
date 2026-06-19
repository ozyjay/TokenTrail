# Token Trail

**Token Trail** is an Open Day demo that shows how a language model generates text one token at a time.

Visitors choose or enter a prompt, then watch the system break the prompt into tokens, predict possible next tokens, select one, and repeat. The goal is to make language model generation visible, understandable, and honest without claiming to show hidden model reasoning.

> Public tagline: **Watch a language model predict text one token at a time.**

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

## What visitors do

Visitors can:

- choose a curated prompt;
- optionally enter a short prompt if staff allow it;
- adjust generation settings such as temperature;
- watch token blocks appear step by step;
- compare likely next-token options;
- reset and try another example.

Example prompt:

```text
Write a short story about a robot at university.
```

---

## What the big screen shows

The large display should make the process obvious from a few metres away.

Suggested panels:

1. **Prompt**
   - the visitor’s selected or typed prompt.

2. **Tokenised prompt**
   - the prompt split into visible token blocks.

3. **Next-token prediction**
   - candidate tokens with probability-style bars.

4. **Selected token**
   - the token chosen for this step.

5. **Generated text**
   - the response growing token by token.

6. **Controls**
   - temperature, speed, reset, scripted/live mode.

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

## MVP scope

The first usable version should include:

- a simple full-screen web or desktop UI;
- curated prompt buttons;
- visible tokenisation;
- step-by-step generation;
- top-k candidate token display;
- adjustable generation speed;
- temperature control if supported;
- reset button;
- scripted fallback mode;
- clear “what this shows” explanation.

---

## Stretch features

Add only after the MVP is reliable:

- live local model backend;
- real tokenizer integration;
- real top-k probabilities;
- side-by-side temperature comparison;
- “why outputs vary” mode;
- context window visualisation;
- staff control panel;
- kiosk/full-screen launcher;
- recorded replay mode;
- exportable demo traces for fallback use.

---

## Architecture

Preferred architecture:

```text
Prompt
  -> Tokeniser
  -> Model or scripted trace
  -> Candidate token probabilities
  -> Sampler
  -> Token stream
  -> Big-screen visualiser
```

Fallback architecture:

```text
Curated prompt
  -> Pre-recorded token trace
  -> Simulated probabilities
  -> Big-screen visualiser
```

The visualiser should not depend tightly on the live model backend. It should be able to replay scripted traces when the model is unavailable.

---

## Candidate stack

The stack is not locked in yet.

Possible implementation options:

- local web app with FastAPI or Flask backend;
- browser front-end with HTML, CSS, and JavaScript;
- local model via Ollama, llama.cpp, or a small Python model wrapper;
- scripted JSON traces for fallback mode.

Keep dependencies minimal so the demo is easy to run on event machines.

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

## Curated prompt examples

Good Open Day prompts:

```text
Write a short story about a robot at university.
```

```text
Explain programming variables using a pizza example.
```

```text
Continue this sentence: At Open Day, the tiny campus robot discovered
```

```text
Write a two-line poem about studying IT in Cairns.
```

```text
Give three beginner tips for learning Python.
```

Avoid prompts that invite:

- personal advice;
- medical, legal, or financial guidance;
- political persuasion;
- private information;
- identity-based jokes or stereotypes;
- unsafe or inappropriate content.

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
- it starts from cold boot without developer intervention.

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

Success test:

```text
A non-technical visitor can explain “it predicts the next token repeatedly” after a 30-second demo.
```

### Phase 2 — Local model integration

Goal: connect the visualiser to a real local model where practical.

Build:

- tokenizer adapter;
- model backend adapter;
- streamed generation;
- real or approximated top-k token display;
- graceful timeout handling;
- switch between live and scripted mode.

Success test:

```text
The live model can generate from three curated prompts and recover cleanly from failure.
```

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

Success test:

```text
A student ambassador can start, run, reset, and switch fallback modes without developer help.
```

---

## Repository status

Current status: **initial planning / README draft**

Next concrete build step:

```text
Create a scripted visual MVP with no live model dependency.
```

---

## License

TBD.

---

## Acknowledgement

Built as part of the Open Day Demos project for demonstrating AI concepts in an engaging, accurate, and public-friendly way.
