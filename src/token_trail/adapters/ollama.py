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

        token_budgets = [max_tokens]
        if disable_thinking and max_tokens < 512:
            token_budgets.append(512)

        response_payload: Any = None
        for token_budget in token_budgets:
            response_payload = self._generate_once(
                model,
                prompt,
                timeout_seconds=timeout_seconds,
                max_tokens=token_budget,
                temperature=temperature,
                disable_thinking=disable_thinking,
            )
            response_text = response_payload.get("response") if isinstance(response_payload, dict) else None
            public_response = _public_response_text(response_text, disable_thinking=disable_thinking)
            if public_response:
                return public_response

        raise AdapterError("Ollama generation returned an empty response")

    def _generate_once(
        self,
        model: str,
        prompt: str,
        *,
        timeout_seconds: float,
        max_tokens: int,
        temperature: float,
        disable_thinking: bool,
    ) -> Any:
        payload = {
            "model": model,
            "prompt": _format_prompt(prompt, disable_thinking=disable_thinking),
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if disable_thinking:
            payload["think"] = False

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

        return response_payload

    def warmup(self, model: str, *, timeout_seconds: float = 45.0, keep_alive: str = "30m") -> None:
        """Warm up a local Ollama model with a tiny non-streaming generation."""

        payload = {
            "model": model,
            "prompt": "/no_think\n\nReply with: ready",
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "num_predict": 2,
                "temperature": 0,
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
            raise AdapterError("Ollama warmup timed out") from error
        except (HTTPError, URLError, OSError) as error:
            raise AdapterError(f"Ollama warmup failed: {error}") from error

        try:
            json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AdapterError("Ollama warmup returned invalid JSON") from error

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


def _public_response_text(response_text: Any, *, disable_thinking: bool) -> str | None:
    """Return only public answer text, never model reasoning preambles."""

    if not isinstance(response_text, str):
        return None

    text = response_text.strip()
    if not text:
        return None

    if disable_thinking and "</think>" in text:
        text = text.rsplit("</think>", 1)[-1].strip()

    if not text:
        return None

    if disable_thinking and _looks_like_reasoning(text):
        return None

    return text


def _looks_like_reasoning(text: str) -> bool:
    lower_text = text.lower()
    reasoning_markers = (
        "hmm, the user",
        "okay, the user",
        "the user wants",
        "the user's query",
        "they specifically said",
        "i need to",
        "i should",
        "i'll",
        "let me",
        "no_think",
        "thinking process",
    )
    return any(marker in lower_text[:500] for marker in reasoning_markers)
