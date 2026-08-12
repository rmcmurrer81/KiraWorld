# Kira R6 reversible live owner-review trial

Status: selected for a reversible owner-review trial on 2026-07-19. This is not a permanent body approval.

## What is live

Kira's normal runtime profile now points to the exact R6 candidate:

- Model: `Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6/r6_20260718_163658/kira_provisional_body_r6.glb`
- SHA-256: `ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77`
- Runtime profile: `Avatar/state/temp_ai/kira.json`
- Selection record: `Avatar/state/body_selections/kira_runtime_body_selection.json`

The model contains the adult external body form and its existing 79-joint rig. It contains no clothing mesh. Clothes remain separate wardrobe assets that Kira can later put on and take off.

The World Shell now enforces this selection at three boundaries: API state only exposes the model after the profile and exact hash-bound selection agree; delivery of that exact live Kira model rechecks the selection and the bytes' SHA-256; and the browser rejects stale loads and unloads a displayed Kira model if the selection becomes invalid or is cleared. Other Avatar assets keep their ordinary static-asset behavior.

## What was preserved

The previous live model was not overwritten:

- Original model: `Avatar/models/temp_ai/kira/avatar.glb`
- SHA-256: `3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e`
- Rollback folder: `Avatar/state/body_selections/backups/kira_pre_r6_live_trial_20260719_001839`
- Rollback manifest SHA-256: `557b509c7671a016bd8352453458657b691ea0da304ea05495fa5f68eda9e7f7`

Deactivate Kira and close the World Shell before running `Restore_Kira_Pre_R6_Live_Body.bat`. The restore tool verifies every bound hash and refuses to proceed if Kira is active.

## Evidence and limits

The exact R6 file passed the inactive browser compatibility sandbox documented in:

- `Data/world_tests/kira_r6_exact_browser_sandbox_20260718/20260718T222144Z/evidence.json`
- Evidence SHA-256: `29f995522ec773774a61ceb1a36aa9ac0c731b3c7b690e5ac8b9de130957a5ed`

Those checks cover exact loading, finite bounds, basic walk displacement and ground contact, sit deformation, gradual turning, door reach, structural eye attachment, and deformation of the existing mouth without creating a second mouth.

They do not prove complete adult anatomy, final Kira likeness, natural
long-duration movement, or permanent acceptance by Kira. The R6 body should
therefore be judged by ordinary live use and can be rolled back without losing
the previous model.

The July 21 reversible Home World composition substantially improves the
staged v3.2 brown-eye fit without changing either source GLB. It uses a
16-degree neutral yaw, 1.08 iris/limbal/pupil scale, and no random idle saccades
in the proof run. Original-resolution review found both irises seated inside
the visible sclera apertures and much better centered. Robert's visual approval
is still pending. The Avatar Builder uses a different composition path: every
visible Builder sweep still protruded outside the R6 eyelids, so the Builder
now hides that incompatible eye component and explicitly reports eye fit as
`UNAPPROVED` instead of showing a known-bad result.

The same Home World pass adds modest audio-playback-timed motion to the
existing 207-vertex lip island and restores it exactly. It creates no second
mouth. This is not phoneme-accurate natural lip sync because R6 has no mouth
interior, facial bones, or phoneme morph targets. Detailed evidence and limits
are in `System/Docs/KIRA_EXISTING_MOUTH_AUDIO_PLAYBACK_LIPSYNC_v1.md`.

The runtime and Builder both use Kira's requested original light base tone
`#e6c0a9`. No localized anatomy coloring was guessed: R6 has no reviewed
semantic anatomical-region masks, and color cannot prove topology.

The enforcement paths have unit, integration, production-build, and isolated exact-R6 browser evidence. A fresh post-hardening activation through the complete normal World Shell was deliberately left for Robert's next ordinary review, so the current proof must not be described as a new full end-to-end live-session pass.

An isolated R7 Blender authoring workspace is now prepared under
`Avatar/avatar_builder/candidate_sources/kira_adult_body_r7/workspace_v1/`.
It preserves R6's exact surface, single mouth, UVs, shape keys, weights, and
79-bone rig and contains five deliberately empty semantic-mask attributes. It
is not a body candidate and is not bound to Kira. Manual reviewed protected
head/mouth/neck selection is required before any geometry or semantic material
work. See
`Data/codex_reports/20260721_kira_r7_authoring_workspace_preparation.md`.

## How Robert reviews it

1. Start the normal Kira World Shell.
2. Activate Kira. Her profile resolves the R6 file above.
3. Observe her body, eyes, ground contact, arms, hands, turns, sitting, door use, and existing-mouth lip movement.
4. Report visual feedback. Do not treat this trial as evidence that any unproven item is finished.

The private contact-sheet launcher is `Open_Kira_R6_Private_Clothed_Owner_Review.bat`. Its reference renders are private review material and must not be copied into the public Facebook or YouTube package.

## 2026-07-23 safe-checkpoint addendum

The exact live R6 body remains unchanged at SHA-256
`ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77`.
The genuine pre-R6 rollback at
`Avatar/state/body_selections/backups/kira_pre_r6_live_trial_20260719_001839/`
was independently rechecked: its manifest and all five named hash
expectations passed. It was not run.

The inactive R4-v10 external-surface artifact removes the failed R3 collar
and cone and passes its engineering/pose gates. Codex fixed-view review found
it suitable for Robert to inspect, but mild shoulder/base dimples remain. It
is not a final body, does not prove complete adult topology or internal
anatomy, has no exported GLB, and is not bound to Kira. See
`Data/codex_reports/20260722_kira_r7_adult_surface_r4_v10.md`.

The current eye runtime now uses the byte-identical v3.3 brown-eye asset with
corrected head binding and iris-only gaze. Automated browser checks and Codex
fixed-view inspection passed; Robert's visual review remains pending. Blink
is blocked because there is no approved skinned eyelid geometry. See
`System/Docs/KIRA_R7_SOCKET_EYE_V3_3_CHECKPOINT_20260723.md`.

The full post-change recovery snapshot and verified pre-R6 rollback duplicate
are recorded in
`System/Docs/evidence_packages/KIRA_CURRENT_WORKSTREAM_SAFE_CHECKPOINT_20260723_034919/`.
This is not an exact pre-change rollback for recent runtime code.
