@echo off
setlocal
cd /d "%~dp0"
set "KIRA_MODEL_BACKEND=ollama"
set "KIRA_MODEL_NAME=qwen3.5:9b"
set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0"
set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0"
echo Kira Creative Writing Class
echo.
echo This runs only the Creative Writing And Innovation class.
echo It continues Kira's school cursor instead of starting over.
echo.
set /p HOURS=Hours to run [1]:
if "%HOURS%"=="" set HOURS=1
set /a MINUTES=%HOURS%*60
set RUN_ID=kira_creative_writing_class_%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set RUN_ID=%RUN_ID: =0%
py tools\run_kira_school_v2.py --student kira --only-class creative_writing --blocks 1 --duration-minutes %MINUTES% --run-until-duration --answer-questions --backend ollama --run-id %RUN_ID%
echo.
pause
