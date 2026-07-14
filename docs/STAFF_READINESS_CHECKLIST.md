# Staff readiness checklist

## Before opening

1. Start ModelDeck separately and confirm its gateway is healthy.
2. In the ModelDeck operator console, confirm the required Qwen workers are ready.
3. Start Token Trail with `pwsh -NoProfile -File ./scripts/run.ps1`.
4. Confirm the runtime selector shows `qwen-0-5b`, `qwen-1-5b`, `qwen-3b`, and scripted prepared traces.
5. Confirm readiness in Token Trail matches ModelDeck; Token Trail must not start or warm a worker.
6. Enter a short prompt with a ready alias and confirm the replay reaches a complete sentence.
7. Confirm Reset restores the selected prepared trace and scripted mode hides the prompt editor.
8. Stop one non-selected worker in ModelDeck and confirm its Token Trail runtime becomes unavailable.
9. Confirm scripted mode still works when ModelDeck is unavailable.

## Go/no-go

- GO: ModelDeck gateway healthy, required worker ready, one live trace completes, Reset works, and scripted fallback works.
- NO-GO for live mode: gateway unreachable, worker unready, responses incomplete or unsuitable, or latency exceeds the event budget. Use scripted prepared traces.

Visitor prompts and generated responses must not be stored by default. Candidate bars are observable alternatives returned by the local model, not private reasoning.
