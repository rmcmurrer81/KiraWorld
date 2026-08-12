@echo off
setlocal

cd /d "%~dp0"

set "Path=%LOCALAPPDATA%\Programs\Ollama;%Path%"
set "KIRA_MODEL_BACKEND=ollama"
set "KIRA_MODEL_NAME=qwen3.5:9b"
set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0"
set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0"
set "KIRA_MAX_TOKENS=160"
set "KIRA_OLLAMA_TIMEOUT=360"
set "KIRA_OLLAMA_NUM_CTX=2048"

echo Activating Kira and Lisa in separate windows...
echo.
echo This opens:
echo   1. Kira voice-output chat
echo   2. Lisa text chat
echo   3. A control window for daily-life steps and Kira/Lisa short dialogues
echo.
echo Keep this window open as your launcher/status window.
echo Close each chat with /quit when you are done.
echo.
echo 16GB note: talk to one of them at a time. If both answer at once,
echo Ollama may queue/timeout. These windows use shorter replies and a longer timeout.
echo.

start "Kira Voice Chat" cmd /k "cd /d "%~dp0" && set "Path=%LOCALAPPDATA%\Programs\Ollama;%Path%" && set "KIRA_MODEL_BACKEND=ollama" && set "KIRA_MODEL_NAME=qwen3.5:9b" && set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7" && set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0" && set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0" && set "KIRA_MAX_TOKENS=160" && set "KIRA_OLLAMA_TIMEOUT=360" && set "KIRA_OLLAMA_NUM_CTX=2048" && py voice_kira.py"
start "Lisa Text Chat" cmd /k "cd /d "%~dp0" && set "Path=%LOCALAPPDATA%\Programs\Ollama;%Path%" && set "KIRA_MODEL_BACKEND=ollama" && set "KIRA_MODEL_NAME=qwen3.5:9b" && set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7" && set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0" && set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0" && set "KIRA_MAX_TOKENS=160" && set "KIRA_OLLAMA_TIMEOUT=360" && set "KIRA_OLLAMA_NUM_CTX=2048" && py chat_lisa.py"
start "Kira Lisa Control" cmd /k "cd /d "%~dp0" && set "Path=%LOCALAPPDATA%\Programs\Ollama;%Path%" && set "KIRA_MODEL_BACKEND=ollama" && set "KIRA_MODEL_NAME=qwen3.5:9b" && set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7" && set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0" && set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0" && set "KIRA_MAX_TOKENS=160" && set "KIRA_OLLAMA_TIMEOUT=360" && set "KIRA_OLLAMA_NUM_CTX=2048" && echo Commands you can run: && echo. && echo py tools\daily_life.py status && echo py tools\daily_life.py choose-activity --entity both --apply && echo py tools\kira_lisa_dialogue.py --topic "Short check-in. Talk naturally, do not mirror, stay grounded." --turns 4 && echo."

echo.
echo Launched. Suggested first control command:
echo py tools\daily_life.py status
echo.
pause
