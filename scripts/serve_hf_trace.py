"""Serve Token Trail-shaped Hugging Face traces over local HTTP."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import threading
import warnings
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import parse_qs, urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from token_trail.adapters.base import AdapterError  # noqa: E402
from token_trail.adapters.hf_trace import validate_trace_payload  # noqa: E402
from token_trail.config import RuntimeConfig, load_config  # noqa: E402


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8600
DEFAULT_CANDIDATE_SOURCE = "forward-logits"
MAX_PROMPT_CHARS = 500
PYTHON_STARTUP_ROOT = PROJECT_ROOT / "scripts" / "hf_trace_python_startup"


def _install_resource_tracker_warning_filter() -> None:
    warnings.filterwarnings(
        "ignore",
        message=r"resource_tracker: There appear to be .* leaked semaphore objects to clean up at shutdown",
        category=UserWarning,
        module="multiprocessing.resource_tracker",
    )

    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath_entries = [entry for entry in existing_pythonpath.split(os.pathsep) if entry]
    startup_entry = str(PYTHON_STARTUP_ROOT)
    if startup_entry not in pythonpath_entries:
        os.environ["PYTHONPATH"] = os.pathsep.join([startup_entry, *pythonpath_entries])


_install_resource_tracker_warning_filter()


class HfTraceServerError(Exception):
    """Raised when a request cannot produce a valid HF trace."""


@dataclass
class TransformersTraceRunner:
    candidate_source: str = DEFAULT_CANDIDATE_SOURCE

    def __post_init__(self) -> None:
        self._probe = _load_probe_module()
        self._torch = None
        self._model_class = None
        self._tokenizer_class = None
        self._config_class = None
        self._metadata_tokenizer_class = None
        self._models: dict[str, tuple[Any, Any]] = {}
        self._generation_lock = threading.Lock()

    def generate_trace(
        self,
        *,
        prompt: str,
        instructions: str = "",
        model: str,
        max_new_tokens: int,
        top_k: int,
        temperature: float,
    ) -> dict[str, Any]:
        with self._generation_lock:
            tokenizer, loaded_model = self._model_and_tokenizer(model)
            generated = self._probe.generate_with_scores(
                tokenizer=tokenizer,
                model=loaded_model,
                torch_module=self._torch,
                prompt=prompt,
                instructions=instructions,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
            )
            trace = self._probe.build_trace_from_generation(
                model_name=model,
                prompt=prompt,
                tokenizer=tokenizer,
                model=loaded_model,
                torch_module=self._torch,
                generated=generated,
                top_k=top_k,
                candidate_source=self.candidate_source,
            )
            validate_trace_payload(trace)
            return trace

    def preload_model(self, model: str) -> None:
        with self._generation_lock:
            self._model_and_tokenizer(model)

    def _model_and_tokenizer(self, model_name: str) -> tuple[Any, Any]:
        if self._torch is None or self._model_class is None or self._tokenizer_class is None:
            self._torch, self._model_class, self._tokenizer_class = self._probe.load_hf_libraries()

        if model_name not in self._models:
            self._models[model_name] = self._probe.load_model_and_tokenizer(
                model_name=model_name,
                model_class=self._model_class,
                tokenizer_class=self._tokenizer_class,
                torch_module=self._torch,
                local_files_only=True,
            )

        return self._models[model_name]

    def is_model_loaded(self, model: str) -> bool:
        return model in self._models

    def list_local_models(self) -> list[str]:
        return self._probe.list_local_models()

    def discover_model(self, model: str) -> dict[str, Any]:
        if self.is_model_loaded(model):
            return {
                "cached": True,
                "metadata_loadable": True,
                "available": True,
                "reason": "Loaded",
            }

        try:
            cached = model in self._probe.list_local_models()
        except Exception as error:
            return {
                "cached": False,
                "metadata_loadable": False,
                "available": False,
                "reason": str(error),
            }

        metadata_loadable = False
        metadata_error = ""
        if cached:
            metadata_loadable, metadata_error = self._metadata_loadable(model)

        if cached:
            if not metadata_loadable:
                return {
                    "cached": True,
                    "metadata_loadable": False,
                    "available": False,
                    "reason": metadata_error or "Local metadata is not loadable",
                }
            return {
                "cached": True,
                "metadata_loadable": metadata_loadable,
                "available": True,
                "reason": "Available locally; not loaded",
            }
        return {
            "cached": False,
            "metadata_loadable": False,
            "available": False,
            "reason": "Not found locally",
        }

    def _metadata_loadable(self, model: str) -> tuple[bool, str]:
        if self._config_class is None or self._metadata_tokenizer_class is None:
            self._config_class, self._metadata_tokenizer_class = _load_hf_metadata_libraries()

        try:
            self._config_class.from_pretrained(model, local_files_only=True)
            self._metadata_tokenizer_class.from_pretrained(model, local_files_only=True)
        except Exception as error:
            return False, str(error)
        return True, ""


@dataclass
class HfTraceServerState:
    trace_runner: Any
    config: RuntimeConfig


class HfTraceHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], state: HfTraceServerState) -> None:
        super().__init__(server_address, HfTraceRequestHandler)
        self.state = state


class HfTraceRequestHandler(BaseHTTPRequestHandler):
    server_version = "TokenTrailHfTrace/0.1"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            payload: dict[str, Any] = {"status": "ok", "service": "token-trail-hf-trace"}
            model = parse_qs(parsed.query).get("model", [""])[0]
            if model:
                is_loaded = getattr(self.server.state.trace_runner, "is_model_loaded", lambda value: False)
                payload["model"] = model
                payload["model_loaded"] = bool(is_loaded(model))
            self._send_json(payload)
            return
        if parsed.path == "/api/models":
            self._send_json(build_model_discovery_payload(self.server.state.config, self.server.state.trace_runner))
            return
        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/api/warmup":
            self._handle_warmup()
            return

        if self.path != "/api/trace":
            self._send_json({"error": "Not found"}, status=404)
            return

        try:
            request = self._read_request()
            trace = self.server.state.trace_runner.generate_trace(**request)
            validate_trace_payload(trace)
        except (AdapterError, HfTraceServerError) as error:
            self._send_json({"error": str(error)}, status=400)
            return
        except Exception as error:  # pragma: no cover - defensive HTTP boundary
            self._send_json({"error": f"HF trace generation failed: {error}"}, status=500)
            return

        self._send_json(trace)

    def _handle_warmup(self) -> None:
        try:
            payload = self._read_json_body()
            model = _required_string(payload, "model")
            self.server.state.trace_runner.preload_model(model)
        except HfTraceServerError as error:
            self._send_json({"error": str(error)}, status=400)
            return
        except Exception as error:  # pragma: no cover - defensive HTTP boundary
            self._send_json({"error": f"HF trace warm-up failed: {error}"}, status=500)
            return

        self._send_json({"status": "ready", "model": model})

    def _read_request(self) -> dict[str, Any]:
        payload = self._read_json_body()

        prompt = _required_string(payload, "prompt")
        if len(prompt) > MAX_PROMPT_CHARS:
            raise HfTraceServerError(f"prompt must be {MAX_PROMPT_CHARS} characters or fewer")
        model = _required_string(payload, "model")
        instructions = _optional_string(payload, "instructions") or self.server.state.config.hf_trace_instructions
        return {
            "prompt": prompt,
            "instructions": instructions,
            "model": model,
            "max_new_tokens": _int_setting(payload, "max_new_tokens", 24, minimum=1),
            "top_k": _int_setting(payload, "top_k", 5, minimum=1),
            "temperature": _float_setting(payload, "temperature", 0.3, minimum=0),
        }

    def _read_json_body(self) -> Any:
        length = int(self.headers.get("Content-Length", "0"))
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise HfTraceServerError("Request body must be valid JSON") from error

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def build_model_discovery_payload(config: RuntimeConfig, trace_runner: Any) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for model in config.hf_trace_models:
        loaded = bool(getattr(trace_runner, "is_model_loaded", lambda value: False)(model))
        try:
            raw_discovery = getattr(trace_runner, "discover_model", _fallback_discover_model)(model)
        except Exception as error:
            raw_discovery = {
                "cached": False,
                "metadata_loadable": False,
                "available": False,
                "reason": str(error),
            }

        cached = bool(raw_discovery.get("cached", False))
        metadata_loadable = bool(raw_discovery.get("metadata_loadable", False))
        available = bool(raw_discovery.get("available", loaded or (cached and metadata_loadable)))
        reason = raw_discovery.get("reason")
        if loaded:
            cached = True
            metadata_loadable = True
            available = True
            reason = "Loaded"
        elif not isinstance(reason, str) or not reason:
            reason = "Available locally; not loaded" if available else "Not found locally"

        entries.append(
            {
                "model": model,
                "configured": True,
                "cached": cached,
                "metadata_loadable": metadata_loadable,
                "loaded": loaded,
                "available": available,
                "reason": reason,
            }
        )

    selected = config.hf_trace_model
    if not any(entry["model"] == selected and entry["available"] for entry in entries):
        selected = next((entry["model"] for entry in entries if entry["available"]), config.hf_trace_model)

    return {
        "default_model": config.hf_trace_model,
        "selected_model": selected,
        "models": entries,
    }


def _fallback_discover_model(model: str) -> dict[str, Any]:
    return {
        "cached": False,
        "metadata_loadable": False,
        "available": False,
        "reason": "Model discovery is not supported by this trace runner",
    }


def create_server(
    server_address: tuple[str, int],
    trace_runner: Any | None = None,
    config: RuntimeConfig | None = None,
) -> HfTraceHTTPServer:
    return HfTraceHTTPServer(server_address, HfTraceServerState(trace_runner or TransformersTraceRunner(), config or load_config()))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve local HF traces for Token Trail.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    parser.add_argument(
        "--candidate-source",
        default=DEFAULT_CANDIDATE_SOURCE,
        choices=("forward-logits", "generation-scores"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    runner = TransformersTraceRunner(candidate_source=args.candidate_source)
    httpd = create_server((args.host, args.port), trace_runner=runner)
    print(f"HF trace server listening at http://{args.host}:{args.port}/api/trace", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping HF trace server.", flush=True)
    finally:
        httpd.server_close()
    return 0


def _load_probe_module() -> Any:
    script_path = PROJECT_ROOT / "scripts" / "probe_hf_trace.py"
    spec = importlib.util.spec_from_file_location("probe_hf_trace", script_path)
    if spec is None or spec.loader is None:
        raise HfTraceServerError("Could not load HF trace probe module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_hf_metadata_libraries() -> tuple[Any, Any]:
    try:
        from transformers import AutoConfig, AutoTokenizer
    except Exception as error:
        raise HfTraceServerError(f"Could not load HF metadata libraries: {error}") from error
    return AutoConfig, AutoTokenizer


def _required_string(payload: Any, key: str) -> str:
    if not isinstance(payload, dict):
        raise HfTraceServerError("Request body must be a JSON object")

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise HfTraceServerError(f"Request body is missing required string: {key}")
    return value.strip()


def _optional_string(payload: Any, key: str) -> str:
    if not isinstance(payload, dict):
        raise HfTraceServerError("Request body must be a JSON object")

    value = payload.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise HfTraceServerError(f"{key} must be a string")
    return value.strip()


def _int_setting(payload: dict[str, Any], key: str, default: int, *, minimum: int) -> int:
    value = payload.get(key, default)
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise HfTraceServerError(f"{key} must be an integer") from error
    if parsed < minimum:
        raise HfTraceServerError(f"{key} must be at least {minimum}")
    return parsed


def _float_setting(payload: dict[str, Any], key: str, default: float, *, minimum: float) -> float:
    value = payload.get(key, default)
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise HfTraceServerError(f"{key} must be a number") from error
    if parsed < minimum:
        raise HfTraceServerError(f"{key} must be at least {minimum}")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
