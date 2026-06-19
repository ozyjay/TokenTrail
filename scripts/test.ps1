$ErrorActionPreference = "Stop"

Write-Host "Running Token Trail tests..."
$env:PYTHONPATH = "src"
poetry run python -m compileall src tests
poetry run pytest
