@echo off
cd /d "%~dp0"
echo Refreshing Laura legal research leads...
py -3 tools\laura_legal_daily_update.py
if errorlevel 1 (
  echo.
  echo Laura legal update failed. Check the message above.
)
echo.
pause
