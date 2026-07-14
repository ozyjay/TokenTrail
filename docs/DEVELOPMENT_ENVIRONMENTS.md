# Development environments

Token Trail uses the active pyenv Python 3.12 interpreter and Poetry for its lightweight web application and tests:

```powershell
pipx install poetry
pwsh -NoProfile -File ./scripts/setup.ps1
pwsh -NoProfile -File ./scripts/test.ps1
```

ModelDeck owns the separate control-plane and ROCm inference environments. Do not install or launch model runtimes from Token Trail.
