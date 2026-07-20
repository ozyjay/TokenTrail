# Local test notes

ModelDeck must be running separately for live-trace validation. In the “2026 OpenDay Demo” set, select and start the worker for the public alias being rehearsed, then run Token Trail:

```powershell
pwsh -NoProfile -File ./scripts/run.ps1
```

Stop Token Trail after rehearsal with:

```powershell
pwsh -NoProfile -File ./scripts/stop.ps1
```

Verify the following:

1. The runtime selector lists `qwen-0-5b`, `qwen-1-5b` and `qwen-3b` in gateway order with readiness matching ModelDeck.
2. Selecting the ready route accepts an editable prompt and returns a `modeldeck-live-trace` replay.
3. Candidate bars show returned model alternatives and probabilities.
4. An unready provider becomes unavailable without Token Trail taking a lifecycle action.
5. A failed or incomplete ModelDeck request reports a live failure without substituting prepared output.
6. Selecting “Prepared replay mode” explicitly replays the curated trace without calling ModelDeck.

Run automated checks with:

```powershell
pwsh -NoProfile -File ./scripts/test.ps1
```
