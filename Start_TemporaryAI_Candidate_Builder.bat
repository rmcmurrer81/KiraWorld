@echo off
cd /d "C:\Users\robmc\Kira"
echo TemporaryAI Candidate Builder
echo.
set /p DISPLAY_NAME=Display name or role: 
set /p AI_TYPE=AI type (canon_reconstruction_temp_ai, generated_original_temp_ai, expert_temp_ai, memory_relative_temp_ai): 
if "%AI_TYPE%"=="" set AI_TYPE=canon_reconstruction_temp_ai
set /p QUERY=Optional local source query, for example miraculous_ladybug or robotics: 
set /p DOMAIN=Optional expert domain: 
echo.
if "%QUERY%"=="" (
  py tools\create_temporary_ai_candidate.py --display-name "%DISPLAY_NAME%" --ai-type "%AI_TYPE%" --expert-domain "%DOMAIN%"
) else (
  py tools\create_temporary_ai_candidate.py --display-name "%DISPLAY_NAME%" --ai-type "%AI_TYPE%" --expert-domain "%DOMAIN%" --query "%QUERY%"
)
echo.
pause
