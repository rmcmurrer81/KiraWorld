$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$presencePath = Join-Path $projectRoot "Data\presence\robert_presence.json"

if (Test-Path $presencePath) {
    Remove-Item -LiteralPath $presencePath
    Write-Host "Cleared Robert presence signal."
} else {
    Write-Host "No Robert presence signal was set."
}
