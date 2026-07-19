# Token Trail Roadmap

## Current State

Token Trail has two runtime families:

- ModelDeck live token traces as the primary backend;
- an explicit prepared replay mode for deterministic fallback.

ModelDeck is the default live token-trace service for staff-entered prompts, generated token candidates and replayable probability bars. ModelDeck owns route configuration and runtime lifecycle; Token Trail consumes only configured public aliases through the stable gateway. Prepared replay remains available as an explicit operator choice when live mode is unavailable or unsuitable.

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
