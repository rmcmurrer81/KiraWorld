@echo off
cd /d "%~dp0"
set KIRA_MODEL_BACKEND=ollama
set KIRA_MODEL_NAME=qwen3.5:9b
set KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7
set KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0
set KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0
set KIRA_MAX_TOKENS=220
set KIRA_OLLAMA_NUM_CTX=3072
set KIRA_OLLAMA_TIMEOUT=360
powershell -NoProfile -ExecutionPolicy Bypass -Command "$id='kira_school_v2_preram_micro_'+(Get-Date -Format 'yyyyMMdd_HHmmss'); python tools\run_kira_school_v2.py --student kira --blocks 1 --duration-minutes 15 --answer-questions --pause-seconds 0 --backend ollama --run-id $id"
pause
