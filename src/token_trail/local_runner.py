"""Local development runner for Token Trail and adapter services."""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from token_trail.adapters.base import AdapterError
from token_trail.adapters.hf_trace import HfTraceAdapter
from token_trail.config import PROJECT_ROOT, RuntimeConfig, load_config
from token_trail.ports import check_port_or_exit
from token_trail.server import run_server


HF_TRACE_HEALTH_TIMEOUT_SECONDS = 20.0
def should_manage_hf_trace(config: RuntimeConfig) -> bool:
    return config.backend == "hf-trace" and config.hf_trace_enabled


def hf_trace_server_address(config: RuntimeConfig) -> tuple[str, int]:
    parsed = urlparse(config.hf_trace_url)
    host = parsed.hostname or "127.0.0.1"
    if parsed.port is not None:
        port = parsed.port
    elif parsed.scheme == "https":
        port = 443
    else:
        port = 80
    return host, port


def hf_trace_health_url(config: RuntimeConfig) -> str:
    parsed = urlparse(config.hf_trace_url)
    scheme = parsed.scheme or "http"
    host, port = hf_trace_server_address(config)
    default_port = 443 if scheme == "https" else 80
    netloc = host if port == default_port else f"{host}:{port}"
    return f"{scheme}://{netloc}/health"


def main() -> None:
    config = load_config()
    run_local_stack(config)


def run_local_stack(config: RuntimeConfig) -> None:
    check_port_or_exit(
        host=config.host,
        port=config.port,
        service_name="Token Trail frontend/kiosk service",
    )

    hf_process: subprocess.Popen[Any] | None = None
    try:
        if should_manage_hf_trace(config):
            hf_process = ensure_hf_trace_server(config)
            config = discover_and_warm_hf_trace_model(config)

        print("Starting Token Trail using .env/default configuration...")
        run_server(host=config.host, port=config.port, config=config)
    finally:
        stop_process(hf_process)


def ensure_hf_trace_server(config: RuntimeConfig) -> subprocess.Popen[Any] | None:
    if is_hf_trace_server_healthy(config):
        print("HF trace server is already running.")
        return None

    host, port = hf_trace_server_address(config)
    print(f"Starting HF trace server at http://{host}:{port}/api/trace...")
    process = subprocess.Popen(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "serve_hf_trace.py"),
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=PROJECT_ROOT,
    )

    try:
        wait_for_hf_trace_health(config, process=process)
    except Exception:
        stop_process(process)
        raise

    return process


def discover_and_warm_hf_trace_model(config: RuntimeConfig) -> RuntimeConfig:
    adapter = HfTraceAdapter(config.hf_trace_url)
    discovery = adapter.models(timeout_seconds=2.0)
    configured_models = tuple(entry["model"] for entry in discovery["models"])
    available_entries = [entry for entry in discovery["models"] if entry["available"]]
    print("Discovered configured HF trace models:")
    for entry in discovery["models"]:
        status = "available" if entry["available"] else "unavailable"
        loaded = ", loaded" if entry["loaded"] else ""
        print(f"  - {entry['model']}: {status}{loaded} ({entry['reason']})")

    selected = _select_hf_trace_model(config.hf_trace_model, available_entries)
    if selected is None:
        detail = "; ".join(f"{entry['model']}: {entry['reason']}" for entry in discovery["models"])
        raise RuntimeError(
            "No configured HF trace models are locally available. "
            "Cache/download one configured model, choose scripted prepared traces, or update config/models.json. "
            f"Discovery results: {detail}"
        )

    if selected != config.hf_trace_model:
        print(f"Configured HF trace model {config.hf_trace_model} is unavailable; selecting {selected}.")
    else:
        print(f"Selected configured HF trace model: {selected}.")

    resolved = replace(config, hf_trace_model=selected, hf_trace_models=configured_models)
    preload_hf_trace_model(resolved, adapter=adapter)
    return resolved


def resolve_hf_trace_models(config: RuntimeConfig) -> RuntimeConfig:
    return discover_and_warm_hf_trace_model(config)


def _select_hf_trace_model(configured_default: str, available_entries: list[dict]) -> str | None:
    for entry in available_entries:
        if entry["model"] == configured_default:
            return configured_default
    if available_entries:
        return str(available_entries[0]["model"])
    return None


def preload_hf_trace_model(config: RuntimeConfig, adapter: HfTraceAdapter | None = None) -> None:
    print(f"Preloading HF trace model {config.hf_trace_model}...")
    try:
        (adapter or HfTraceAdapter(config.hf_trace_url)).warmup(
            config.hf_trace_model,
            timeout_seconds=config.hf_trace_warmup_timeout_seconds,
        )
    except AdapterError as error:
        raise RuntimeError(
            "HF trace model warm-up failed for "
            f"{config.hf_trace_model} after {config.hf_trace_warmup_timeout_seconds:g} seconds. "
            "Increase TOKEN_TRAIL_HF_TRACE_WARMUP_TIMEOUT_SECONDS, choose a smaller model, "
            "or use scripted prepared traces."
        ) from error
    print(f"HF trace model ready: {config.hf_trace_model}")


def is_hf_trace_server_healthy(config: RuntimeConfig, *, timeout_seconds: float = 1.0) -> bool:
    try:
        with urlopen(hf_trace_health_url(config), timeout=timeout_seconds) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def wait_for_hf_trace_health(
    config: RuntimeConfig,
    *,
    process: subprocess.Popen[Any],
    timeout_seconds: float = HF_TRACE_HEALTH_TIMEOUT_SECONDS,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"HF trace server exited early with status {process.returncode}")
        if is_hf_trace_server_healthy(config):
            return
        time.sleep(0.25)

    raise RuntimeError("Timed out waiting for HF trace server health check")


def stop_process(process: subprocess.Popen[Any] | None) -> None:
    if process is None or process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


if __name__ == "__main__":
    main()
