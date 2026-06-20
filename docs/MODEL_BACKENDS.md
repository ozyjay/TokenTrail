# Model Backends

Token Trail supports two runtime families:

| Runtime | Role |
| --- | --- |
| HF trace server | Primary live token-trace backend with prompt tokens and candidate probabilities |
| Scripted prepared traces | Mandatory scripted fallback and secondary prepared mode for the public demo |

The HF trace server is the only live backend. The app does not expose paragraph-only live generation or other live runtime families. Normal operation is to use HF trace when the server is healthy and the selected model produces clean traces, then fall back to scripted prepared traces if HF trace fails, is too slow, or is not ready.

## HF Trace Contract

HF traces must return:

- `mode: "hf-live-trace"`;
- `prompt_tokens`;
- generated `steps`;
- top returned candidate tokens and probabilities for each retained step;
- explanations for each retained step.

The server keeps only generated steps through the first complete sentence after at least eight generated steps. If no complete sentence is found within the generation budget, Token Trail uses the scripted fallback payload. Public wording should describe the bars as local model token alternatives, not private reasoning.

## Configuration

```text
TOKEN_TRAIL_MODEL_CONFIG_PATH=config/models.json
TOKEN_TRAIL_HF_TRACE_MODEL=Qwen/Qwen2.5-1.5B-Instruct
TOKEN_TRAIL_HF_TRACE_MODELS=Qwen/Qwen2.5-1.5B-Instruct,Qwen/Qwen2.5-0.5B-Instruct
```
