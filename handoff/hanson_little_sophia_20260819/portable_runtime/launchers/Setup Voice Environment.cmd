@echo off
setlocal
set "RUNTIME_ROOT=%~dp0.."
pushd "%RUNTIME_ROOT%"
py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 2)"
if errorlevel 1 (
  echo Python 3.11 is required. Install/register it before voice setup.
  goto :failed
)
py -3.11 -m venv .venv-voice
if errorlevel 1 goto :failed
"%RUNTIME_ROOT%\.venv-voice\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed
rem Resolve platform dependencies, then reinstall only the direct Chatterbox wheel from its exact hash.
rem Transitive dependencies are version-checked by voice-env-check but are not fully hash-locked.
"%RUNTIME_ROOT%\.venv-voice\Scripts\python.exe" -m pip install chatterbox-tts==0.1.7
if errorlevel 1 goto :failed
"%RUNTIME_ROOT%\.venv-voice\Scripts\python.exe" -m pip uninstall -y chatterbox-tts
if errorlevel 1 goto :failed
"%RUNTIME_ROOT%\.venv-voice\Scripts\python.exe" -m pip install --no-deps --require-hashes -r voice-package-hash.lock
if errorlevel 1 goto :failed
"%RUNTIME_ROOT%\.venv-voice\Scripts\python.exe" -m portable_mind voice-env-check --person kira --backend stub --allow-download
if errorlevel 1 goto :failed
echo Voice environment and pinned model files verified.
popd
exit /b 0
:failed
echo Voice setup or verification failed. Review the error above; do not label the neural route verified.
popd
exit /b 1
