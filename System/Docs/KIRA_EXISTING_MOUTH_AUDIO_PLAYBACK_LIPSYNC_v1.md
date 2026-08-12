# Kira Existing-Mouth Audio Playback Lip Sync v1

Status: playback-bridge telemetry passed, but Robert's 2026-07-21 owner-visible test failed. Real visible lip sync remains open.

## 2026-07-21 owner-test correction

Robert reported that Kira's lips did not move while she was speaking. That
owner observation is authoritative for visible behavior. The playback log did
show that matching Kira audio reached the active avatar and drove the fallback
mouth code, but telemetry is not visual proof. Original-resolution inspection
after the owner report also did not show a clearly readable mouth aperture.

The current 207-vertex region is a sealed, connected lip-surface island. The
fallback stretches that existing surface and changes its vertex color. It does
not have authored inner-mouth topology to reveal, and R6 has no facial bones or
phoneme/viseme morph targets. Consequently:

- sealed-island deformation is not owner-visible or real lip sync;
- the calculated `openingDistance` is a deformation-envelope value, not proof
  that a visible mouth opening exists;
- playback matching, vertex displacement, projected bounds, and restoration
  prove only that the fallback code ran;
- the current implementation must remain marked `deformationOnly: true`,
  `visemeReady: false`, and `visualMotionProven: false`.

Do not describe this pass as visible lip motion or a completed lip-sync fix.
The open production requirement is to author the existing single mouth in R7
with reviewed mouth-interior topology and phoneme/viseme morph targets, or a
reviewed lip/jaw facial rig. It must use Kira's existing mouth and must not add
a second mouth mesh, accessory, or overlay.

## Contract

- Kira's authored mouth is the only mouth used.
- The runtime creates no mouth mesh, mouth node, or mouth accessory.
- The selected region is the existing connected lip island in `Object_85` (207 vertices).
- Lip motion begins at `chunk_playback_start`, not when chat is submitted and not when synthesis begins.
- Lip motion returns to the exact stored base positions and vertex colors after `chunk_playback_end` or any non-playing state.
- Playback state sent to the world contains timing/identity metadata only; it contains no spoken text.

The v7 fallback deformation is deliberately bounded to the authored lip
surface:

- The deformation envelope is derived from the selected lip-island height and
  clamped to 5.5-10 mm. The canonical telemetry reported 8.566 mm; that value
  is not a visually measured aperture.
- Upper and lower seam vertices separate symmetrically. The exterior lip perimeter and corners remain anchored; the canonical maximum perimeter displacement was 0 m.
- Depth movement is seam-confined and capped at 0.35 mm.
- A warm, narrow vertex-color shade is applied during playback. It does not
  create an aperture, inner-mouth geometry, a material overlay, or a second
  mouth.

The current body has no facial bones and no phoneme morph targets. This pass
therefore supplies only an audio-playback-timed deformation envelope by
changing the existing position attribute in place. Accurate, owner-visible
phoneme shapes require the reviewed R7 existing-mouth topology and rig work
described above.

## Runtime path

1. `Core/voice_output.py` emits playback start/end boundaries around actual WAV playback.
2. `tools/kira_world_shell_server.py` records a text-free playback state and exposes `/api/voice-playback`.
3. The shell forwards only changed playback revisions to the home-world iframe.
4. `preview/src/main.js` verifies the playback identity matches active Kira.
5. `preview/src/existing_mouth_lipsync.js` deforms and restores the existing lip
   vertices. It does not currently provide proven visible lip sync.

## Historical eye-fit assessment (v3.2; superseded)

This section records the eye state that accompanied the 2026-07-21 mouth
test. It is not the current eye authority. The current reversible v3.3 asset,
head binding, gaze behavior, browser evidence, and SHA-256 are documented in
`System/Docs/KIRA_R7_SOCKET_EYE_V3_3_CHECKPOINT_20260723.md`.

The staged brown-eye GLB remains geometrically unchanged. Runtime placement uses a reversible 16-degree neutral yaw, a 1.08 uniform iris/limbal-ring/pupil diameter scale, and no independent iris offset. Codex inspected the canonical full-face frames at original resolution: both brown irises are seated inside the visible sclera apertures and substantially better centered than the earlier fit. Autonomous idle saccades were disabled for proof with `?kiraEyeIdleFit=off`, so the evidence is the authored neutral fit rather than a random gaze sample. Robert's owner approval is still pending.

The runtime skin remains the requested original light base color `#e6c0a9`.

## Evidence and tests

- Earlier browser telemetry: `Data/world_tests/kira_r6_face_motion_runtime_20260718/browser_smoke.json`
- Latest owner-test follow-up evidence:
  `Data/world_tests/kira_eye_fit_sweep_20260721/final_candidate_yaw16_iris108_v4/browser_smoke.json`
- Original-resolution review inputs: the full frames and `*_closeup.png` mouth
  crops in those evidence directories. These images did not overturn Robert's
  failed owner-visible result.
- Unit geometry test: `node --test Testing/test_existing_mouth_lipsync.mjs`
- Playback bridge test: `python -m unittest -q Testing.test_kira_world_shell_lipsync_playback`
- Live-model smoke: `node tools/kira_existing_mouth_lipsync_browser_smoke.mjs`
- Preview build: run `npm.cmd run build` from the home-world preview directory.

The live smoke is isolated: it does not activate a person, start a life loop, persist shell state, or modify Kira's GLB.

Exact source hashes after validation:

- R6 body: `ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77`
- Historical brown-eye rig v3.2: `fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413`

## Honest limitation

This is actual-playback-timed deformation of Kira's existing sealed lip
surface, with exact restoration. It is not owner-visible or real lip sync. The
R6 source body has no facial bones, mouth interior, teeth/tongue geometry, or
phoneme morph targets. Increasing the deformation amplitude would risk
recreating the rejected detached lower-lip/chin appearance without solving the
missing topology. R7 must add reviewed mouth-interior topology and viseme
controls to the existing mouth while preserving the playback, identity, and
single-mouth contracts.

## 2026-07-23 runtime checkpoint addendum

The Home World playback adapter continues to use Kira's existing mouth only.
No mouth node, overlay, accessory or second mouth was added. The current pass
adds same-surface playback movement and telemetry and restores the base lip
state. It remains a sealed-surface deformation rather than an approved
phoneme/viseme system.

Fresh deterministic verification passed the current existing-mouth and
ambient JavaScript tests (9 of 9), relevant syntax checks, the focused Python
dialogue/audio/runtime suite (94 of 94), and the Home World production build.
The server's first playback chunk was shortened to reduce startup latency.
No fresh owner listening test was performed, so audible latency and visible
lip motion remain **AWAITING ROBERT REVIEW**. Oral interior, teeth, tongue,
facial controls and phoneme timing remain **BLOCKED / NOT PROVEN**.

Checkpoint sources and evidence are preserved in
`System/Docs/evidence_packages/KIRA_CURRENT_WORKSTREAM_SAFE_CHECKPOINT_20260723_034919/`.
It is a post-change recovery snapshot, not a pre-change runtime rollback.
