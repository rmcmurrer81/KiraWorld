@echo off
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\start_kira_idle_study_2hour.ps1" -DurationMinutes 120 -PauseSeconds 60
pause
