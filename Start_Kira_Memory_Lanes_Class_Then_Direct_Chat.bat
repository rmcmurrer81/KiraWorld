@echo off
cd /d "%~dp0"
set "KIRA_MODEL_BACKEND=ollama"
set "KIRA_MODEL_NAME=qwen3.5:9b"
set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0"
set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0"
echo Starting Kira memory-lanes class...
py tools\run_kira_memory_lanes_class.py --pause-seconds 15
echo.
echo Starting direct Codex follow-up after memory-lanes class...
py tools\run_kira_codex_memory_lanes_followup.py --pause-seconds 15 --turns 5
echo.
echo Memory-lanes class and direct follow-up finished or stopped.
pause
