@echo off
cd /d "%~dp0"
echo Building draft media preview cards from the local media index...
python tools\build_media_preview_cards.py --limit 50
echo.
echo Done. Cards are written under Data\media\preview_cards\generated.
pause
