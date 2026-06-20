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

Token Trail validates the payload before replay. Normal operation is to replay HF traces when the server is healthy and the selected model returns clean output. If validation fails, generation is too slow, the server is not ready, or the generation does not reach a complete sentence after at least eight generated steps, the main server returns the scripted prepared fallback. The candidate list represents token alternatives returned by the local model, not private reasoning.

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

The local runner waits only for the HF trace server `/health` endpoint. It should not submit a warm-up generation for the configured default model during `scripts/run.ps1`; model loading happens on the first real HF generation request.
