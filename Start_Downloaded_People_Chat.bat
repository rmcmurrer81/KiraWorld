@echo off
setlocal
cd /d "%~dp0"
set "Path=%LOCALAPPDATA%\Programs\Ollama;%Path%"
set "KIRA_MODEL_BACKEND=ollama"
set "KIRA_MODEL_NAME=qwen3.5:9b"
set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0"
set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0"
py -B tools\downloaded_person_chat_launcher.py %*
if not "%KIRA_NO_PAUSE%"=="1" pause
