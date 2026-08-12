# Kira Labs Video Studio v2 staging status

Date: 2026-07-23  
Version inspected: `2.0.0-alpha.1`  
Staging root: `C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1`  
Status: **alpha staging only; not approved as a replacement for the active studio**

> **Historical checkpoint:** This July 23 status is superseded for current v2
> staging details by
> `System/Docs/KIRA_LABS_VIDEO_STUDIO_V2_POST_HARDENING_SAFE_CLOSEOUT_20260726.md`,
> `Data/codex_reports/20260726_kira_labs_video_studio_v2_post_hardening_safe_closeout.md`,
> and
> `System/Docs/evidence_packages/KIRA_LABS_VIDEO_STUDIO_V2_ALPHA1_POST_HARDENING_CHECKPOINT_20260726_010949/`.
> Keep this file as point-in-time history. Active v1.9 remains authoritative
> and v2 remains isolated, private, and unapproved for replacement.
> Current automation is 142/142 passed; the fresh real proof is
> `20260725_234948_...` and the fresh concept proof is `20260725_233935_...`.
> Also read
> `System/Docs/KIRA_LABS_VIDEO_STUDIO_VIRTUAL_PRODUCTION_DIRECTION_20260725.md`
> before future animation or virtual-production implementation.

## Safety and authority

- The active installation remains `C:\KiraVideos\VideoStudio` (v1.9).
- Nothing in this v2 pass renamed, deleted, replaced, or migrated the active v1.9 installation.
- Kira was not activated and no Kira life loop was started for this work.
- No file was uploaded or published. The v2 schema, workflow, interface, and future contract expose no automatic publication action.
- Rejected eye, body, movement, mouth, and media candidates remain inactive. The current R6 Kira body remains recoverable.
- This document describes verified staging behavior. It does not promote an experiment to working status and does not override the sealed Kira body/workstream checkpoint.

Current Kira workstream authority remains:

- `System/Docs/KIRA_CURRENT_WORKSTREAM_SAFE_CHECKPOINT_20260723.md`
- `Data/codex_reports/20260723_kira_current_workstreams_final_checkpoint_and_v2_gate.md`

## Stage status

| Area | Status | What is proven | What is not yet proven |
|---|---|---|---|
| Schema, presets, and v1.9 import | **PASSED (automated)** | Versioned project schema, ten distinct presets, nine-stage workflow, three native output formats, and read-only legacy import validation | Robert has not approved migration or replacement |
| Research and fact sheets | **PASSED (offline automation)** | Source records, named attribution, claim classification, fact strictness, deduplication, explicit online opt-in, and unsupported-claim omission | A complete current-news private-review production with live sources is still pending |
| Visuals and rights | **PASSED (offline automation)** | Manifest fields, failed-placeholder quarantine, identity mismatch blocking, protected-region crops, permission tracking, private-review separation, and clean-final rights gate | EPK.TV authenticated retrieval is not implemented; automatic face detection and a real multi-source visual review remain pending |
| Script, slides, voice, cache, captions, and MP4 assembly | **PASSED (automated/private fixture)** | Preset-specific scripts, native layouts, slide validation, narration cache/reuse, fail-closed approved-voice binding, SRT output, ffmpeg MP4 assembly, muted source-video audio, and clean-final gates | Live Chatterbox inference with Robert's approved voice was not run; the MP4 proof used a synthetic sine-wave test backend in a temporary test directory |
| Kira World Update mode | **PASSED (scanner automation); AWAITING CURATION/REVIEW** | Reads local handoff/System Docs/Codex reports, records source line and authority rank, separates completed/experiment/rejected/blocker/next/superseded, and separates automated/Codex/Robert/document observers | The broad scan is not a curated update, script, slide set, or persistent private-review MP4 |
| Interview mode | **PASSED (contract automation); BLOCKED for real interview** | Separate interviewer/guest identities, approved Chatterbox voice gates, disclosure, refusal/disagreement/question actions, verified-context abstention, stop control, and private-context separation | No synthetic person was activated; no real synthetic interview was recorded or rendered |
| Desktop interface and launcher | **PASSED (headless automation); AWAITING ROBERT VISUAL REVIEW** | One interface exposes presets, controls, stages, review actions, and no publication control. The staging launcher uses `pyw`, `pythonw`, or `py` without PowerShell, elevation, or a second batch file | A visible GUI and ordinary double-click owner walkthrough have not been completed; production buttons are not yet connected to a complete project service |
| Active installation replacement | **BLOCKED** | The staging application is isolated and rollback is simple | Replacement is forbidden until a real private project proves research, script, visuals, approved voice, review, render, correction, and rebuild, and Robert approves it |

## Automated evidence

Commands run from the staging root:

```text
C:\Python314\python.exe -m unittest discover -s tests -v
```

Result: **86 tests passed; 0 failures; 0 errors**.

Test-file counts:

- `tests\test_foundation_safety.py`: 8
- `tests\test_media_pipeline.py`: 9
- `tests\test_online_acquisition.py`: 12
- `tests\test_research_facts_visuals.py`: 22
- `tests\test_stage1_schema_presets.py`: 10
- `tests\test_ui_launcher.py`: 10
- `tests\test_workflow_render_voice_modes.py`: 15

Additional checks:

```text
C:\Python314\python.exe -m compileall -q kira_video_studio app.py
```

Result: **PASSED** (exit code 0).

```text
C:\Python314\python.exe app.py --self-test
```

Result: **PASSED**. The self-test reported:

```json
{
  "application": "Kira Labs Video Studio",
  "errors": [],
  "mode": "staging_private_review",
  "output_profiles": 3,
  "presets": 10,
  "publication_enabled": false,
  "status": "PASSED",
  "version": "2.0.0-alpha.1",
  "workflow_stages": 9
}
```

## What exists in staging

The verified backend covers:

- versioned projects and read-only v1.9 import;
- preset-specific script sections;
- deterministic offline research fixtures and explicit opt-in online discovery;
- fact sheets and claim-to-source records;
- visual candidates, rights state, permission state, and placeholder rejection;
- native 16:9, 9:16, and 1:1 slide layouts;
- approved-voice validation with no silent generic fallback;
- chapter-level slide and narration cache keys;
- private-review watermarking and clean-final gates;
- captions and ffmpeg MP4 assembly;
- Kira World Update authority scanning;
- consent-preserving interview records;
- a data-only future Kira World Video Lab integration contract;
- one desktop interface and a non-elevated staging launcher.

## Important limits

- “Tests passed” does not mean the application is production-ready.
- Online research is gated and was not used to publish or produce a final current-news video.
- EPK.TV login, credential storage, and authenticated download are not implemented. Passwords must not be placed in project JSON or handed to the future 3D client.
- Cropping protects explicitly supplied face/object regions; there is no automatic face detector yet.
- The Kira Update scanner produced a broad smoke result of 281 documents and 4,701 evidence lines. Its classification is mechanical and requires curation. It is not evidence that every line is current or video-worthy.
- No real interview was conducted.
- The real approved Robert Chatterbox voice was validated as a binding, but live inference was not run in the v2 proof. The temporary MP4 test used a clearly synthetic sine backend.
- The GUI test was headless. Robert still needs to inspect layout, launcher behavior, and workflow clarity.
- The current interface does not yet have a complete production service behind every stage/review button.
- No clean public final has been approved or generated as a publishable result.

## Preserved backups

Active v1.9 backup:

```text
C:\KiraVideos\Backups\VideoStudio_v1_9_pre_v2_20260723_040331
```

- 118 files
- 13 directories
- 21,953,950 bytes
- 89 alternate data streams recorded
- aggregate SHA-256: `7e36756a953a266d0adf52343b7271c0306bcdd3908508c1567615ffc58a5460`
- ACL application was blocked; ACL manifests were retained.

External outputs backup:

```text
C:\KiraVideos\Backups\StudioOutputs_pre_v2_20260723_073835
```

- 497 files
- 126 directories
- 315,717,929 bytes
- 66 alternate data streams recorded
- payload seal: `36c0559b6812855931f45f9b1c307d82b318f4a2fc8025f74becf0dba38e7cd3`
- metadata seal: `7916d82a0a5533aa72ca39e69338429ae9ab6ff853cb1dbd2c61f9f8830d80be`
- ACL application was blocked; ACL manifests were retained.

Current R6 body recovery hash:

```text
ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77
```

## Selected staging hashes

| File | SHA-256 |
|---|---|
| `app.py` | `5c053cd51f181999e3da50316e8aba4357eb86e89ad3a975af9f94fdb20c223e` |
| `START_KIRA_LABS_VIDEO_STUDIO.bat` | `b9c8048c511d9dd21f389acc1067558767b0835ad7b3c737ab5816ea65fba845` |
| `START_KIRA_LABS_VIDEO_STUDIO.pyw` | `69b176af80c1d4e855e259d9d8111ff86a5f9d0d2271dbc428867ae3e33f813a` |
| `kira_video_studio\schema.py` | `4df36243ef13ad2fe84b198d79c1a432578e3eb557d85f51829caeaede71b35e` |
| `kira_video_studio\online_research.py` | `3ab891a6f3c8a44718aae8b6e1e8b7ac3e1800f279d4d1e7113d2abd7383ebde` |
| `kira_video_studio\visual_acquisition.py` | `87d92a20ddb9cb951d786c3dbb14dc544661051dacbf323012983dacfc88ce02` |
| `kira_video_studio\media_builder.py` | `7ad24c9e425576afa2504879d67c07e5755d796f34ae8b274c2fbb376a917379` |
| `kira_video_studio\update_mode.py` | `2ccd77862f70fe36a86c7d91f7336f00bfc899b9acf2588fa7a148dcf1a8b613` |
| `kira_video_studio\interview.py` | `194da8656543fdd6e2cab098451ba55e44359e9346b887399c19226bef16ed72` |
| `kira_video_studio\future_contract.py` | `cc21f56d4cb8216a70818314ab8a2abdc38f91111f1e1572dd6cc57093c32806` |
| `kira_video_studio\ui.py` | `53321039126526df3e6fcb55187766ac989e5fef5b877a538fe8627fc31bf053` |
| `voice\approved_reference.wav` | `761458a0fe9c5da1c2671faa738c1e329336630cd47138a4e738f7de2030542b` |

The per-stage reports in `Data/codex_reports` record the complete relevant file/test hashes.

## Launch and review

The staging launcher is:

```text
C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1\START_KIRA_LABS_VIDEO_STUDIO.bat
```

This is for private staging review only. It must not replace Robert's active v1.9 shortcut yet.

## Rollback

Because v2 is isolated, the immediate rollback is:

1. Close the staging application.
2. Do not copy staging files over `C:\KiraVideos\VideoStudio`.
3. Continue launching the active v1.9 installation.
4. If the staging tree must be removed, first preserve its reports/evidence and obtain Robert's approval; then remove only the staging tree.
5. If a v1.9 restore is ever needed, restore the sealed backup into a new verification directory first, verify manifests/hashes, and only then plan an approved replacement. Do not overwrite the active installation blindly.

## Promotion gate

Keep v2 in staging until all of the following are true:

1. ordinary double-click and visible GUI review pass;
2. one small real private-review project completes research, fact sheet, script, visuals, approved Robert narration, slides, captions, and MP4;
3. Robert corrects at least one script or visual and the project rebuilds without regenerating approved narration;
4. rights and clean-final gates fail closed and then pass only after explicit approvals;
5. no upload or publication occurs;
6. Robert reviews the evidence and explicitly approves replacement.
