# Staff Readiness Checklist

## Before Visitors Arrive

1. Run the tests.
2. Start Token Trail.
3. Open `http://127.0.0.1:3100`.
4. Confirm the runtime selector shows scripted traces and any available HF trace models.
5. Confirm the trail speed selector offers Slow, Normal, and Fast.
6. In HF trace mode, enter a short prompt and confirm the response replays to a complete sentence.
7. Switch to scripted mode and confirm the prompt editor disappears.
8. Press Reset and confirm the selected curated prompt and prepared trace are restored.

```powershell
pwsh -NoProfile -File ./scripts/test.ps1
pwsh -NoProfile -File ./scripts/run.ps1
```

## Fallback Rule

If HF trace mode is slow, unavailable, or returns an incomplete generation, use scripted prepared traces. The demo remains useful in scripted mode.

## Shutdown Check

When stopping the local stack with Ctrl+C, expect:

```text
Stopping Token Trail.
Stopping HF trace server.
```

The known Python leaked semaphore shutdown warning from the HF/ML stack is filtered by the HF trace server script.
