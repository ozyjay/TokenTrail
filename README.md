# Token Trail

Token Trail is a local Open Day demo that shows text generation one token at a time. Visitors choose a curated prompt, then watch prompt tokens, next-token candidates, probabilities, and generated text build up as a replayable trail.

Current app status: **scripted fallback traces plus optional Hugging Face Transformers live token traces**. Scripted traces are always available. HF trace mode lets staff enter a custom prompt and replays real prompt tokens, generated tokens, candidates, and probabilities returned by the local HF trace server.

## Runtime Families

| Runtime | Purpose | Status |
| --- | --- | --- |
| `scripted:prepared-traces` | Guaranteed local teaching path | Always available |
| `hf-trace:<model>` | Live replayable token traces from the local HF trace server | Available when enabled and healthy |

The browser UI exposes only these runtime families. If an HF trace cannot complete a sentence, Token Trail falls back to the scripted trace for that prompt.

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

`scripts/run.ps1` starts and warms the local HF trace server when `TOKEN_TRAIL_BACKEND=hf-trace` and `TOKEN_TRAIL_HF_TRACE_ENABLED=true`.

## UX Notes

- Trail speed presets are Slow, Normal, and Fast.
- Normal is the default replay speed.
- Non-scripted mode means HF trace mode, and it accepts staff-entered prompts.
- Scripted mode keeps the prompt locked to curated traces; reset and runtime switching restore the curated prompt view.
- Generated HF traces are trimmed to the first complete sentence after at least eight generated steps.

## Shutdown Notes

The HF trace server suppresses Python's known `multiprocessing.resource_tracker` leaked semaphore warning on shutdown. Other HF trace startup, request, and generation errors should still be visible in the terminal.
