@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 set "KIRA_HANSON_PY=py"
if not defined KIRA_HANSON_PY (
  where python >nul 2>nul
  if not errorlevel 1 set "KIRA_HANSON_PY=python"
)
if not defined KIRA_HANSON_PY (
  echo Blocked: Python 3 was not found. Install Python 3.10 or newer first.
  set "KIRA_HANSON_EXIT=3"
  goto FINISH
)

%KIRA_HANSON_PY% -c "import yaml, jsonschema" >nul 2>nul
if errorlevel 1 (
  echo Installing the ROS-independent bridge validation requirements...
  %KIRA_HANSON_PY% -m pip install -r integrations\hanson_ros2_bridge\standalone\requirements.txt
  if errorlevel 1 (
    echo Blocked: standalone bridge requirements could not be installed.
    set "KIRA_HANSON_EXIT=3"
    goto FINISH
  )
)

%KIRA_HANSON_PY% -B tools\hanson_ros2_bridge_launcher.py standalone %*
set "KIRA_HANSON_EXIT=%ERRORLEVEL%"

:FINISH
if not "%KIRA_NO_PAUSE%"=="1" pause
exit /b %KIRA_HANSON_EXIT%
