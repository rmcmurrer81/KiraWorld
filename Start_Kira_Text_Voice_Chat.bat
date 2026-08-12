@echo off
setlocal
cd /d "%~dp0"

if /I "%KIRA_LAUNCHER_PROBE%"=="1" goto KIRA_LAUNCHER_PROBE

set "KIRA_MODEL_BACKEND=ollama"
set "KIRA_MODEL_NAME=qwen3.5:9b"
set "KIRA_MODEL_DIGEST=6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
set "KIRA_ENABLE_QWEN35_BUFFERED_STREAM_TIMING_CANDIDATE=1"
set "KIRA_ENABLE_LLAMA_KEEP_ALIVE_CANDIDATE=0"
set "KIRA_ENABLE_LLAMA_BUFFERED_STREAM_TIMING_CANDIDATE=0"
set "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE=0"
set "KIRA_ENABLE_PERSISTENT_BLACKWELL_VOICE_CANDIDATE_V2=1"
set "KIRA_SHELL_PORT=8768"
set "KIRA_SHELL_URL=http://127.0.0.1:%KIRA_SHELL_PORT%/"
set "KIRA_SHELL_TEXT_ONLY=1"
set "KIRA_TEXT_VOICE_CHAT_ACTIVE=1"
set "KIRA_WORLD_SHELL_ACTIVE=0"
set "KIRA_ASR_PORT=8770"
set "KIRA_VISUAL_PORT=8771"
set "KIRA_PRE_RAM_KIRA_ONLY=0"
set "KIRA_PERSONHOOD_EVAL_MODE=0"
set "KIRA_CHATTERBOX_DEVICE=cuda"
set "KIRA_DISABLE_BLACKWELL_GPU_VOICE=0"
set "KIRA_DISABLE_CHATTERBOX_PY311_SIDECAR=1"
set "KIRA_VOICE_FORCE_SAPI=0"
set "KIRA_CHATTERBOX_MIN_FREE_VRAM_MIB=6144"
set "KIRA_MESSAGE_TARGET_VOICE=1"
set "KIRA_VOICE_IDLE_UNLOAD_SECONDS=600"
set "KIRA_VOICE_PREWARM_ON_ACTIVATE=1"
set "KIRA_VOICE_BENCHMARK_CAPTURE=1"
set "KIRA_WORLD_VOICE_MAX_CHARS=180"
set "KIRA_SPEAK_FULL_REPLY=1"
set "KIRA_UNLOAD_VOICE_AFTER_SPEAK=0"
set "KIRA_RUNTIME=%CD%\Data\runtime"
if not exist "%KIRA_RUNTIME%" mkdir "%KIRA_RUNTIME%"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "KIRA_PY=py"
) else (
  set "KIRA_PY=python"
)

for /f "usebackq delims=" %%P in (`%KIRA_PY% -c "import sys; print(sys.executable)"`) do set "KIRA_SERVER_PY=%%P"
for /f "usebackq delims=" %%T in (`%KIRA_PY% -c "import secrets; print(secrets.token_urlsafe(32))"`) do set "KIRA_ASR_SESSION_TOKEN=%%T"
for /f "usebackq delims=" %%T in (`%KIRA_PY% -c "import secrets; print(secrets.token_urlsafe(32))"`) do set "KIRA_VISUAL_SESSION_TOKEN=%%T"
for /f "usebackq delims=" %%T in (`%KIRA_PY% -c "import secrets; print(secrets.token_urlsafe(32))"`) do set "KIRA_SHELL_API_TOKEN=%%T"
for /f "usebackq delims=" %%T in (`%KIRA_PY% -c "import uuid; print(uuid.uuid4().hex)"`) do set "KIRA_SHELL_LAUNCH_ID=%%T"
if not defined KIRA_SERVER_PY exit /b 3
if not defined KIRA_ASR_SESSION_TOKEN exit /b 3
if not defined KIRA_VISUAL_SESSION_TOKEN exit /b 3
if not defined KIRA_SHELL_API_TOKEN exit /b 3
if not defined KIRA_SHELL_LAUNCH_ID exit /b 3

%KIRA_PY% -c "import importlib.util, subprocess, sys; sys.exit(0 if importlib.util.find_spec('webview') else subprocess.call([sys.executable, '-m', 'pip', 'install', 'pywebview']))"
if %ERRORLEVEL% NEQ 0 (
  echo Failed to install or load pywebview.
  echo See %KIRA_RUNTIME%\kira_text_voice_chat_stderr.log
  pause
  exit /b 1
)

set "KIRA_SHELL_PID_FILE=%KIRA_RUNTIME%\kira_text_voice_chat_server_%KIRA_SHELL_LAUNCH_ID%.pid"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Start-Process -FilePath '%KIRA_SERVER_PY%' -ArgumentList @('tools\kira_world_shell_server.py','--no-browser') -WorkingDirectory '%CD%' -WindowStyle Hidden -RedirectStandardOutput '%KIRA_RUNTIME%\kira_text_voice_chat_stdout.log' -RedirectStandardError '%KIRA_RUNTIME%\kira_text_voice_chat_stderr.log' -PassThru; [IO.File]::WriteAllText('%KIRA_SHELL_PID_FILE%', [string]$p.Id)"
if exist "%KIRA_SHELL_PID_FILE%" set /p "KIRA_SHELL_CHILD_PID="<"%KIRA_SHELL_PID_FILE%"
if not defined KIRA_SHELL_CHILD_PID (
  echo Kira Text + Voice Chat server process could not be created.
  exit /b 2
)

set "KIRA_READINESS_LOG=%KIRA_RUNTIME%\kira_text_voice_chat_readiness_%KIRA_SHELL_LAUNCH_ID%.log"
%KIRA_PY% tools\wait_for_kira_world_shell.py --url "%KIRA_SHELL_URL%" --timeout 60 --owned-pid "%KIRA_SHELL_CHILD_PID%" > "%KIRA_READINESS_LOG%" 2>&1
if %ERRORLEVEL% NEQ 0 (
  %KIRA_PY% tools\stop_owned_kira_world_shell.py --pid "%KIRA_SHELL_CHILD_PID%" --port "%KIRA_SHELL_PORT%" --runtime "%KIRA_RUNTIME%" --launch-id "%KIRA_SHELL_LAUNCH_ID%"
  echo.
  echo Kira Text + Voice Chat server did not become ready.
  echo Check these logs:
  echo %KIRA_RUNTIME%\kira_text_voice_chat_stdout.log
  echo %KIRA_RUNTIME%\kira_text_voice_chat_stderr.log
  echo %KIRA_READINESS_LOG%
  pause
  exit /b 2
)

where pyw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  start "Kira Text + Voice Chat" pyw tools\kira_world_shell_viewer.py --url "%KIRA_SHELL_URL%" --wait 60 --title "Kira Text + Voice Chat"
) else (
  start "Kira Text + Voice Chat" %KIRA_PY% tools\kira_world_shell_viewer.py --url "%KIRA_SHELL_URL%" --wait 60 --title "Kira Text + Voice Chat"
)
goto :eof

:KIRA_LAUNCHER_PROBE
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "KIRA_PROBE_PY=py"
) else (
  set "KIRA_PROBE_PY=python"
)
%KIRA_PROBE_PY% tools\kira_launcher_probe.py serve --launcher-id text_voice_chat --probe-root "%KIRA_LAUNCHER_PROBE_ROOT%" --port "%KIRA_LAUNCHER_PROBE_PORT%"
exit /b %ERRORLEVEL%
