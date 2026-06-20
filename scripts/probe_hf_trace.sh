#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if ! command -v poetry >/dev/null 2>&1; then
  echo "Poetry is required to run the HF trace probe." >&2
  echo "Install Poetry, then rerun: bash scripts/probe_hf_trace.sh" >&2
  exit 2
fi

echo "Installing optional HF trace probe dependencies with Poetry..."
poetry install --with hf-trace

echo "Running HF trace probe..."
PYTHONPATH=src poetry run python scripts/probe_hf_trace.py "$@"
