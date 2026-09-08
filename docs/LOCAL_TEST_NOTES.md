# Local test notes

ModelDeck must be running separately for live-trace validation. Confirm the intended installation publishes the required `native-ar-trace-v1` capability through `GET /native/v1/capabilities`. Match its `public_name` and canonical surface, then manage its Worker separately in ModelDeck before running Token Trail:

```powershell
pwsh -NoProfile -File ./scripts/run.ps1
```

Stop Token Trail after rehearsal with:

```powershell
pwsh -NoProfile -File ./scripts/stop.ps1
```

Verify the following:

1. The runtime selector lists `qwen-0-5b`, `qwen-1-5b` and `qwen-3b` in configuration order with readiness matching ModelDeck.
2. Selecting the ready route accepts an editable prompt and returns a `modeldeck-live-trace` replay.
3. Candidate bars show returned model alternatives and probabilities.
4. An unready provider becomes unavailable without Token Trail taking a lifecycle action.
5. A failed or incomplete ModelDeck request reports a live failure without substituting prepared output.
6. Selecting “Prepared replay mode” explicitly replays the curated trace without calling ModelDeck.

Run automated checks with:

```powershell
pwsh -NoProfile -File ./scripts/test.ps1
```

Automated contract checks use fixtures derived from ModelDeck checkout `6037a98d94f606d59214d736e3923b8c3a9ff209`, specifically `backend/modeldeck/gateway/app.py`, `workers/autoregressive_worker.py` and `docs/OPEN_DAY_DEMO_CONTRACTS.md`. They do not launch inference or manage Workers. Node.js enables the reset/cancelled-response behaviour test; it is explicitly skipped if Node.js is unavailable.

Hardware rehearsal remains separate: check each configured alias serially for complete-sentence output, true user-prompt token separation, generated tokens, alternatives/probabilities and timing. Reset during a pending request and confirm cancellation in ModelDeck, including not-found and Worker-unavailable acknowledgements. Check stopped Workers, missing publication, incompatible contracts and gateway loss; explicitly select prepared replay to recover. Follow ModelDeck's hardware and thermal procedures before any inference. Readiness alone does not prove capacity or output quality.
