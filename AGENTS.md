# AGENTS.md

## Response Language

- Use Australian grammar and spelling.

## Python

- This project uses `pyenv` for Python.
- Prefer `python3` from the active `pyenv` version when creating virtual environments, installing packages, or running Python tooling.
- Do not assume the macOS system Python is the intended interpreter.

## Script Policy

- Use PowerShell scripts only for project automation.
- Do not add shell scripts, Bash wrappers, or `.sh` files.
- Put runnable project commands in `scripts/*.ps1`.
- Run scripts with `pwsh`, for example:

```powershell
pwsh -NoProfile -File ./scripts/clean.ps1
pwsh -NoProfile -File ./scripts/test.ps1
pwsh -NoProfile -File ./scripts/run.ps1
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1
```

## Dependency Management

- Use Poetry for project dependencies.
- Keep heavyweight or experimental dependencies in optional Poetry groups where practical.
- Use the normal install path:

```powershell
poetry install
```

## Model service

- ModelDeck owns model discovery, worker lifecycle, warm-up, and GPU memory.
- Token Trail must not start, warm, stop, or download model workers.
- Discover ready aliases through ModelDeck `GET /v1/models` and request traces through `POST /native/autoregressive/trace`.

## Live Runtime UX

- ModelDeck is the primary/default live token-trace backend when a configured alias is ready.
- Scripted mode remains the mandatory fallback and secondary prepared mode, and should keep curated prompts static.
- Resetting or switching into scripted mode must re-render the curated prompt view, hide the prompt editor, and restore the selected prepared trace.
- Available ModelDeck runtimes should expose an editable prompt box.
- ModelDeck mode sends the fixed hidden instruction prompt from `config/instructions/modeldeck_default.txt` to keep public responses short and suitable for the demo.
- ModelDeck traces should finish at a complete sentence or fall back to scripted mode if ModelDeck fails, is too slow, or is not ready.
- Public wording should describe candidate bars as top returned alternatives from the local model, not private reasoning.
- The generated output area should use available horizontal browser space and avoid forcing page-level scrolling for normal live output.
- Do not store visitor prompts or generated responses by default.

## ModelDeck availability

- If ModelDeck is unavailable, Token Trail should still start with scripted prepared traces.
- An unavailable configured alias must remain visible with an actionable status; Token Trail must not try to make it ready.
