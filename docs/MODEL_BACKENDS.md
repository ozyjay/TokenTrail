# Model Backends

Token Trail supports two runtime families:

| Runtime | Role |
| --- | --- |
| HF trace server | Primary live token-trace backend with prompt tokens and candidate probabilities |
| Scripted prepared traces | Mandatory scripted fallback and secondary prepared mode for the public demo |

The HF trace server is the only live backend. The app does not expose paragraph-only live generation or other live runtime families. Normal operation is:

1. Start the HF trace server.
2. Preload/warm the selected model.
3. Run HF trace mode when healthy.
4. Fall back to scripted prepared traces if HF trace is slow, unavailable, unstable, unreadable, confusing, or incomplete.

## HF Trace Contract

HF traces must return:

- `mode: "hf-live-trace"`;
- `prompt_tokens`;
- generated `steps`;
- top returned candidate tokens and probabilities for each retained step;
- explanations for each retained step.

The server keeps only generated steps through the first complete sentence after at least eight generated steps. If no complete sentence is found within the generation budget, Token Trail uses the scripted fallback payload. Public wording should say: "The bars show top returned token alternatives from the local model, not private reasoning."

## Configuration

```text
TOKEN_TRAIL_MODEL_CONFIG_PATH=config/models.json
TOKEN_TRAIL_HF_TRACE_MODEL=Qwen/Qwen2.5-1.5B-Instruct
TOKEN_TRAIL_HF_TRACE_MODELS=Qwen/Qwen2.5-1.5B-Instruct,Qwen/Qwen2.5-0.5B-Instruct
```
