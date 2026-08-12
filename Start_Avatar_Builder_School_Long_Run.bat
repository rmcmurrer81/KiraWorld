@echo off
cd /d "%~dp0"
py tools\run_avatar_builder_school_loop_20260712.py --duration-hours 4 --cycle-minutes 15 --source-root "%USERPROFILE%\Desktop\1model" --source-root "%USERPROFILE%\Desktop\21"
pause
