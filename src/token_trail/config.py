"""Runtime configuration for Token Trail.

The defaults are intentionally safe for development on personal computers:
scripted mode, localhost only, and no model server required.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeConfig:
    """Machine-specific runtime settings loaded from environment variables."""

    backend: str
    host: str
    port: int
    ollama_base_url: str
    ollama_model: str
    vllm_base_url: str
    vllm_model: str


def load_config() -> RuntimeConfig:
    """Load config from environment variables with development-safe defaults."""

    return RuntimeConfig(
        backend=os.getenv("TOKEN_TRAIL_BACKEND", "scripted").strip().lower(),
        host=os.getenv("TOKEN_TRAIL_HOST", "127.0.0.1"),
        port=int(os.getenv("TOKEN_TRAIL_PORT", "8000")),
        ollama_base_url=os.getenv("TOKEN_TRAIL_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        ollama_model=os.getenv("TOKEN_TRAIL_OLLAMA_MODEL", "qwen3:4b"),
        vllm_base_url=os.getenv("TOKEN_TRAIL_VLLM_BASE_URL", "http://127.0.0.1:8001/v1"),
        vllm_model=os.getenv("TOKEN_TRAIL_VLLM_MODEL", "Qwen/Qwen3-4B"),
    )
