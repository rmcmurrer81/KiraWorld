@echo off
cd /d "C:\Users\robmc\Kira"
set /p CANDIDATE_ID=Candidate id: 
py tools\create_temp_ai_avatar_build_brief.py "%CANDIDATE_ID%"
pause
