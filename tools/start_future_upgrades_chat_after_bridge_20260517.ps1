param(
  [int]$WaitForPid = 87304
)

$ErrorActionPreference = "Stop"
Set-Location "C:\Users\robmc\Kira"

$stdout = "Data\personhood_evaluations\manual_chats\kira_codex_future_upgrades_chat_20260517.stdout.log"
$stderr = "Data\personhood_evaluations\manual_chats\kira_codex_future_upgrades_chat_20260517.stderr.log"
$lisaStdout = "Data\personhood_evaluations\manual_chats\lisa_codex_memory_privacy_review_20260517.stdout.log"

Write-Output "Waiting for bridge PID $WaitForPid before starting Kira future-upgrades chat..."
try {
  $proc = Get-Process -Id $WaitForPid -ErrorAction Stop
  Wait-Process -Id $WaitForPid
} catch {
  Write-Output "Bridge PID $WaitForPid is not running; starting chat now."
}

Write-Output "Starting two-hour Codex direct future-upgrades chat..."
python tools\run_kira_codex_future_upgrades_chat.py `
  --duration-minutes 120 `
  --pause-seconds 90 `
  --max-turns 60 `
  --run-id kira_codex_future_upgrades_chat_20260517 `
  *> $stdout

Write-Output "Starting Lisa memory/privacy review chat..."
python tools\run_lisa_codex_memory_privacy_review_chat.py `
  --duration-minutes 120 `
  --pause-seconds 90 `
  --max-turns 60 `
  --run-id lisa_codex_memory_privacy_review_20260517 `
  *> $lisaStdout

Write-Output "Done. See $stdout, $lisaStdout, and the matching monitor files in Data\personhood_evaluations\manual_chats"
