@echo off
cd /d "%~dp0"
set KIRA_MODEL_BACKEND=ollama
set KIRA_MODEL_NAME=qwen3.5:9b
set KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7
set KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0
set KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0
set KIRA_MAX_TOKENS=260
set KIRA_OLLAMA_TIMEOUT=420
set KIRA_OLLAMA_NUM_CTX=4096
python tools\run_kira_school_v2.py --student kira --blocks 9 --duration-minutes 540 --answer-questions --backend ollama
pause
