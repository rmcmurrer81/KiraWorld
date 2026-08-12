@echo off
setlocal
cd /d "%~dp0"
echo Kira GPU Media First-Look Note
echo.
echo This creates a draft visual/media note. It does not create memory.
echo.
set /p SOURCE_PATH=Source path:
if "%SOURCE_PATH%"=="" (
  echo No source path entered.
  pause
  exit /b 1
)
set /p VIEWER=Viewer [kira]:
if "%VIEWER%"=="" set VIEWER=kira
set /p VISION_MODEL=Optional Ollama vision model, e.g. llava:7b [blank for metadata/samples only]:
if "%VISION_MODEL%"=="" (
  py tools\create_gpu_media_first_look_note.py "%SOURCE_PATH%" --viewer "%VIEWER%"
) else (
  py tools\create_gpu_media_first_look_note.py "%SOURCE_PATH%" --viewer "%VIEWER%" --vision-model "%VISION_MODEL%"
)
echo.
pause
