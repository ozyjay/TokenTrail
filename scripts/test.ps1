$ErrorActionPreference = "Stop"

Write-Host "Running Token Trail tests..."
$env:PYTHONPATH = "src"
poetry run python -m compileall src tests
if ($LASTEXITCODE -ne 0) {
    throw "compileall failed with exit code $LASTEXITCODE."
}
poetry run pytest
if ($LASTEXITCODE -ne 0) {
    throw "pytest failed with exit code $LASTEXITCODE."
}
