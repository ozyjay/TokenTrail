#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="src"

HOST="${TOKEN_TRAIL_HOST:-127.0.0.1}"
PORT="${TOKEN_TRAIL_PORT:-3100}"

poetry run python -m token_trail.ports --host "$HOST" --port "$PORT"

echo "Starting Token Trail at http://${HOST}:${PORT} ..."
poetry run python -m token_trail.server --host "$HOST" --port "$PORT"
