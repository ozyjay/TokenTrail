"""Ollama adapter for local model discovery and generation."""

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
    """Discover locally installed Ollama models and generate short responses."""

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

    def generate(
        self,
        model: str,
        prompt: str,
        *,
        timeout_seconds: float = 20.0,
        max_tokens: int = 256,
        temperature: float = 0.4,
        disable_thinking: bool = True,
    ) -> str:
        """Generate a short non-streaming continuation from a local Ollama model."""

        payload = {
            "model": model,
            "prompt": _format_prompt(prompt, disable_thinking=disable_thinking),
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        request = Request(
            urljoin(self.base_url, "api/generate"),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with self._opener(request, timeout=timeout_seconds) as response:
                raw_body = response.read()
        except TimeoutError as error:
            raise AdapterError("Ollama generation timed out") from error
        except (HTTPError, URLError, OSError) as error:
            raise AdapterError(f"Ollama generation failed: {error}") from error

        try:
            response_payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AdapterError("Ollama generation returned invalid JSON") from error

        response_text = response_payload.get("response") if isinstance(response_payload, dict) else None
        if not isinstance(response_text, str) or not response_text.strip():
            raise AdapterError("Ollama generation returned an empty response")

        return response_text.strip()

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


def _format_prompt(prompt: str, *, disable_thinking: bool) -> str:
    """Format a prompt for short, public-demo-friendly Ollama generation."""

    base_prompt = "\n".join(
        [
            "Write a short, direct answer.",
            "Do not show reasoning.",
            "",
            "Prompt:",
            prompt,
        ]
    )
    if not disable_thinking:
        return base_prompt

    return f"/no_think\n\n{base_prompt}"
