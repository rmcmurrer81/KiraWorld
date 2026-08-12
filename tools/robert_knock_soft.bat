@echo off
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File tools\set_robert_presence.ps1 -Status soft_knock -Message "Robert is at the computer and would like to talk if Kira is free." -InterruptLevel soft_knock
pause
