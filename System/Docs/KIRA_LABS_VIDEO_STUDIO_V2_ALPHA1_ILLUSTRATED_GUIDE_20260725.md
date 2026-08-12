# Kira Labs Video Studio 2.0.0-alpha.1 — Illustrated Private-Review Guide

> **Current-link update — 2026-07-26:** Use the current proof links and review
> states in
> `System/Docs/KIRA_LABS_VIDEO_STUDIO_V2_POST_HARDENING_SAFE_CLOSEOUT_20260726.md`.
> The current real proof is `20260725_234948_...` and passed 1,117 read-only
> checks. The current concept proof is `20260725_233935_...`. Older
> `20260723_111612_...` and `20260725_193114_...` links below are preserved
> historical links, not current proof. The standard-user launcher hardening
> passed automated checks, but Robert still needs to perform a visible
> ordinary double-click review. If the staged launcher cannot write beside
> itself, its fallback log is
> `%LOCALAPPDATA%\KiraLabs\VideoStudio\2.0.0-alpha.1\launcher_failure.log`.
> For the future animation boundary, also read
> `System/Docs/KIRA_LABS_VIDEO_STUDIO_VIRTUAL_PRODUCTION_DIRECTION_20260725.md`.

Date: 2026-07-25  
Audience: Robert  
Build state: isolated staging, private review only

## Start here

The active Video Studio is still v1.9:

`C:\KiraVideos\VideoStudio`

The version in this guide is the isolated `2.0.0-alpha.1` stage:

`C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1`

It has not replaced v1.9. It cannot be treated as finished, clean-final-ready,
rights-cleared, or approved for publication.

## Launch the staged program

1. Open
   `C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1`.
2. Double-click
   `START_KIRA_LABS_VIDEO_STUDIO.bat`.
3. Confirm that the window title contains
   `Kira Labs Video Studio — 2.0.0-alpha.1 STAGING`.
4. Do not use Run as administrator as the normal launch method.
5. If it does not open, double-click `CHECK_SETUP.bat`.
6. Inspect `launcher_failure.log` if the setup check reports a problem.

The automated self-test, Python compile check, and hidden Tk construction
passed. Robert still needs to verify a visible ordinary double-click on his
Windows desktop.

## Review the real Kira World Update proof

Proof folder:

[`Open the real private-proof project`](<C:/Users/robmc/KiraVideos/StudioOutputs/V2_PrivateTests/20260723_111612_kira_world_july_23_2026_engineering_checkpoint_v2_kira_world_july_2>)

Private-review videos:

- [`Landscape 16:9 private review`](<C:/Users/robmc/KiraVideos/StudioOutputs/V2_PrivateTests/20260723_111612_kira_world_july_23_2026_engineering_checkpoint_v2_kira_world_july_2/build/private_review/rebuild_landscape_16_9_PRIVATE_REVIEW.mp4>)
- [`Vertical 9:16 private review`](<C:/Users/robmc/KiraVideos/StudioOutputs/V2_PrivateTests/20260723_111612_kira_world_july_23_2026_engineering_checkpoint_v2_kira_world_july_2/build/private_review/rebuild_vertical_9_16_PRIVATE_REVIEW.mp4>)
- [`Square 1:1 private review`](<C:/Users/robmc/KiraVideos/StudioOutputs/V2_PrivateTests/20260723_111612_kira_world_july_23_2026_engineering_checkpoint_v2_kira_world_july_2/build/private_review/rebuild_square_1_1_PRIVATE_REVIEW.mp4>)

Listen and look for:

- Robert’s correct voice identity;
- comfortable volume;
- timing, gaps, cutoffs, and pronunciation;
- truthful distinction among completed work, experiments, blockers, and plans;
- correct image identity and chapter placement;
- readable layout in each native format;
- private-review watermarking;
- anything that should be corrected before a later rebuild.

The proof’s read-only verifier passed 1,123 checks. That does not replace
Robert’s listening and visual review.

## Review the concept images

Passed concept-proof folder:

[`Open the passed concept/motion private proof`](<C:/Users/robmc/KiraVideos/StudioOutputs/V2_PrivateTests/20260725_193114_kira_labs_concept_motion_private_proof_v2_concept_motion_pr>)

These links open the actual three native PNGs. The images are linked rather
than copied or embedded in this guide:

- [`Landscape 16:9 concept image — 1920×1080`](<C:/Users/robmc/KiraVideos/StudioOutputs/V2_PrivateTests/20260725_193114_kira_labs_concept_motion_private_proof_v2_concept_motion_pr/visual_candidates/concepts/concept_4c911a00607b/concept_4c911a00607b_landscape_16_9.png>)
- [`Vertical 9:16 concept image — 1080×1920`](<C:/Users/robmc/KiraVideos/StudioOutputs/V2_PrivateTests/20260725_193114_kira_labs_concept_motion_private_proof_v2_concept_motion_pr/visual_candidates/concepts/concept_4c911a00607b/concept_4c911a00607b_vertical_9_16.png>)
- [`Square 1:1 concept image — 1080×1080`](<C:/Users/robmc/KiraVideos/StudioOutputs/V2_PrivateTests/20260725_193114_kira_labs_concept_motion_private_proof_v2_concept_motion_pr/visual_candidates/concepts/concept_4c911a00607b/concept_4c911a00607b_square_1_1.png>)

Each image must visibly retain:

- the truth label `CONCEPT VISUALIZATION`;
- the private-review status;
- the statement that it is not documentary evidence.

Reject or request a rebuild if any disclosure is missing, hard to read, or
could make a viewer think the image is real Kira World footage.

## Review the motion preview

[`Open the silent 1920×1080 still-motion private preview`](<C:/Users/robmc/KiraVideos/StudioOutputs/V2_PrivateTests/20260725_193114_kira_labs_concept_motion_private_proof_v2_concept_motion_pr/build/private_review/concept_motion/concept_4c911a00607b_still_pan_zoom_landscape_16_9_001_landscape_16_9_PRIVATE_REVIEW.mp4>)

This preview is:

- a disclosed concept still;
- animated only by a short pan/zoom or diagram-motion treatment;
- 1920×1080;
- silent, with no audio stream;
- private-review-only;
- not narration;
- not character animation;
- not Kira or resident movement;
- not runtime or virtual-camera footage.

There is no external or AI image generator connected to this alpha. The
concept card is a deterministic offline abstract planning visual made from
Robert-entered project text.

## How the fail-closed concept workflow works

Concept fallback is **off by default**.

Do not turn it on merely because a concept picture would be convenient.

A concept candidate is allowed only if either:

1. the subject is inherently conceptual, such as a future studio that does not
   exist yet; or
2. a documented visual search has been completed and found no usable real,
   local, licensed, EPK-approved, or otherwise approved visual.

If the project already records an eligible real visual, the fallback is
blocked.

### Create a private concept candidate

1. Create or open a private v2 project.
2. Go to the review controls.
3. Leave concept fallback off while real or approved visuals are available.
4. If the subject is inherently conceptual, record that condition.
5. Otherwise, complete and record the visual search and the result that no
   usable real visual was found.
6. Enable concept fallback.
7. Select the chapter.
8. Enter a factual title, description, and visual direction.
9. Choose the truthful label:
   `CONCEPT VISUALIZATION`, `PLANNED FEATURE`, or
   `SIMULATED DEMONSTRATION`.
10. Create the private candidate.
11. Inspect landscape, vertical, and square versions.
12. Keep rights as unknown/private-review-only until an actual rights decision
    is recorded.
13. Approve, reject, replace, or request corrections. Do not publish.

### Make a bounded motion preview

1. Select an already disclosed concept candidate.
2. Choose a short still pan/zoom or diagram-motion treatment.
3. Render only to the private-review folder.
4. Confirm the disclosure remains visible throughout.
5. Confirm the result is silent unless a separately approved later workflow
   intentionally adds reviewed narration.
6. Confirm the file does not imply character, resident, or runtime movement.
7. Review it before reuse.

## Status labels Robert should expect

| Label | Meaning |
|---|---|
| Passed automated test | Code or artifact passed a bounded automated check |
| Passed private proof | A private artifact decoded and met the stated machine-checkable conditions |
| Awaiting Robert review | Robert has not yet approved what he sees or hears |
| Rights unknown | Possession of the file is not permission for public use |
| Private-review-only | The artifact must not be treated as a clean public final |
| Blocked | A required integration, source, permission, or review is absent |

## What is not available yet

This alpha does not provide or prove:

- an AI or external concept-image generator;
- character or body animation;
- Kira facial or lip animation;
- Kira World runtime capture;
- autonomous virtual cameras;
- resident activation or embodiment;
- EPK.TV login;
- complete live web research or automatic fact verification;
- automatic rights clearance;
- a future 3D Kira Video Lab;
- clean-final approval;
- upload or publication.

Nothing should upload automatically. No Kira activation is needed to review
the files in this guide.

## Historical aborted proof — do not use

Do not review or approve this historical 805-byte aborted folder:

`C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests\20260725_192527_kira_labs_concept_motion_private_proof_v2_concept_motion_pr`

The passed proof is the later folder beginning with `20260725_193114`.

## Suggested review notes

For each artifact, Robert can record:

- `Approve for continued private development`
- `Reject`
- `Replace visual`
- `Correct factual wording`
- `Correct crop or layout`
- `Correct voice, volume, timing, or pronunciation`
- `Keep private pending rights`

Approval for continued private development is not the same as rights approval
or public-release approval.

## Roll back to the safe state

The v1.9 installation is still active, so the safest rollback is simply to
close v2 staging and use:

`C:\KiraVideos\VideoStudio`

If the staged source itself needs restoration, preserve the failed copy and
restore from:

`C:\KiraVideos\Backups\KiraLabsVideoStudio_v2_alpha1_checkpoint_20260725_203101`

Verification record:

`C:\Users\robmc\Kira\Data\codex_reports\20260725_kira_labs_video_studio_v2_alpha1_backup_verification.json`

Do not copy v2 files into v1.9. Do not overwrite
`C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests` with an older output
backup. Preserve rejected and aborted proof folders as inactive audit history.

Full checkpoint details:

[`KIRA_LABS_VIDEO_STUDIO_V2_ALPHA1_CHECKPOINT_20260725.md`](<C:/Users/robmc/Kira/System/Docs/KIRA_LABS_VIDEO_STUDIO_V2_ALPHA1_CHECKPOINT_20260725.md>)
