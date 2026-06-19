# Development Environments

Token Trail should be easy to develop on personal computers and run reliably on the Framework Desktop for Open Day.

The project uses Poetry and Python 3.12. The current MVP does not require a model server, GPU, NPU, Ollama, or vLLM.

---

## Recommended modes

| Machine | Recommended mode | Notes |
|---|---|---|
| Personal Windows machine | Scripted mode | Use PowerShell scripts. No model server required. |
| Personal macOS/Linux machine | Scripted mode | Use shell scripts. No model server required. |
| Framework Desktop development | Scripted + Ollama mode | Use pyenv, Poetry, and Ollama for local SLM testing. |
| Framework Desktop Open Day | Scripted fallback + one approved live backend | Prefer one live backend during the event to reduce operational risk. |

---

## Python version

The repo pins `.python-version` to `3.12.13` to match the VoiceChanger baseline.

For day-to-day development, any compatible Python 3.12 patch version should be fine. For the Framework Desktop and final rehearsal, use pyenv to match the pinned version exactly.

```bash
pyenv install 3.12.13
pyenv local 3.12.13
python --version
```

---

## Windows setup

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/setup.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/test.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/run.ps1
```

Open:

```text
http://127.0.0.1:8000
```

---

## Linux / Ubuntu setup

Ubuntu 22.04 or 24.04 should both be suitable for the scripted MVP.

Install system basics if needed:

```bash
sudo apt update
sudo apt install -y git curl build-essential python3.12 python3.12-venv
```

Install Poetry using the official installer or your preferred package manager.

Then run:

```bash
bash ./scripts/setup.sh
bash ./scripts/test.sh
bash ./scripts/run.sh
```

Open:

```text
http://127.0.0.1:8000
```

---

## Environment configuration

Copy the example file when you need machine-specific settings:

```bash
cp .env.example .env
```

The current app defaults to scripted mode even without a `.env` file.
When `.env` exists, the local server loads it automatically. Environment
variables already set in the shell take precedence.

Important settings:

```text
TOKEN_TRAIL_BACKEND=scripted
TOKEN_TRAIL_HOST=127.0.0.1
TOKEN_TRAIL_PORT=8000
```

Future model-backed modes:

```text
TOKEN_TRAIL_BACKEND=ollama
TOKEN_TRAIL_OLLAMA_BASE_URL=http://127.0.0.1:11434
TOKEN_TRAIL_OLLAMA_MODEL=qwen3:4b
```

```text
TOKEN_TRAIL_BACKEND=vllm
TOKEN_TRAIL_VLLM_BASE_URL=http://127.0.0.1:8001/v1
TOKEN_TRAIL_VLLM_MODEL=Qwen/Qwen3-4B
```

---

## Ollama and vLLM on the same workstation

It is acceptable to install both on the Framework Desktop, but avoid depending on both during the public event.

Recommended approach:

1. Use scripted mode as the guaranteed fallback.
2. Use Ollama as the first live SLM backend for Token Trail.
3. Keep vLLM as an experimental or shared-serving path until it is proven with the full booth load.
4. During final rehearsal, run all planned demos together and watch memory, thermals, ports, and restart complexity.

Suggested port convention:

| Service | Port |
|---|---:|
| Token Trail app | 8000 |
| Ollama | 11434 |
| vLLM OpenAI-compatible server | 8001 |

Do not run Ollama and vLLM with large models loaded at the same time unless the full booth test proves it is stable.

---

## Open Day reliability rule

For the public booth, prefer:

```text
Token Trail scripted fallback always available
Token Trail live backend optional
One model-serving path active at a time
```

The visitor-facing demo should remain useful even if the live model backend is stopped or unavailable.
