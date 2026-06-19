$ErrorActionPreference = "Stop"

$env:PYTHONPATH = "src"

poetry run python -m token_trail.ports

Write-Host "Starting Token Trail using .env/default configuration..."
poetry run python -m token_trail.server
