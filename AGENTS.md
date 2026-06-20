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
pwsh -NoProfile -File ./scripts/test.ps1
pwsh -NoProfile -File ./scripts/run.ps1
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1
```

## Dependency Management

- Use Poetry for project dependencies.
- Keep heavyweight or experimental dependencies in optional Poetry groups where practical.
- The HF trace probe dependencies live in the optional `hf-trace` group:

```powershell
poetry install --with hf-trace
```

## HF Trace Probe

- Run the local probe through PowerShell:

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --candidate-source forward-logits
```

- `--candidate-source forward-logits` is the default probe mode and should stay the documented path for local validation.
- Use `--candidate-source generation-scores` only for comparison or debugging of processed generation scores.
