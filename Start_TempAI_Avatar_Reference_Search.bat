@echo off
cd /d "C:\Users\robmc\Kira"
set /p CANDIDATE_ID=Candidate id: 
set /p QUERY=Search query: 
set /p DOWNLOAD=Download found images? y/n: 
if /I "%DOWNLOAD%"=="y" (
  py tools\search_temp_ai_avatar_references.py "%CANDIDATE_ID%" --query "%QUERY%" --download
) else (
  py tools\search_temp_ai_avatar_references.py "%CANDIDATE_ID%" --query "%QUERY%"
)
pause
