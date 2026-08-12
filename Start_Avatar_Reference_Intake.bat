@echo off
setlocal
cd /d "%~dp0"
py -3 tools\intake_avatar_downloads.py
pause
