@echo off
setlocal
cd /d "%~dp0"

if /I "%KIRA_LAUNCHER_PROBE%"=="1" goto ENABLED
if /I not "%~1"=="--enable-experimental-high-resource" goto DISABLED

:ENABLED
set "KIRA_HIGH_RESOURCE_MEDIA_EXPERIMENT=1"
set "KIRA_WORLD_GROUP_SESSIONS=1"
set "KIRA_WORLD_MAX_ACTIVE_SESSIONS=4"
set "KIRA_WORLD_RAM_GB_PER_ACTIVE_SESSION=32"

call "%~dp0Start_Kira_Text_Voice_Chat.bat"
exit /b %ERRORLEVEL%

:DISABLED
echo.
echo This optional high-resource media and group launcher is disabled by default.
echo It has not been tested on this machine because of local RAM and GPU restrictions.
echo Review System\Docs\HIGH_RESOURCE_MEDIA_EXPERIMENT_v1.md first.
echo Then run:
echo   %~nx0 --enable-experimental-high-resource
echo.
exit /b 4
