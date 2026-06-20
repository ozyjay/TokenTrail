# Token Trail Roadmap

## Current State

Token Trail has two runtime families:

- scripted prepared traces;
- HF live token traces.

Scripted traces remain the guaranteed public-demo fallback. HF trace mode is the live path for staff-entered prompts, real prompt tokens, generated token candidates, and replayable probability bars.

## Near-Term Polish

- Keep the browser layout wide enough that generated text is readable without page scrolling during normal demos.
- Keep Slow, Normal, and Fast trail speed presets available beside Start and Reset.
- Keep scripted reset behaviour strict: no prompt editor, selected curated prompt restored, prepared trace replayed.
- Treat incomplete HF generations as fallback events rather than replaying cut-off text.
- Keep docs, tests, and config aligned with the two supported runtime families.

## Validation

```powershell
pwsh -NoProfile -File ./scripts/test.ps1
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source forward-logits
```
