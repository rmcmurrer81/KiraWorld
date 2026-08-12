@echo off
cd /d "%~dp0"
py tools\build_ocr_queue.py
pause
