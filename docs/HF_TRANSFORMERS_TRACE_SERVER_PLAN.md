# HF Transformers Trace Server Plan

CLI probe implemented for the primary HF trace backend and default live token-trace path.

## Contract

The trace server returns Token Trail JSON with:

- `mode: "hf-live-trace"`;
- `model`;
- `prompt`;
- `prompt_tokens`;
- generated `steps`;
- top returned `candidates` and `explanation` for each step.

Token Trail validates the payload before replay. Normal operation is to start the HF trace server, preload the selected model, replay HF traces when the server is healthy and the selected model returns clean output, then use scripted prepared traces as the mandatory fallback / secondary prepared mode if validation fails, generation is slow, the server is unavailable, the output is unstable, unreadable, confusing, or the generation does not reach a complete sentence after at least eight generated steps. The bars show top returned token alternatives from the local model, not private reasoning.

## Configuration

```text
TOKEN_TRAIL_MODEL_CONFIG_PATH=config/models.json
TOKEN_TRAIL_HF_TRACE_MODEL=Qwen/Qwen2.5-1.5B-Instruct
TOKEN_TRAIL_HF_TRACE_MODELS=Qwen/Qwen2.5-1.5B-Instruct,Qwen/Qwen2.5-0.5B-Instruct
TOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS=96
```

## Probe Commands

Use forward logits for normal validation:

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source forward-logits
```

Use generation-scores only for comparison or debugging:

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source generation-scores
```

## Shutdown Behaviour

The HF trace server may load libraries that use Python multiprocessing primitives. The server script suppresses Python's known `multiprocessing.resource_tracker` leaked semaphore warning during shutdown so a normal Ctrl+C stop stays readable.

Keep that suppression narrow to the known shutdown warning. Request failures, trace validation failures, and model-loading errors should still be reported.

## Startup Behaviour

The local runner waits for the HF trace server `/health` endpoint, then calls `POST /api/warmup` for the configured default model before starting the Token Trail web app. Warm-up loads the tokenizer and model into the server cache without generating a visible trace. If warm-up fails, startup fails visibly so the operator can use scripted prepared traces.
