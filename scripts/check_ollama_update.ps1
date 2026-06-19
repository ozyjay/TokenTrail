$ErrorActionPreference = "Stop"

function Get-VersionNumberFromText {
    param([string]$Text)

    $match = [regex]::Match($Text, '\d+\.\d+\.\d+')
    if (-not $match.Success) {
        throw "Could not parse version from: $Text"
    }

    return $match.Value
}

try {
    $currentOutput = & ollama --version 2>$null
    $current = Get-VersionNumberFromText $currentOutput
} catch {
    Write-Host "Ollama does not appear to be installed or available on PATH."
    Write-Host "Install/update with:"
    Write-Host "  irm https://ollama.com/install.ps1 | iex"
    exit 1
}

$latestRelease = Invoke-RestMethod `
    -Uri "https://api.github.com/repos/ollama/ollama/releases/latest" `
    -Headers @{ "User-Agent" = "TokenTrail-Ollama-Update-Check" }

$latest = $latestRelease.tag_name.TrimStart("v")

Write-Host "Installed Ollama: $current"
Write-Host "Latest Ollama:    $latest"

if ([version]$current -lt [version]$latest) {
    Write-Host ""
    Write-Host "Update available."
    Write-Host "Run:"
    Write-Host "  irm https://ollama.com/install.ps1 | iex"
    exit 2
}

Write-Host ""
Write-Host "Ollama is up to date."