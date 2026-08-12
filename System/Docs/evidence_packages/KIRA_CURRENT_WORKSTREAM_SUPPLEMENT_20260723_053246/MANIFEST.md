# Manifest — Kira current-workstream supplement

Package path:
`System/Docs/evidence_packages/KIRA_CURRENT_WORKSTREAM_SUPPLEMENT_20260723_053246`

Created: 2026-07-23 05:32:46 America/New_York

## Scope

This supplement preserves three evidence boundaries requested before further
Video Studio work:

1. The complete inactive R4-v10 adult-surface/neck-transition directory,
   including the Blend and renders.
2. The later eye-v3.3 browser evidence directory.
3. The fresh non-activating eye-v3.3 validation directory and dated report
   produced while this supplement was still unsealed.
4. Recovery/status pointer metadata for the reversible R6 selection and for
   rejected/inactive R4-v8 and R4-v9 states.

It supplements rather than replaces:

`System/Docs/evidence_packages/KIRA_CURRENT_WORKSTREAM_SAFE_CHECKPOINT_20260723_034919`

The earlier package was not changed.

## Payload totals

- Copied payload files: **42**
- Copied payload bytes: **154,607,266**
- Source/copy hash matches: **42**
- Source/copy hash mismatches: **0**

The payload is the complete `preserved/` tree. `README.md`, `MANIFEST.md`,
`COPY_VERIFICATION.tsv`, and `SHA256SUMS.tsv` are package-authored seal/index
files and are not included in the copied-payload totals.

## Bundle inventory

| Package-relative directory | Source | Files | Bytes |
|---|---|---:|---:|
| `preserved/r4_v10_candidate` | `Data/avatar_builder_workspace_tests/kira_r7_adult_surface_trial_20260722/reconstructed_neck_surface_r4_v10` | 21 | 150,298,178 |
| `preserved/eye_v3_3_browser_evidence` | `Data/world_tests/kira_socket_eye_v3_3_20260722/browser` | 6 | 2,074,877 |
| `preserved/eye_v3_3_fresh_validation_ephemeral_20260723_0554` | `Data/world_tests/kira_socket_eye_v3_3_20260722/fresh_validation_ephemeral_20260723_0554` | 6 | 2,151,372 |
| `preserved/runtime_recovery_metadata` | Three pointer/rollback JSON files under `Avatar/state/body_selections` | 3 | 7,646 |
| `preserved/candidate_status_evidence` | R4-v8/R4-v9 evidence plus three dated authority/validation snapshots | 6 | 75,193 |

## Copy method and verification

- Directory payloads were copied with Windows `robocopy`; exit code `1`
  indicated successful copies with new destination files.
- Individual metadata/status files were copied with PowerShell `Copy-Item`.
- SHA-256 and byte counts were calculated independently for each source and
  destination.
- Every comparison is recorded in `COPY_VERIFICATION.tsv`.
- Every copied payload checksum is recorded in `SHA256SUMS.tsv`.

## Truth and authority rules

- No evidence capture in this package is an activation or promotion.
- Eye-v3.3 browser evidence is passed technical/visual evidence awaiting
  Robert's review, not owner approval.
- The fresh validation records 103 unit tests, the eye browser smoke and the
  Home World production build passing without activation. It remains
  automated evidence, not Robert's visual or listening approval.
- R4-v10 is an inactive Blend awaiting Robert review; it is not a final body,
  has no GLB/binding/promotion, and does not prove complete adult anatomy.
- R4-v8 and R4-v9 are rejected and inactive under the newest copied authority
  snapshot. Older machine evidence remains preserved without alteration.
- R6 remains a reversible owner-review selection. Permanent promotion is not
  authorized.
- The original generic temporary body remains unchanged at its original path
  and exact pre-trial backup.
- No rejected candidate binary was copied into this package. Only evidence and
  status metadata for rejected revisions was preserved.
- No Kira activation, life loop, publishing, upload, deletion or runtime
  mutation occurred while creating this supplement.

## Important external hashes

These are recovery pointers, not copied payload entries:

| Asset | SHA-256 |
|---|---|
| Original runtime/fallback body and exact pre-R6 backup | `3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e` |
| R6 reversible-review candidate | `ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77` |
| Eye-v3.3 staged/public GLB | `b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5` |
| `Restore_Kira_Pre_R6_Live_Body.bat` | `5bf59612a540a664e4be1427a86f65122d1eed3ced3a59af49fd06f26f70df2b` |

## Rollback boundary

The genuine pre-R6 recovery authority is:

`Avatar/state/body_selections/backups/kira_pre_r6_live_trial_20260719_001839/rollback_manifest.json`

Read-only verification:

```powershell
py tools\restore_kira_pre_r6_live_body.py --verify-only
```

Actual rollback was not run. It requires Kira inactive and all related World
Shell processes closed. Use `Restore_Kira_Pre_R6_Live_Body.bat` only after a
fresh current-state backup. This supplement is evidence and does not itself
perform restoration.
