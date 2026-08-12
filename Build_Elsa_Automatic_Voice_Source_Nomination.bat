@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py tools\auto_nominate_temp_ai_voice_sources.py ^
    --candidate-id elsa_frozen_frozen_fever_frozen_ii_20260716 ^
    --url "https://www.youtube.com/watch?v=utAwhtPlx8c" ^
    --start-seconds 40.12 ^
    --end-seconds 43.72 ^
    --metadata-search
) else (
  python tools\auto_nominate_temp_ai_voice_sources.py ^
    --candidate-id elsa_frozen_frozen_fever_frozen_ii_20260716 ^
    --url "https://www.youtube.com/watch?v=utAwhtPlx8c" ^
    --start-seconds 40.12 ^
    --end-seconds 43.72 ^
    --metadata-search
)

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo Automatic Elsa source search was blocked. No voice or person was changed.
  pause
  exit /b 1
)

echo.
echo Finished. You do not need to approve or reject hundreds of clips.
echo This search does not assign a voice or activate Elsa.
pause
endlocal
