$ErrorActionPreference = "Stop"

Write-Host "Installing Token Trail dependencies with Poetry..."
poetry install
if ($LASTEXITCODE -ne 0) {
    throw "Poetry install failed with exit code $LASTEXITCODE."
}

Write-Host "Setup complete."
