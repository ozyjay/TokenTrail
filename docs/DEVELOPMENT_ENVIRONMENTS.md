# Development Environments

Token Trail should be easy to develop on personal computers and run reliably on the Framework Desktop for Open Day.

The project uses Poetry and Python 3.12. The current MVP does not require a model server, GPU, NPU, Ollama, or vLLM.

---

## Recommended modes

| Machine | Recommended mode | Notes |
|---|---|---|
| Personal Windows machine | Scripted mode | Use PowerShell scripts. No model server required. |
| Personal macOS/Linux machine | Scripted mode | Use PowerShell 7 scripts. No model server required. |
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

## PowerShell setup

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/setup.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/test.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/check_ports.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File ./scripts/run.ps1
```

Open:

```text
http://127.0.0.1:3100
```

Health check:

```text
http://127.0.0.1:3100/health
```

---

## Linux / Ubuntu setup notes

Ubuntu 22.04 or 24.04 should both be suitable for the scripted MVP.

Install system basics if needed:

```bash
sudo apt update
sudo apt install -y git curl build-essential python3.12 python3.12-venv
```

Install PowerShell 7 and Poetry using the official installers or your preferred package manager, then use the PowerShell setup commands above.

Open:

```text
http://127.0.0.1:3100
```

Health check:

```text
http://127.0.0.1:3100/health
```

---

## Poetry Dependencies

The default setup installs the dependencies needed for scripted mode, tests, the local app, and HF trace probing.

HF trace dependencies are installed by the normal Poetry setup. After `poetry install`, run the probe wrapper directly:

```powershell
pwsh -NoProfile -File ./scripts/probe_hf_trace.ps1 --model Qwen/Qwen2.5-0.5B-Instruct --max-new-tokens 24 --top-k 5 --candidate-source forward-logits
```

Manual equivalent:

```bash
poetry install
PYTHONPATH=src poetry run python scripts/probe_hf_trace.py --model Qwen/Qwen2.5-0.5B-Instruct --max-new-tokens 24 --top-k 5 --candidate-source forward-logits
```

`--candidate-source forward-logits` is the default probe mode. It performs a second forward pass over the generated sequence and gives more useful candidate alternatives than `--candidate-source generation-scores`, which is kept for comparison and debugging.

Keep `TOKEN_TRAIL_HF_TRACE_ENABLED=false` unless the probe and server are reliable on the target machine.

---

## Environment configuration

Copy the example file when you need machine-specific settings:

```bash
cp .env.example .env
```

The current app defaults to scripted mode even without a `.env` file. When `.env` exists, the local server loads it automatically. Environment variables already set in the shell take precedence.

Important settings:

```text
TOKEN_TRAIL_BACKEND=scripted
TOKEN_TRAIL_HOST=127.0.0.1
TOKEN_TRAIL_PORT=3100
TOKEN_TRAIL_BACKEND_PORT=8100
```

Future model-backed modes:

```text
TOKEN_TRAIL_BACKEND=ollama
TOKEN_TRAIL_OLLAMA_BASE_URL=http://127.0.0.1:11434
TOKEN_TRAIL_OLLAMA_MODEL=qwen3:4b
```

```text
TOKEN_TRAIL_BACKEND=hf-trace
TOKEN_TRAIL_HF_TRACE_ENABLED=true
TOKEN_TRAIL_HF_TRACE_URL=http://127.0.0.1:8600/api/trace
TOKEN_TRAIL_HF_TRACE_MODEL=Qwen/Qwen2.5-0.5B-Instruct
```

```text
TOKEN_TRAIL_BACKEND=vllm
TOKEN_TRAIL_VLLM_BASE_URL=http://127.0.0.1:8000/v1
TOKEN_TRAIL_VLLM_MODEL=Qwen/Qwen3-4B
```

---

## Local service ports

Token Trail uses the Open Day fixed local service map.

| Service | Port | Notes |
|---|---:|---|
| Token Trail scripted/kiosk app | 3100 | Current single-process MVP |
| Token Trail backend/API | 8100 | Reserved for future split backend |
| HF trace server / model adapter | 8600 | Optional live trace adapter |
| Ollama | 11434 | External Ollama runtime |
| vLLM OpenAI-compatible server | 8000 | External vLLM runtime, if deliberately enabled |

For rehearsal and Open Day, do not silently fall back to random ports. The launch scripts check the configured Token Trail port before starting.

---

## Ollama and vLLM on the same workstation

It is acceptable to install both on the Framework Desktop, but avoid depending on both during the public event.

Recommended approach:

1. Use scripted mode as the guaranteed fallback.
2. Use either Ollama or HF trace as the supervised live backend for Token Trail, depending on rehearsal reliability.
3. Keep vLLM as an experimental or shared-serving path until it is proven with the full booth load.
4. During final rehearsal, run all planned demos together and watch memory, thermals, ports, and restart complexity.

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
