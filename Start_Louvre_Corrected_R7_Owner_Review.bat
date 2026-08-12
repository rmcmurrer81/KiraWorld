@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py tools\launch_louvre_corrected_r7_owner_review.py
) else (
  python tools\launch_louvre_corrected_r7_owner_review.py
)
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo Louvre corrected R7 did not start. R4, R5, R6, Home World, TARDIS, and all people were left unchanged.
  pause
  exit /b 1
)
exit /b 0
