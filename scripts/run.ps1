$ErrorActionPreference = "Stop"

$env:PYTHONPATH = "src"

poetry run python -m token_trail.local_runner
