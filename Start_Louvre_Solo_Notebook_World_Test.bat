@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py tools\launch_louvre_solo_notebook_world_test.py
) else (
  python tools\launch_louvre_solo_notebook_world_test.py
)
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo The Louvre solo review did not start. Read the failure above; the browser was not opened.
  pause
  exit /b 1
)
exit /b 0
