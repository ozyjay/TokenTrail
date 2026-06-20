$ErrorActionPreference = "Stop"

$env:PYTHONPATH = "src"

$RequiresHfTrace = poetry run python -c "from token_trail.config import load_config; c = load_config(); print('true' if c.backend == 'hf-trace' and c.hf_trace_enabled else 'false')"

if ($RequiresHfTrace.Trim() -eq "true") {
    Write-Host "Installing optional HF trace dependencies with Poetry..."
    poetry install --with hf-trace
}

poetry run python -m token_trail.local_runner
