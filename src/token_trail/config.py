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
DEFAULT_OLLAMA_MODEL = "qwen3:4b"
DEFAULT_VLLM_MODEL = "Qwen/Qwen3-4B"
DEFAULT_OLLAMA_NUM_PREDICT = 256
DEFAULT_OLLAMA_TEMPERATURE = 0.4
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 20.0
DEFAULT_OLLAMA_WARMUP_TIMEOUT_SECONDS = 45.0
DEFAULT_OLLAMA_KEEP_ALIVE = "30m"
DEFAULT_OLLAMA_REASONING_RETRY_TOKENS = (("qwen3:4b", 512),)
DEFAULT_HF_TRACE_URL = "http://127.0.0.1:8600/api/trace"
DEFAULT_HF_TRACE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
DEFAULT_HF_TRACE_TOP_K = 5
DEFAULT_HF_TRACE_MAX_NEW_TOKENS = 48
DEFAULT_HF_TRACE_TEMPERATURE = 0.3
DEFAULT_HF_TRACE_TIMEOUT_SECONDS = 20.0


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
    ollama_models: tuple[str, ...] = ()
    vllm_models: tuple[str, ...] = ()
    ollama_num_predict: int = DEFAULT_OLLAMA_NUM_PREDICT
    ollama_temperature: float = DEFAULT_OLLAMA_TEMPERATURE
    ollama_timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS
    ollama_disable_thinking: bool = True
    ollama_warmup_enabled: bool = True
    ollama_warmup_timeout_seconds: float = DEFAULT_OLLAMA_WARMUP_TIMEOUT_SECONDS
    ollama_keep_alive: str = DEFAULT_OLLAMA_KEEP_ALIVE
    ollama_reasoning_retry_tokens: dict[str, int] | None = None
    hf_trace_enabled: bool = False
    hf_trace_url: str = DEFAULT_HF_TRACE_URL
    hf_trace_model: str = DEFAULT_HF_TRACE_MODEL
    hf_trace_top_k: int = DEFAULT_HF_TRACE_TOP_K
    hf_trace_max_new_tokens: int = DEFAULT_HF_TRACE_MAX_NEW_TOKENS
    hf_trace_temperature: float = DEFAULT_HF_TRACE_TEMPERATURE
    hf_trace_timeout_seconds: float = DEFAULT_HF_TRACE_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if not self.ollama_models:
            object.__setattr__(self, "ollama_models", (self.ollama_model,))
        if not self.vllm_models:
            object.__setattr__(self, "vllm_models", (self.vllm_model,))
        if self.ollama_reasoning_retry_tokens is None:
            object.__setattr__(self, "ollama_reasoning_retry_tokens", dict(DEFAULT_OLLAMA_REASONING_RETRY_TOKENS))



def load_config(env_file: Path | None = DEFAULT_ENV_FILE) -> RuntimeConfig:
    """Load config from process environment and an optional .env file."""

    file_values = _load_env_file(env_file)

    def get_setting(name: str, default: str) -> str:
        if name in os.environ:
            return os.environ[name]
        return file_values.get(name, default)

    ollama_model = get_setting("TOKEN_TRAIL_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    vllm_model = get_setting("TOKEN_TRAIL_VLLM_MODEL", DEFAULT_VLLM_MODEL)

    return RuntimeConfig(
        backend=get_setting("TOKEN_TRAIL_BACKEND", "scripted").strip().lower(),
        host=get_setting("TOKEN_TRAIL_HOST", "127.0.0.1"),
        port=int(get_setting("TOKEN_TRAIL_PORT", str(DEFAULT_TOKEN_TRAIL_PORT))),
        backend_port=int(get_setting("TOKEN_TRAIL_BACKEND_PORT", str(DEFAULT_TOKEN_TRAIL_BACKEND_PORT))),
        ollama_base_url=get_setting("TOKEN_TRAIL_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        ollama_model=ollama_model,
        ollama_models=_parse_csv_setting(get_setting("TOKEN_TRAIL_OLLAMA_MODELS", ollama_model)),
        ollama_num_predict=int(get_setting("TOKEN_TRAIL_OLLAMA_NUM_PREDICT", str(DEFAULT_OLLAMA_NUM_PREDICT))),
        ollama_temperature=float(get_setting("TOKEN_TRAIL_OLLAMA_TEMPERATURE", str(DEFAULT_OLLAMA_TEMPERATURE))),
        ollama_timeout_seconds=float(
            get_setting("TOKEN_TRAIL_OLLAMA_TIMEOUT_SECONDS", str(DEFAULT_OLLAMA_TIMEOUT_SECONDS))
        ),
        ollama_disable_thinking=_parse_bool_setting(get_setting("TOKEN_TRAIL_OLLAMA_DISABLE_THINKING", "true")),
        ollama_warmup_enabled=_parse_bool_setting(get_setting("TOKEN_TRAIL_OLLAMA_WARMUP_ENABLED", "true")),
        ollama_warmup_timeout_seconds=float(
            get_setting("TOKEN_TRAIL_OLLAMA_WARMUP_TIMEOUT_SECONDS", str(DEFAULT_OLLAMA_WARMUP_TIMEOUT_SECONDS))
        ),
        ollama_keep_alive=get_setting("TOKEN_TRAIL_OLLAMA_KEEP_ALIVE", DEFAULT_OLLAMA_KEEP_ALIVE),
        ollama_reasoning_retry_tokens=_parse_model_int_setting(
            get_setting("TOKEN_TRAIL_OLLAMA_REASONING_RETRY_TOKENS", _format_model_int_setting(DEFAULT_OLLAMA_REASONING_RETRY_TOKENS))
        ),
        vllm_base_url=get_setting("TOKEN_TRAIL_VLLM_BASE_URL", "http://127.0.0.1:8000/v1"),
        vllm_model=vllm_model,
        vllm_models=_parse_csv_setting(get_setting("TOKEN_TRAIL_VLLM_MODELS", vllm_model)),
        hf_trace_enabled=_parse_bool_setting(get_setting("TOKEN_TRAIL_HF_TRACE_ENABLED", "false")),
        hf_trace_url=get_setting("TOKEN_TRAIL_HF_TRACE_URL", DEFAULT_HF_TRACE_URL),
        hf_trace_model=get_setting("TOKEN_TRAIL_HF_TRACE_MODEL", DEFAULT_HF_TRACE_MODEL),
        hf_trace_top_k=int(get_setting("TOKEN_TRAIL_HF_TRACE_TOP_K", str(DEFAULT_HF_TRACE_TOP_K))),
        hf_trace_max_new_tokens=int(
            get_setting("TOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS", str(DEFAULT_HF_TRACE_MAX_NEW_TOKENS))
        ),
        hf_trace_temperature=float(
            get_setting("TOKEN_TRAIL_HF_TRACE_TEMPERATURE", str(DEFAULT_HF_TRACE_TEMPERATURE))
        ),
        hf_trace_timeout_seconds=float(
            get_setting("TOKEN_TRAIL_HF_TRACE_TIMEOUT_SECONDS", str(DEFAULT_HF_TRACE_TIMEOUT_SECONDS))
        ),
    )



def _parse_csv_setting(value: str) -> tuple[str, ...]:
    """Parse a comma-separated environment setting into unique non-empty values."""

    parsed: list[str] = []
    for raw_item in value.split(","):
        item = raw_item.strip()
        if item and item not in parsed:
            parsed.append(item)
    return tuple(parsed)



def _parse_bool_setting(value: str) -> bool:
    """Parse a permissive boolean environment setting."""

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _format_model_int_setting(values: tuple[tuple[str, int], ...]) -> str:
    return ",".join(f"{model}={amount}" for model, amount in values)


def _parse_model_int_setting(value: str) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue

        if "=" not in item:
            continue

        model, raw_amount = item.split("=", 1)
        model = model.strip()
        raw_amount = raw_amount.strip()
        if not model or not raw_amount:
            continue

        try:
            amount = int(raw_amount)
        except ValueError:
            continue

        if amount > 0:
            parsed[model] = amount

    return parsed



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
