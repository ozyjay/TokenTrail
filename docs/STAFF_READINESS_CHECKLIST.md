# Staff readiness checklist

## Before opening

1. Start ModelDeck separately and confirm its gateway is healthy.
2. Use `GET /native/v1/capabilities` on the configured gateway. Confirm `qwen-0-5b`, `qwen-1-5b` and `qwen-3b` (or configured overrides) appear as `public_name` with `protocol_contract: native-ar-trace-v1` and surface `POST /native/v1/autoregressive/traces`. Manage publication in the intended ModelDeck installation; `/v1/models` does not list native traces.
3. Start Token Trail with `pwsh -NoProfile -File ./scripts/run.ps1`.
4. Confirm the runtime selector shows all three aliases in configuration order and “Prepared replay mode”.
5. Confirm readiness in Token Trail matches ModelDeck; Token Trail must not start or warm a worker.
6. Enter a short prompt with a ready alias and confirm the replay reaches a complete sentence.
7. Confirm Reset restores the selected prepared trace and scripted mode hides the prompt editor.
8. Make the route provider unavailable in ModelDeck, confirm Token Trail reports it as not ready, then use Refresh runtime to recover after restoring it.
9. Use Cancel generation during a pending request and confirm ModelDeck receives cancellation; an acknowledgement is not proof the Worker has stopped. No late response should start a replay.
10. Confirm scripted mode still works when ModelDeck is unavailable.

## Go/no-go

- GO: ModelDeck gateway healthy, selected route ready, one live trace completes, Reset works and explicit prepared replay works.
- NO-GO for live mode: gateway unreachable, native capability absent, incompatible or unready, responses incomplete or unsuitable, or latency exceeds the event budget. Explicitly select “Prepared replay mode”.

Visitor prompts and generated responses must not be stored by default. Candidate bars are observable alternatives returned by the local model, not private reasoning.
