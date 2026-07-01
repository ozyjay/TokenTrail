$ErrorActionPreference = "Stop"

$env:PYTHONPATH = "src"

poetry run python -m token_trail.local_runner
if ($LASTEXITCODE -ne 0) {
    throw "Token Trail exited with code $LASTEXITCODE."
}
