@echo off
setlocal
cd /d "%~dp0"
echo Elsa's old manual clip review has been retired.
echo Running the one-click official spoken-source evidence preparation instead...
echo.
call "%~dp0Build_Elsa_Automatic_Voice_Evidence.bat"
