$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Set-Location $ProjectRoot

if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Error "Poetry is required to run the HF trace probe. Install Poetry, then rerun this script."
}

Write-Host "Running HF trace probe..."
$env:PYTHONPATH = "src"
poetry run python scripts/probe_hf_trace.py @args
