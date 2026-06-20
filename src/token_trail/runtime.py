"""Runtime backend/model selection for Token Trail.

This module is intentionally lightweight. It gives the UI a runtime selector now,
without requiring live model generation to be implemented before the scripted MVP
is solid.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from token_trail.adapters.ollama import OllamaStatus
from token_trail.config import RuntimeConfig


@dataclass(frozen=True)
class RuntimeOption:
    """A selectable runtime backend/model option."""

    id: str
    label: str
    backend: str
    model: str | None
    available: bool
    notes: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RuntimeState:
    """Mutable runtime selection for the local demo server process."""

    selected_id: str

    def to_dict(self, options: list[RuntimeOption]) -> dict:
        selected = next((option for option in options if option.id == self.selected_id), options[0])
        return {
            "selected_id": selected.id,
            "selected": selected.to_dict(),
            "options": [option.to_dict() for option in options],
        }


def build_runtime_options(
    config: RuntimeConfig,
    ollama_status: OllamaStatus | None = None,
    hf_trace_available: bool = False,
) -> list[RuntimeOption]:
    """Build selectable runtime options from config.

    Ollama and vLLM options are listed from configuration. Ollama options are
    enriched with local model discovery when an adapter status is provided.
    """

    options = [
        RuntimeOption(
            id="scripted:prepared-traces",
            label="Scripted fallback traces",
            backend="scripted",
            model=None,
            available=True,
            notes="Guaranteed local fallback; no model server required.",
        )
    ]

    installed_ollama_models = set(ollama_status.models if ollama_status else ())
    ollama_reachable = bool(ollama_status and ollama_status.available)

    for model in config.ollama_models:
        available = model in installed_ollama_models
        if available:
            notes = "Installed local Ollama model."
        elif ollama_reachable:
            notes = "Configured, but not found in local Ollama."
        else:
            notes = "Configured local Ollama model, but Ollama is unavailable."

        options.append(
            RuntimeOption(
                id=f"ollama:{model}",
                label=f"Ollama · {model}",
                backend="ollama",
                model=model,
                available=available,
                notes=notes,
            )
        )

    for model in config.vllm_models:
        options.append(
            RuntimeOption(
                id=f"vllm:{model}",
                label=f"vLLM · {model}",
                backend="vllm",
                model=model,
                available=False,
                notes="Configured vLLM/OpenAI-compatible model. Availability is checked when the live adapter is added.",
            )
        )

    if config.hf_trace_enabled:
        notes = (
            "Configured HF trace server is reachable."
            if hf_trace_available
            else "Configured HF trace server is unavailable; scripted fallback remains available."
        )
        options.append(
            RuntimeOption(
                id=f"hf-trace:{config.hf_trace_model}",
                label=f"HF trace · {config.hf_trace_model}",
                backend="hf-trace",
                model=config.hf_trace_model,
                available=hf_trace_available,
                notes=notes,
            )
        )

    return options


def default_runtime_id(config: RuntimeConfig, options: list[RuntimeOption]) -> str:
    """Choose the initial runtime option from config, falling back safely."""

    configured_backend = config.backend
    configured_model = {
        "scripted": None,
        "ollama": config.ollama_model,
        "vllm": config.vllm_model,
        "hf-trace": config.hf_trace_model,
    }.get(configured_backend)

    for option in options:
        if option.backend == configured_backend and option.model == configured_model:
            return option.id

    return options[0].id


def select_runtime(requested_id: str, options: list[RuntimeOption]) -> str:
    """Validate a requested runtime option id."""

    valid_ids = {option.id for option in options}
    if requested_id not in valid_ids:
        raise KeyError(f"Unknown runtime option: {requested_id}")
    return requested_id
