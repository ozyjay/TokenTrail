# Local Test Notes

## 2026-06-20 — HF Trace CLI Probe

The HF trace CLI probe is the supported live-trace validation path.

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source forward-logits
pwsh -NoProfile -File ./scripts/serve_hf_trace.ps1 --candidate-source forward-logits
```

Use `--candidate-source generation-scores` only to compare processed generation scores while debugging.

## 2026-06-20 — Complete Response Behaviour

HF traces now trim generated steps to the first complete sentence after at least eight generated steps. If a generation does not reach `.`, `!`, or `?` within the configured budget, the app falls back to the scripted trace.

The default HF trace budget is:

```text
TOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS=96
```

## 2026-06-20 — Browser UX

The replay controls include Slow, Normal, and Fast presets. Normal remains the default. HF trace mode accepts staff-entered prompts; scripted mode stays locked to curated prepared traces.

Reset now re-renders the prompt for the current runtime. In scripted mode this hides the prompt editor, restores the selected curated trace, and shows curated prompt tokens only.

## 2026-06-20 — HF Trace Shutdown

Stopping the combined local stack prints the Token Trail and HF trace server stop messages. Python's known `multiprocessing.resource_tracker` leaked semaphore warning from the HF/ML stack is suppressed in `scripts/serve_hf_trace.py` so Ctrl+C shutdown stays clean.

## 2026-06-20 — HF Trace Startup

`scripts/run.ps1` starts the HF trace server, waits for `/health`, calls `POST /api/warmup` for the configured model, and then starts the Token Trail web app. Warm-up failure should be visible to the operator before visitors use the booth.

Normal operation is:

1. Start the HF trace server.
2. Preload/warm the selected model.
3. Run HF trace mode when healthy.
4. Fall back to scripted prepared traces if HF trace is slow, unavailable, unstable, unreadable, confusing, or incomplete.

## 2026-06-21 — Local HF Model Benchmarks

Choose the final booth default from measured local performance, not assumptions. Run each candidate with the forward-logits path:

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --model <model> --candidate-source forward-logits
```

Use this table for local results:

| Model | Machine | Candidate source | Cold load time | Warm trace time | Repeat trace time | Peak RAM/VRAM if known | Complete-sentence success | Candidate quality notes | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Qwen/Qwen2.5-0.5B-Instruct` | To measure locally | `forward-logits` | Not yet measured | Not yet measured | Not yet measured | Not yet measured | Not yet measured | Not yet measured | Candidate |
| `Qwen/Qwen2.5-1.5B-Instruct` | To measure locally | `forward-logits` | Not yet measured | Not yet measured | Not yet measured | Not yet measured | Not yet measured | Not yet measured | Configured default until measured otherwise |
| `HuggingFaceTB/SmolLM2-1.7B-Instruct` | To measure locally | `forward-logits` | Not yet measured | Not yet measured | Not yet measured | Not yet measured | Not yet measured | Not yet measured | Candidate |
| `Qwen/Qwen2.5-3B-Instruct` | To measure locally | `forward-logits` | Not yet measured | Not yet measured | Not yet measured | Not yet measured | Not yet measured | Not yet measured | Candidate |
