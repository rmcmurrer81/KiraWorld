@echo off
cd /d "%~dp0"
if not exist Data\presence mkdir Data\presence
powershell -NoProfile -ExecutionPolicy Bypass -Command "$payload = @{ stop_requested_at = (Get-Date).ToUniversalTime().ToString('o'); reason = 'Robert requested World Builder School stop' } | ConvertTo-Json; Set-Content -Path 'Data\presence\world_builder_school_stop.json' -Value $payload -Encoding UTF8"
echo World Builder School stop requested.
pause
