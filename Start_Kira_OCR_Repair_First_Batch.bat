@echo off
cd /d "%~dp0"
py tools\repair_ocr_batch.py --limit 1 --priority high --max-pages 5
pause
