@echo off
cd /d "%~dp0"
py tools\kira_gpu_bridge_status.py
echo.
pause
