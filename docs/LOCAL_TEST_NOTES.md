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
