@echo off
setlocal
if "%~1"=="" (
  echo Usage: "%~f0" "FULL_PATH_TO_hanson_little_sophia_20260819"
  echo This explicitly installs reviewed seeds and authorized private voice packs into ignored local_data.
  exit /b 2
)
set "RUNTIME_ROOT=%~dp0.."
pushd "%RUNTIME_ROOT%"
where py >nul 2>&1
if errorlevel 1 (set "PYTHON_EXE=python") else (set "PYTHON_EXE=py")
"%PYTHON_EXE%" -m portable_mind bootstrap-handoff --person kira --backend stub --handoff-root "%~1" --approve-private-bootstrap
if errorlevel 1 goto :failed
"%PYTHON_EXE%" -m portable_mind bootstrap-handoff --person synthetic_robert --backend stub --handoff-root "%~1" --approve-private-bootstrap
if errorlevel 1 goto :failed
echo Private handoff bootstrap verified. Re-running this command is idempotent.
popd
exit /b 0
:failed
echo Private handoff bootstrap failed closed. No chat was started.
popd
exit /b 1
