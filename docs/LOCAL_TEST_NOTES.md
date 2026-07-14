# Local test notes

ModelDeck must be running separately for physical live-trace validation. Make the required Qwen workers ready in ModelDeck, then run Token Trail:

```powershell
pwsh -NoProfile -File ./scripts/run.ps1
```

Verify the following:

1. The runtime selector lists `qwen-0-5b`, `qwen-1-5b`, and `qwen-3b` with readiness matching ModelDeck.
2. Selecting a ready alias accepts an editable prompt and returns a `modeldeck-live-trace` replay.
3. Candidate bars show returned model alternatives and probabilities.
4. A stopped worker becomes unavailable without Token Trail starting or warming it.
5. A failed or incomplete ModelDeck request uses the scripted prepared trace.

Run automated checks with:

```powershell
pwsh -NoProfile -File ./scripts/test.ps1
```
