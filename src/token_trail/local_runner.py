"""Local development runner for the Token Trail web app."""

from __future__ import annotations

from token_trail.config import RuntimeConfig, load_config
from token_trail.ports import check_port_or_exit
from token_trail.server import run_server


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
    run_server(host=config.host, port=config.port, config=config)


if __name__ == "__main__":
    main()
