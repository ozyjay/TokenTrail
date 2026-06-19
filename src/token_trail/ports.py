"""Port availability checks for Token Trail launch scripts."""

from __future__ import annotations

import argparse
import socket
import sys
from contextlib import closing

from token_trail.config import load_config


def is_port_available(host: str, port: int) -> bool:
    """Return True if a TCP port can be bound on the requested host."""

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def check_port_or_exit(host: str, port: int, service_name: str) -> None:
    """Print a clear error and exit if a required port is occupied."""

    if is_port_available(host, port):
        print(f"OK: {service_name} port {host}:{port} is available.")
        return

    print(f"ERROR: Port {host}:{port} is already in use.", file=sys.stderr)
    print(f"Expected service: {service_name}", file=sys.stderr)
    print("Stop the existing process or change TOKEN_TRAIL_PORT in .env.", file=sys.stderr)
    print("For rehearsal/Open Day mode, do not continue with an unplanned port.", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    config = load_config()
    parser = argparse.ArgumentParser(description="Check Token Trail launch ports.")
    parser.add_argument("--host", default=None, help="Host/interface to check")
    parser.add_argument("--port", default=None, type=int, help="Port to check")
    args = parser.parse_args()

    check_port_or_exit(
        host=args.host or config.host,
        port=args.port or config.port,
        service_name="Token Trail frontend/kiosk service",
    )


if __name__ == "__main__":
    main()
