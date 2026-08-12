@echo off
cd /d "%~dp0"
python tools\build_media_lookup_queue.py
pause
