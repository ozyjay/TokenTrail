# Local Test Notes

This file records local setup or test issues found while running Token Trail on real development machines.

---

## 2026-06-19 — Ollama warm-up rehearsal

**Status:** warm-up and one live generation verified

**Context:** The warm-up flow was implemented across the adapter, server endpoint, configuration, and UI status. A local endpoint rehearsal was run against real Ollama.

**Observed result:**

- `ollama list` reported both configured Qwen models installed: `qwen3:1.7b` and `qwen3:4b`.
- `.\scripts\check_ports.ps1` reported port `3100` available.
- `.\scripts\test.ps1` passed.
- A temporary Token Trail server reported `/health` as `ok`.
- `POST /api/runtime/warmup` for `ollama:qwen3:1.7b` returned `status: ready` and `message: Local model warmed`.
- Initial `POST /api/generate-trace` fell back because Qwen returned `response: ""` and put text in Ollama's `thinking` field.
- Adding Ollama's explicit `think: false` generation flag fixed the empty visible response.
- A follow-up `POST /api/generate-trace` returned `mode: live`, `fallback_used: false`, and visible generated text.

**Why this matters:** Warm-up works, fallback remains mandatory, and the configured Qwen runtime can produce a visible live response during setup.

**Follow-up:** Repeat the browser-based rehearsal on the demo display to confirm the warm-up status, live paragraph layout, reset, and scripted mode are readable from 2-3 metres.

---

## 2026-06-19 — Browser rehearsal attempt

**Status:** staff checklist added; visual browser pass still required

**Context:** After endpoint-level warm-up and live generation passed, a browser/display rehearsal was attempted from the automation environment.

**Observed result:**

- Token Trail reported `/health` as `ok` with Ollama available.
- The in-app browser automation runtime failed during setup with a local sandbox startup error before it could navigate to `http://127.0.0.1:3100`.
- A staff-facing checklist was added so the remaining visual rehearsal can be run directly on the demo display.

**Follow-up:** Run `docs/STAFF_READINESS_CHECKLIST.md` in a real browser on the demo machine. Confirm warm-up status, live paragraph layout, reset, scripted mode, and TV-distance readability.

---

## 2026-06-20 — qwen3:4b reasoning preamble fix

**Status:** fixed locally

**Context:** During visual rehearsal, switching from `qwen3:1.7b` to `qwen3:4b` showed reasoning-style text in the live output panel.

**Observed issue:** `qwen3:4b` ignored the no-thinking prompt initially and placed reasoning text in the visible Ollama `response`. With the configured short token budget, the public story appeared only after a later `</think>` marker.

**Fix captured in repo:**

- Live Ollama generation now strips text before a closing `</think>` marker.
- Obvious reasoning preambles are rejected instead of shown to visitors.
- If no-thinking generation returns only reasoning with a short budget, the adapter retries once with a larger token budget before falling back.

**Follow-up:** Recheck `qwen3:4b` in the browser. It should show only the story text or fall back to scripted mode; it should not show reasoning-style text.

---

## 2026-06-19 — Runtime model selection local fix

**Status:** fixed locally and pushed

**Context:** Runtime selection was added so the app can choose between scripted traces, Ollama models, and vLLM models without editing code.

**Observed issue:** During local testing, the runtime model configuration needed to support multiple selectable installed models, not only a single default model per backend.

**Fix captured in repo:**

- `RuntimeConfig` now carries both the selected model and the configured selectable model list for Ollama and vLLM.
- `TOKEN_TRAIL_OLLAMA_MODELS` and `TOKEN_TRAIL_VLLM_MODELS` are comma-separated lists used to populate runtime options.
- Duplicate model names are de-duplicated while preserving order.
- Tests now clear and cover the model-list environment variables so local `.env` or shell settings do not mask failures.

**Example `.env` values:**

```env
TOKEN_TRAIL_OLLAMA_MODEL=qwen3:4b
TOKEN_TRAIL_OLLAMA_MODELS=qwen3:4b,qwen3:1.7b

TOKEN_TRAIL_VLLM_MODEL=Qwen/Qwen3-4B
TOKEN_TRAIL_VLLM_MODELS=Qwen/Qwen3-4B
```

**Why this matters:** Different development machines and the Framework Desktop may already have different local models installed. Token Trail should let staff or developers choose from configured installed models at runtime rather than requiring code edits.

**Follow-up:** When the live Ollama adapter is implemented, replace or supplement configured model lists with live discovery from `ollama list` / Ollama API where practical. Keep scripted traces as the guaranteed fallback.

---

## 2026-06-19 — Pytest local temp and cache permissions fix

**Status:** fixed locally

**Context:** The PowerShell test script was run repeatedly on Windows while validating the setup and recent config changes.

**Observed issues:**

- Pytest could not write to the repo-local `.pytest_cache` directory and emitted a cache warning.
- Redirecting pytest temp output to `.pytest-tmp` exposed another Windows permissions problem when pytest tried to remove that directory.
- The config tests used `tmp_path`, which caused setup errors before the tests ran when pytest could not access the temp base directory.
- The server tests had stale `RuntimeConfig` fixtures after `backend_port` was added.

**Fix captured in repo:**

- Pytest cache provider is disabled in `pyproject.toml` with `addopts = "-p no:cacheprovider"`.
- Config tests no longer use `tmp_path`; they pass a small fake env-file object into `load_config`.
- Server test fixtures now include `backend_port`.
- The test script now completes cleanly with all 15 tests passing.

**Why this matters:** Local Windows temp and cache directories can have stale ACL or cleanup problems. The test suite should avoid depending on machine-specific temp locations unless a test is explicitly about filesystem behavior.

**Follow-up:** If future tests genuinely need temporary files, prefer a helper that creates files under a known writable project test-artifact directory and cleans them up carefully, or fix the machine ACLs before relying on pytest's default temp root.

---

## Local testing rule

When a local machine fix is needed:

1. Push the code fix.
2. Add a short note here with the symptom, fix, and follow-up.
3. If it affects setup, ports, or runtime selection, update `.env.example` and the README.
4. If it affects Open Day operation, update the relevant project source-of-truth document as well.
