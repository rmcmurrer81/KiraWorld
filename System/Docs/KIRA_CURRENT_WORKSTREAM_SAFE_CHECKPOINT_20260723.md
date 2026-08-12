# Kira current-workstream safe checkpoint — 2026-07-23

Status: authoritative bounded checkpoint before Kira Labs Video Studio v2 work.

This document records the exact state reached without activating Kira, starting
a life loop, publishing media, promoting an avatar candidate, or replacing the
working Video Studio installation.

## Status table

| Workstream | Automated or engineering status | Codex visual/listening status | Robert review | Current boundary |
|---|---|---|---|---|
| Eye v3.3 asset, iris, head binding, gaze and browser behavior | **PASSED** | **PASSED visually for bounded neutral/gaze evidence** | **AWAITING ROBERT REVIEW** | Brown eye asset remains reversible; gaze moves only the iris surface. |
| Natural blink | **BLOCKED** | Not applicable | Not ready | No approved skinned eyelid geometry exists; no fake lid was added. |
| Adult surface R4-v10 neck transition | **PASSED engineering gates** | **PASSED TO OWNER REVIEW, NOT FINAL** | **AWAITING ROBERT REVIEW** | Inactive Blend only; mild shoulder/base dimples remain; no GLB or binding. |
| Complete adult topology/internal anatomy | **BLOCKED / NOT PROVEN** | Not claimed | Not ready | R4-v10 is an external-surface engineering artifact, not anatomy proof. |
| Person-owned dialogue movement/posture dispatch | **PASSED deterministic tests** | **AWAITING LIVE VISUAL REVIEW** | **AWAITING ROBERT REVIEW** | Supported explicit first-person choices can route to outside/couch/bed actions; written stage directions remain unexecuted records. |
| Ambient posture and micro-movement | **PASSED deterministic bounds/drift tests** | **AWAITING LIVE VISUAL REVIEW** | **AWAITING ROBERT REVIEW** | Relaxed elbows/fingers and bounded settling are implemented without claiming human-quality motion. |
| Same-mouth playback movement | **PASSED code and geometry-safety tests** | **AWAITING LIVE VISUAL REVIEW** | **AWAITING ROBERT REVIEW** | Uses Kira's existing sealed lip surface; no second mouth; not phoneme-viseme proof. |
| Text-to-audio timing | **PASSED deterministic continuity tests** | **NOT AUDIBLY REVIEWED IN THIS CHECKPOINT** | **AWAITING ROBERT REVIEW** | First playback chunk was shortened; real listening latency remains an owner test. |
| Home World production build | **PASSED** | Browser evidence inspected | **AWAITING ROBERT REVIEW** | Build warning concerns chunk size only. |
| Video Studio v1.9 active installation | **PASSED prior independent non-admin launcher audit** | Walkthrough copy reviewed | Existing working install preserved | No active file was replaced for v2. |
| Video Studio v1.9 full backup | **PASSED** | Not applicable | Available if needed | 118 files and 89 named streams match; exact ACL application is separately blocked. |
| Video Studio external-output backup | **PASSED** | Not applicable | Available if needed | 497 files and 66 named streams match; restore sandbox passed; exact ACL application is separately blocked. |
| Exact runtime pre-change rollback | **BLOCKED / NOT AVAILABLE** | Not applicable | Not applicable | The safe package is a post-change checkpoint snapshot. |
| Genuine pre-R6 rollback | **PASSED** | Not run | Available if Robert intentionally leaves R6 | All five rollback-manifest expectations match. |
| Activation, life loop or publishing | **NOT PERFORMED** | Not applicable | Not applicable | Intentionally excluded from this checkpoint. |

## Eye v3.3 authority

The exact source, staged and public eye GLBs are byte-identical:

- Source: `Avatar/avatar_builder/candidate_sources/kira_r7_socket_eye_fit/review_20260722_v3/kira_r7_socket_eye_v3.glb`
- Staged: `Avatar/models/staged/kira/eyes/kira_socket_eye_rig_v3_3/kira_socket_eye_rig_v3_3.glb`
- Public Home World copy: `Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/public/models/home_world/kira/kira_socket_eye_rig_v3_3.glb`
- SHA-256 for all three: `b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5`

The current runtime binds the rest-coordinate eye asset through the matching
skinned mesh head-bone inverse. The default is skin binding. The diagnostic
query is `?kiraEyeBinding=root`; the fail-closed opt-out is
`?kiraEyeRig=off`. Gaze changes only the iris surface. The socket, sclera and
cornea remain fixed.

Current production browser evidence:

- `Data/world_tests/kira_socket_eye_v3_3_20260722/production_default_skin_fit/`
- `Data/world_tests/kira_socket_eye_v3_3_20260722/browser/`
- `Data/world_tests/kira_socket_eye_v3_3_20260722/fresh_validation_ephemeral_20260723_0554/`

The final fresh validation report is
`Data/codex_reports/20260723_kira_current_workstreams_fresh_validation.md`
(SHA-256
`649793b29fb45554724f1ec60c3b24b16322a9e24d362f029eb35da48d6688c0`).

The fresh browser run passed exact-asset hashes, default/explicit/opt-out
behavior, structural checks, head binding, stability, iris-only gaze, absence
of old procedural-eye nodes, absence of fake blink nodes, unchanged R6 and
shell state, and zero browser/runtime errors. Measured iris travel was
0.0025 m horizontally and 0.00144 m vertically; fixed eye-shell motion was
0 m; maximum measured head-binding-distance drift was 0.0000000002 m.

## Adult surface R4-v10 authority

R4-v10 is the first inactive R4 pass considered suitable for Robert to inspect:

- Folder: `Data/avatar_builder_workspace_tests/kira_r7_adult_surface_trial_20260722/reconstructed_neck_surface_r4_v10/`
- Blend: `inactive_reconstructed_neck_surface_r4_v10.blend`
- Blend SHA-256: `41ce3556beefaba1e8e48224b3af704832d2f5919fefe3eb171ee08714161822`
- Evidence SHA-256: `04580989c19952916d2dc0965c49c816df5d06b7db5c1634b514f759654d5307`
- Manifest SHA-256: `a1db9d5f101d0995937418c8918e52752d7c94dac6b1fce1ce55b5debc66716b`

It has one connected component, only the three intended face apertures, zero
degenerate or overused faces, all 79 rig groups, zero unweighted vertices, all
fixed pose gates passing, and a 16-ring 0.039953 m reconstructed transition.
Original-resolution review found the rejected collar/cone removed. Mild
shoulder/base dimples remain, particularly in side and back views. No GLB was
exported, no body binding changed, and R4-v8/R4-v9 remain rejected and inactive.

The exact live R6 body remains:

- `Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6/r6_20260718_163658/kira_provisional_body_r6.glb`
- SHA-256: `ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77`

## Movement, posture, mouth and audio authority

The runtime now distinguishes two different things:

1. A supported, explicit first-person choice in Kira's reply can publish a
   body intent such as go outside, sit on the couch, lie on the couch, or lie
   on the bed. Negative or excluded alternatives do not dispatch.
2. Model-written narrative stage directions remain candidate-owned,
   unexecuted future-body records under
   `System/Docs/CANDIDATE_OWNED_MOVEMENT_INTENTS_V1.md`. They are not evidence
   that a body action happened.

The Home World supplies collision-checked home-exit and couch routes plus
bounded posture/micro-movement changes. Automated proof is deterministic and
static; it does not replace Robert's visual review of naturalness or successful
navigation in a normal session.

The mouth pass uses the authored mouth already on R6. It changes the existing
sealed lip surface during actual audio playback and restores its base state.
It does not create a second mouth. It remains `deformationOnly`; no oral
interior, teeth, tongue, facial rig, approved viseme set or phoneme timing is
proved. The shorter first audio chunk is intended to reduce perceived startup
latency, but no real owner listening test was performed in this checkpoint.

## Verification run

Fresh checkpoint verification passed:

- 94 focused Python runtime tests
- 9 JavaScript mouth/ambient tests
- JavaScript syntax checks for the current preview modules
- deterministic movement-realism verifier
- eye v3.3 control verifier
- Home World production build
- production eye browser smoke with all current checks true and no errors

Kira was not activated and no life loop was started for any of these checks.

## Recovery package

Authoritative package:

`System/Docs/evidence_packages/KIRA_CURRENT_WORKSTREAM_SAFE_CHECKPOINT_20260723_034919/`

It contains 79 files totaling 50,972,054 bytes. All 75 source-to-copy
comparisons matched and all 78 entries listed in `SHA256SUMS.tsv` verified.

Key package hashes:

- `README.md`: `ba4999d16712504cf1ce9c97cf8fcf89f5f5c572ce425275a48cfb6f5f91c53d`
- `MANIFEST.md`: `83ddbfa5841faacbf749cfa71e778cbb1abb26fd7a56ab70a2983911a2b467fa`
- `COPY_VERIFICATION.tsv`: `6cb1a70a5aa806a619fd66c3a5b6292c0a96d8c87468d39b40eeb5eb4e411e73`
- `SHA256SUMS.tsv`: `f0cdf7ce5b5ac63730525e660f075f6475beb5f977480327d2d9c4117e367537`

Use `COPY_VERIFICATION.tsv` for an exact original-to-checkpoint-copy map.
Close all runtime/preview/Blender processes, hash the current destination,
restore only the selected checkpoint file, and rerun its verifier. Do not
blindly restore the whole snapshot over newer work.

Append-only supplement:

`System/Docs/evidence_packages/KIRA_CURRENT_WORKSTREAM_SUPPLEMENT_20260723_053246/`

The supplement preserves the complete inactive R4-v10 directory (including
the 135,349,726-byte Blend and all renders), the later and fresh eye-v3.3
browser evidence, the fresh validation report, R6 recovery pointers, and
R4-v8/R4-v9 status evidence. Independent verification found 42 of 42
source-to-copy matches and 42 of 42 payload checksums, totaling 154,607,266
payload bytes. The total package is 46 files and 154,638,183 bytes.

Supplement seal hashes:

- `README.md`: `e5c43f4c7cb34fd417f014e719cea0ec54ad6c8c28f72111ef632875439a8e51`
- `MANIFEST.md`: `a8b968cb5ca826629194dd4eb8d5e63e01d370386c76894a1d0339d2126f4355`
- `COPY_VERIFICATION.tsv`: `0cc38d838616a8e46bde630d69948a1110b70c452fc1d8f86545f60830e7b15b`
- `SHA256SUMS.tsv`: `8cfe5624c44f4b877322ae19d3a21f3bc6456b0cd0cd1fe5a5d19d6c8cf8dce0`

The supplement is evidence, not an automatic restore or authorization to
promote R4-v10. R4-v8/R4-v9 remain rejected and inactive.

The only genuine earlier-body rollback is:

`Avatar/state/body_selections/backups/kira_pre_r6_live_trial_20260719_001839/`

Its manifest and all five expected files were independently verified. It must
only be used intentionally, with Kira inactive and all World Shell processes
closed, following the included manifest/restore instructions.

## Video Studio v1.9 preservation

Active installation: `C:\KiraVideos\VideoStudio`

Verified full backup:

`C:\KiraVideos\Backups\VideoStudio_v1_9_pre_v2_20260723_040331`

The source and backup each contain 118 application files, 13 subdirectories,
21,953,950 application bytes and 89 named NTFS streams. Their aggregate tree
SHA-256 is
`7e36756a953a266d0adf52343b7271c0306bcdd3908508c1567615ffc58a5460`.
Exact source ACL application was blocked by Windows access control, but the
ACL manifest was preserved and all data, attributes, timestamps, directories
and named streams match. See
`Data/codex_reports/20260723_kira_labs_video_studio_v19_pre_v2_backup.md`.

The fail-closed restore verifier was also run against the separate sandbox
`C:\KiraVideos\Backups\VideoStudio_v19_restore_verify_sandbox_20260723_051927`.
It proved the exact 118-file, 13-directory and 89-named-stream set with zero
problems and did not touch the active installation. The report SHA-256 is
`042562a996c92933231d0abce5ebe796448b61df34b27f9a717c7d8865dc4765`.

The external output root omitted from that application-tree backup is now
separately preserved at
`C:\KiraVideos\Backups\StudioOutputs_pre_v2_20260723_073835`. Its 497 files,
126 directories, 315,717,929 ordinary bytes, 66 named streams and 7,236
named-stream bytes all matched source hashes and a separate restore sandbox
with zero problems. Canonical payload seal:
`36c0559b6812855931f45f9b1c307d82b318f4a2fc8025f74becf0dba38e7cd3`.
Metadata seal:
`7916d82a0a5533aa72ca39e69338429ae9ab6ff853cb1dbd2c61f9f8830d80be`.
Report:
`Data/codex_reports/20260723_kira_labs_studio_outputs_pre_v2_backup.md`
(SHA-256
`d8230b2d3c325e6c86c3730b3103e07111878f3b8dc4a1c5d87da1127fb585b6`).
ACL application remains blocked; captured SDDL is evidence, not a proved ACL
restore.

## Next safe action

All current workstreams have now reached a documented safe checkpoint. Items
marked awaiting Robert review or blocked above remain exactly that; automated
success does not convert them into owner approval. Video Studio v2 may now be
developed only beside the active v1.9 installation.
Do not replace, clean, delete from, or migrate the active installation until
the staged replacement passes its required private tests and Robert approves
the switch. No generated result may publish automatically.
