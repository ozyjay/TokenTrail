#!/usr/bin/env bash
set -euo pipefail

echo "Running Token Trail tests..."
export PYTHONPATH="src"
poetry run python -m compileall src tests
poetry run pytest
