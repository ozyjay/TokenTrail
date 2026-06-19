"""Runtime configuration for Token Trail.

The defaults are intentionally safe for development on personal computers:
scripted mode, localhost only, and no model server required.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_TOKEN_TRAIL_PORT = 3100
DEFAULT_TOKEN_TRAIL_BACKEND_PORT = 8100


@dataclass(frozen=True)
class RuntimeConfig:
    """Machine-specific runtime settings loaded from environment variables."""

    backend: str
    host: str
    port: int
    backend_port: int
    ollama_base_url: str
    ollama_model: str
    vllm_base_url: str
    vllm_model: str



def load_config(env_file: Path | None = DEFAULT_ENV_FILE) -> RuntimeConfig:
    """Load config from process environment and an optional .env file."""

    file_values = _load_env_file(env_file)

    def get_setting(name: str, default: str) -> str:
        if name in os.environ:
            return os.environ[name]
        return file_values.get(name, default)

    return RuntimeConfig(
        backend=get_setting("TOKEN_TRAIL_BACKEND", "scripted").strip().lower(),
        host=get_setting("TOKEN_TRAIL_HOST", "127.0.0.1"),
        port=int(get_setting("TOKEN_TRAIL_PORT", str(DEFAULT_TOKEN_TRAIL_PORT))),
        backend_port=int(get_setting("TOKEN_TRAIL_BACKEND_PORT", str(DEFAULT_TOKEN_TRAIL_BACKEND_PORT))),
        ollama_base_url=get_setting("TOKEN_TRAIL_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        ollama_model=get_setting("TOKEN_TRAIL_OLLAMA_MODEL", "qwen3:4b"),
        vllm_base_url=get_setting("TOKEN_TRAIL_VLLM_BASE_URL", "http://127.0.0.1:8000/v1"),
        vllm_model=get_setting("TOKEN_TRAIL_VLLM_MODEL", "Qwen/Qwen3-4B"),
    )



def _load_env_file(env_file: Path | None) -> Mapping[str, str]:
    """Read simple KEY=VALUE pairs without mutating the process environment."""

    if env_file is None or not env_file.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        values[name] = value

    return values
