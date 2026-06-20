"""Client for the optional local Hugging Face trace server."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from token_trail.adapters.base import AdapterError


UrlOpen = Callable[..., Any]


@dataclass(frozen=True)
class HfTraceStatus:
    """Reachability summary for the optional HF trace server."""

    available: bool
    error: str | None = None


class HfTraceAdapter:
    """Call a local HF server that returns Token Trail-shaped trace JSON."""

    def __init__(self, trace_url: str, opener: UrlOpen = urlopen) -> None:
        self.trace_url = trace_url
        self._opener = opener

    def status(self, **kwargs: Any) -> HfTraceStatus:
        """Return true only when a tiny trace probe returns usable steps."""

        try:
            self.generate_trace(
                prompt="Token Trail readiness check.",
                model=str(kwargs.get("model") or ""),
                max_new_tokens=int(kwargs.get("max_new_tokens") or 1),
                top_k=int(kwargs.get("top_k") or 1),
                temperature=float(kwargs.get("temperature") or 0),
                timeout_seconds=float(kwargs.get("timeout_seconds") or 2.0),
            )
        except AdapterError as error:
            if _is_incomplete_trace_error(str(error)):
                return HfTraceStatus(available=True)
            return HfTraceStatus(available=False, error=str(error))

        return HfTraceStatus(available=True)

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
