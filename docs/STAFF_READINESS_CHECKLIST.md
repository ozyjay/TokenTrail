# Staff Readiness Checklist

## Before Visitors Arrive

1. Run the tests.
2. Start Token Trail.
3. Open `http://127.0.0.1:3100`.
4. Confirm the runtime selector shows available HF trace models and scripted prepared traces.
5. Confirm the trail speed selector offers Slow, Normal, and Fast.
6. In HF trace mode, enter a short prompt and confirm the selected model produces a clean trace that replays to a complete sentence.
7. Switch to scripted mode and confirm the prompt editor disappears.
8. Press Reset and confirm the selected curated prompt and prepared trace are restored.

```powershell
pwsh -NoProfile -File ./scripts/test.ps1
pwsh -NoProfile -File ./scripts/run.ps1
```

## Fallback Rule

Normal operation is HF trace first when the server is healthy. If HF trace mode is slow, unavailable, not ready, unstable, unreadable, confusing, or returns an incomplete generation, use scripted prepared traces. The scripted fallback is mandatory for public reliability.

## Go/No-Go

- GO: HF trace server healthy, selected model produces clean traces, and Reset works.
- FALLBACK: scripted prepared traces.
- NO-GO for HF: model load or generation is slow, unstable, unreadable, or confusing.

## Shutdown Check

When stopping the local stack with Ctrl+C, expect:

```text
Stopping Token Trail.
Stopping HF trace server.
```

The known Python leaked semaphore shutdown warning from the HF/ML stack is filtered by the HF trace server script.
