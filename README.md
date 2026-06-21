# Token Trail

Token Trail is a local Open Day demo that shows text generation one token at a time. Visitors choose a curated prompt, then watch prompt tokens, next-token candidates, probabilities, and generated text build up as a replayable trail.

Current app status: **primary Hugging Face Transformers live token traces with scripted prepared traces as the guaranteed fallback.** HF trace mode lets staff enter a custom prompt and replays real prompt tokens, generated tokens, top returned alternatives, and probabilities from the local HF trace server. Scripted prepared traces remain mandatory for public reliability when HF trace is not ready, too slow, or fails.

## Runtime Families

| Runtime | Purpose | Status |
| --- | --- | --- |
| `hf-trace:<model>` | Default live token-trace backend from the local HF trace server | Primary when enabled and healthy |
| `scripted:prepared-traces` | Guaranteed scripted fallback and secondary prepared mode | Always available |

The browser UI exposes only these runtime families. Normal operation is to start the HF trace server, discover which configured HF models are locally available, warm the selected available model, then start Token Trail ready for HF trace mode. Scripted prepared traces remain the fallback if HF trace is slow, unavailable, unstable, unreadable, confusing, or incomplete. The bars show top returned token alternatives from the local model, not private reasoning.

## Setup

```powershell
pwsh -NoProfile -File ./scripts/setup.ps1
pwsh -NoProfile -File ./scripts/test.ps1
pwsh -NoProfile -File ./scripts/run.ps1
```

HF trace dependencies are installed by the normal Poetry setup.

## HF Trace

HF trace runtime options come from configured model candidates in `config/models.json`. `GET /api/models` checks those configured candidates against the local Hugging Face cache without downloading models or loading full model weights. Use `TOKEN_TRAIL_HF_TRACE_MODEL` only as a preferred initial model when that model is already installed locally:

```text
TOKEN_TRAIL_MODEL_CONFIG_PATH=config/models.json
TOKEN_TRAIL_HF_TRACE_MODEL=Qwen/Qwen2.5-1.5B-Instruct
TOKEN_TRAIL_HF_TRACE_MODELS=Qwen/Qwen2.5-1.5B-Instruct,Qwen/Qwen2.5-0.5B-Instruct
TOKEN_TRAIL_HF_TRACE_WARMUP_TIMEOUT_SECONDS=180
```

Run the local probe with the documented candidate source. Probe and server loads use locally cached/installed model files by default; they should not download model weights during the booth flow.

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source forward-logits
```

Use `--allow-download` only for an intentional setup/probe download before the demo.

`scripts/run.ps1` starts the local HF trace server when `TOKEN_TRAIL_BACKEND=hf-trace` and `TOKEN_TRAIL_HF_TRACE_ENABLED=true`. It waits for `/health`, calls `GET /api/models`, chooses the configured default model when available or the first available configured model otherwise, then calls `POST /api/warmup` for that selected model before starting Token Trail. If no configured HF model is locally available, startup fails visibly so the operator can cache/download one configured model or use scripted prepared traces.

## UX Notes

- Trail speed presets are Slow, Normal, and Fast.
- Normal is the default replay speed.
- Non-scripted mode means HF trace mode, and it accepts staff-entered prompts.
- Scripted mode keeps the prompt locked to curated traces; reset and runtime switching restore the curated prompt view.
- Generated HF traces are trimmed to the first complete sentence after at least eight generated steps.
- Staff line: This live mode asks a small local model to continue the prompt. The bars show top returned token alternatives, not private reasoning.

## Shutdown Notes

The HF trace server suppresses Python's known `multiprocessing.resource_tracker` leaked semaphore warning on shutdown. Other HF trace startup, request, and generation errors should still be visible in the terminal.
