"""Runtime backend/model selection for Token Trail."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

from token_trail.config import RuntimeConfig


@dataclass(frozen=True)
class RuntimeOption:
    """A selectable runtime backend/model option."""

    id: str
    label: str
    backend: str
    model: str | None
    available: bool
    status: str
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
    hf_trace_available: bool = False,
    hf_trace_statuses: Mapping[str, Mapping[str, bool]] | None = None,
) -> list[RuntimeOption]:
    """Build selectable runtime options from config."""

    options = [
        RuntimeOption(
            id="scripted:prepared-traces",
            label="Scripted fallback traces",
            backend="scripted",
            model=None,
            available=True,
            status="ready",
            notes="Guaranteed local fallback; no model server required.",
        )
    ]

    if config.hf_trace_enabled:
        for model in config.hf_trace_models:
            status_payload = (hf_trace_statuses or {}).get(model, {})
            model_available = bool(status_payload.get("available", hf_trace_available))
            model_loaded = bool(status_payload.get("model_loaded", False))
            model_loading = bool(status_payload.get("loading", False))
            if not model_available:
                status = "unavailable"
                notes = "Configured HF trace server is unavailable; scripted fallback remains available."
            elif model_loaded:
                status = "ready"
                notes = "HF trace server is running and this model is ready."
            elif model_loading:
                model_available = False
                status = "loading"
                notes = "HF trace server is loading this model."
            else:
                model_available = False
                status = "idle"
                notes = "Select this model to load it."
            options.append(
                RuntimeOption(
                    id=f"hf-trace:{model}",
                    label=f"HF trace · {model}",
                    backend="hf-trace",
                    model=model,
                    available=model_available,
                    status=status,
                    notes=notes,
                )
            )

    return options


def default_runtime_id(config: RuntimeConfig, options: list[RuntimeOption]) -> str:
    """Choose the initial runtime option from config, falling back safely."""

    configured_model = config.hf_trace_model if config.backend == "hf-trace" else None

    for option in options:
        if option.backend == config.backend and option.model == configured_model:
            return option.id

    return options[0].id


def select_runtime(requested_id: str, options: list[RuntimeOption]) -> str:
    """Validate a requested runtime option id."""

    valid_ids = {option.id for option in options}
    if requested_id not in valid_ids:
        raise KeyError(f"Unknown runtime option: {requested_id}")
    return requested_id
