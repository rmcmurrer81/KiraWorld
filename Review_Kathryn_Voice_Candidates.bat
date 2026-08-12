@echo off
setlocal
cd /d "%~dp0"
echo Kathryn's old 400-clip pilot review has been retired.
echo Running automatic source and same-speaker checks instead...
echo.
call "%~dp0Build_Kathryn_Automatic_Voice_Evidence.bat"
