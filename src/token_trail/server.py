"""Tiny local web server for the scripted Token Trail MVP."""

from __future__ import annotations

import argparse
import json
import mimetypes
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from token_trail.adapters.base import AdapterError
from token_trail.adapters.hf_trace import HfTraceAdapter, HfTraceStatus, validate_trace_payload
from token_trail.adapters.ollama import OllamaAdapter, OllamaStatus
from token_trail.config import DEFAULT_TOKEN_TRAIL_PORT, load_config
from token_trail.config import RuntimeConfig
from token_trail.runtime import RuntimeOption, RuntimeState, build_runtime_options, default_runtime_id, select_runtime
from token_trail.traces import get_trace, list_traces

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"


@dataclass
class ServerState:
    """Runtime state owned by one Token Trail server process."""

    config: RuntimeConfig
    runtime_options: list[RuntimeOption]
    runtime_state: RuntimeState
    ollama_status: OllamaStatus
    ollama_adapter: OllamaAdapter
    hf_trace_status: HfTraceStatus
    hf_trace_adapter: HfTraceAdapter


class TokenTrailServer(ThreadingHTTPServer):
    """HTTP server carrying Token Trail runtime state."""

    def __init__(self, server_address: tuple[str, int], state: ServerState) -> None:
        super().__init__(server_address, TokenTrailHandler)
        self.state = state


def build_server_state(
    config: RuntimeConfig,
    ollama_adapter: OllamaAdapter | None = None,
    hf_trace_adapter: HfTraceAdapter | None = None,
) -> ServerState:
    """Build runtime state at startup without doing work at import time."""

    adapter = ollama_adapter or OllamaAdapter(config.ollama_base_url)
    ollama_status = adapter.status()
    trace_adapter = hf_trace_adapter or HfTraceAdapter(config.hf_trace_url)
    hf_trace_status = (
        trace_adapter.status(
            model=config.hf_trace_model,
            max_new_tokens=1,
            top_k=1,
            temperature=0,
            timeout_seconds=min(config.hf_trace_timeout_seconds, 2.0),
        )
        if config.hf_trace_enabled
        else HfTraceStatus(available=False)
    )
    runtime_options = build_runtime_options(
        config,
        ollama_status=ollama_status,
        hf_trace_available=hf_trace_status.available,
    )
    runtime_state = RuntimeState(selected_id=default_runtime_id(config, runtime_options))
    return ServerState(
        config=config,
        runtime_options=runtime_options,
        runtime_state=runtime_state,
        ollama_status=ollama_status,
        ollama_adapter=adapter,
        hf_trace_status=hf_trace_status,
        hf_trace_adapter=trace_adapter,
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
                    "ollama_available": state.ollama_status.available,
                    "ollama_models": state.ollama_status.models,
                }
            )
            return

        if self.path == "/api/runtime":
            state = self._state
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

        if self.path == "/api/runtime/warmup":
            self._warmup_runtime()
            return

        if self.path == "/api/generate-trace":
            self._generate_trace()
            return

        self.send_error(404, "Route not found")

    def log_message(self, format: str, *args: object) -> None:
        """Keep console output compact for public-demo use."""

        print(f"{self.address_string()} - {format % args}")

    def _select_runtime(self) -> None:
        state = self._state
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8") or "{}")
            state.runtime_state.selected_id = select_runtime(str(payload["runtime_id"]), state.runtime_options)
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, status=400)
            return

        self._send_json(state.runtime_state.to_dict(state.runtime_options))

    def _warmup_runtime(self) -> None:
        state = self._state
        try:
            payload = self._read_json_body()
            runtime_id = select_runtime(str(payload["runtime_id"]), state.runtime_options)
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, status=400)
            return

        runtime = next(option for option in state.runtime_options if option.id == runtime_id)
        if runtime.backend == "scripted":
            self._send_json(
                {
                    "status": "skipped",
                    "runtime_id": runtime_id,
                    "message": "Scripted runtime does not need warm-up",
                }
            )
            return

        if runtime.backend == "ollama" and runtime.available and runtime.model:
            if not state.config.ollama_warmup_enabled:
                self._send_json(
                    {
                        "status": "skipped",
                        "runtime_id": runtime_id,
                        "message": "Ollama warm-up disabled",
                    }
                )
                return

            try:
                state.ollama_adapter.warmup(
                    runtime.model,
                    timeout_seconds=state.config.ollama_warmup_timeout_seconds,
                    keep_alive=state.config.ollama_keep_alive,
                )
            except AdapterError:
                self._send_json(_warmup_fallback_payload(runtime_id))
                return

            self._send_json(
                {
                    "status": "ready",
                    "runtime_id": runtime_id,
                    "message": "Local model warmed",
                }
            )
            return

        self._send_json(_warmup_fallback_payload(runtime_id))

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

        if runtime.backend == "ollama" and runtime.available and runtime.model:
            try:
                generated_text = state.ollama_adapter.generate(
                    runtime.model,
                    live_prompt,
                    timeout_seconds=state.config.ollama_timeout_seconds,
                    max_tokens=state.config.ollama_num_predict,
                    temperature=state.config.ollama_temperature,
                    disable_thinking=state.config.ollama_disable_thinking,
                    reasoning_retry_tokens=state.config.ollama_reasoning_retry_tokens.get(runtime.model),
                )
            except AdapterError:
                self._send_json(_scripted_fallback_payload(runtime_id, trace))
                return

            self._send_json(
                {
                    "mode": "live",
                    "runtime_id": runtime_id,
                    "fallback_used": False,
                    "generated_text": generated_text,
                }
            )
            return

        if runtime.backend == "hf-trace" and runtime.available and runtime.model:
            try:
                hf_trace = state.hf_trace_adapter.generate_trace(
                    prompt=live_prompt,
                    model=runtime.model,
                    max_new_tokens=state.config.hf_trace_max_new_tokens,
                    top_k=state.config.hf_trace_top_k,
                    temperature=state.config.hf_trace_temperature,
                    timeout_seconds=state.config.hf_trace_timeout_seconds,
                )
                validate_trace_payload(hf_trace)
            except AdapterError:
                self._send_json(_scripted_fallback_payload(runtime_id, trace))
                return

            self._send_json(
                {
                    "mode": "hf-live-trace",
                    "runtime_id": runtime_id,
                    "fallback_used": False,
                    "trace": hf_trace,
                }
            )
            return

        self._send_json(_scripted_fallback_payload(runtime_id, trace))

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


def _scripted_fallback_payload(runtime_id: str, trace) -> dict:
    return {
        "mode": "scripted-fallback",
        "runtime_id": runtime_id,
        "fallback_used": True,
        "message": "Live generation unavailable",
        "trace": trace.to_dict(),
    }


def _live_prompt_from_payload(payload: dict, fallback_prompt: str) -> str:
    prompt = payload.get("prompt")
    if not isinstance(prompt, str):
        return fallback_prompt

    prompt = prompt.strip()
    if not prompt:
        return fallback_prompt
    return prompt[:500]


def _warmup_fallback_payload(runtime_id: str) -> dict:
    return {
        "status": "fallback",
        "runtime_id": runtime_id,
        "message": "Could not warm local model; scripted fallback remains available",
    }


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
    if not state.ollama_status.available and state.config.backend == "ollama":
        print("Warning: TOKEN_TRAIL_BACKEND=ollama but Ollama is unavailable; scripted fallback remains available.")
    print("Press Ctrl+C to stop.")
    httpd.serve_forever()


def main() -> None:
    config = load_config()
    parser = argparse.ArgumentParser(description="Run the Token Trail scripted MVP server.")
    parser.add_argument("--host", default=None, help="Host/interface to bind")
    parser.add_argument("--port", default=None, type=int, help="Port to bind")
    args = parser.parse_args()
    run_server(host=args.host or config.host, port=args.port or config.port, config=config)


if __name__ == "__main__":
    main()
