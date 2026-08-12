@echo off
setlocal

cd /d "%~dp0"

echo Running Kira quick regression tests...
echo.

py -m unittest ^
  Testing.test_response_polish ^
  Testing.test_conversation_grounding ^
  Testing.test_day_one_conversation_readiness ^
  Testing.test_voice_output ^
  Testing.test_media_library_index ^
  Testing.test_auto_rename_media_library ^
  Testing.test_read_next_chunk ^
  Testing.test_update_reading_tastes ^
  Testing.test_temp_ai_source_pack_planner

echo.
echo Quick tests complete.
if not "%KIRA_NO_PAUSE%"=="1" pause
