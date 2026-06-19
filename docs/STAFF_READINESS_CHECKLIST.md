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

## Live Mode Check

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
4. Click **Generate live trail**.
5. Confirm the generated text is readable in paragraph form.
6. Confirm the candidate panel says:

```text
Live local model response
Prepared token probabilities are shown in scripted mode.
```

## Fallback And Reset Check

1. Click **Reset**.
2. Confirm the normal generated-text layout is restored.
3. Switch to scripted mode.
4. Confirm no warm-up status appears.
5. Click **Start trail**.
6. Confirm the large token-by-token teaching trace runs.

## Go/No-Go

Use live mode only if warm-up and one live generation both succeed during setup.

If warm-up, live generation, or readability is doubtful, run scripted mode. Scripted fallback is the booth-safe mode.

## Staff Script

```text
This shows the basic loop behind language models. The model turns text into tokens, predicts likely next tokens, chooses one, and repeats.
```

Optional live-mode note:

```text
This mode uses a local model running on this computer. If live generation is unavailable, the demo switches to a prepared trace.
```
