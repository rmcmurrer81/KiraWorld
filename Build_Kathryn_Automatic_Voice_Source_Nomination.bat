@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py tools\auto_nominate_temp_ai_voice_sources.py --candidate-id kathryn_merteuil_kathryn_merteuil_20260605_213017 --url "https://www.youtube.com/watch?v=yPPzi-TjE94" --start-seconds 4.15 --owner-nominated-target-only --owner-note "Robert confirms Kathryn alone; machine review trims the dead lead and keeps faint score residue flagged for cleanup/QC." --search-query "Kathryn Merteuil Sarah Michelle Gellar non musical dialogue scene" --metadata-search --local-media "_tmp_kathryn_youtube_source\source.mp4" --local-wav "_tmp_kathryn_youtube_source\kathryn_4p15s_to_end.wav" --owner-attestation "TemporaryAI\candidates\kathryn_merteuil_kathryn_merteuil_20260605_213017\workbench\inputs\identity_reviews\kathryn_monologue_youtube_owner_attestation_20260717.json" --contamination-evidence "TemporaryAI\candidates\kathryn_merteuil_kathryn_merteuil_20260605_213017\workbench\inputs\identity_reviews\kathryn_monologue_audio_contamination_audit_20260717.json"
) else (
  python tools\auto_nominate_temp_ai_voice_sources.py --candidate-id kathryn_merteuil_kathryn_merteuil_20260605_213017 --url "https://www.youtube.com/watch?v=yPPzi-TjE94" --start-seconds 4.15 --owner-nominated-target-only --owner-note "Robert confirms Kathryn alone; machine review trims the dead lead and keeps faint score residue flagged for cleanup/QC." --search-query "Kathryn Merteuil Sarah Michelle Gellar non musical dialogue scene" --metadata-search --local-media "_tmp_kathryn_youtube_source\source.mp4" --local-wav "_tmp_kathryn_youtube_source\kathryn_4p15s_to_end.wav" --owner-attestation "TemporaryAI\candidates\kathryn_merteuil_kathryn_merteuil_20260605_213017\workbench\inputs\identity_reviews\kathryn_monologue_youtube_owner_attestation_20260717.json" --contamination-evidence "TemporaryAI\candidates\kathryn_merteuil_kathryn_merteuil_20260605_213017\workbench\inputs\identity_reviews\kathryn_monologue_audio_contamination_audit_20260717.json"
)
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo Automatic Kathryn source nomination was blocked. No voice or person was changed.
  pause
  exit /b 1
)
echo.
echo Finished. You do not need to approve or reject hundreds of clips.
echo Kathryn's selected range is queued for background cleanup and QC.
echo No voice was assigned and Kathryn was not activated.
pause
endlocal
