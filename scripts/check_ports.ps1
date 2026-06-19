$ErrorActionPreference = "Stop"

$HostName = if ($env:TOKEN_TRAIL_HOST) { $env:TOKEN_TRAIL_HOST } else { "127.0.0.1" }
$Port = if ($env:TOKEN_TRAIL_PORT) { $env:TOKEN_TRAIL_PORT } else { "3100" }

$env:PYTHONPATH = "src"
poetry run python -m token_trail.ports --host $HostName --port $Port
