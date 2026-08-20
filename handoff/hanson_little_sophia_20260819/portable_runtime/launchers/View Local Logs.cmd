@echo off
setlocal
set "RUNTIME_ROOT=%~dp0.."
pushd "%RUNTIME_ROOT%"
where py >nul 2>&1
if errorlevel 1 (set "PYTHON_COMMAND=python") else (set "PYTHON_COMMAND=py")
set /p "PERSON_ID=Person (kira, synthetic_robert, or synthetic_sophia): "
set /p "CHANNEL_ID=Channel (spoken, reflection, facts, state, loops, consolidations, imports, voice, or people): "
"%PYTHON_COMMAND%" -m portable_mind logs --person "%PERSON_ID%" --channel "%CHANNEL_ID%" --tail 50
set "RUNTIME_EXIT=%ERRORLEVEL%"
pause
popd
exit /b %RUNTIME_EXIT%
