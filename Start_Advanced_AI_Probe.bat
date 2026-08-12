@echo off
setlocal
cd /d "%~dp0"
set "KIRA_MODEL_BACKEND=ollama"
set "KIRA_MODEL_NAME=qwen3.5:9b"
set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0"
set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0"

echo Advanced AI Probe
echo.
echo 1. Kira companion probe
echo 2. Lisa companion probe
echo 3. Ladybug TemporaryAI probe
echo 4. Kira short smoke test
echo 5. Ladybug short smoke test
echo.
set /p choice="Choose a probe: "

if "%choice%"=="1" (
  py tools\run_advanced_ai_probe.py --subject kira
) else if "%choice%"=="2" (
  py tools\run_advanced_ai_probe.py --subject lisa
) else if "%choice%"=="3" (
  py tools\run_advanced_ai_probe.py --subject temp:ladybug
) else if "%choice%"=="4" (
  py tools\run_advanced_ai_probe.py --subject kira --turns 2 --pause-seconds 2
) else if "%choice%"=="5" (
  py tools\run_advanced_ai_probe.py --subject temp:ladybug --turns 2 --pause-seconds 2
) else (
  echo Unknown choice.
)

echo.
pause
