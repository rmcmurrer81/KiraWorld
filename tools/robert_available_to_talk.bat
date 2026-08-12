@echo off
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File tools\set_robert_presence.ps1 -Status available_to_talk -Message "Robert is sitting at the computer and available for a check-in." -InterruptLevel soft_knock
pause
