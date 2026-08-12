@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path 'Data\presence\current_avatar_builder_subject_school_run.json') { Get-Content 'Data\presence\current_avatar_builder_subject_school_run.json' -Raw } else { Write-Host 'No Avatar Builder Subject School run file found.' }"
pause
