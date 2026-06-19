#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="src"

poetry run python -m token_trail.ports

echo "Starting Token Trail using .env/default configuration..."
poetry run python -m token_trail.server
