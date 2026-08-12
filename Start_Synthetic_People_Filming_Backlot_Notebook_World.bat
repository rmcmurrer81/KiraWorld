@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py tools\serve_synthetic_people_filming_backlot_notebook_world.py
) else (
  python tools\serve_synthetic_people_filming_backlot_notebook_world.py
)
