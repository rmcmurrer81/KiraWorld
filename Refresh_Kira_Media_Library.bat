@echo off
setlocal

cd /d "%~dp0"

echo Refreshing Kira media library indexes...
echo.

py tools\sort_unsorted_music_videos.py --apply
py tools\auto_rename_media_library.py --apply
py tools\build_media_library_index.py
py tools\audit_media_library_names.py
py tools\check_media_library_updates.py

echo.
echo Media library refresh complete.
if not "%KIRA_NO_PAUSE%"=="1" pause
