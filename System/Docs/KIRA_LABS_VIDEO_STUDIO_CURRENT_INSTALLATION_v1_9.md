# Kira Labs Video Studio current installation — v1.9

Status: preserved working installation; complete pre-v2 backup passed; no staged replacement is approved yet. The separate v2 alpha checkpoint dated 2026-07-25 does not change this authority.

## Active installation

- Path: `C:\KiraVideos\VideoStudio`
- Version label: `Kira Labs Video Studio v1.9 - Walkthrough Updates and Read-Only Handoff Sources`
- Ordinary launcher: `C:\KiraVideos\VideoStudio\START_KIRA_LABS_VIDEO_STUDIO.bat`

The prior independent audit established that the BAT does not request
elevation, does not depend on PowerShell, has no `Zone.Identifier`, and passed
a non-administrator launch smoke. The walkthrough path and current project
copy are bounded local inputs. The approved Robert voice remains required;
generic silent/robotic substitution is not an acceptable success condition.

Current independent audit:

`Data/codex_reports/20260722_kira_labs_video_studio_v19_independent_audit.md`

That audit did not run a fresh Chatterbox synthesis or encode a real owner
recording. Those remain separate private-review proof requirements.

## Verified backup

- Backup: `C:\KiraVideos\Backups\VideoStudio_v1_9_pre_v2_20260723_040331`
- Source and backup application files: 118 each
- Source and backup subdirectories: 13 each
- Source and backup application bytes: 21,953,950 each
- Source and backup named NTFS streams: 89 each
- File, directory and named-stream mismatches: 0
- Aggregate source/backup SHA-256: `7e36756a953a266d0adf52343b7271c0306bcdd3908508c1567615ffc58a5460`

The 118-file backup preserves the complete active application tree, including
its projects, settings, source safeguards, generated assets and the approved
Robert voice reference. The external output root
`C:\Users\robmc\KiraVideos\StudioOutputs` remains preserved in place and was
not changed, but it is **not included** in this 118-file application-tree
backup.

A separate verified preservation copy now covers that external output tree:

- Backup: `C:\KiraVideos\Backups\StudioOutputs_pre_v2_20260723_073835`
- Payload: 497 files, 126 directories and 315,717,929 bytes
- Named NTFS streams: 66 streams and 7,236 bytes
- Content/path/stream mismatches: 0
- Canonical payload seal:
  `36c0559b6812855931f45f9b1c307d82b318f4a2fc8025f74becf0dba38e7cd3`
- Metadata seal:
  `7916d82a0a5533aa72ca39e69338429ae9ab6ff853cb1dbd2c61f9f8830d80be`

The separate restore sandbox passed with zero problems. Exact ACL
application remains blocked without elevation; 624 owner/group/DACL SDDL
records were captured, while SACL and ACL restoration remain unproved. See
`Data/codex_reports/20260723_kira_labs_studio_outputs_pre_v2_backup.md`
(SHA-256
`d8230b2d3c325e6c86c3730b3103e07111878f3b8dc4a1c5d87da1127fb585b6`).

Important preserved hashes include:

- `START_KIRA_LABS_VIDEO_STUDIO.bat`: `4c5bff1600fd0feb6a858143ab0faaea2918b99452896615c04014c8899afc62`
- `START_KIRA_LABS_VIDEO_STUDIO.pyw`: `27a381c70f51fa4d22e6adee8b04eef323470c1477229861cd62f94ace1182e3`
- `VERSION.txt`: `b56227c8ae5bf22325556c30895df34bf8fdca4649c3fda65341c230e30eeb82`
- `user_settings.json`: `294d5b977a4029c3dd53df3deac4c7172e67a052f5037e2c2c03e2f7558032a8`
- `voice\approved_reference.wav`: `761458a0fe9c5da1c2671faa738c1e329336630cd47138a4e738f7de2030542b`

Exact ACL application was blocked under the standard-user token. The source
ACL inventory is preserved, while all file data, attributes, timestamps,
directories and named streams were verified. A standard-user restore can
inherit the restore folder's permissions.

Full evidence and non-destructive restore commands:

`Data/codex_reports/20260723_kira_labs_video_studio_v19_pre_v2_backup.md`

That report has SHA-256
`042562a996c92933231d0abce5ebe796448b61df34b27f9a717c7d8865dc4765`.
Its strict restore verifier was executed against the separate, non-active
validation path
`C:\KiraVideos\Backups\VideoStudio_v19_restore_verify_sandbox_20260723_051927`.
The verifier found the exact 118 files, 13 directories, 89 named streams and
10,728 named-stream bytes with zero problems. The sandbox is evidence only;
it is not an approved installation switch. Original ACL application remains
the one blocked item.

## v2 safety boundary

The next Video Studio must be built beside this installation. Until Robert
approves a tested replacement:

- do not overwrite or rename the active v1.9 folder;
- do not delete files from v1.9 merely because a staged build appears newer;
- do not migrate projects/settings destructively;
- do not change or regenerate the approved Robert voice reference;
- do not auto-upload, auto-publish, or log into a third-party account without
  a separate explicit credential and rights workflow;
- do not call the staged application finished because its interface opens.

A staged replacement must prove, with a real private project, research, fact
sheet, preset-specific scripting, visual candidates, approved voice use,
slides, private rendering, corrections and a rebuild that reuses approved
narration. Only after that proof and Robert's approval may a folder switch be
considered.

## 2026-07-25 v2 staging cross-reference

The isolated `2.0.0-alpha.1` staging tree has now completed a real private
Kira World Update proof, narration-reuse rebuild proof, and a separate
persistently labeled concept-card/silent-still-motion proof. Those results
advance the staged replacement, but they do **not** promote it and do not
replace this v1.9 authority.

- Staging:
  `C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1`
- Frozen v2 checkpoint backup:
  `C:\KiraVideos\Backups\KiraLabsVideoStudio_v2_alpha1_checkpoint_20260725_203101`
- Staging/backup canonical tree SHA-256:
  `4d0d9dd1e7484c6b0ce9fb77dc88fdbaabff73fa485903d5e1dbaaa01bd9176b`
- Checkpoint:
  `System/Docs/KIRA_LABS_VIDEO_STUDIO_V2_ALPHA1_CHECKPOINT_20260725.md`
- Illustrated private-review guide:
  `System/Docs/KIRA_LABS_VIDEO_STUDIO_V2_ALPHA1_ILLUSTRATED_GUIDE_20260725.md`
- Evidence package:
  `System/Docs/evidence_packages/KIRA_LABS_VIDEO_STUDIO_V2_ALPHA1_CHECKPOINT_20260725_203723/`

The July 23 external-output backup is an exact historical pre-v2 snapshot.
New private v2 proofs now exist under
`C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests`; therefore the older
`StudioOutputs_pre_v2_20260723_073835` backup must **not** be restored over the
current output root. If historical output recovery is ever needed, restore it
to a separate verification folder and copy only explicitly reviewed files.

Current promotion blockers include Robert's visual/listening review, rights
review, a visible ordinary-double-click walkthrough, and clean-final gate
review. Nothing was uploaded or published, and no clean final was produced.

## Rollback summary

Restore the backup to a new staging directory and verify it against
`_backup_metadata\backup_file_manifest.csv`. Do not copy directly over the
active folder. If Robert approves the verified restore, move the old active
folder to a timestamped safety path and move the verified restore staging
folder into place. Retain the former active folder until launcher, voice,
projects, settings and outputs are reviewed.

Use the exact PowerShell procedure in the backup report rather than an
unverified bulk copy.
