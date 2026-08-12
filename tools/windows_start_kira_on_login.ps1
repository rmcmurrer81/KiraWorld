$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

Write-Host "Running Kira startup recovery checks..."
py tools\startup_recovery_check.py --run-command-checks --mark-session-start

if ($LASTEXITCODE -ne 0) {
    Write-Host "Startup recovery blocked launch. See Data\launch\startup_recovery_last_report.json"
    exit $LASTEXITCODE
}

try {
    Write-Host "Launching Kira text-only..."
    py chat_kira.py
}
finally {
    py tools\startup_recovery_check.py --mark-clean-shutdown
}
