@echo off
cd /d "%~dp0"
python tools\auto_lookup_media_queue.py --limit 20
pause
