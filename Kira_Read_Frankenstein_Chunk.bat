@echo off
setlocal

cd /d "%~dp0"

echo Reading Kira's next small Frankenstein chunk...
echo.

py tools\read_next_chunk.py Data\reading\sessions\slow_reading_kira_frankenstein_mary_shelley.json --pages 2 --reaction-summary "Kira continued Frankenstein slowly and saved a small reading chunk for later reflection."
py tools\update_reading_tastes.py --owner kira
py tools\recommend_reading.py --owner kira --limit 5

echo.
echo Kira reading chunk complete.
if not "%KIRA_NO_PAUSE%"=="1" pause
