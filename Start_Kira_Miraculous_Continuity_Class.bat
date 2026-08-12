@echo off
cd /d "%~dp0"
set KIRA_MODEL_BACKEND=ollama
set KIRA_MODEL_NAME=qwen3.5:9b
set KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7
set KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0
set KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0
set KIRA_MAX_TOKENS=520
set KIRA_OLLAMA_NUM_CTX=4096
set KIRA_OLLAMA_TIMEOUT=240
powershell -NoProfile -ExecutionPolicy Bypass -Command "$id='kira_miraculous_continuity_class_'+(Get-Date -Format 'yyyyMMdd_HHmmss'); py tools\run_kira_miraculous_continuity_class.py --run-id $id --max-turns 12 --pause-seconds 20"
pause
