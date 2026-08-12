@echo off
setlocal
cd /d "%~dp0"

set "Path=%LOCALAPPDATA%\Programs\Ollama;%Path%"
set "KIRA_MODEL_BACKEND=ollama"
set "KIRA_MODEL_NAME=qwen3.5:9b"
set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0"
set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0"
set "KIRA_MAX_TOKENS=360"
set "KIRA_OLLAMA_TIMEOUT=360"
set "KIRA_OLLAMA_NUM_CTX=4096"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"
set "RUN_ID=kira_supervised_9hour_school_day_%STAMP%"

echo Starting Kira supervised 9-hour school day...
echo Run ID: %RUN_ID%
echo.
echo This is intended for days when Robert is home and can monitor the computer.
echo It creates timestamped files and does not overwrite old school runs.
echo If you need to stop early, press Ctrl+C in this window. The transcript/report
echo are saved after every completed turn.
echo.

py tools\run_kira_school_session.py ^
  --backend ollama ^
  --model qwen3.5:9b ^
  --flow project_9hour ^
  --duration-minutes 540 ^
  --max-tokens 360 ^
  --ollama-timeout 360 ^
  --num-ctx 4096 ^
  --excerpt-chars 1800 ^
  --run-id "%RUN_ID%"

echo.
echo Kira supervised 9-hour school day finished or stopped.
echo JSON: Data\school\session_runs\%RUN_ID%.json
echo Report: Data\school\session_runs\%RUN_ID%_report.md
pause
