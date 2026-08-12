@echo off
setlocal
cd /d "%~dp0"
set "KIRA_MODEL_BACKEND=ollama"
set "KIRA_MODEL_NAME=qwen3.5:9b"
set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0"
set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0"

echo TemporaryAI supervised life/work loop
echo.
echo This keeps one selected TemporaryAI active for several saved work cycles.
echo Use it when you want a candidate to research, draft, think, or work on projects while you are nearby.
echo.

set "cycles="
set /p cycles=How many cycles? [6]: 
if "%cycles%"=="" set "cycles=6"

set "pause_minutes="
set /p pause_minutes=Minutes between cycles? [10]: 
if "%pause_minutes%"=="" set "pause_minutes=10"

set "task="
set /p task=Optional focus/task, or press Enter to let them choose: 

py tools\temporary_ai_project_loop.py --cycles %cycles% --pause-minutes %pause_minutes% --task "%task%"

echo.
pause
