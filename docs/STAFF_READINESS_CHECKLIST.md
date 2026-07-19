# Staff readiness checklist

## Before opening

1. Start ModelDeck separately and confirm its gateway is healthy.
2. In the ModelDeck operator console, confirm `qwen-0-5b`, `qwen-1-5b` and `qwen-3b` are in the active “2026 OpenDay Demo” set.
3. Start Token Trail with `pwsh -NoProfile -File ./scripts/run.ps1`.
4. Confirm the runtime selector shows all three aliases in gateway order and “Prepared replay mode”.
5. Confirm readiness in Token Trail matches ModelDeck; Token Trail must not start or warm a worker.
6. Enter a short prompt with a ready alias and confirm the replay reaches a complete sentence.
7. Confirm Reset restores the selected prepared trace and scripted mode hides the prompt editor.
8. Make the route provider unavailable in ModelDeck and confirm Token Trail reports it as not ready.
9. Confirm scripted mode still works when ModelDeck is unavailable.

## Go/no-go

- GO: ModelDeck gateway healthy, selected route ready, one live trace completes, Reset works and explicit prepared replay works.
- NO-GO for live mode: gateway unreachable, route absent or unready, responses incomplete or unsuitable, or latency exceeds the event budget. Use scripted prepared traces.

Visitor prompts and generated responses must not be stored by default. Candidate bars are observable alternatives returned by the local model, not private reasoning.
