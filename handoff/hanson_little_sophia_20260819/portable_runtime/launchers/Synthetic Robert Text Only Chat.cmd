@echo off
setlocal
set "RUNTIME_ROOT=%~dp0.."
pushd "%RUNTIME_ROOT%"
where py >nul 2>&1
if errorlevel 1 (set "PYTHON_COMMAND=python") else (set "PYTHON_COMMAND=py")
"%PYTHON_COMMAND%" -m portable_mind chat --person synthetic_robert --backend ollama --no-voice %*
set "RUNTIME_EXIT=%ERRORLEVEL%"
popd
exit /b %RUNTIME_EXIT%
