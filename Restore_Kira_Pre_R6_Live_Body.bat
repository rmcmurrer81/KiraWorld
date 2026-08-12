@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py tools\restore_kira_pre_r6_live_body.py
) else (
  python tools\restore_kira_pre_r6_live_body.py
)
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo Rollback did not run. Deactivate Kira and close the World Shell, then try again.
  pause
  exit /b 1
)
echo.
echo The exact pre-R6 body selection is restored. Reopen Kira World Shell to see it.
pause
endlocal
