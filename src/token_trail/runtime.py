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
    modeldeck_statuses: Mapping[str, Mapping[str, object]] | None = None,
) -> list[RuntimeOption]:
    """Build selectable runtime options from config."""

    options = [
        RuntimeOption(
            id="scripted:prepared-traces",
            label="Prepared replay mode",
            backend="scripted",
            model=None,
            available=True,
            status="ready",
            notes="Explicit prepared replay; no live model request is made.",
        )
    ]

    if config.modeldeck_enabled:
        statuses = modeldeck_statuses or {}
        ordered_models = config.modeldeck_models
        for model in ordered_models:
            status_payload = statuses.get(model, {})
            model_available = bool(status_payload.get("available", False))
            reason = status_payload.get("reason")
            state = status_payload.get("state")
            notes = reason if isinstance(reason, str) and reason else "ModelDeck readiness is unknown."
            options.append(
                RuntimeOption(
                    id=f"modeldeck:{model}",
                    label=f"ModelDeck · {model}",
                    backend="modeldeck",
                    model=model,
                    available=model_available,
                    status=str(state) if isinstance(state, str) else "gateway_unavailable",
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
        if option.backend == config.backend and option.model == configured_model:
            return option.id

    return options[0].id


def select_runtime(requested_id: str, options: list[RuntimeOption]) -> str:
    """Validate a requested runtime option id."""

    valid_ids = {option.id for option in options}
    if requested_id not in valid_ids:
        raise KeyError(f"Unknown runtime option: {requested_id}")
    return requested_id
