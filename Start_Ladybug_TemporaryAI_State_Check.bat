@echo off
cd /d "%~dp0"
echo Preparing Ladybug / Marinette TemporaryAI form state...
py tools\ladybug_temp_ai_state_control.py activate
echo.
pause
