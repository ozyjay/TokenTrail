# Token Trail Roadmap

## Current State

Token Trail has two runtime families:

- HF live token traces as the primary backend;
- scripted prepared traces as the mandatory fallback and secondary prepared mode.

HF trace mode is the default live token-trace backend for staff-entered prompts, real prompt tokens, generated token candidates, and replayable probability bars. Scripted prepared traces remain the guaranteed public-demo fallback when HF trace is slow, unavailable, not ready, or confusing.

## Near-Term Polish

- Keep the browser layout wide enough that generated text is readable without page scrolling during normal demos.
- Keep Slow, Normal, and Fast trail speed presets available beside Start and Reset.
- Keep scripted reset behaviour strict: no prompt editor, selected curated prompt restored, prepared trace replayed.
- Treat incomplete HF generations as fallback events rather than replaying cut-off text.
- Keep docs, tests, and config aligned with the two supported runtime families.
- Keep public wording clear that candidates are top returned alternatives from a local model, not private reasoning.

## Validation

```powershell
pwsh -NoProfile -File ./scripts/test.ps1
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source forward-logits
```
