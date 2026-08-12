@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py tools\world_builder_workspace.py
) else (
  python tools\world_builder_workspace.py
)
