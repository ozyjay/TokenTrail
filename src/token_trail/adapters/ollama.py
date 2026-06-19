"""Ollama adapter for local model discovery."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from token_trail.adapters.base import AdapterError


UrlOpen = Callable[..., Any]


@dataclass(frozen=True)
class OllamaStatus:
    """Reachability and installed-model summary for Ollama."""

    available: bool
    models: tuple[str, ...]
    error: str | None = None


class OllamaAdapter:
    """Discover locally installed Ollama models."""

    def __init__(self, base_url: str, timeout_seconds: float = 1.0, opener: UrlOpen = urlopen) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout_seconds = timeout_seconds
        self._opener = opener

    def status(self) -> OllamaStatus:
        """Return reachability and model-list status without raising adapter errors."""

        try:
            models = self._fetch_models()
        except AdapterError as error:
            return OllamaStatus(available=False, models=(), error=str(error))

        return OllamaStatus(available=True, models=models)

    def is_available(self) -> bool:
        """Return true when Ollama's tags endpoint is reachable and parseable."""

        return self.status().available

    def list_models(self) -> tuple[str, ...]:
        """Return installed model names, or an empty tuple on adapter failure."""

        return self.status().models

    def has_model(self, model_name: str) -> bool:
        """Return true when the exact model name is installed locally."""

        return model_name in self.list_models()

    def _fetch_models(self) -> tuple[str, ...]:
        request = Request(urljoin(self.base_url, "api/tags"), method="GET")

        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read()
        except TimeoutError as error:
            raise AdapterError("Ollama request timed out") from error
        except (HTTPError, URLError, OSError) as error:
            raise AdapterError(f"Ollama is unreachable: {error}") from error

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AdapterError("Ollama returned invalid JSON") from error

        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            raise AdapterError("Ollama returned an unexpected model list")

        names: list[str] = []
        for model in models:
            if not isinstance(model, dict):
                continue

            name = model.get("name")
            if isinstance(name, str) and name and name not in names:
                names.append(name)

        return tuple(names)
