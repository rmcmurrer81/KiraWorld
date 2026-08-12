@echo off
setlocal
cd /d "C:\Users\robmc\Kira"
echo AI Workspace Intake
echo.
echo This creates a reviewed workspace from a local folder.
echo Original files are not modified.
echo.
set /p SOURCE_FOLDER=Folder to intake: 
set /p OWNER=Owner label (temporary_ai, kira, lisa, robert, project): 
if "%OWNER%"=="" set OWNER=temporary_ai
set /p WORKSPACE_NAME=Workspace name: 
set /p CANDIDATE_ID=Optional TemporaryAI candidate id to attach: 
echo.
if "%CANDIDATE_ID%"=="" (
  py tools\ai_workspace_intake.py "%SOURCE_FOLDER%" --owner "%OWNER%" --workspace-name "%WORKSPACE_NAME%"
) else (
  py tools\ai_workspace_intake.py "%SOURCE_FOLDER%" --owner "%OWNER%" --workspace-name "%WORKSPACE_NAME%" --candidate-id "%CANDIDATE_ID%"
)
echo.
pause
