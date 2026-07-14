"""Client for ModelDeck's stable local model gateway."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen

from token_trail.adapters.base import AdapterError


UrlOpen = Callable[..., Any]
MIN_COMPLETE_SENTENCE_STEPS = 8


@dataclass(frozen=True)
class ModelDeckStatus:
    """Readiness summary for one ModelDeck model alias."""

    available: bool
    model_loaded: bool = False
    error: str | None = None


class ModelDeckAdapter:
    """Discover and call ready autoregressive workers through ModelDeck."""

    def __init__(self, gateway_url: str, opener: UrlOpen = urlopen) -> None:
        self.gateway_url = gateway_url.rstrip("/")
        self._opener = opener

    def status(self, *, model: str | None = None, timeout_seconds: float = 2.0, **_: Any) -> ModelDeckStatus:
        try:
            payload = self.models(timeout_seconds=timeout_seconds)
        except AdapterError as error:
            return ModelDeckStatus(available=False, error=str(error))

        entry = next((item for item in payload["data"] if item["id"] == model), None)
        if entry is None:
            return ModelDeckStatus(available=False, error=f"ModelDeck does not advertise alias {model}")
        ready = bool(entry["ready"])
        provider = entry.get("effective_provider")
        reason = None if ready else f"ModelDeck alias {model} has no ready worker"
        if ready and isinstance(provider, str):
            reason = f"Ready through {provider}"
        return ModelDeckStatus(available=ready, model_loaded=ready, error=reason)

    def models(self, *, timeout_seconds: float = 2.0) -> dict:
        request = Request(_gateway_url(self.gateway_url, "/v1/models"), method="GET")
        payload = self._request_json(request, timeout_seconds, "model discovery")
        if not _is_valid_models_payload(payload):
            raise AdapterError("ModelDeck model discovery returned an unexpected response")
        return payload

    def generate_trace(
        self,
        *,
        prompt: str,
        instructions: str | None,
        model: str,
        max_new_tokens: int,
        top_k: int,
        temperature: float,
        timeout_seconds: float,
    ) -> dict:
        messages = []
        if instructions:
            messages.append({"role": "system", "content": instructions})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_new_tokens,
            "min_tokens": MIN_COMPLETE_SENTENCE_STEPS,
            "top_k": top_k,
            "temperature": temperature,
            "stream": False,
        }
        request = Request(
            _gateway_url(self.gateway_url, "/native/autoregressive/trace"),
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        payload = self._request_json(request, timeout_seconds, "trace request")
        trace = _convert_trace(payload, prompt=prompt, model=model)
        validate_trace_payload(trace)
        return trace

    def _request_json(self, request: Request, timeout_seconds: float, operation: str) -> Any:
        try:
            with self._opener(request, timeout=float(timeout_seconds)) as response:
                raw_body = response.read()
        except TimeoutError as error:
            raise AdapterError(f"ModelDeck {operation} timed out") from error
        except HTTPError as error:
            raise AdapterError(f"ModelDeck {operation} failed: {_http_error_message(error)}") from error
        except (URLError, OSError) as error:
            raise AdapterError(f"ModelDeck {operation} failed: {error}") from error
        try:
            return json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AdapterError(f"ModelDeck {operation} returned invalid JSON") from error


def _convert_trace(payload: Any, *, prompt: str, model: str) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise AdapterError("ModelDeck trace returned an unexpected response")

    events = payload["events"]
    complete_index = next(
        (
            index
            for index, event in enumerate(events)
            if index + 1 >= MIN_COMPLETE_SENTENCE_STEPS
            and isinstance(event, dict)
            and _ends_with_sentence(event.get("text_so_far"))
        ),
        None,
    )
    if complete_index is None:
        raise AdapterError("ModelDeck trace did not reach a complete sentence")

    prompt_tokens = payload.get("prompt_tokens")
    if not isinstance(prompt_tokens, list) or not all(isinstance(token, str) for token in prompt_tokens):
        prompt_token_ids = payload.get("prompt_token_ids", [])
        if not isinstance(prompt_token_ids, list) or not all(isinstance(token_id, int) for token_id in prompt_token_ids):
            raise AdapterError("ModelDeck trace is missing prompt token data")
        # Protocol v1 exposes token IDs, which are the lossless model-tokenised representation.
        prompt_tokens = [f"<{token_id}>" for token_id in prompt_token_ids]

    steps = [_convert_event(event) for event in events[: complete_index + 1]]
    return {
        "mode": "modeldeck-live-trace",
        "model": model,
        "prompt": prompt,
        "prompt_tokens": prompt_tokens,
        "steps": steps,
    }


def _convert_event(event: Any) -> dict:
    if not isinstance(event, dict) or not isinstance(event.get("selected"), dict):
        raise AdapterError("ModelDeck trace contains an invalid event")
    selected = event["selected"]
    token = selected.get("token")
    probability = selected.get("probability")
    if not isinstance(token, str) or not token or not _is_probability(probability):
        raise AdapterError("ModelDeck trace contains an invalid selected token")

    candidates: list[dict[str, Any]] = [{"token": token, "probability": probability}]
    alternatives = event.get("alternatives", [])
    if not isinstance(alternatives, list):
        raise AdapterError("ModelDeck trace contains invalid alternatives")
    for alternative in alternatives:
        if not isinstance(alternative, dict):
            raise AdapterError("ModelDeck trace contains an invalid alternative")
        alternative_token = alternative.get("token")
        alternative_probability = alternative.get("probability")
        if not isinstance(alternative_token, str) or not _is_probability(alternative_probability):
            raise AdapterError("ModelDeck trace contains an invalid alternative")
        if alternative_token and alternative_token != token:
            candidates.append({"token": alternative_token, "probability": alternative_probability})

    candidates.sort(key=lambda candidate: candidate["probability"], reverse=True)
    return {
        "selected_token": token,
        "candidates": candidates,
        "explanation": "This was the token selected from the local model's returned probabilities.",
    }


def validate_trace_payload(trace: Any) -> None:
    if not isinstance(trace, dict) or trace.get("mode") != "modeldeck-live-trace":
        raise AdapterError("ModelDeck trace payload has an unexpected mode")
    if not isinstance(trace.get("prompt"), str) or not trace["prompt"]:
        raise AdapterError("ModelDeck trace payload is missing a prompt")
    prompt_tokens = trace.get("prompt_tokens")
    if not isinstance(prompt_tokens, list) or not prompt_tokens or not all(isinstance(token, str) for token in prompt_tokens):
        raise AdapterError("ModelDeck trace payload has invalid prompt tokens")
    steps = trace.get("steps")
    if not isinstance(steps, list) or not steps:
        raise AdapterError("ModelDeck trace payload has no replay steps")
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("selected_token"), str):
            raise AdapterError("ModelDeck trace payload contains an invalid replay step")
        candidates = step.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise AdapterError("ModelDeck trace step has no candidates")
        if not isinstance(step.get("explanation"), str) or not step["explanation"]:
            raise AdapterError("ModelDeck trace step is missing an explanation")


def _is_valid_models_payload(payload: Any) -> bool:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return False
    return all(
        isinstance(entry, dict)
        and isinstance(entry.get("id"), str)
        and isinstance(entry.get("ready"), bool)
        and (entry.get("effective_provider") is None or isinstance(entry.get("effective_provider"), str))
        for entry in payload["data"]
    )


def _gateway_url(base_url: str, path: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse((parsed.scheme or "http", parsed.netloc, path, "", "", ""))


def _ends_with_sentence(value: Any) -> bool:
    return isinstance(value, str) and re.search(r"[.!?](?:[\"')\]]*)\s*$", value) is not None


def _is_probability(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and 0 <= value <= 1


def _http_error_message(error: HTTPError) -> str:
    try:
        body = error.read().decode("utf-8", errors="replace")
    except OSError:
        return str(error)
    if not body:
        return str(error)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
        service_error = payload.get("error")
        if isinstance(service_error, dict) and isinstance(service_error.get("message"), str):
            return service_error["message"]
    return body
