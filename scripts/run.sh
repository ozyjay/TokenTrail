#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="src"

HOST="${TOKEN_TRAIL_HOST:-127.0.0.1}"
PORT="${TOKEN_TRAIL_PORT:-8000}"

echo "Starting Token Trail at http://${HOST}:${PORT} ..."
poetry run python -m token_trail.server --host "$HOST" --port "$PORT"
