param(
    [int]$DurationMinutes = 120,
    [int]$PauseSeconds = 60,
    [string]$RunId = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = "kira_idle_study_live_" + (Get-Date -Format "yyyyMMdd_HHmmss")
}

Write-Host "Starting Kira idle study loop..."
Write-Host "Run ID: $RunId"
Write-Host "Duration: $DurationMinutes minutes"
Write-Host "Pause: $PauseSeconds seconds"
Write-Host ""

python tools\run_kira_idle_study_loop.py `
    --backend ollama `
    --duration-minutes $DurationMinutes `
    --pause-seconds $PauseSeconds `
    --actions read,creative `
    --run-id $RunId `
    --pages 1 `
    --lines 60 `
    --max-tokens 220
