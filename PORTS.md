# Token Trail Port Map

Token Trail is part of the Open Day demo stack. It should avoid default development ports that may collide with other local demos, model servers, and staff-control services running on the same workstation.

## Reserved ports

| Port | Service | Purpose |
|---:|---|---|
| `3100` | Token Trail frontend | Public/kiosk UI for the LLM explainer |
| `8100` | Token Trail backend/API | Tokenisation, model calls, scripted traces, and demo state |

## Related Open Day ports

These are not owned by Token Trail, but they are likely to exist on the same machine during development, rehearsal, or Open Day.

| Port | Service | Notes |
|---:|---|---|
| `3200` | QR Crowd AI frontend/screen | Visitor-facing screen/controller UI |
| `8200` | QR Crowd AI backend/WebSocket | Voting/session API |
| `3300` | Text Diffusion Lab | Supporting generative-text demo |
| `3400` | AI With Guardrails | State/guardrails demo |
| `8500` | NeCTAR Lab Coach mock | Local fallback/mock endpoint |
| `8600` | Token Trail HF trace server | Local replayable token-trace API |
| `11434` | External model tooling | Not used by Token Trail |
| `8000` | External model tooling | Not used by Token Trail |

## Rules

- Do not use framework defaults such as `3000` or `8000` unless explicitly overridden for a specific local-only experiment.
- Keep the frontend default at `3100`.
- Keep the backend/API default at `8100`.
- Put ports in `.env.example` and read them from environment variables in launch scripts.
- Startup scripts should fail clearly if a required port is already in use.
- Staff/demo launch scripts should print the URLs to open.
- Event machines should use fixed ports during rehearsal and Open Day.

## Suggested environment variables

```env
TOKEN_TRAIL_FRONTEND_PORT=3100
TOKEN_TRAIL_BACKEND_PORT=8100
TOKEN_TRAIL_BACKEND_HOST=127.0.0.1
TOKEN_TRAIL_BACKEND_URL=http://127.0.0.1:8100
```

For phone or second-device access, bind deliberately and document it:

```env
TOKEN_TRAIL_BACKEND_HOST=0.0.0.0
TOKEN_TRAIL_BACKEND_URL=http://<demo-machine-ip>:8100
```

Use `0.0.0.0` only when the machine/network setup is intentional and tested.
