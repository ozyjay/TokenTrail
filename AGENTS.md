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
- HF trace probe and server dependencies are core project dependencies now. Use the normal install path:

```powershell
poetry install
```

## HF Trace Probe

- Run the local probe through PowerShell:

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source forward-logits
```

- `--candidate-source forward-logits` is the default probe mode and should stay the documented path for local validation.
- Use `--candidate-source generation-scores` only for comparison or debugging of processed generation scores.

## Live Runtime UX

- HF trace is the primary/default live token-trace backend when healthy.
- Scripted mode remains the mandatory fallback and secondary prepared mode, and should keep curated prompts static.
- Resetting or switching into scripted mode must re-render the curated prompt view, hide the prompt editor, and restore the selected prepared trace.
- Available HF trace runtimes should expose an editable prompt box.
- HF trace mode returns replayable `hf-live-trace` data with model-tokenised `prompt_tokens`; after generation, show those returned tokens rather than word-split preview tokens.
- HF traces should finish at a complete sentence or fall back to scripted mode if HF trace fails, is too slow, or is not ready.
- Public wording should describe candidate bars as top returned alternatives from the local model, not private reasoning.
- The generated output area should use available horizontal browser space and avoid forcing page-level scrolling for normal live output.
- Do not store visitor prompts or generated responses by default.

## HF Trace Server Shutdown

- `scripts/serve_hf_trace.py` intentionally suppresses Python's known `multiprocessing.resource_tracker` leaked semaphore shutdown warning from the HF/ML stack.
- Do not broaden that warning filter; real runtime and generation errors should remain visible.

## HF Trace Startup

- `scripts/run.ps1` should start or detect the HF trace server, wait for `/health`, discover local models, and then start the Token Trail web app without waiting for a model to load.
- The Token Trail web app should call `POST /api/warmup` for the selected HF trace model, including the default selected model, and surface loading/ready status in the runtime UX.
- Live generation must stay disabled while the selected model is loading so generation does not race or become the accidental warm-up path.
- Keep `/health` fast; model loading belongs in `/api/warmup`.
