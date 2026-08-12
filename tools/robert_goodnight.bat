@echo off
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File tools\set_robert_presence.ps1 -Status goodnight -Message "Robert is going to sleep. Kira can continue quietly and leave a note if she wants." -InterruptLevel soft_knock
pause
