@echo off
setlocal
cd /d "%~dp0"
py tools\process_temp_ai_voice_discovery_queue.py --max-candidates 3
pause
