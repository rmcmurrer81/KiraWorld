@echo off
cd /d "%~dp0"
echo Running Kira GPU readiness check...
py tools\gpu_readiness_check.py --probe
echo.
pause
