"""Client for the local Hugging Face trace server."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse, urlunparse
from urllib.request import Request, urlopen

from token_trail.adapters.base import AdapterError


UrlOpen = Callable[..., Any]


@dataclass(frozen=True)
class HfTraceStatus:
    """Reachability summary for the HF trace server."""

    available: bool
    model_loaded: bool = False
    error: str | None = None


class HfTraceAdapter:
    """Call a local HF server that returns Token Trail-shaped trace JSON."""

    def __init__(self, trace_url: str, opener: UrlOpen = urlopen) -> None:
        self.trace_url = trace_url
        self._opener = opener

    def status(self, **kwargs: Any) -> HfTraceStatus:
        """Return true when the HF trace server health endpoint is reachable."""

        timeout_seconds = float(kwargs.get("timeout_seconds") or 2.0)
        model = kwargs.get("model")
        request = Request(_health_url_for_trace_url(self.trace_url, model=model if isinstance(model, str) else None), method="GET")
        try:
            with self._opener(request, timeout=timeout_seconds) as response:
                if not 200 <= int(response.status) < 300:
                    return HfTraceStatus(available=False, error=f"HF trace health returned HTTP {response.status}")
                raw_body = response.read()
        except AdapterError as error:
            if _is_incomplete_trace_error(str(error)):
                return HfTraceStatus(available=True)
            return HfTraceStatus(available=False, error=str(error))
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            return HfTraceStatus(available=False, error=str(error))

        model_loaded = False
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {}
        if isinstance(payload, dict):
            model_loaded = bool(payload.get("model_loaded"))

        return HfTraceStatus(available=True, model_loaded=model_loaded)

    def generate_trace(
        self,
        *,
        prompt: str,
        model: str,
        max_new_tokens: int,
        top_k: int,
        temperature: float,
        timeout_seconds: float,
    ) -> dict:
        """Request one non-streaming trace and validate the replay contract."""

        payload = {
            "prompt": prompt,
            "model": model,
            "max_new_tokens": max_new_tokens,
            "top_k": top_k,
            "temperature": temperature,
        }
        request = Request(
            self.trace_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with self._opener(request, timeout=timeout_seconds) as response:
                raw_body = response.read()
        except TimeoutError as error:
            raise AdapterError("HF trace request timed out") from error
        except HTTPError as error:
            raise AdapterError(f"HF trace request failed: {_http_error_message(error)}") from error
        except (URLError, OSError) as error:
            raise AdapterError(f"HF trace request failed: {error}") from error

        try:
            trace = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AdapterError("HF trace server returned invalid JSON") from error

        validate_trace_payload(trace)
        return trace

    def warmup(self, model: str, *, timeout_seconds: float) -> dict:
        """Ask the HF trace server to load the selected model without generating a trace."""

        payload = {"model": model}
        request = Request(
            _warmup_url_for_trace_url(self.trace_url),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with self._opener(request, timeout=float(timeout_seconds)) as response:
                raw_body = response.read()
        except TimeoutError as error:
            raise AdapterError("HF trace warm-up timed out") from error
        except HTTPError as error:
            raise AdapterError(f"HF trace warm-up failed: {_http_error_message(error)}") from error
        except (URLError, OSError) as error:
            raise AdapterError(f"HF trace warm-up failed: {error}") from error

        try:
            result = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AdapterError("HF trace warm-up returned invalid JSON") from error

        if not isinstance(result, dict) or result.get("status") != "ready" or result.get("model") != model:
            raise AdapterError("HF trace warm-up returned an unexpected response")
        return result

    def available_models(self, *, timeout_seconds: float) -> list[str]:
        """Return locally available HF trace models reported by the trace server."""

        request = Request(_models_url_for_trace_url(self.trace_url), method="GET")
        try:
            with self._opener(request, timeout=float(timeout_seconds)) as response:
                raw_body = response.read()
        except TimeoutError as error:
            raise AdapterError("HF trace model discovery timed out") from error
        except HTTPError as error:
            raise AdapterError(f"HF trace model discovery failed: {_http_error_message(error)}") from error
        except (URLError, OSError) as error:
            raise AdapterError(f"HF trace model discovery failed: {error}") from error

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AdapterError("HF trace model discovery returned invalid JSON") from error

        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list) or not all(isinstance(model, str) and model.strip() for model in models):
            raise AdapterError("HF trace model discovery returned an unexpected response")
        return list(dict.fromkeys(model.strip() for model in models))


def validate_trace_payload(trace: Any) -> None:
    if not isinstance(trace, dict):
        raise AdapterError("HF trace payload is not an object")

    if trace.get("mode") != "hf-live-trace":
        raise AdapterError("HF trace payload has an unexpected mode")

    if not isinstance(trace.get("prompt"), str) or not trace["prompt"]:
        raise AdapterError("HF trace payload is missing a prompt")

    prompt_tokens = trace.get("prompt_tokens")
    if not isinstance(prompt_tokens, list) or not all(isinstance(token, str) for token in prompt_tokens):
        raise AdapterError("HF trace payload has invalid prompt tokens")

    steps = trace.get("steps")
    if not isinstance(steps, list) or not steps:
        raise AdapterError("HF trace payload has no replay steps")

    for step in steps:
        if not isinstance(step, dict):
            raise AdapterError("HF trace step is not an object")
        if not isinstance(step.get("selected_token"), str) or not step["selected_token"]:
            raise AdapterError("HF trace step is missing a selected token")
        if not isinstance(step.get("explanation"), str) or not step["explanation"]:
            raise AdapterError("HF trace step is missing an explanation")

        candidates = step.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise AdapterError("HF trace step has no candidates")
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise AdapterError("HF trace candidate is not an object")
            if not isinstance(candidate.get("token"), str) or not candidate["token"]:
                raise AdapterError("HF trace candidate is missing a token")
            probability = candidate.get("probability")
            if not isinstance(probability, int | float) or probability < 0 or probability > 1:
                raise AdapterError("HF trace candidate has invalid probability")


def _http_error_message(error: HTTPError) -> str:
    try:
        body = error.read().decode("utf-8", errors="replace")
    except OSError:
        body = ""

    if body:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return body
        if isinstance(payload, dict) and isinstance(payload.get("error"), str):
            return payload["error"]
        return body

    return str(error)


def _is_incomplete_trace_error(message: str) -> bool:
    return "complete sentence" in message


def _health_url_for_trace_url(trace_url: str, *, model: str | None = None) -> str:
    parsed = urlparse(trace_url)
    query = f"model={quote(model, safe='')}" if model else ""
    return urlunparse((parsed.scheme or "http", parsed.netloc, "/health", "", query, ""))


def _warmup_url_for_trace_url(trace_url: str) -> str:
    parsed = urlparse(trace_url)
    return urlunparse((parsed.scheme or "http", parsed.netloc, "/api/warmup", "", "", ""))


def _models_url_for_trace_url(trace_url: str) -> str:
    parsed = urlparse(trace_url)
    return urlunparse((parsed.scheme or "http", parsed.netloc, "/api/models", "", "", ""))
