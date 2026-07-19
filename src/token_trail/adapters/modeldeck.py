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
MAX_TRACE_TOKENS = 128
MAX_TRACE_TOP_K = 20
MAX_TRACE_TEMPERATURE = 2.0
MAX_REQUEST_TIMEOUT_SECONDS = 60.0


class ModelDeckError(AdapterError):
    """A structured failure returned by, or while contacting, ModelDeck."""

    def __init__(self, message: str, *, code: str, http_status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


@dataclass(frozen=True)
class ModelDeckStatus:
    """Readiness summary for one ModelDeck model alias."""

    available: bool
    state: str
    error: str | None = None


class ModelDeckAdapter:
    """Discover and call a public trace route through ModelDeck."""

    def __init__(self, gateway_url: str, opener: UrlOpen = urlopen) -> None:
        self.gateway_url = gateway_url.rstrip("/")
        self._opener = opener

    def status(self, *, model: str, timeout_seconds: float = 2.0, **_: Any) -> ModelDeckStatus:
        try:
            models = self.models(timeout_seconds=timeout_seconds)
        except ModelDeckError as error:
            return ModelDeckStatus(available=False, state="gateway_unavailable", error=str(error))

        entry = next((item for item in models["data"] if item["id"] == model), None)
        if entry is None:
            return ModelDeckStatus(
                available=False,
                state="route_not_advertised",
                error=f"ModelDeck does not advertise the '{model}' demo route.",
            )
        ready = bool(entry["ready"])
        if not ready:
            return ModelDeckStatus(
                available=False,
                state="provider_not_ready",
                error=(
                    "This model is configured in ModelDeck but its worker is not ready. "
                    "Start it from the ModelDeck Workers view."
                ),
            )
        return ModelDeckStatus(available=True, state="ready", error="ModelDeck trace route is ready.")

    def models(self, *, timeout_seconds: float = 2.0) -> dict:
        request = Request(_gateway_url(self.gateway_url, "/v1/models"), method="GET")
        payload = self._request_json(request, timeout_seconds, "model discovery")
        if not _is_valid_models_payload(payload):
            raise ModelDeckError(
                "ModelDeck model discovery returned an unexpected response",
                code="gateway_invalid_response",
            )
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
        request_id: str,
    ) -> dict:
        bounded_max_tokens = max(1, min(int(max_new_tokens), MAX_TRACE_TOKENS))
        bounded_top_k = max(1, min(int(top_k), MAX_TRACE_TOP_K))
        bounded_temperature = max(0.0, min(float(temperature), MAX_TRACE_TEMPERATURE))
        messages = []
        if instructions:
            messages.append({"role": "system", "content": instructions})
        messages.append({"role": "user", "content": prompt})
        body = {
            "request_id": request_id,
            "model": model,
            "messages": messages,
            "max_tokens": bounded_max_tokens,
            "min_tokens": min(MIN_COMPLETE_SENTENCE_STEPS, bounded_max_tokens),
            "top_k": bounded_top_k,
            "temperature": bounded_temperature,
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

    def cancel(self, request_id: str, *, timeout_seconds: float = 2.0) -> dict:
        request = Request(
            _gateway_url(self.gateway_url, f"/v1/requests/{request_id}/cancel"),
            data=b"",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        payload = self._request_json(request, timeout_seconds, "cancellation request")
        if not isinstance(payload, dict) or not isinstance(payload.get("ok"), bool):
            raise ModelDeckError(
                "ModelDeck cancellation returned an unexpected response",
                code="gateway_invalid_response",
            )
        return payload

    def _request_json(self, request: Request, timeout_seconds: float, operation: str) -> Any:
        bounded_timeout = max(0.1, min(float(timeout_seconds), MAX_REQUEST_TIMEOUT_SECONDS))
        try:
            with self._opener(request, timeout=bounded_timeout) as response:
                raw_body = response.read()
        except TimeoutError as error:
            raise ModelDeckError(
                f"ModelDeck {operation} timed out", code="gateway_unavailable"
            ) from error
        except HTTPError as error:
            message, code = _http_error_details(error)
            raise ModelDeckError(
                f"ModelDeck {operation} failed: {message}",
                code=code,
                http_status=error.code,
            ) from error
        except (URLError, OSError) as error:
            raise ModelDeckError(
                f"ModelDeck {operation} failed: {error}", code="gateway_unavailable"
            ) from error
        try:
            return json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ModelDeckError(
                f"ModelDeck {operation} returned invalid JSON", code="gateway_invalid_response"
            ) from error


def _convert_trace(payload: Any, *, prompt: str, model: str) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise ModelDeckError(
            "ModelDeck trace returned an unexpected response", code="invalid_worker_trace_metadata"
        )

    events = payload["events"]
    if payload.get("cancelled") is True or any(
        isinstance(event, dict) and event.get("cancelled") is True for event in events
    ):
        raise ModelDeckError("ModelDeck trace request was cancelled.", code="request_cancelled")
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
        raise ModelDeckError(
            "ModelDeck trace did not reach a complete sentence", code="incomplete_trace"
        )

    prompt_tokens = payload.get("prompt_tokens")
    prompt_token_ids = payload.get("prompt_token_ids")
    if not _aligned_token_metadata(prompt_token_ids, prompt_tokens):
        raise ModelDeckError(
            "ModelDeck trace contains invalid prompt token metadata",
            code="invalid_worker_trace_metadata",
        )
    user_prompt_tokens = payload.get("user_prompt_tokens")
    user_prompt_token_ids = payload.get("user_prompt_token_ids")
    if not _aligned_token_metadata(user_prompt_token_ids, user_prompt_tokens):
        raise ModelDeckError(
            "ModelDeck trace contains invalid user prompt token metadata",
            code="invalid_worker_trace_metadata",
        )

    steps = [_convert_event(event) for event in events[: complete_index + 1]]
    trace = {
        "mode": "modeldeck-live-trace",
        "model": model,
        "prompt": prompt,
        "request_id": payload.get("request_id"),
        "prompt_token_ids": prompt_token_ids,
        "prompt_tokens": prompt_tokens,
        "user_prompt_token_ids": user_prompt_token_ids,
        "user_prompt_tokens": user_prompt_tokens,
        "steps": steps,
    }
    metrics = payload.get("metrics")
    if isinstance(metrics, dict):
        trace["metrics"] = metrics
    return trace


def _convert_event(event: Any) -> dict:
    if not isinstance(event, dict) or not isinstance(event.get("selected"), dict):
        raise AdapterError("ModelDeck trace contains an invalid event")
    selected = event["selected"]
    token = selected.get("token")
    probability = selected.get("probability")
    if not isinstance(token, str) or not token or not _is_probability(probability):
        raise AdapterError("ModelDeck trace contains an invalid selected token")

    candidates: list[dict[str, Any]] = [
        {"token_id": selected.get("token_id"), "token": token, "probability": probability}
    ]
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
            candidates.append(
                {
                    "token_id": alternative.get("token_id"),
                    "token": alternative_token,
                    "probability": alternative_probability,
                }
            )

    candidates.sort(key=lambda candidate: candidate["probability"], reverse=True)
    step = {
        "step": event.get("step"),
        "selected_token_id": selected.get("token_id"),
        "selected_token": token,
        "candidates": candidates,
        "explanation": "This was the token selected from the local model's returned probabilities.",
    }
    for name in (
        "generated_token_ids",
        "text_so_far",
        "timestamp",
        "elapsed_seconds",
        "complete",
    ):
        if name in event:
            step[name] = event[name]
    return step


def validate_trace_payload(trace: Any) -> None:
    if not isinstance(trace, dict) or trace.get("mode") != "modeldeck-live-trace":
        raise AdapterError("ModelDeck trace payload has an unexpected mode")
    if not isinstance(trace.get("prompt"), str) or not trace["prompt"]:
        raise AdapterError("ModelDeck trace payload is missing a prompt")
    prompt_tokens = trace.get("prompt_tokens")
    if not _aligned_token_metadata(trace.get("prompt_token_ids"), prompt_tokens):
        raise AdapterError("ModelDeck trace payload has invalid prompt tokens")
    user_prompt_tokens = trace.get("user_prompt_tokens")
    if not _aligned_token_metadata(trace.get("user_prompt_token_ids"), user_prompt_tokens):
        raise AdapterError("ModelDeck trace payload has invalid user prompt tokens")
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
        for entry in payload["data"]
    )


def _aligned_token_metadata(token_ids: Any, tokens: Any) -> bool:
    return (
        isinstance(token_ids, list)
        and isinstance(tokens, list)
        and bool(tokens)
        and len(token_ids) == len(tokens)
        and all(isinstance(token_id, int) and not isinstance(token_id, bool) for token_id in token_ids)
        and all(isinstance(token, str) for token in tokens)
    )


def _gateway_url(base_url: str, path: str) -> str:
    parsed = urlparse(base_url)
    return urlunparse((parsed.scheme or "http", parsed.netloc, path, "", "", ""))


def _ends_with_sentence(value: Any) -> bool:
    return isinstance(value, str) and re.search(r"[.!?](?:[\"')\]]*)\s*$", value) is not None


def _is_probability(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and 0 <= value <= 1


def _http_error_details(error: HTTPError) -> tuple[str, str]:
    try:
        body = error.read().decode("utf-8", errors="replace")
    except OSError:
        return str(error), "modeldeck_http_error"
    if not body:
        return str(error), "modeldeck_http_error"
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body, "modeldeck_http_error"
    if isinstance(payload, dict):
        code = "modeldeck_http_error"
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail, code
        service_error = payload.get("error")
        if isinstance(service_error, dict):
            if isinstance(service_error.get("code"), str):
                code = service_error["code"]
            if isinstance(service_error.get("message"), str):
                return service_error["message"], code
    return body, "modeldeck_http_error"
