@echo off
setlocal
cd /d "%~dp0"

echo Preparing Elsa's two selected official spoken-source ranges automatically.
echo No clip-review box will open. No voice will be assigned or activated.
echo.

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py tools\build_elsa_automatic_voice_evidence.py
) else (
  python tools\build_elsa_automatic_voice_evidence.py
)

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo Automatic evidence preparation was blocked. No voice or person was changed.
  pause
  exit /b 1
)

echo.
echo Finished. The old approve/reject box is not used.
echo This prepared evidence only; it did not assign a voice or activate Elsa.
pause
endlocal
