@echo off
setlocal
cd /d "%~dp0"
py tools\voice_reference_control_center.py
if errorlevel 1 pause
