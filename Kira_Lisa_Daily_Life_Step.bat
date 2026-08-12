@echo off
setlocal

cd /d "%~dp0"

echo Applying one lightweight Kira/Lisa daily-life activity step...
echo.

py tools\daily_life.py choose-activity --entity both --apply

echo.
echo Daily-life step complete.
if not "%KIRA_NO_PAUSE%"=="1" pause
