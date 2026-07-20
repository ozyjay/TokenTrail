$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$PidFile = Join-Path $ProjectRoot ".token-trail.pid"

if (-not (Test-Path -LiteralPath $PidFile)) {
    Write-Host "Token Trail is not running (no service PID file found)."
    exit 0
}

$PidText = (Get-Content -LiteralPath $PidFile -Raw).Trim()
$ServiceProcessId = 0
if (-not [int]::TryParse($PidText, [ref]$ServiceProcessId) -or $ServiceProcessId -le 0) {
    throw "Refusing to stop a process: $PidFile does not contain a valid process ID."
}

$ServiceProcess = Get-Process -Id $ServiceProcessId -ErrorAction SilentlyContinue
if ($null -eq $ServiceProcess) {
    Remove-Item -LiteralPath $PidFile -Force
    Write-Host "Token Trail is not running; removed stale PID file $PidFile."
    exit 0
}

if ($IsWindows) {
    $CommandLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $ServiceProcessId").CommandLine
} else {
    $CommandLine = (& ps -p $ServiceProcessId -o command= 2>$null | Out-String).Trim()
}

if ([string]::IsNullOrWhiteSpace($CommandLine) -or $CommandLine -notmatch "token_trail\.local_runner") {
    throw "Refusing to stop PID $ServiceProcessId because it is not a Token Trail local runner."
}

Write-Host "Stopping Token Trail process $ServiceProcessId..."
if ($IsWindows) {
    Stop-Process -Id $ServiceProcessId
} else {
    & kill -TERM $ServiceProcessId
    if ($LASTEXITCODE -ne 0) {
        throw "Could not signal Token Trail process $ServiceProcessId."
    }
}

try {
    Wait-Process -Id $ServiceProcessId -Timeout 10 -ErrorAction Stop
} catch {
    if ($null -ne (Get-Process -Id $ServiceProcessId -ErrorAction SilentlyContinue)) {
        throw "Token Trail process $ServiceProcessId did not stop within 10 seconds."
    }
}

if (Test-Path -LiteralPath $PidFile) {
    $RemainingPid = (Get-Content -LiteralPath $PidFile -Raw).Trim()
    if ($RemainingPid -eq $PidText) {
        Remove-Item -LiteralPath $PidFile -Force
    }
}

Write-Host "Token Trail stopped."
