$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Set-Location $ProjectRoot

if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Error "Poetry is required to run the HF trace probe. Install Poetry, then rerun this script."
}

Write-Host "Installing optional HF trace probe dependencies with Poetry..."
poetry install --with hf-trace

Write-Host "Running HF trace probe..."
$env:PYTHONPATH = "src"
poetry run python scripts/probe_hf_trace.py @args
