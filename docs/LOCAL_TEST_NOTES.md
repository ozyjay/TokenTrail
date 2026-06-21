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

`scripts/run.ps1` starts the HF trace server, waits for `/health`, calls `GET /api/models` to discover locally available configured models, selects the configured default when available or the first available configured model otherwise, calls `POST /api/warmup`, and then starts the Token Trail web app. Discovery does not download models or load full model weights. Warm-up uses `TOKEN_TRAIL_HF_TRACE_WARMUP_TIMEOUT_SECONDS`, separate from the shorter live generation timeout.

Normal operation is:

1. Start the HF trace server.
2. Discover locally available configured models.
3. Warm the selected available model.
4. Run HF trace mode when the selected model is ready.
5. Fall back to scripted prepared traces if HF trace is slow, unavailable, unstable, unreadable, confusing, or incomplete.

## 2026-06-21 — Local HF Model Benchmarks

Choose the final booth default from measured local performance, not assumptions. Run each candidate with the forward-logits path:

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --model <model> --candidate-source forward-logits
```

For a repeatable benchmark across locally available configured models, start the HF trace server with the forward-logits path in one terminal:

```powershell
pwsh -NoProfile -File ./scripts/serve_hf_trace.ps1 --candidate-source forward-logits
```

Then run the benchmark in another terminal:

```powershell
pwsh -NoProfile -File ./scripts/benchmark_hf_trace.ps1
```

The benchmark calls `GET /api/models`, only attempts configured models that the server reports as locally available, calls `POST /api/warmup` before timing traces, and writes JSON and CSV files under `artifacts/hf_trace_benchmarks/`. It uses fixed Open Day-safe prompts and does not download models.

Press Ctrl+C in the benchmark terminal to stop before the remaining traces. The benchmark saves partial JSON and CSV results before exiting; an already-running server-side trace may still finish inside the HF trace server process.

Use this table for local results:

| Model | Machine | Candidate source | Cold load time | Warm trace time | Repeat trace time | Peak RAM/VRAM if known | Complete-sentence success | Candidate quality notes | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Qwen/Qwen2.5-0.5B-Instruct` | Local Open Day Mac, `20260621T145358Z` run | `forward-logits` | Not captured by this run | `1.47s` average trace, `1.14s`-`1.99s` range | Not measured separately | Not measured | `3/3` successful traces | Fastest overall, but more verbose and less disciplined; robot prompt ran to 56 steps | Fast fallback/candidate, not preferred default |
| `Qwen/Qwen2.5-1.5B-Instruct` | Local Open Day Mac, `20260621T145358Z` run | `forward-logits` | Not captured by this run | `1.97s` average trace, `1.96s`-`1.97s` range | Not measured separately | Not measured | `3/3` successful traces | Best balance of speed, clean wording, and stable output shape | Preferred Open Day default |
| `Qwen/Qwen2.5-3B-Instruct` | Local Open Day Mac, `20260621T145358Z` run | `forward-logits` | Not captured by this run | `2.29s` average trace, `1.02s`-`3.40s` range | Not measured separately | Not measured | `3/3` successful traces | Good short tokenisation answer, but slower and sometimes chatty with assistant-style formatting | Candidate only if quality improves enough to justify latency |

`20260621T145358Z` benchmark summary: all 9 configured-model traces succeeded, with no fallback or error text. `candidate_count` matched `5 x step_count` for every row, which confirms the forward-logits candidate path was returning the expected five alternatives per generated step. Keep `Qwen/Qwen2.5-1.5B-Instruct` as the booth default unless later local measurements show a better speed/quality trade-off.
