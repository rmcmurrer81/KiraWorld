# Kira Labs Video Studio v2 post-hardening safe closeout

Date: 2026-07-26  
Version: `2.0.0-alpha.1`  
Status: `private_staging_checkpoint_awaiting_robert_review`  
Decision: **safe to stop; do not promote or replace v1.9**

## Current authority

This document is the current Video Studio v2 checkpoint/status authority. It
supersedes older v2 paths, counts, hashes, and test totals where they conflict.
The older documents and evidence packages remain preserved as point-in-time
history.

Read with:

1. `HANDOFF_FOR_NEXT_CODEX_SESSION.md`
2. this document
3. `System/Docs/KIRA_LABS_VIDEO_STUDIO_INSTALLATION_AUTHORITY_20260726.md`
4. `Data/codex_reports/20260726_kira_labs_video_studio_v2_post_hardening_safe_closeout.md`
5. `System/Docs/evidence_packages/KIRA_LABS_VIDEO_STUDIO_V2_ALPHA1_POST_HARDENING_CHECKPOINT_20260726_010949/checkpoint_summary.json`
6. `System/Docs/KIRA_LABS_VIDEO_STUDIO_VIRTUAL_PRODUCTION_DIRECTION_20260725.md`

Do not edit these evidence-linked sources merely to refresh wording. The fresh
real proof depends on their exact bytes:

- `System/Docs/KIRA_LABS_VIDEO_STUDIO_CURRENT_INSTALLATION_v1_9.md`
- `Data/codex_reports/20260723_kira_current_workstreams_final_checkpoint_and_v2_gate.md`
- `Data/codex_reports/20260723_kira_current_workstreams_fresh_validation.md`

## Closeout decision

The isolated v2 stage is internally consistent and recoverable. It has a fresh
verified backup, a post-hardening evidence seal, a fresh real Kira World Update
private proof, and a fresh disclosed concept-motion private proof. Automated
and read-only verification passed. Robert's visible launcher, visual,
listening, factual, and rights reviews remain required.

No clean final was built. No public-release approval was granted. Nothing was
uploaded or published. The active v1.9 installation was not changed.

## What was completed

- Hardened concept fallback eligibility and project-root containment.
- Kept concept truth and rights disclosures fixed on screen while motion zooms.
- Added a 15-second, 450-frame disclosure regression.
- Hardened standard-user launcher selection and diagnostic fallbacks.
- Ran the complete 142-test suite plus setup, launcher, compile, application
  self-test, start probe, active-v1 manifest, proof, decode, and rebuild checks.
- Rebuilt and sealed a fresh real Kira World Update private proof.
- Rebuilt and sealed a fresh concept image and still-motion private proof.
- Visually inspected all three native concept layouts and representative
  start, middle, and end motion frames.
- Created an exact post-hardening staging backup and verified it independently,
  including alternate data streams.
- Sealed active-v1, staging, backup, proof, R6-recovery, runtime-inactive, and
  private-only state in one post-hardening evidence package.
- Recorded the virtual-production and animation direction without implementing
  a heavy 3D studio or beginning a new production.

## Exact changes after the earlier checkpoint and independent audits

Comparison base:

`C:\KiraVideos\Backups\KiraLabsVideoStudio_v2_alpha1_checkpoint_20260725_203101`

Current stage:

`C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1`

No authored files were removed. One regression file was added and twelve files
changed:

| Staged relative path | Change | SHA-256 |
|---|---|---|
| `tests/test_launcher_hardening.py` | added | `1af8e1122fbb389183a30a4e5877aa11984578043a5a2fecd96cc3dd30b6d1c0` |
| `CHECK_SETUP.bat` | changed | `d7a67ce85708f37c486c6536c0b9dff41b5e43601f0d73fa043a0af788457b08` |
| `kira_video_studio/concept_renderer.py` | changed | `dd612a9e6883615b5a065437940887a65dfb823bf9294e660c8b1e73ffbdabe8` |
| `kira_video_studio/motion_preview.py` | changed | `781f423177040974a9f548ebe96787e72ef51b8958becde5fc103f7c6d3558a8` |
| `kira_video_studio/project_service.py` | changed | `2844f704e702623e24295a8c9a86d729f246c0e2a1530eaa51716ea8da291823` |
| `kira_video_studio/ui.py` | changed | `f2222e414b9ff2f42c60e5f3387158b5f2796c9ffa055d8ea088cd367314c7a6` |
| `kira_video_studio/visual_truth.py` | changed | `b3c949ebbf329e85f8e6d96ed7841545f763ccd9efcb7517be106e200b2ab8f0` |
| `RUN_SELF_TEST.bat` | changed | `ab53f5f275d1f6c6bb4ed493d77f2dd8bed792f7d869761d8130372e9d249fb1` |
| `START_KIRA_LABS_VIDEO_STUDIO.bat` | changed | `367b857ac1da49198ad33537306d7af4d396c5fb3d2ba6242891252aaac714aa` |
| `START_KIRA_LABS_VIDEO_STUDIO.pyw` | changed | `0ce8fa25c1d3f73ae800776bfba8cf8511a63b28dcb053dee0036fdc3d36ea48` |
| `tests/test_concept_animation_planning.py` | changed | `ebe7af4c023cc74f9d4a565608bbc17368a2ff1b1e8d8cd6d0de978f791fb9d1` |
| `tests/test_concept_motion_rendering.py` | changed | `6c5d5fb111b35e8b54eed515e809475ee8b3e2a042e83a7d3593a02490cfe07f` |
| `tests/test_ui_launcher.py` | changed | `17dd070911f29744c70d3e340825b02f48a8662b48239ad36da024103b363ca6` |

The nonconcept fallback now requires an explicit opt-in, a nonblank query, and
linked in-project search evidence or a passed Research stage with a real,
nonempty artifact. Evidence must remain within the project root. The launcher
now probes Python 3.11 or newer plus Tk, rejects WindowsApps aliases, operates
as a standard user, and falls back to a readable failure log under:

`%LOCALAPPDATA%\KiraLabs\VideoStudio\2.0.0-alpha.1\launcher_failure.log`

## Latest tests and independent read-only audit

| Check | Result |
|---|---|
| Complete unit suite | **PASSED: 142/142** |
| Focused concept/evidence suite | **PASSED: 42/42** |
| Focused launcher-hardening suite | **PASSED: 18/18** |
| Python compile | **PASSED** |
| Application self-test | **PASSED** |
| Staging start probe | **PASSED** |
| `CHECK_SETUP.bat` | **PASSED, exit 0** |
| Active-v1 manifest check | **PASSED: 51/51** |
| Fresh real-proof verifier | **PASSED: 1,117 checks** |
| Fresh concept proof | **PASSED_PRIVATE_REVIEW_PROOF** |
| Actual concept-motion frame disclosure | **PASSED: 60/60 decoded frames** |
| Native concept still dimensions/disclosure | **PASSED: 3/3** |
| Visible ordinary double-click GUI | **AWAITING ROBERT REVIEW** |

The read-only audit found no technical blocker to this private staging
checkpoint. It did not grant promotion, clean-final, rights, or publication
approval.

## Fresh real Kira World Update proof

Root:

`C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests\20260725_234948_kira_world_july_23_2026_engineering_checkpoint_v2_kira_world_july_2`

The proof contains 5 chapters, 15 slides, 3 sources, 5 visuals, 6 WAV files,
and 3 private-review MP4 files. It uses Robert's approved Chatterbox reference
with generic fallback disabled, `-9.5 dB` gain, unchanged pitch, and 6/6
narration cache hits during the visual-only rebuild.

Rebuilt private-review video hashes:

- landscape: `a75acfc296e318e074fe72bb60100653be42ad56550eb8bc0c33b3e5ca2aef7c`
- vertical: `f75c43ad1fc9a773e707bf367467568299c1527d4738b6444e2581b40896b3ce`
- square: `ceb26c7682da726034f20184c976eaea6b3699542aefcb0bae7ebcd06dbd778b`
- SRT: `16e20461e4c886812dbe5d8c45ebbea9b5b9ca22981c824d58199f77b4097ce7`
- narration-reuse proof: `60b0e9747dd170f14801d4a946f088b4dc09e861a502b631012a7a9561e05942`
- project-service rebuild proof: `e56f70ed85dad24516dd1e641d267be707a517707cbcfa97a0bbea080ac436be`

Sealed proof inventory: 110 files, 39,295,402 bytes, seal-method tree SHA-256
`3ade04a8eef2c285e82605681b4199c04834f6c5c969be99434cf2f07d4e76af`.

The earlier
`20260723_111612_kira_world_july_23_2026_engineering_checkpoint_v2_kira_world_july_2`
proof is historical. A source it intentionally hash-binds changed, so the
current verifier correctly rejects it. Preserve it; do not use it as current
proof.

## Fresh concept and concept-motion proof

Root:

`C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests\20260725_233935_kira_labs_concept_motion_private_proof_v2_concept_motion_pr`

Verified boundary:

- truth label: `CONCEPT VISUALIZATION`;
- permission: `private_review_only`;
- rights review: `unknown`;
- clean final: false;
- publication: false;
- runtime capture: false;
- resident activation: false;
- external or AI image generation: false;
- motion: silent two-second still-image pan/zoom only, not character animation.

Artifact hashes:

- landscape PNG: `aaddf553d66afe7836a954f45471f9352942468d5bff327731e537d67f7a6d05`
- vertical PNG: `c9610dcf1cb8d463ae78efc9e2cf2bb46935cab1384df430db51595dd13bb9df`
- square PNG: `57a450336a65b1e8e4215eaf2823898e308005256fc5c98e62cbc3cf1c6cdd59`
- landscape motion MP4: `08119c6befcd2b89b77c0ef9fb05e9179cd90d0aad05364ded34c49018014060`

Sealed proof inventory: 10 files, 659,962 bytes, tree SHA-256
`4faa49988f9bcd4a9e817f2ad1d395318d3672a6385a407fca36e14f6d73f639`.

The earlier `20260725_193114_...` concept proof and aborted
`20260725_192527_...` attempt are historical and superseded. Preserve them.

## What Codex visually inspected

Codex inspected:

- the actual native landscape, vertical, and square concept PNGs;
- representative start, middle, and end frames decoded from the actual motion
  MP4;
- layout readability, clipping, persistent top truth disclosure, and bottom
  rights/private-review disclosure.

Inspection evidence:

`C:\Users\robmc\Kira\Data\codex_reports\20260725_v2_post_hardening_visual_validation`

Result: no clipping or disclosure loss was observed. The path line appears
white/off-white rather than the requested warm gold. That is a pending
aesthetic correction, not a safety or truth-disclosure failure.

Robert has not yet approved the concept layouts, motion, real-update visuals,
narration, facts, rights, or visible launcher behavior.

## Current backup and evidence seal

Current exact post-hardening backup:

`C:\KiraVideos\Backups\KiraLabsVideoStudio_v2_alpha1_post_hardening_20260726_005514`

Independent verification:

`C:\Users\robmc\Kira\Data\codex_reports\20260726_kira_labs_video_studio_v2_alpha1_post_hardening_backup_verification.json`

Verification result:

- 66 authored files and 6,289,013 bytes in both source and backup;
- no missing, extra, or mismatched authored files;
- seven alternate data streams matched;
- verifier-method source and backup tree SHA-256
  `c650af634cef2e77ab5ecb7c8ad627d51fe281d31f44b6a5e3ac7ff3c9aaaf3b`;
- seal-method source and backup tree SHA-256
  `5b1362ff528a273495dd7f5428f94c6431009de3798bf616affbea2e3d566599`;
- verification-record SHA-256
  `799aa41aa2eb09adba55c2877334b922715401e44de3c89ea222ee942004cf1f`.

Current post-hardening evidence seal:

`C:\Users\robmc\Kira\System\Docs\evidence_packages\KIRA_LABS_VIDEO_STUDIO_V2_ALPHA1_POST_HARDENING_CHECKPOINT_20260726_010949`

Primary summary:

`C:\Users\robmc\Kira\System\Docs\evidence_packages\KIRA_LABS_VIDEO_STUDIO_V2_ALPHA1_POST_HARDENING_CHECKPOINT_20260726_010949\checkpoint_summary.json`

The seal was created at `2026-07-26T05:11:12.644334+00:00`.

Documentation-closeout evidence addendum:

`C:\Users\robmc\Kira\System\Docs\evidence_packages\KIRA_LABS_VIDEO_STUDIO_V2_SAFE_CLOSEOUT_DOCS_20260726_020427`

This addendum hashes the final handoff, authority, status, index, guide, and
Codex-report documents. It does not modify or replace the sealed staging
evidence.

Historical, superseded checkpoint assets that must remain preserved:

- backup:
  `C:\KiraVideos\Backups\KiraLabsVideoStudio_v2_alpha1_checkpoint_20260725_203101`
- verification:
  `C:\Users\robmc\Kira\Data\codex_reports\20260725_kira_labs_video_studio_v2_alpha1_backup_verification.json`
- seal:
  `C:\Users\robmc\Kira\System\Docs\evidence_packages\KIRA_LABS_VIDEO_STUDIO_V2_ALPHA1_CHECKPOINT_20260725_203723`

## Installation, activation, and publication facts

- Active installation: v1.9 at `C:\KiraVideos\VideoStudio`.
- Active v1.9 changed by this closeout: **no**.
- Active-v1 inventory: 118 files, 21,953,950 bytes.
- Active-v1 tree SHA-256:
  `7e36756a953a266d0adf52343b7271c0306bcdd3908508c1567615ffc58a5460`.
- Active-v1 canonical POSIX tree SHA-256:
  `7bcfc1bcc58cf3c93658a4dbcd9e3bcc38c8f908cda3ab7fe0c88417879ea891`.
- Kira activated by this staging, testing, backup, seal, or closeout work:
  **no**.
- Another synthetic person activated by this work: **no**.
- Runtime at seal: no active candidate and no active conversation mode.
- The seal does not claim Robert did not activate Kira earlier in the day.
- Uploaded by this work: **nothing**.
- Published by this work: **nothing**.
- Automatic publication available in v2 staging: **no**.

The evidence-linked v1.9 authority document was intentionally left byte
unchanged so the fresh real proof remains valid. Its SHA-256 is
`b9c2cf077e7294fcc15d6186a28d8e1b4dcb5b629eaa8e0b52cad762dfacbcbb`.
The dated installation-authority supplement records the current relation
between active v1.9 and unapproved v2 staging.

## Pass, unreviewed, and incomplete matrix

| Item | Closeout state |
|---|---|
| Concept evidence gate and project containment | **PASSED automated/audit** |
| Fixed concept disclosures during motion | **PASSED automated/audit** |
| Standard-user launcher logic | **PASSED automated/audit** |
| Visible ordinary double-click launch | **UNREVIEWED by Robert** |
| Fresh real Kira update proof | **PASSED verifier; UNREVIEWED by Robert** |
| Fresh native concept stills | **PASSED verifier/Codex visual; UNREVIEWED by Robert** |
| Concept still-motion preview | **PASSED verifier/Codex visual; UNREVIEWED by Robert** |
| Robert voice identity/volume/timing/pronunciation | **UNREVIEWED by Robert for current proof** |
| Factual and rights review | **UNREVIEWED by Robert** |
| Vertical and square concept motion | **NOT IMPLEMENTED** |
| External/AI concept-image generation | **NOT IMPLEMENTED** |
| Character animation | **NOT IMPLEMENTED** |
| Conversational video editor | **DEFERRED to next thread** |
| TemporaryAI repairs | **DEFERRED to next thread** |
| Phone request system | **DEFERRED to next thread** |
| Two new video productions | **DEFERRED to next thread** |
| Clean final, promotion, or publication | **BLOCKED pending later gates and Robert approval** |

## Rollback

Safest rollback from v2 staging:

1. Do not alter `C:\KiraVideos\VideoStudio`; it is already the active v1.9
   installation.
2. Close any staged v2 process.
3. Preserve the current stage and proof folders for diagnosis.
4. Copy the post-hardening backup to a new recovery directory; do not restore
   over the current stage in place.
5. Compare the recovery copy against
   `20260726_kira_labs_video_studio_v2_alpha1_post_hardening_backup_verification.json`.
6. If the post-hardening state itself is under investigation, use the older
   `20260725_203101` backup only as the pre-hardening historical baseline.
7. Never copy v2 over active v1.9 without a future explicit promotion plan,
   fresh proof, rollback rehearsal, and Robert approval.

## Safest first steps for the next Codex thread

1. Read the six current-authority items listed at the top of this document.
2. Read the three evidence-linked sources without editing them.
3. Inspect the post-hardening seal summary and backup-verification JSON before
   changing staged files.
4. Confirm active v1.9 still matches its preserved 118-file seal.
5. Confirm the stage still matches the post-hardening backup before new work.
6. Ask Robert for the pending visible/listening/visual/factual/rights review,
   or continue only with a separately authorized deferred workstream.
7. Keep Kira inactive for automated work, keep R6 recoverable, keep rejected
   candidates inactive, and do not publish.
8. Do not treat the two proof projects as clean finals.

This is the deliberate safe stopping point for this thread.
