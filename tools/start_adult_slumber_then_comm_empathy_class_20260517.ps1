$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$slumberPid = 83700
$runId = "kira_communication_empathy_bridge_4hour_after_slumber_20260517"
$stdout = "Data\school\session_runs\$runId.stdout.log"
$stderr = "Data\school\session_runs\$runId.stderr.log"

New-Item -ItemType Directory -Force -Path "Data\school\session_runs" | Out-Null

"Waiting for adult relationship slumber process $slumberPid to finish..." | Tee-Object -FilePath $stdout

while (Get-Process -Id $slumberPid -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 30
}

"Starting 4-hour communication/empathy bridge class..." | Tee-Object -FilePath $stdout -Append

python tools\run_kira_communication_empathy_class.py `
  --duration-minutes 240 `
  --pause-seconds 45 `
  --max-tokens 260 `
  --timeout 180 `
  --run-id $runId `
  1>> $stdout `
  2>> $stderr

"Bridge class finished." | Tee-Object -FilePath $stdout -Append
