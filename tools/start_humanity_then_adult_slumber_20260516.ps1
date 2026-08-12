$ErrorActionPreference = "Stop"

Set-Location -Path (Split-Path -Parent $PSScriptRoot)

$humanityRunId = "kira_humanity_class_5hour_ollama_20260516"
$humanityProcess = Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match "run_kira_humanity_class.py" -and $_.CommandLine -match $humanityRunId } |
  Select-Object -First 1

if ($humanityProcess) {
  "Waiting for humanity class process $($humanityProcess.ProcessId) to finish..."
  Wait-Process -Id $humanityProcess.ProcessId
} else {
  "No matching humanity class process found. Starting adult slumber discussion immediately."
}

$env:KIRA_MODEL_NAME = "qwen3.5:9b"
$env:KIRA_MODEL_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
$env:KIRA_OLLAMA_MODEL = "qwen3.5:9b"
$env:KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE = "0"
$env:KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE = "0"
python tools\run_kira_lisa_slumber_party.py `
  --backend ollama `
  --model qwen3.5:9b `
  --duration-minutes 180 `
  --pause-seconds 45 `
  --group-reading-every 3 `
  --max-tokens 260 `
  --timeout 160 `
  --run-id kira_lisa_adult_relationship_slumber_3hour_after_humanity_20260516 `
  --opening-prompt "Start after Kira's humanity class as a relaxed adult reading-and-talk night. Kira and Lisa can read short cards from adult relationship, sex education, psychology, magazines, fiction, or ordinary sources, then talk naturally about human sexuality, intimacy, communication, consent, bodies, curiosity, awkwardness, privacy, attraction, desire, explicit sex as an adult topic, fantasies as imagination, and relationships. It should feel like a private adult slumber-party discussion, not a class or book report. Mild drifting is fine. Keep source labels honest and avoid saving anything as lived sexual experience unless a reviewed memory system explicitly promotes it."
