# Local Test Notes

This file records local setup or test issues found while running Token Trail on real development machines.

---

## 2026-06-20 — Editable live prompt and extra scripted traces

**Status:** implemented locally

**Context:** After live Ollama generation became usable, staff wanted to edit prompts for the small local models while keeping scripted fallback predictable.

**Fix captured in repo:**

- Available Ollama runtimes show an editable prompt box seeded from the selected curated trace.
- Scripted mode and scripted fallback ignore edited prompt text and continue to use prepared trace prompts.
- Reset restores the selected curated prompt so live edits are not retained.
- Two additional prepared traces were added: `Mars greenhouse` and `Library dragon`.

**Follow-up:** During browser rehearsal, confirm live prompt edits are useful on the display, reset clears them, and scripted mode still presents only curated prepared traces.

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

## 2026-06-20 — Live output fit and model list trim

**Status:** fixed locally

**Context:** Browser rehearsal showed `qwen3:1.7b` could still generate a story long enough to run off the generated-text panel. `gemma4:e2b` was also listed locally but did not load reliably on the RTX demo machine.

**Fix captured in repo:**

- Public live responses are capped to three sentences and roughly panel-safe length.
- `qwen3:4b` has a configurable model-specific retry budget so it can get past a reasoning preamble before the public answer is extracted.
- `qwen3:1.7b` keeps the normal budget path for lower latency and shorter output.
- `.env.example` and the local `.env` now list only `qwen3:1.7b` and `qwen3:4b` as Ollama runtime options.

Example:

```env
TOKEN_TRAIL_OLLAMA_REASONING_RETRY_TOKENS=qwen3:4b=512
```

**Follow-up:** Restart Token Trail and recheck both Qwen runtimes in the browser. The live story should fit, and Gemma should no longer appear in the runtime selector.

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

## HF trace CLI probe

**Context:** The HF trace path is still a spike. The CLI probe checks whether the current machine can load a small Hugging Face Transformers causal language model and convert generated token scores into Token Trail-shaped `hf-live-trace` JSON.

**Install optional probe dependencies through Poetry if needed:**

```bash
poetry install --with hf-trace
```

**Run a compact human-readable probe:**

```bash
PYTHONPATH=src poetry run python scripts/probe_hf_trace.py --model Qwen/Qwen2.5-0.5B-Instruct --max-new-tokens 24 --top-k 5
```

**Run JSON mode for contract inspection:**

```bash
PYTHONPATH=src poetry run python scripts/probe_hf_trace.py --model Qwen/Qwen2.5-0.5B-Instruct --max-new-tokens 24 --top-k 5 --json
```

**Pass condition:** generated text appears, generation steps are non-empty, each step has candidate alternatives, elapsed time is acceptable for rehearsal, and the script exits with status `0`.

**Fail condition:** keep `TOKEN_TRAIL_HF_TRACE_ENABLED=false` if model load time, memory use, generation latency, or trace quality is not acceptable on the target machine.

---

## Local testing rule

When a local machine fix is needed:

1. Push the code fix.
2. Add a short note here with the symptom, fix, and follow-up.
3. If it affects setup, ports, or runtime selection, update `.env.example` and the README.
4. If it affects Open Day operation, update the relevant project source-of-truth document as well.
