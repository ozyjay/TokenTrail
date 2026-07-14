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
    modeldeck_statuses: Mapping[str, Mapping[str, bool]] | None = None,
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

    if config.modeldeck_enabled:
        for model in config.modeldeck_models:
            status_payload = (modeldeck_statuses or {}).get(model, {})
            model_available = bool(status_payload.get("available", False))
            reason = status_payload.get("reason")
            notes = (
                reason
                if isinstance(reason, str) and reason
                else "Ready through ModelDeck" if model_available else "No ready ModelDeck worker; scripted fallback remains available."
            )
            options.append(
                RuntimeOption(
                    id=f"modeldeck:{model}",
                    label=f"ModelDeck · {model}",
                    backend="modeldeck",
                    model=model,
                    available=model_available,
                    status="ready" if model_available else "unavailable",
                    notes=notes,
                )
            )

    return options


def default_runtime_id(config: RuntimeConfig, options: list[RuntimeOption]) -> str:
    """Choose the initial runtime option from config, falling back safely."""

    configured_model = None
    if config.backend == "modeldeck":
        configured_model = config.modeldeck_model

    for option in options:
        if option.backend == config.backend and option.model == configured_model and option.available:
            return option.id

    return options[0].id


def select_runtime(requested_id: str, options: list[RuntimeOption]) -> str:
    """Validate a requested runtime option id."""

    valid_ids = {option.id for option in options}
    if requested_id not in valid_ids:
        raise KeyError(f"Unknown runtime option: {requested_id}")
    return requested_id
