@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py tools\launch_louvre_realism_r5_owner_review.py
) else (
  python tools\launch_louvre_realism_r5_owner_review.py
)
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo Louvre R5 did not start. R4 on port 5183 was not changed.
  pause
  exit /b 1
)
exit /b 0
