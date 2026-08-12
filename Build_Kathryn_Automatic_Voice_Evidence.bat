@echo off
setlocal
cd /d "%~dp0"
set "TRANSFORMERS_VERBOSITY=error"
set "HF_HUB_DISABLE_PROGRESS_BARS=1"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "PY=py"
) else (
  set "PY=python"
)

echo Checking Kathryn's supplied source and comparing the best pilot clips automatically...
echo No clip-review window will open.
echo.

%PY% tools\auto_nominate_temp_ai_voice_sources.py ^
  --candidate-id kathryn_merteuil_kathryn_merteuil_20260605_213017 ^
  --url "https://www.youtube.com/watch?v=yPPzi-TjE94" ^
  --start-seconds 4.15 ^
  --owner-nominated-target-only ^
  --owner-note "Robert confirms Kathryn alone; machine review trims the dead lead and keeps faint score residue flagged for cleanup/QC." ^
  --search-query "Kathryn Merteuil Sarah Michelle Gellar non musical dialogue scene" ^
  --metadata-search ^
  --local-media "_tmp_kathryn_youtube_source\source.mp4" ^
  --local-wav "_tmp_kathryn_youtube_source\kathryn_4p15s_to_end.wav" ^
  --owner-attestation "TemporaryAI\candidates\kathryn_merteuil_kathryn_merteuil_20260605_213017\workbench\inputs\identity_reviews\kathryn_monologue_youtube_owner_attestation_20260717.json" ^
  --contamination-evidence "TemporaryAI\candidates\kathryn_merteuil_kathryn_merteuil_20260605_213017\workbench\inputs\identity_reviews\kathryn_monologue_audio_contamination_audit_20260717.json" >nul 2>nul
if %ERRORLEVEL% NEQ 0 goto :failed

%PY% tools\check_temp_ai_speaker_consistency.py ^
  --anchor-wav "_tmp_kathryn_youtube_source\kathryn_4p15s_to_end.wav" ^
  --anchor-source-id kathryn_youtube_1999_monologue ^
  --owner-confirmed-anchor ^
  --candidate "kathryn_2016_pilot_clip0345=Voice\reference_packs\kathryn_merteuil_kathryn_merteuil_20260605_213017\kathryn_merteuil_kathryn_merteuil_20260605_213017_cruel_intentions_nbc_unaired_pilot_2016_sd_20260717_035509\candidate_clips\clip_0345.wav" ^
  --candidate "kathryn_2016_pilot_clip0346=Voice\reference_packs\kathryn_merteuil_kathryn_merteuil_20260605_213017\kathryn_merteuil_kathryn_merteuil_20260605_213017_cruel_intentions_nbc_unaired_pilot_2016_sd_20260717_035509\candidate_clips\clip_0346.wav" ^
  --candidate "kathryn_2016_pilot_clip0350=Voice\reference_packs\kathryn_merteuil_kathryn_merteuil_20260605_213017\kathryn_merteuil_kathryn_merteuil_20260605_213017_cruel_intentions_nbc_unaired_pilot_2016_sd_20260717_035509\candidate_clips\clip_0350.wav" ^
  --output "TemporaryAI\candidates\kathryn_merteuil_kathryn_merteuil_20260605_213017\workbench\inputs\identity_reviews\kathryn_cross_source_speaker_consistency_ranked_20260717.json" >nul 2>nul
if %ERRORLEVEL% NEQ 0 goto :failed

echo Finished.
echo The listener supported the same speaker in pilot clips 0345, 0346, and 0350.
echo Clip 0346 ranked strongest. Faint background residue still requires cleanup and QC.
echo No voice was assigned and Kathryn was not activated.
echo.
pause
exit /b 0

:failed
echo.
echo Automatic Kathryn evidence checking stopped safely. No voice or person was changed.
pause
exit /b 1
