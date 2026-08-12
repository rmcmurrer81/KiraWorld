$ErrorActionPreference = "Stop"
Set-Location "C:\Users\robmc\Kira"
$waitForPid = 90288
$logDir = "Data\personhood_evaluations\manual_chats"
$stdout = Join-Path $logDir "kira_codex_future_upgrades_repair_20260517.stdout.log"
$stderr = Join-Path $logDir "kira_codex_future_upgrades_repair_20260517.stderr.log"
Write-Output "Waiting for Lisa review PID $waitForPid before starting patched Kira repair chat..."
try {
  Get-Process -Id $waitForPid -ErrorAction Stop | Out-Null
  Wait-Process -Id $waitForPid
} catch {
  Write-Output "Lisa PID $waitForPid is not running; starting Kira repair chat now."
}
Write-Output "Starting patched two-hour Kira future-upgrades repair chat..."
python tools\run_kira_codex_future_upgrades_chat.py `
  --duration-minutes 120 `
  --pause-seconds 90 `
  --max-turns 60 `
  --run-id kira_codex_future_upgrades_repair_20260517 `
  1> $stdout 2> $stderr
Write-Output "Kira repair chat finished."
