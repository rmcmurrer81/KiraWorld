# Kira current workstreams safe checkpoint — 2026-07-23

## Outcome

**SAFE CHECKPOINT REACHED.** The current eye, inactive adult-surface,
movement/posture, same-mouth/audio, Home World and Video Studio v1.9
workstreams have explicit evidence and recovery boundaries. Kira was not
activated, no life loop ran, no avatar candidate was promoted, the exact live
R6 body remained recoverable, the working Video Studio installation was not
replaced, and nothing was uploaded or published.

## Workstream decisions

### Eye v3.3

- Automated asset/hash, browser, head-binding, iris-only gaze, opt-out and
  state-preservation checks: **PASSED**.
- Codex original-resolution bounded visual inspection: **PASSED TO ROBERT
  REVIEW**.
- Robert visual review: **AWAITING ROBERT REVIEW**.
- Natural blink: **BLOCKED** by absence of approved skinned eyelid geometry.
- Source/staged/public GLB SHA-256:
  `b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5`.

### Adult body and neck transition

- R4-v10 engineering gates: **PASSED**.
- Codex original-resolution review: **PASSED TO OWNER REVIEW, NOT FINAL**.
- Robert visual review: **AWAITING ROBERT REVIEW**.
- Complete adult topology/internal anatomy: **BLOCKED / NOT PROVEN**.
- R4-v10 remains an inactive Blend; no GLB, binding or promotion exists.
- Mild shoulder/base dimples remain visible, especially from side/back.
- Blend SHA-256:
  `41ce3556beefaba1e8e48224b3af704832d2f5919fefe3eb171ee08714161822`.

### Candidate-owned movement and posture

- Explicit first-person dialogue-choice extraction and supported body-intent
  dispatch: **PASSED deterministic tests**.
- Negated/excluded-alternative suppression: **PASSED deterministic tests**.
- Home exit/couch route and posture-source verifier: **PASSED**.
- Ambient bounds, priority and drift tests: **PASSED**.
- Human-quality movement/navigation: **AWAITING ROBERT REVIEW**.
- Model-written stage directions are still unexecuted records and were not
  reclassified as completed actions.

### Same-mouth movement and audio timing

- Existing-mouth-only and restoration tests: **PASSED**.
- No second mouth: **PASSED code/structure checks**.
- Dialogue/audio continuity tests and shorter first playback chunk: **PASSED
  deterministic checks**.
- Owner-visible lip movement: **AWAITING ROBERT REVIEW**.
- Real listening latency: **AWAITING ROBERT REVIEW**.
- Oral interior, teeth, tongue, reviewed facial rig and phoneme visemes:
  **BLOCKED / NOT PROVEN**.

### Video Studio v1.9

- Prior independent ordinary-user launcher smoke: **PASSED**.
- Full pre-v2 content backup: **PASSED**.
- File, directory, byte and NTFS named-stream verification: **PASSED**.
- Exact ACL application to backup: **BLOCKED by Windows access control**;
  ACL manifest preserved.
- Fresh Chatterbox synthesis and real-owner-recording encode in the independent
  v1.9 audit: **NOT RUN**.
- Active-install changes, deletion, replacement or publishing: **NONE**.

## Fresh automated evidence

- Focused Python runtime suite: **94 passed, 0 failed**.
- Existing-mouth and ambient JavaScript suite: **9 passed, 0 failed**.
- Relevant JavaScript syntax checks: **PASSED**.
- `verify_kira_movement_realism_r5.mjs`: **PASSED**; deterministic/static,
  no activation and no visual-review claim.
- `verify_kira_eye_control_exam.mjs`: **PASSED** for eye v3.3.
- Home World `npm.cmd run build`: **PASSED**; only the existing chunk-size
  warning was emitted.
- Production eye browser smoke: **PASSED** with no browser/runtime errors,
  no Kira activation, no life loop and unchanged shell state.

## Exact runtime files changed in the completed pass

- `tools/kira_world_shell_server.py`
  - explicit Kira first-person supported-action extraction/dispatch repair
  - affirmative outside/couch handling and negative-alternative exclusion
  - shorter first voice chunk for lower startup latency
- `Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js`
  - v3.3 rest-coordinate eye head binding
  - iris-only gaze and fixed shell
  - same-mouth playback movement/telemetry
  - relaxed elbows/fingers
  - supported go-outside route and collision-checked exit behavior
- `Testing/test_kira_chat_body_intent_bridge.py`
- `Testing/test_kira_unified_body_intent.py`
- `Testing/test_kira_world_dialogue_audio_continuity.py`
- `Testing/test_kira_world_latest_session_repairs.py`
- `Testing/test_kira_world_shell_lipsync_playback.py`
- `Testing/test_kira_movement_realism_r5.py`
- `Testing/test_existing_mouth_lipsync.mjs`
- `Testing/test_ambient_micro_movements.mjs`
- `tools/verify_kira_movement_realism_r5.mjs`
- `tools/verify_kira_eye_control_exam.mjs`
- `tools/kira_socket_eye_v3_3_browser_smoke.mjs`

Current key source hashes:

- Home World `main.js`:
  `41fb94394a97e4ad1c96dce5f70560cb7e428692aaa0a5b65f1bf48ee6304bdd`
- Kira World shell server:
  `28cf54a24c4499682c2dc7ec5674230c85d9442e992960121555bc965fea9590`
- Exact live R6 GLB:
  `ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77`

## Inactive adult-surface artifact

Folder:

`Data/avatar_builder_workspace_tests/kira_r7_adult_surface_trial_20260722/reconstructed_neck_surface_r4_v10/`

Key files/hashes:

- `inactive_reconstructed_neck_surface_r4_v10.blend`:
  `41ce3556beefaba1e8e48224b3af704832d2f5919fefe3eb171ee08714161822`
- `evidence.json`:
  `04580989c19952916d2dc0965c49c816df5d06b7db5c1634b514f759654d5307`
- `manifest.json`:
  `a1db9d5f101d0995937418c8918e52752d7c94dac6b1fce1ce55b5debc66716b`

R4-v8 and R4-v9 remain rejected and inactive. No auto-build gate was opened.

## Checkpoint backup and rollback

Post-change recovery package:

`System/Docs/evidence_packages/KIRA_CURRENT_WORKSTREAM_SAFE_CHECKPOINT_20260723_034919/`

- 79 files
- 50,972,054 bytes
- 75 of 75 source-to-copy comparisons matched
- 78 of 78 package checksum entries matched
- `README.md` SHA-256:
  `ba4999d16712504cf1ce9c97cf8fcf89f5f5c572ce425275a48cfb6f5f91c53d`
- `MANIFEST.md` SHA-256:
  `83ddbfa5841faacbf749cfa71e778cbb1abb26fd7a56ab70a2983911a2b467fa`
- `COPY_VERIFICATION.tsv` SHA-256:
  `6cb1a70a5aa806a619fd66c3a5b6292c0a96d8c87468d39b40eeb5eb4e411e73`
- `SHA256SUMS.tsv` SHA-256:
  `f0cdf7ce5b5ac63730525e660f075f6475beb5f977480327d2d9c4117e367537`

Important: this package is a **post-change checkpoint**, not a trustworthy
pre-change rollback for runtime code. To restore one checkpoint file, close
all related applications, find its row in `COPY_VERIFICATION.tsv`, compare the
current destination hash, copy only that file, and rerun its verifier.

Genuine pre-R6 rollback:

`Avatar/state/body_selections/backups/kira_pre_r6_live_trial_20260719_001839/`

The rollback manifest and all five expectations matched. It was not run. Use
it only with Kira inactive and all World Shell processes closed.

## Video Studio backup and rollback

- Active: `C:\KiraVideos\VideoStudio`
- Backup:
  `C:\KiraVideos\Backups\VideoStudio_v1_9_pre_v2_20260723_040331`
- Application tree SHA-256:
  `7e36756a953a266d0adf52343b7271c0306bcdd3908508c1567615ffc58a5460`
- 118 files, 13 subdirectories, 21,953,950 application bytes, 89 named streams,
  zero content/path/stream mismatches.

Use the non-destructive restore-staging and folder-switch commands in
`Data/codex_reports/20260723_kira_labs_video_studio_v19_pre_v2_backup.md`.
Never restore directly over the active folder and never delete the former
active folder until Robert verifies launcher, voice, projects, settings and
outputs.

## Documentation files created or updated

Current-authority documents and reports created or updated during the
checkpoint sequence include:

- `System/Docs/KIRA_CURRENT_WORKSTREAM_SAFE_CHECKPOINT_20260723.md`
- `System/Docs/KIRA_R7_SOCKET_EYE_V3_3_CHECKPOINT_20260723.md`
- `System/Docs/KIRA_LABS_VIDEO_STUDIO_CURRENT_INSTALLATION_v1_9.md`
- `Data/codex_reports/20260722_kira_r7_adult_surface_r4_v10.md`
- `Data/codex_reports/20260723_kira_labs_video_studio_v19_pre_v2_backup.md`
- `System/Docs/README_MASTER_INDEX.md`
- `System/Docs/KIRA_R6_REVERSIBLE_LIVE_OWNER_REVIEW_TRIAL_v1.md`
- `System/Docs/KIRA_EXISTING_MOUTH_AUDIO_PLAYBACK_LIPSYNC_v1.md`
- `System/Docs/AMBIENT_PERSON_OWNED_MICRO_MOVEMENT_V1.md`
- `HANDOFF_FOR_NEXT_CODEX_SESSION.md`
- this report

## Safe transition decision

Every current workstream now has a status, evidence boundary and recovery
path. Video Studio v2 work may begin only in a separate staging installation.
The active v1.9 installation and approved Robert voice remain authoritative.
No staged v2 result may replace v1.9 until it proves a real private workflow
and Robert approves the replacement.
