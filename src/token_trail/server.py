"""Local web server for Token Trail's ModelDeck and scripted runtimes."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from token_trail.adapters.base import AdapterError
from token_trail.adapters.modeldeck import (
    ModelDeckAdapter,
    ModelDeckError,
    ModelDeckStatus,
    capability_status,
    validate_trace_payload,
)
from token_trail.config import DEFAULT_TOKEN_TRAIL_PORT, RuntimeConfig, load_config
from token_trail.runtime import RuntimeOption, RuntimeState, build_runtime_options, default_runtime_id, select_runtime
from token_trail.traces import get_trace, list_traces


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"
MODELDECK_DISCOVERY_TIMEOUT_SECONDS = 2.0
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


@dataclass
class ServerState:
    """Runtime state owned by one Token Trail server process."""

    config: RuntimeConfig
    runtime_options: list[RuntimeOption]
    runtime_state: RuntimeState
    modeldeck_status: ModelDeckStatus
    modeldeck_adapter: ModelDeckAdapter


class TokenTrailServer(ThreadingHTTPServer):
    """HTTP server carrying Token Trail runtime state."""

    def __init__(self, server_address: tuple[str, int], state: ServerState) -> None:
        super().__init__(server_address, TokenTrailHandler)
        self.state = state


def build_server_state(
    config: RuntimeConfig,
    modeldeck_adapter: ModelDeckAdapter | None = None,
) -> ServerState:
    """Build runtime state at startup without doing work at import time."""

    trace_adapter = modeldeck_adapter or ModelDeckAdapter(config.modeldeck_url)
    statuses = _modeldeck_statuses(config, trace_adapter)
    modeldeck_status = statuses.get(
        config.modeldeck_model,
        ModelDeckStatus(available=False, state="gateway_unavailable"),
    )
    runtime_options = build_runtime_options(config, modeldeck_statuses=_runtime_status_payload(statuses))
    runtime_state = RuntimeState(selected_id=default_runtime_id(config, runtime_options))
    return ServerState(
        config=config,
        runtime_options=runtime_options,
        runtime_state=runtime_state,
        modeldeck_status=modeldeck_status,
        modeldeck_adapter=trace_adapter,
    )


class TokenTrailHandler(BaseHTTPRequestHandler):
    """Serve the static UI and small JSON API."""

    server_version = "TokenTrail/0.1"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/health":
            state = self._state
            self._send_json(
                {
                    "status": "ok",
                    "service": "token-trail",
                    "runtime": state.runtime_state.selected_id,
                }
            )
            return

        if self.path == "/api/runtime":
            state = self._state
            _refresh_runtime_options(state)
            self._send_json(state.runtime_state.to_dict(state.runtime_options))
            return

        if self.path == "/api/traces":
            self._send_json({"traces": list_traces()})
            return

        if self.path.startswith("/api/traces/"):
            trace_id = unquote(self.path.removeprefix("/api/traces/"))
            try:
                self._send_json(get_trace(trace_id).to_dict())
            except KeyError:
                self._send_json({"error": "Trace not found"}, status=404)
            return

        self._serve_static_file()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/api/runtime/select":
            self._select_runtime()
            return

        if self.path == "/api/generate-trace":
            self._generate_trace()
            return

        if self.path == "/api/generate-trace/cancel":
            self._cancel_trace()
            return

        self._send_json({"message": "Route not found"}, status=404)

    def log_message(self, format: str, *args: object) -> None:
        """Keep console output compact for public-demo use."""

        print(f"{self.address_string()} - {format % args}")

    def _select_runtime(self) -> None:
        state = self._state
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8") or "{}")
            state.runtime_state.selected_id = select_runtime(str(payload["runtime_id"]), state.runtime_options)
            _refresh_runtime_options(state)
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, status=400)
            return

        self._send_json(state.runtime_state.to_dict(state.runtime_options))

    def _generate_trace(self) -> None:
        state = self._state
        try:
            payload = self._read_json_body()
            runtime_id = str(payload["runtime_id"])
            trace_id = str(payload["trace_id"])
            select_runtime(runtime_id, state.runtime_options)
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, status=400)
            return

        try:
            trace = get_trace(trace_id)
        except KeyError as error:
            self._send_json({"error": str(error)}, status=404)
            return

        live_prompt = _live_prompt_from_payload(payload, trace.prompt)
        _refresh_runtime_options(state)
        runtime = next(option for option in state.runtime_options if option.id == runtime_id)
        if runtime.backend == "scripted":
            self._send_json(
                {
                    "mode": "scripted",
                    "runtime_id": runtime_id,
                    "fallback_used": False,
                    "message": "Prepared Demo Mode",
                    "trace": trace.to_dict(),
                }
            )
            return

        if runtime.backend == "modeldeck" and runtime.available and runtime.model:
            try:
                request_id = _request_id_from_payload(payload)
            except ValueError as error:
                self._send_json({"error": str(error), "code": "invalid_request_id"}, status=400)
                return
            try:
                modeldeck_trace = state.modeldeck_adapter.generate_trace(
                    prompt=live_prompt,
                    instructions=state.config.modeldeck_instructions,
                    model=runtime.model,
                    max_new_tokens=state.config.modeldeck_max_new_tokens,
                    top_k=state.config.modeldeck_top_k,
                    temperature=state.config.modeldeck_temperature,
                    timeout_seconds=state.config.modeldeck_timeout_seconds,
                    request_id=request_id,
                )
                validate_trace_payload(modeldeck_trace)
            except ModelDeckError as error:
                self._send_json(
                    _live_error_payload(
                        runtime_id,
                        state=_request_error_state(error.code),
                        code=error.code,
                    ),
                    status=error.http_status or _live_error_status(error.code),
                )
                return
            except AdapterError as error:
                self._send_json(
                    _live_error_payload(
                        runtime_id,
                        state="invalid_worker_trace_metadata",
                        code="invalid_worker_trace_metadata",
                    ),
                    status=502,
                )
                return

            self._send_json(
                {
                    "mode": "modeldeck-live-trace",
                    "runtime_id": runtime_id,
                    "fallback_used": False,
                    "trace": modeldeck_trace,
                }
            )
            return

        self._send_json(
            _live_error_payload(runtime_id, state=runtime.status),
            status=503,
        )

    def _cancel_trace(self) -> None:
        try:
            payload = self._read_json_body()
            request_id = _request_id_from_payload(payload)
            result = self._state.modeldeck_adapter.cancel(
                request_id,
                timeout_seconds=MODELDECK_DISCOVERY_TIMEOUT_SECONDS,
            )
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error), "code": "invalid_request_id"}, status=400)
            return
        except ModelDeckError as error:
            self._send_json(
                {"error": str(error), "code": error.code, "state": _request_error_state(error.code)},
                status=error.http_status or 503,
            )
            return

        self._send_json(
            {
                "request_id": request_id,
                "cancelled": result["ok"],
                "state": "request_cancelled" if result["ok"] else "request_not_active",
                "gateway_state": result.get("state"),
                "worker_id": result.get("worker_id"),
            }
        )

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(content_length).decode("utf-8") or "{}")

    @property
    def _state(self) -> ServerState:
        return self.server.state  # type: ignore[attr-defined]

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static_file(self) -> None:
        requested = self.path.split("?", 1)[0]
        relative = "index.html" if requested in {"", "/"} else requested.lstrip("/")
        path = (WEB_ROOT / relative).resolve()

        if not path.is_file() or WEB_ROOT.resolve() not in path.parents:
            self.send_error(404, "File not found")
            return

        content_type, _ = mimetypes.guess_type(path.name)
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _live_error_payload(
    runtime_id: str,
    *,
    state: str = "request_failed",
    code: str | None = None,
) -> dict:
    return {
        "mode": "modeldeck-unavailable",
        "runtime_id": runtime_id,
        "fallback_used": False,
        "message": _live_error_message(state),
        "state": state,
        "code": code,
    }


def _modeldeck_statuses(config: RuntimeConfig, adapter: ModelDeckAdapter) -> dict[str, ModelDeckStatus]:
    if not config.modeldeck_enabled:
        return {}

    try:
        payload = adapter.capabilities(timeout_seconds=MODELDECK_DISCOVERY_TIMEOUT_SECONDS)
    except ModelDeckError as error:
        return {
            model: ModelDeckStatus(False, "gateway_unavailable", str(error))
            for model in config.modeldeck_models
        }

    return {model: capability_status(payload, model) for model in config.modeldeck_models}


def _runtime_status_payload(statuses: dict[str, ModelDeckStatus]) -> dict[str, dict]:
    return {
        model: {
            "available": status.available,
            "state": status.state,
            "reason": status.error,
        }
        for model, status in statuses.items()
    }


def _refresh_runtime_options(state: ServerState) -> None:
    statuses = _modeldeck_statuses(state.config, state.modeldeck_adapter)
    state.modeldeck_status = statuses.get(
        state.config.modeldeck_model,
        ModelDeckStatus(available=False, state="gateway_unavailable"),
    )
    state.runtime_options = build_runtime_options(
        state.config,
        modeldeck_statuses=_runtime_status_payload(statuses),
    )


def _live_prompt_from_payload(payload: dict, fallback_prompt: str) -> str:
    prompt = payload.get("prompt")
    if not isinstance(prompt, str):
        return fallback_prompt

    prompt = prompt.strip()
    if not prompt:
        return fallback_prompt
    return prompt[:500]


def _request_id_from_payload(payload: dict) -> str:
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or REQUEST_ID_PATTERN.fullmatch(request_id) is None:
        raise ValueError("request_id must be 1–128 safe identifier characters")
    return request_id


def _request_error_state(code: str) -> str:
    return {
        "local_provider_unavailable": "provider_not_ready",
        "local_route_unavailable": "route_unavailable",
        "invalid_worker_trace_metadata": "invalid_worker_trace_metadata",
        "request_cancelled": "request_cancelled",
        "gateway_unavailable": "gateway_unavailable",
    }.get(code, "request_failed")


def _live_error_message(state: str) -> str:
    messages = {
        "gateway_unavailable": "The ModelDeck gateway is unavailable. Check that ModelDeck is running.",
        "route_not_advertised": "This native capability is not published in ModelDeck. Check its publication.",
        "incompatible_contract": "This capability requires native-ar-trace-v1 and its canonical trace surface. Check ModelDeck publication and version.",
        "provider_not_ready": (
            "This model is configured in ModelDeck but its worker is not ready. "
            "Start it from the ModelDeck Workers view."
        ),
        "route_unavailable": "The selected ModelDeck route cannot serve this request. Refresh readiness and check its publication, protocol and Workers in ModelDeck.",
        "request_cancelled": "The live ModelDeck trace request was cancelled.",
        "invalid_worker_trace_metadata": "ModelDeck returned invalid trace metadata; no live trace was shown.",
        "request_failed": "The live ModelDeck trace request failed; no prepared output was substituted.",
    }
    return messages.get(state, messages["request_failed"])


def _live_error_status(code: str) -> int:
    if code == "invalid_worker_trace_metadata":
        return 502
    if code == "request_cancelled":
        return 409
    return 503


def run_server(
    host: str = "127.0.0.1",
    port: int = DEFAULT_TOKEN_TRAIL_PORT,
    config: RuntimeConfig | None = None,
) -> None:
    """Start the local demo server."""

    state = build_server_state(config or load_config())
    httpd = TokenTrailServer((host, port), state)
    print(f"Token Trail running at http://{host}:{port}")
    print(f"Health check: http://{host}:{port}/health")
    print(f"Runtime selector: {state.runtime_state.selected_id}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Token Trail.")
    finally:
        httpd.server_close()


def main() -> None:
    config = load_config()
    parser = argparse.ArgumentParser(description="Run the Token Trail demo server.")
    parser.add_argument("--host", default=None, help="Host/interface to bind")
    parser.add_argument("--port", default=None, type=int, help="Port to bind")
    args = parser.parse_args()
    run_server(host=args.host or config.host, port=args.port or config.port, config=config)


if __name__ == "__main__":
    main()
