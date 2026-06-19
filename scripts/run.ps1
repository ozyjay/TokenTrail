$ErrorActionPreference = "Stop"

$HostName = if ($env:TOKEN_TRAIL_HOST) { $env:TOKEN_TRAIL_HOST } else { "127.0.0.1" }
$Port = if ($env:TOKEN_TRAIL_PORT) { $env:TOKEN_TRAIL_PORT } else { "8000" }

Write-Host "Starting Token Trail at http://${HostName}:${Port} ..."
$env:PYTHONPATH = "src"
poetry run python -m token_trail.server --host $HostName --port $Port
