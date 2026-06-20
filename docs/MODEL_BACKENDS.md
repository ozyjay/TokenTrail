# Model Backends

Token Trail now supports two runtime families:

| Runtime | Role |
| --- | --- |
| Scripted prepared traces | Guaranteed local fallback for the public demo |
| HF trace server | Live, replayable token traces with prompt tokens and candidate probabilities |

The HF trace server is the only live backend. The app does not expose paragraph-only live generation.

## HF Trace Contract

HF traces must return:

- `mode: "hf-live-trace"`;
- `prompt_tokens`;
- generated `steps`;
- candidate tokens and probabilities for each retained step;
- explanations for each retained step.

The server keeps only generated steps through the first complete sentence after at least eight generated steps. If no complete sentence is found within the generation budget, Token Trail uses the scripted fallback payload.

## Configuration

```text
TOKEN_TRAIL_MODEL_CONFIG_PATH=config/models.json
TOKEN_TRAIL_HF_TRACE_MODEL=Qwen/Qwen2.5-1.5B-Instruct
TOKEN_TRAIL_HF_TRACE_MODELS=Qwen/Qwen2.5-1.5B-Instruct,Qwen/Qwen2.5-0.5B-Instruct
```
