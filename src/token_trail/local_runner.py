"""Local development runner for Token Trail and optional adapter services."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen

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
