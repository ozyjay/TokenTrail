"""Local development runner for the Token Trail web app."""

from __future__ import annotations

import os
import signal
from contextlib import contextmanager
from pathlib import Path
from types import FrameType
from typing import Iterator

from token_trail.config import RuntimeConfig, load_config
from token_trail.config import PROJECT_ROOT
from token_trail.ports import check_port_or_exit
from token_trail.server import run_server


PID_FILE = PROJECT_ROOT / ".token-trail.pid"


def main() -> None:
    run_local_stack(load_config())


def run_local_stack(config: RuntimeConfig) -> None:
    """Run Token Trail without owning any external model-service processes."""

    check_port_or_exit(
        host=config.host,
        port=config.port,
        service_name="Token Trail frontend/kiosk service",
    )
    print("Starting Token Trail using .env/default configuration...")
    if config.backend == "modeldeck":
        print(f"Using externally managed ModelDeck gateway at {config.modeldeck_url}.")
    with _managed_service_process(PID_FILE):
        run_server(host=config.host, port=config.port, config=config)


@contextmanager
def _managed_service_process(pid_file: Path) -> Iterator[None]:
    """Record the service PID and translate termination into a clean shutdown."""

    process_id = os.getpid()
    pid_file.write_text(f"{process_id}\n", encoding="utf-8")
    previous_handler = signal.getsignal(signal.SIGTERM)

    def stop_service(_signal_number: int, _frame: FrameType | None) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop_service)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
        try:
            recorded_process_id = pid_file.read_text(encoding="utf-8").strip()
        except OSError:
            recorded_process_id = ""
        if recorded_process_id == str(process_id):
            pid_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
