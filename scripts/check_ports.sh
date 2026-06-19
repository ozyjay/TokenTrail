#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="src"
poetry run python -m token_trail.ports
