@echo off
setlocal
cd /d "%~dp0"
set "KIRA_MODEL_BACKEND=ollama"
set "KIRA_MODEL_NAME=qwen3.5:9b"
set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0"
set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0"
echo TemporaryAI supervised project loop
echo.
echo This runs ONE candidate for ONE short work/research cycle.
echo Output is saved for Robert review. It does not send emails or modify original files.
echo.
py tools\temporary_ai_project_loop.py
echo.
pause
