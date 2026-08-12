@echo off
cd /d "%~dp0"
py tools\build_image_reference_queue.py
pause
