# Kira R7 socket-eye v3.3 checkpoint — 2026-07-23

Status: automated and Codex visual checkpoint passed; Robert visual review is pending; blink is blocked.

## Exact asset

The source candidate, staged asset and public Home World copy are
byte-identical and remain reversible:

- `Avatar/avatar_builder/candidate_sources/kira_r7_socket_eye_fit/review_20260722_v3/kira_r7_socket_eye_v3.glb`
- `Avatar/models/staged/kira/eyes/kira_socket_eye_rig_v3_3/kira_socket_eye_rig_v3_3.glb`
- `Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/public/models/home_world/kira/kira_socket_eye_rig_v3_3.glb`
- SHA-256: `b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5`

No GLB was edited during the runtime binding correction.

## Binding and gaze implementation

The asset is authored in rest coordinates. The Home World now binds it using
the matching skinned mesh head-bone inverse rather than applying the head
transform twice. Default binding is skin-based. Diagnostic switches are:

- `?kiraEyeBinding=root` — compare diagnostic root binding
- `?kiraEyeRig=off` — fail-closed opt-out

The bounded socket correction is -0.008 m vertically and -0.002 m in depth.
Gaze moves only the iris surface. Socket, sclera and cornea remain fixed.

## Automated browser result

Evidence:

- `Data/world_tests/kira_socket_eye_v3_3_20260722/production_default_skin_fit/`
- `Data/world_tests/kira_socket_eye_v3_3_20260722/browser/`
- `Data/world_tests/kira_socket_eye_v3_3_20260722/fresh_validation_ephemeral_20260723_0554/`

The fresh evidence JSON has SHA-256
`4144e71106b7924bf820a60f7c55b15f02dcb0cf80789684872356ac2e503f83`.
The complete fresh checkpoint report is
`Data/codex_reports/20260723_kira_current_workstreams_fresh_validation.md`
(SHA-256
`649793b29fb45554724f1ec60c3b24b16322a9e24d362f029eb35da48d6688c0`).

Current checks passed:

- exact R6 and eye hashes
- default, explicit and opt-out behavior
- structural eye asset checks
- head-bound attachment and stable head-binding distance
- iris-only horizontal and vertical gaze
- zero socket/sclera/cornea local motion
- no retired procedural-eye nodes
- no fake blink geometry
- no browser/runtime error
- no activation, life loop or shell-state mutation

Reported metrics:

- horizontal iris travel: 0.0025 m
- vertical iris travel: 0.00144 m
- maximum fixed-shell motion: 0 m
- maximum head-binding-distance drift: 0.0000000002 m

## Review boundary

Codex original-resolution inspection found the neutral brown-eye result clean
and seated enough to pass to Robert for review. This is not Robert's approval.
Robert still needs to judge identity, comfort, centering and natural gaze in
ordinary use.

Blink is **BLOCKED**. The current R6 eyelid/socket opening does not have an
approved skinned eyelid solution. No fake lid mesh or procedural overlay was
added. Earlier eye v1 and v2 candidates remain rejected and inactive.

## Recovery

The asset, runtime source, verifier, screenshots and evidence are preserved in:

`System/Docs/evidence_packages/KIRA_CURRENT_WORKSTREAM_SAFE_CHECKPOINT_20260723_034919/`

Later and fresh eye evidence is additionally hash-sealed in:

`System/Docs/evidence_packages/KIRA_CURRENT_WORKSTREAM_SUPPLEMENT_20260723_053246/`

This package is a post-change checkpoint, not a pre-change runtime rollback.
Use its `COPY_VERIFICATION.tsv` to restore only a selected file after comparing
the current destination and closing all related processes.
