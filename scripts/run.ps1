$ErrorActionPreference = "Stop"

Write-Host "Starting Token Trail at http://127.0.0.1:8000 ..."
$env:PYTHONPATH = "src"
poetry run python -m token_trail.server --host 127.0.0.1 --port 8000
