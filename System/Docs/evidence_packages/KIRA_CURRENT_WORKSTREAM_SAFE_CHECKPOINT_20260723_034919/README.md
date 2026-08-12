# Kira current-workstream safe checkpoint

Created: 2026-07-23 03:49:19 America/New_York

This package preserves the exact current files needed to recover or audit the Kira eye, R6 body selection, movement/posture, existing-mouth lip movement, audio-continuity bridge, and Home World runtime workstreams.

No Kira activation, life loop, publishing, live-binding change, GLB mutation, or Video Studio change was performed while making this package.

## Important distinction

- `snapshot/` is a **post-change checkpoint snapshot**. It can restore the code and assets to this checkpoint, but it is not evidence of the state before the recent runtime and eye changes.
- `genuine_rollback/kira_pre_r6_live_trial_20260719_001839/` is an exact copy of the existing **pre-R6 reversible-trial rollback**. Its internal manifest and every named file were independently hash-verified at checkpoint time.
- This package does not create a pre-change rollback for runtime code that was already modified before the package was made.

## Preserved areas

- `snapshot/runtime/preview_src/`
  - Home World `main.js`
  - movement realism
  - person-owned ambient micro-movements
  - eye control
  - existing-mouth lip movement
- `snapshot/runtime/server/`
  - Kira World shell server, including movement-intent and audio-continuity handling
- `snapshot/tools/`
  - current eye, movement, and existing-mouth browser/verifier tools
- `snapshot/tests/`
  - current deterministic Python and JavaScript tests for these workstreams
- `snapshot/eye/`
  - R7-v3 source candidate and its offline evidence
  - staged v3.3 asset and source evidence
  - exact public Home World copy
  - production default skin-binding browser screenshots and evidence
- `snapshot/body/`
  - exact current R6 candidate directory, including GLB, manifest, and renders
- `snapshot/state/`
  - checkpoint copies of runtime body selection, R6 review staging, temporary-person state, and shell state
- `genuine_rollback/`
  - verified pre-R6 trial rollback set

## Verification files

- `COPY_VERIFICATION.tsv` maps every original file to its exact checkpoint copy. It records source hash, backup hash, size, and comparison result.
- `SHA256SUMS.tsv` records hashes for package contents. It intentionally excludes itself.
- `MANIFEST.md` records key hashes and the checkpoint truth/status boundaries.

At creation, `COPY_VERIFICATION.tsv` contained 75 comparisons and zero mismatches.

## Restore a selected post-change file

Do not restore over a running server or open authoring application.

1. Close Kira World Shell, the Home World preview, Blender, and any local Vite server.
2. Find the desired row in `COPY_VERIFICATION.tsv`.
3. Hash the current destination before changing it.
4. Copy only the listed `exact_backup` file to the listed `source` path.
5. Re-run the relevant verifier before launching a person.

These snapshot files are deliberately not restored automatically. A later change may be newer and valid, so compare first.

## Restore the genuine pre-R6 state

This rollback is only for intentionally leaving the reversible R6 live owner-review trial. It was **not** run while creating this package.

After closing all Kira runtime and authoring processes, use the copies under:

`genuine_rollback/kira_pre_r6_live_trial_20260719_001839/`

Restore:

1. `avatar_original_live_3ec62ba8.glb` to `Avatar/models/temp_ai/kira/avatar.glb`
2. `kira_runtime_body_selection.pre_trial.json` to `Avatar/state/body_selections/kira_runtime_body_selection.json`
3. `kira_r6_review_staging.pre_trial.json` to `Avatar/state/body_selections/kira_r6_review_staging.json`
4. `kira_temp_ai_state.pre_trial.json` to `Avatar/state/temp_ai/kira.json`

Then verify the restored files against `rollback_manifest.json` before starting Kira World.

The repository’s original rollback remains at:

`Avatar/state/body_selections/backups/kira_pre_r6_live_trial_20260719_001839/`

## Eye and runtime truth boundary

The preserved browser evidence reports the current v3.3 eye checks as passed with:

- exact R6 and eye hashes
- R6 and shell state unchanged by the test
- default, explicit, and opt-out behavior
- head binding and binding-distance stability
- gaze limited to the iris surface
- fixed socket, sclera, and cornea positions
- no old procedural-eye nodes
- no fake blink implementation
- no browser/runtime errors

Those are automated results. The screenshots remain subject to Robert’s visual review. Blink remains unsupported because no visually approved skinned eyelid geometry exists.

The preserved movement, posture, existing-mouth, and audio files are a post-change recovery point. Their deterministic tests do not replace Robert’s visual or listening review.

