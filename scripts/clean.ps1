param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

function Remove-CleanItem {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $resolvedPath = (Resolve-Path -LiteralPath $Path).Path
    if (-not $resolvedPath.StartsWith($ProjectRoot, [System.StringComparison]::Ordinal)) {
        throw "Refusing to remove path outside project root: $resolvedPath"
    }

    if ($DryRun) {
        Write-Host "Would remove $resolvedPath"
        return
    }

    Write-Host "Removing $resolvedPath"
    Remove-Item -LiteralPath $resolvedPath -Recurse -Force
}

$namedDirectories = @(
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".coverage",
    "htmlcov",
    "build",
    "dist"
)

foreach ($directory in $namedDirectories) {
    Remove-CleanItem -Path (Join-Path $ProjectRoot $directory)
}

$recursiveDirectories = Get-ChildItem -Path $ProjectRoot -Directory -Recurse -Force -Filter "__pycache__"
foreach ($directory in $recursiveDirectories) {
    Remove-CleanItem -Path $directory.FullName
}

$compiledPythonFiles = Get-ChildItem -Path $ProjectRoot -File -Recurse -Force -Include "*.pyc", "*.pyo"
foreach ($file in $compiledPythonFiles) {
    Remove-CleanItem -Path $file.FullName
}

Write-Host "Clean complete."
