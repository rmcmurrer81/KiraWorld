# Robert private runtime voice level calibration v1

Date: 2026-07-19

## Outcome

Synthetic Robert's private live Chatterbox voice now uses the same one-pass
level treatment Robert approved in the two finalized Kira World narration
videos:

- output gain: `-9.5 dB`
- gentle proximity correction: `95 Hz`, `0.30` mix
- pitch change: none
- stage: rendered Chatterbox PCM, before the WAV is written or played
- applications: exactly one per rendered chunk

The setting is stored only in
`Voice/profiles/temp_ai/robert_mcmurrer_voice_profile.json`. Default voice
configuration remains neutral, so this does not alter Kira, Elsa, Kathryn, or
another synthetic person's voice. It also does not reprocess either finalized
video.

## Measured result

The approved video narrations average `-21.323 LUFS`. An earlier private Robert
runtime sample measured `-11.913 LUFS`. Applying the profile treatment to that
same sample produced `-21.485 LUFS`, a difference of only `-0.162 LU` from the
approved-video average.

The calibrated sample peak is `-9.675 dBFS`, approximate 4x true peak is
`-9.560 dBTP`, and no samples clipped.

Machine-readable evidence, hashes, and guard results are in
`Data/codex_reports/20260719_robert_runtime_voice_level_calibration.json`.
The offline, non-playing comparison WAV is in
`Voice/generated/owner_review/robert_runtime_level_20260719/`.

## Runtime safety

Both full-message and streaming Chatterbox routes call the same PCM helper
once. Playback receives the already-calibrated WAV and adds no second gain.
Signal validation still evaluates the raw generated voice before calibration,
so the lower approved listening level cannot make a healthy generation fail
the speech-quality gate.

Automated coverage verifies:

- default profiles are PCM-identical;
- Robert's gain is applied once;
- no clipping is introduced in the test signal;
- Robert's candidate resolves to the bound approved reference and exact
  `-9.5 dB / 95 Hz / 0.30` values.

Re-run the audit without playing audio:

```powershell
python tools\audit_robert_runtime_voice_level.py
```
