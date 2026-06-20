# Staff Readiness Checklist

Use this before running Token Trail in front of visitors.

## Setup

```powershell
ollama list
.\scripts\check_ports.ps1
.\scripts\test.ps1
.\scripts\run.ps1
```

Open:

```text
http://127.0.0.1:3100
```

## Scripted Mode Check

1. Select scripted mode.
2. Click **Start trail**.
3. Confirm the large token-by-token teaching trace runs.
4. Confirm candidate bars are visible.
5. Click **Reset**.
6. Confirm the display returns to a clean state.

## Ollama Live Text Check

Use this only if Ollama live mode is part of the setup.

1. Select the preferred available Ollama runtime.
2. Confirm the status changes from:

```text
Warming local model...
```

to:

```text
Local model ready
```

3. Confirm **Generate live trail** is disabled only while warming.
4. Confirm the prompt appears in an editable text box.
5. Optionally make a short safe edit to the prompt.
6. Click **Generate live trail**.
7. Confirm the generated text is readable in paragraph form.
8. Confirm longer live text uses the wide generated-text area and does not force page-level scrolling.
9. Confirm the candidate panel says:

```text
Live local model response
Prepared token probabilities are shown in scripted mode.
```

## HF Live Trace Check

HF live trace is not a required booth dependency yet.

Only run this check if the custom Hugging Face Transformers trace server has been rehearsed on the demo machine.

Expected local service:

```text
http://127.0.0.1:8600/api/trace
```

Verify:

1. HF trace server starts cleanly.
2. The selected HF runtime shows an editable prompt box.
3. Make a short safe edit to the prompt.
4. One short trace request succeeds.
5. The generated trace replays through the Token Trail animation.
6. The prompt token row updates to the model-tokenised tokens returned by the HF trace server.
7. Candidate bars are labelled as top returned alternatives.
8. Stopping the HF server causes Token Trail to fall back to scripted mode.

If any of these fail, leave HF live trace disabled.

## Fallback And Reset Check

1. Click **Reset**.
2. Confirm the prompt returns to the selected curated prompt.
3. Confirm the normal generated-text layout is restored.
4. Switch to scripted mode.
5. Confirm no warm-up status appears and the prompt is no longer editable.
6. Click **Start trail**.
7. Confirm the large token-by-token teaching trace runs.

## Go/No-Go

Scripted mode is the booth-safe mode.

Use Ollama live text only if warm-up and one live generation both succeed during setup.

Use HF live trace only if the HF trace server starts cleanly, returns a trace, replays cleanly, and falls back instantly when unavailable.

If live generation, live trace, or readability is doubtful, run scripted mode.

## Staff Script

```text
This shows the basic loop behind language models. The model turns text into tokens, predicts likely next tokens, chooses one, and repeats.
```

Optional Ollama live-mode note:

```text
This mode uses a local model running on this computer. If live generation is unavailable, the demo switches to a prepared trace.
```

Optional HF live-trace note:

```text
This mode builds a token trail from top returned alternatives from a local model. It still does not show private model reasoning.
```
