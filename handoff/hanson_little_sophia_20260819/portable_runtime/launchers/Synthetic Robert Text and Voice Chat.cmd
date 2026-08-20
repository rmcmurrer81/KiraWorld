@echo off
setlocal
set "RUNTIME_ROOT=%~dp0.."
pushd "%RUNTIME_ROOT%"
set "PYTHON_FLAG="
if exist "%RUNTIME_ROOT%\.venv-voice\Scripts\python.exe" (
  set "PYTHON_COMMAND=%RUNTIME_ROOT%\.venv-voice\Scripts\python.exe"
) else (
  where py >nul 2>&1
  if errorlevel 1 (set "PYTHON_COMMAND=python") else (set "PYTHON_COMMAND=py" & set "PYTHON_FLAG=-3.11")
)
"%PYTHON_COMMAND%" %PYTHON_FLAG% -m portable_mind chat --person synthetic_robert --backend ollama %*
set "RUNTIME_EXIT=%ERRORLEVEL%"
popd
exit /b %RUNTIME_EXIT%
