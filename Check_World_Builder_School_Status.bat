@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path 'Data\presence\current_world_builder_school_run.json') { Get-Content 'Data\presence\current_world_builder_school_run.json' -Raw } else { Write-Host 'No World Builder School run file found.' }"
pause
