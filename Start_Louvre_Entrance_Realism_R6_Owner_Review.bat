@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py tools\launch_louvre_entrance_realism_r6_owner_review.py
) else (
  python tools\launch_louvre_entrance_realism_r6_owner_review.py
)
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo Louvre R6 did not start. R4 on 5183, R5 on 5195, Home World, and TARDIS were not changed.
  pause
  exit /b 1
)
exit /b 0
