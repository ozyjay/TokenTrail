# Development Environments

Token Trail uses Poetry and Python 3.12. The supported local runtime families are the primary Hugging Face Transformers trace server and scripted prepared traces as the mandatory fallback / secondary prepared mode.

HF trace dependencies are installed by the normal Poetry setup.

## Setup

```powershell
pwsh -NoProfile -File ./scripts/setup.ps1
pwsh -NoProfile -File ./scripts/test.ps1
pwsh -NoProfile -File ./scripts/run.ps1
```

## HF Trace Validation

Use the forward-logits candidate source for local validation:

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source forward-logits
pwsh -NoProfile -File ./scripts/serve_hf_trace.ps1 --candidate-source forward-logits
```

The probe and HF trace server load local model files only by default. Use `--allow-download` with `probe_hf_trace.ps1` only when intentionally fetching a model during setup, not during a public booth run.

The comparison path is available for debugging processed generation scores:

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source generation-scores
```

## Configuration

```text
TOKEN_TRAIL_BACKEND=hf-trace
TOKEN_TRAIL_HF_TRACE_ENABLED=true
TOKEN_TRAIL_HF_TRACE_MODEL=Qwen/Qwen2.5-1.5B-Instruct
TOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS=96
TOKEN_TRAIL_HF_TRACE_TIMEOUT_SECONDS=20
TOKEN_TRAIL_HF_TRACE_WARMUP_TIMEOUT_SECONDS=180
```

Token Trail binds to `127.0.0.1:3100` by default. The HF trace server binds to `127.0.0.1:8600` by default when managed by `scripts/run.ps1`.

`scripts/run.ps1` waits for the HF trace server health endpoint, asks the HF trace server for locally installed models, preloads the selected discovered model through `POST /api/warmup`, and then starts the Token Trail web app. Warm-up uses `TOKEN_TRAIL_HF_TRACE_WARMUP_TIMEOUT_SECONDS`; visitor generation still uses `TOKEN_TRAIL_HF_TRACE_TIMEOUT_SECONDS`. If no local HF models are discovered or warm-up fails, setup stays honest and scripted prepared traces remain available.
