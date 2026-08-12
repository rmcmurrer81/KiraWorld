@echo off
cd /d "%~dp0"
echo Creating debrief for the latest Kira session/chat JSON...
python tools\create_kira_session_debrief.py --latest
echo.
pause
