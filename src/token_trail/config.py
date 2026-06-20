"""Runtime configuration for Token Trail."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_MODEL_CONFIG_PATH = ""
DEFAULT_TOKEN_TRAIL_PORT = 3100
DEFAULT_TOKEN_TRAIL_BACKEND_PORT = 8100
DEFAULT_HF_TRACE_URL = "http://127.0.0.1:8600/api/trace"
DEFAULT_HF_TRACE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
DEFAULT_HF_TRACE_TOP_K = 5
DEFAULT_HF_TRACE_MAX_NEW_TOKENS = 96
DEFAULT_HF_TRACE_TEMPERATURE = 0.3
DEFAULT_HF_TRACE_TIMEOUT_SECONDS = 20.0


@dataclass(frozen=True)
class RuntimeConfig:
    """Machine-specific runtime settings loaded from environment variables."""

    backend: str
    host: str
    port: int
    backend_port: int
    model_config_path: str = DEFAULT_MODEL_CONFIG_PATH
    hf_trace_enabled: bool = False
    hf_trace_url: str = DEFAULT_HF_TRACE_URL
    hf_trace_model: str = DEFAULT_HF_TRACE_MODEL
    hf_trace_models: tuple[str, ...] = ()
    hf_trace_top_k: int = DEFAULT_HF_TRACE_TOP_K
    hf_trace_max_new_tokens: int = DEFAULT_HF_TRACE_MAX_NEW_TOKENS
    hf_trace_temperature: float = DEFAULT_HF_TRACE_TEMPERATURE
    hf_trace_timeout_seconds: float = DEFAULT_HF_TRACE_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if not self.hf_trace_models:
            object.__setattr__(self, "hf_trace_models", (self.hf_trace_model,))
        elif self.hf_trace_model not in self.hf_trace_models:
            object.__setattr__(self, "hf_trace_models", (self.hf_trace_model, *self.hf_trace_models))


def load_config(env_file: Path | None = DEFAULT_ENV_FILE) -> RuntimeConfig:
    """Load config from process environment and an optional .env file."""

    file_values = _load_env_file(env_file)
    model_config_path = _get_raw_setting("TOKEN_TRAIL_MODEL_CONFIG_PATH", file_values, DEFAULT_MODEL_CONFIG_PATH)
    model_config = _load_model_config(_resolve_model_config_path(model_config_path, env_file))

    def get_setting(name: str, default: str, model_default: str | None = None) -> str:
        if name in os.environ:
            return os.environ[name]
        if name in file_values:
            return file_values[name]
        if model_default is not None:
            return model_default
        return default

    hf_trace_model = get_setting(
        "TOKEN_TRAIL_HF_TRACE_MODEL",
        DEFAULT_HF_TRACE_MODEL,
        _model_config_default(model_config, "hf_trace_model"),
    )
    hf_trace_models = _model_config_models(model_config, "hf_trace") or (hf_trace_model,)

    return RuntimeConfig(
        backend=get_setting("TOKEN_TRAIL_BACKEND", "scripted", _model_config_default(model_config, "backend")).strip().lower(),
        host=get_setting("TOKEN_TRAIL_HOST", "127.0.0.1"),
        port=int(get_setting("TOKEN_TRAIL_PORT", str(DEFAULT_TOKEN_TRAIL_PORT))),
        backend_port=int(get_setting("TOKEN_TRAIL_BACKEND_PORT", str(DEFAULT_TOKEN_TRAIL_BACKEND_PORT))),
        model_config_path=model_config_path,
        hf_trace_enabled=_parse_bool_setting(get_setting("TOKEN_TRAIL_HF_TRACE_ENABLED", "false")),
        hf_trace_url=get_setting("TOKEN_TRAIL_HF_TRACE_URL", DEFAULT_HF_TRACE_URL),
        hf_trace_model=hf_trace_model,
        hf_trace_models=_parse_csv_setting(get_setting("TOKEN_TRAIL_HF_TRACE_MODELS", ",".join(hf_trace_models))),
        hf_trace_top_k=int(get_setting("TOKEN_TRAIL_HF_TRACE_TOP_K", str(DEFAULT_HF_TRACE_TOP_K))),
        hf_trace_max_new_tokens=int(
            get_setting("TOKEN_TRAIL_HF_TRACE_MAX_NEW_TOKENS", str(DEFAULT_HF_TRACE_MAX_NEW_TOKENS))
        ),
        hf_trace_temperature=float(get_setting("TOKEN_TRAIL_HF_TRACE_TEMPERATURE", str(DEFAULT_HF_TRACE_TEMPERATURE))),
        hf_trace_timeout_seconds=float(
            get_setting("TOKEN_TRAIL_HF_TRACE_TIMEOUT_SECONDS", str(DEFAULT_HF_TRACE_TIMEOUT_SECONDS))
        ),
    )


def _get_raw_setting(name: str, file_values: Mapping[str, str], default: str) -> str:
    if name in os.environ:
        return os.environ[name]
    return file_values.get(name, default)


def _resolve_model_config_path(value: str, env_file: Path | None) -> Path | None:
    raw_path = value.strip()
    if not raw_path:
        return None

    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path

    base_dir = env_file.parent if isinstance(env_file, Path) else PROJECT_ROOT
    return base_dir / path


def _load_model_config(path: Path | None) -> Mapping[str, Any]:
    if path is None or not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid model config JSON at {path}: {error}") from error

    if not isinstance(payload, dict):
        raise ValueError(f"Model config JSON at {path} must contain an object")

    return payload


def _model_config_default(model_config: Mapping[str, Any], key: str) -> str | None:
    defaults = model_config.get("defaults", {})
    if not isinstance(defaults, dict):
        return None

    value = defaults.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _model_config_models(model_config: Mapping[str, Any], key: str) -> tuple[str, ...]:
    entries = model_config.get(key, ())
    if not isinstance(entries, list):
        return ()

    parsed: list[str] = []
    for entry in entries:
        model = ""
        if isinstance(entry, str):
            model = entry.strip()
        elif isinstance(entry, dict):
            raw_model = entry.get("model")
            if isinstance(raw_model, str):
                model = raw_model.strip()

        if model and model not in parsed:
            parsed.append(model)

    return tuple(parsed)


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
