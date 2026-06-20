# HF Transformers Trace Server Plan

CLI probe implemented for the supported live-token trace path.

## Contract

The trace server returns Token Trail JSON with:

- `mode: "hf-live-trace"`;
- `model`;
- `prompt`;
- `prompt_tokens`;
- generated `steps`;
- `candidates` and `explanation` for each step.

Token Trail validates the payload before replay. If validation fails or the generation does not reach a complete sentence after at least eight generated steps, the main server returns scripted fallback.

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
