param(
    [ValidateSet("available_to_talk", "soft_knock", "urgent", "leaving_note", "do_not_disturb", "goodnight")]
    [string]$Status = "available_to_talk",
    [string]$Message = "Robert is at the computer and available to talk.",
    [string]$InterruptLevel = "soft_knock"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$presenceDir = Join-Path $projectRoot "Data\presence"
$presencePath = Join-Path $presenceDir "robert_presence.json"
New-Item -ItemType Directory -Force -Path $presenceDir | Out-Null

$payload = [ordered]@{
    status = $Status
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    message = $Message
    interrupt_level = $InterruptLevel
    note = "Presence is a soft signal. Kira may answer, defer, ignore, or keep private time."
}

$payload | ConvertTo-Json -Depth 5 | Set-Content -Path $presencePath -Encoding UTF8
Write-Host "Wrote presence signal:" $presencePath
