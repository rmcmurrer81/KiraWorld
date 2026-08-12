# Kira R7 inactive adult surface R4-v10 — 2026-07-22

## Outcome

**Current authority: the inactive R4-v10 engineering artifact passed Codex's
2026-07-23 original-resolution fixed-view review to Robert's owner review, but
it is not final, exported, bound, or promoted.**

The machine-authored `evidence.json`, `manifest.json`, and decision string
below were sealed before that human visual review. Their
`visual_review_pending` / false visual-gate fields accurately describe the
engineering run at the time it was generated; they were intentionally not
rewritten afterward. The dated visual-review addendum at the end of this
report supersedes only that pending-review narrative. It does not open the
export gate or change the sealed engineering evidence.

R4-v10 removes the visibly defective R3 collar while preserving the natural upper neck,
then joins clean retained shoulder and neck loops with
16 arc-length-aligned ruled-loft rings with bounded
circumferential relaxation that fades to zero at both retained boundaries.
This is a geometry reconstruction, not a material concealment. The original light
skin contract remains `#e6c0a9`.

All 10555 protected head,
face, mouth, eye-aperture, ear, and cranium vertices remain unchanged. The removed
source vertices are confined to the approved 116
body and 230 lower-neck
topological zones. Maximum displacement of every retained source vertex is
`0.0` m.

Decision: `inactive_r4v10_engineering_pass_visual_review_pending_no_candidate`

## Geometry and rig

- Removed R3 bridge faces: 230.
- Added transition vertices/faces: 1216 / 1346.
- Connected components: 1.
- Boundary cycles: 3 (the same three sealed eye/mouth openings; no neck opening).
- Overused/degenerate faces: 0 / 0.
- Defined rig groups: 79.
- Unweighted vertices: 0.
- Maximum positive groups per vertex: 4.
- Fixed pose gates: `{'rest': True, 'upper_limb': True, 'hip_knee': True, 'spine_neck': True, 'bilateral_squat': True}`.
- Bounded-reconstruction engineering gate: `True`.

## Fixed original-resolution renders

- `neutral_front`: `neutral_front.png`
- `neutral_back`: `neutral_back.png`
- `neutral_left`: `neutral_left.png`
- `neutral_right`: `neutral_right.png`
- `neck_closeup_front`: `neck_closeup_front.png`
- `neck_closeup_back`: `neck_closeup_back.png`
- `neck_closeup_left`: `neck_closeup_left.png`
- `neck_closeup_right`: `neck_closeup_right.png`
- `identity_front`: `identity_front.png`
- `identity_left_profile`: `identity_left_profile.png`
- `pose_upper_limb`: `pose_upper_limb.png`
- `pose_hip_knee`: `pose_hip_knee.png`
- `pose_spine_neck`: `pose_spine_neck.png`
- `pose_bilateral_squat`: `pose_bilateral_squat.png`

Review Blend: `Data/avatar_builder_workspace_tests/kira_r7_adult_surface_trial_20260722/reconstructed_neck_surface_r4_v10/inactive_reconstructed_neck_surface_r4_v10.blend`

Evidence: `Data/avatar_builder_workspace_tests/kira_r7_adult_surface_trial_20260722/reconstructed_neck_surface_r4_v10/evidence.json`

Manifest: `Data/avatar_builder_workspace_tests/kira_r7_adult_surface_trial_20260722/reconstructed_neck_surface_r4_v10/manifest.json`

## Safety and truth limits

- No GLB has been exported while visual review is pending.
- No Avatar Builder binding, live body, activation state, or autobuild record changed.
- Complete adult topology/internal anatomy is not claimed.
- Eyes, lip sync, and runtime movement remain separate unfinished tasks.
- A rollback-safe inactive GLB may be authored later only after fixed-view visual approval.

## Visual-review addendum — 2026-07-23

Codex completed an original-resolution engineering visual review of the fixed
front, back, left, right, neck-closeup, identity, and pose renders.

Visual verdict: **owner-review-worthy, but not final**. R4-v10 removes the
rejected collar and long cone defects while preserving the natural upper neck.
Mild shoulder/base dimples remain visible, especially in the side and back
views, and still require Robert's review.

This addendum does not promote the artifact or change its engineering evidence:

- R4-v10 remains inactive.
- Robert's owner review is pending.
- No GLB was exported.
- No Avatar Builder binding or promotion occurred.
- The live R6 body remains unchanged.
