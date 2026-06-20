# Token Trail

Token Trail is a local Open Day demo that shows text generation one token at a time. Visitors choose a curated prompt, then watch prompt tokens, next-token candidates, probabilities, and generated text build up as a replayable trail.

Current app status: **primary Hugging Face Transformers live token traces with scripted prepared traces as the guaranteed fallback.** HF trace mode lets staff enter a custom prompt and replays real prompt tokens, generated tokens, top returned alternatives, and probabilities from the local HF trace server. Scripted prepared traces remain mandatory for public reliability when HF trace is not ready, too slow, or fails.

## Runtime Families

| Runtime | Purpose | Status |
| --- | --- | --- |
| `hf-trace:<model>` | Default live token-trace backend from the local HF trace server | Primary when enabled and healthy |
| `scripted:prepared-traces` | Guaranteed scripted fallback and secondary prepared mode | Always available |

The browser UI exposes only these runtime families. Normal operation is to run HF trace when healthy, then fall back to scripted prepared traces if HF trace fails, is too slow, is not ready, or cannot complete a sentence. The candidates shown are returned token alternatives from the local model, not private reasoning.

## Setup

```powershell
pwsh -NoProfile -File ./scripts/setup.ps1
pwsh -NoProfile -File ./scripts/test.ps1
pwsh -NoProfile -File ./scripts/run.ps1
```

HF trace dependencies are installed by the normal Poetry setup.

## HF Trace

Configure selectable HF trace models in `config/models.json`:

```text
TOKEN_TRAIL_MODEL_CONFIG_PATH=config/models.json
TOKEN_TRAIL_HF_TRACE_MODEL=Qwen/Qwen2.5-1.5B-Instruct
TOKEN_TRAIL_HF_TRACE_MODELS=Qwen/Qwen2.5-1.5B-Instruct,Qwen/Qwen2.5-0.5B-Instruct
```

Run the local probe with the documented candidate source:

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source forward-logits
```

`scripts/run.ps1` starts the local HF trace server when `TOKEN_TRAIL_BACKEND=hf-trace` and `TOKEN_TRAIL_HF_TRACE_ENABLED=true`. It waits only for the trace server health check; the selected model loads on the first HF generation request in the web app.

## UX Notes

- Trail speed presets are Slow, Normal, and Fast.
- Normal is the default replay speed.
- Non-scripted mode means HF trace mode, and it accepts staff-entered prompts.
- Scripted mode keeps the prompt locked to curated traces; reset and runtime switching restore the curated prompt view.
- Generated HF traces are trimmed to the first complete sentence after at least eight generated steps.

## Shutdown Notes

The HF trace server suppresses Python's known `multiprocessing.resource_tracker` leaked semaphore warning on shutdown. Other HF trace startup, request, and generation errors should still be visible in the terminal.
