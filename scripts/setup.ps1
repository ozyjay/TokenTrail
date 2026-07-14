$ErrorActionPreference = "Stop"

if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Error "Poetry is required. Install it with 'pipx install poetry', restart PowerShell, then rerun this script."
}

Write-Host "Installing Token Trail dependencies with Poetry..."
poetry install
if ($LASTEXITCODE -ne 0) {
    throw "Poetry install failed with exit code $LASTEXITCODE."
}

Write-Host "Setup complete."
