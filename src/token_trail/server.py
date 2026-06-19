"""Tiny local web server for the scripted Token Trail MVP."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from token_trail.config import DEFAULT_TOKEN_TRAIL_PORT, load_config
from token_trail.runtime import RuntimeState, build_runtime_options, default_runtime_id, select_runtime
from token_trail.traces import get_trace, list_traces

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"

CONFIG = load_config()
RUNTIME_OPTIONS = build_runtime_options(CONFIG)
RUNTIME_STATE = RuntimeState(selected_id=default_runtime_id(CONFIG, RUNTIME_OPTIONS))


class TokenTrailHandler(BaseHTTPRequestHandler):
    """Serve the static UI and small JSON API."""

    server_version = "TokenTrail/0.1"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/health":
            self._send_json(
                {
                    "status": "ok",
                    "service": "token-trail",
                    "runtime": RUNTIME_STATE.selected_id,
                }
            )
            return

        if self.path == "/api/runtime":
            self._send_json(RUNTIME_STATE.to_dict(RUNTIME_OPTIONS))
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

        self.send_error(404, "Route not found")

    def log_message(self, format: str, *args: object) -> None:
        """Keep console output compact for public-demo use."""

        print(f"{self.address_string()} - {format % args}")

    def _select_runtime(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8") or "{}")
            RUNTIME_STATE.selected_id = select_runtime(str(payload["runtime_id"]), RUNTIME_OPTIONS)
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, status=400)
            return

        self._send_json(RUNTIME_STATE.to_dict(RUNTIME_OPTIONS))

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


def run_server(host: str = "127.0.0.1", port: int = DEFAULT_TOKEN_TRAIL_PORT) -> None:
    """Start the local demo server."""

    httpd = ThreadingHTTPServer((host, port), TokenTrailHandler)
    print(f"Token Trail running at http://{host}:{port}")
    print(f"Health check: http://{host}:{port}/health")
    print(f"Runtime selector: {RUNTIME_STATE.selected_id}")
    print("Press Ctrl+C to stop.")
    httpd.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Token Trail scripted MVP server.")
    parser.add_argument("--host", default=None, help="Host/interface to bind")
    parser.add_argument("--port", default=None, type=int, help="Port to bind")
    args = parser.parse_args()
    run_server(host=args.host or CONFIG.host, port=args.port or CONFIG.port)


if __name__ == "__main__":
    main()
