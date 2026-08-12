# Kira current-workstream evidence supplement

Created: 2026-07-23 05:32:46 America/New_York  
Package: `KIRA_CURRENT_WORKSTREAM_SUPPLEMENT_20260723_053246`

## Outcome

This is a non-activating, append-only evidence supplement to the existing
current-workstream safe checkpoint. It preserves evidence that was too large
or too late for the earlier checkpoint package without changing that earlier
package.

- Copied payload: **42 files**
- Copied payload bytes: **154,607,266**
- Source-to-copy SHA-256 comparisons: **42 matched, 0 mismatched**
- Kira activation: **not performed**
- Life loop: **not run**
- Runtime selection or promotion: **not changed**
- Rejected candidates: **not activated and not copied as runnable candidates**
- Existing checkpoint package: **not modified**
- Publishing or uploading: **not performed**

`COPY_VERIFICATION.tsv` records every source-to-copy comparison.
`SHA256SUMS.tsv` seals the 42 copied payload files. The four package-authored
index files are intentionally outside that payload checksum table so the
tables do not attempt to hash themselves.

This package is hash-sealed and intended to be append-only. Windows filesystem
immutability is not asserted.

## Preserved content

| Bundle | Files | Bytes | Purpose |
|---|---:|---:|---|
| `preserved/r4_v10_candidate` | 21 | 150,298,178 | Complete inactive R4-v10 work directory, including the Blend, configuration, logs, reopen verification, manifest, evidence and all rendered review images. |
| `preserved/eye_v3_3_browser_evidence` | 6 | 2,074,877 | Later eye-v3.3 browser evidence JSON and the center/left/right/up/down captures. |
| `preserved/eye_v3_3_fresh_validation_ephemeral_20260723_0554` | 6 | 2,151,372 | Fresh non-activating eye-v3.3 validation evidence and five original-resolution captures generated during the final validation run. |
| `preserved/runtime_recovery_metadata` | 3 | 7,646 | Current runtime-selection pointer, R6 review-staging pointer and genuine pre-R6 rollback manifest. |
| `preserved/candidate_status_evidence` | 6 | 75,193 | R4-v8/R4-v9 machine evidence plus current-authority report snapshots that establish their later rejected/inactive status, R4-v10's review boundary, and the fresh non-activating validation result. |

## Status boundaries

| Item | Status preserved by this package |
|---|---|
| Eye v3.3 | Automated/browser/head-binding/iris-gaze evidence passed to Robert review. Browser captures are evidence, not visual approval. Natural blink remains blocked without approved skinned eyelid geometry. |
| R4-v10 adult-surface and neck-transition candidate | Inactive Blend only. Engineering gates passed; Codex review passed it to Robert review, not to final or promotion. Robert review is pending. There is no GLB export, runtime binding or promotion. Complete adult anatomy remains not proven. |
| R4-v8 | Rejected and inactive under the current safe-checkpoint authority. Its preserved machine evidence records the failed engineering gate and no candidate/live binding. |
| R4-v9 | Rejected and inactive under the later safe-checkpoint authority. Its older machine evidence only reached inactive engineering-pass/visual-pending status; the copied dated authority snapshot records the later rejected/inactive decision. |
| R6 runtime body selection | Reversible owner-review trial selected through metadata; not permanently promoted. The original generic temporary rig remains unchanged and recoverable. |

The dated authority snapshot at
`preserved/candidate_status_evidence/authority_snapshots/20260723_kira_current_workstreams_safe_checkpoint.md`
is the status authority when an older candidate evidence file describes an
earlier intermediate state. The later
`preserved/candidate_status_evidence/authority_snapshots/20260723_kira_current_workstreams_fresh_validation.md`
records a fresh 103-test, browser-smoke and production-build pass without
activation; it does not change any owner-review or promotion boundary.

## Key payload hashes

- R4-v10 Blend:
  `41ce3556beefaba1e8e48224b3af704832d2f5919fefe3eb171ee08714161822`
- R4-v10 `evidence.json`:
  `04580989c19952916d2dc0965c49c816df5d06b7db5c1634b514f759654d5307`
- R4-v10 `manifest.json`:
  `a1db9d5f101d0995937418c8918e52752d7c94dac6b1fce1ce55b5debc66716b`
- Eye-v3.3 browser `evidence.json`:
  `d7604ea60e57f77524e717919af0fa6afc1675a9089a192cf93c91d9e5faa53d`
- Fresh eye-v3.3 validation `evidence.json`:
  `4144e71106b7924bf820a60f7c55b15f02dcb0cf80789684872356ac2e503f83`
- Fresh current-workstream validation report:
  `fcd7ba04bbc85a290ee7f2964197383cc2855ab11ea7a5cdb07d643c825bbe3a`
- Eye center capture:
  `c438a4abb5a4f8f3e6c3e3a34a1d5171f23b7f0ae61fe3359058acf134fb26a8`
- Runtime-body-selection metadata:
  `245668981c10ba82399c8685f77b4ad111c26dbb5ccc4d9bad729eef2029f94b`
- Genuine pre-R6 rollback manifest:
  `557b509c7671a016bd8352453458657b691ea0da304ea05495fa5f68eda9e7f7`

## External recovery pointers

These assets remain at their authoritative locations and are referenced by
the copied metadata. They are not duplicated in this supplement:

- Preserved original runtime/fallback body:
  `Avatar/models/temp_ai/kira/avatar.glb`
  - bytes: `4,559,016`
  - SHA-256:
    `3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e`
- R6 reversible-review candidate:
  `Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6/r6_20260718_163658/kira_provisional_body_r6.glb`
  - bytes: `5,105,808`
  - SHA-256:
    `ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77`
- Exact pre-R6 backup body:
  `Avatar/state/body_selections/backups/kira_pre_r6_live_trial_20260719_001839/avatar_original_live_3ec62ba8.glb`
  - bytes: `4,559,016`
  - SHA-256:
    `3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e`
- Eye-v3.3 staged/public GLB:
  - bytes: `1,994,524`
  - SHA-256:
    `b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5`
- Restore launcher:
  `Restore_Kira_Pre_R6_Live_Body.bat`
  - bytes: `428`
  - SHA-256:
    `5bf59612a540a664e4be1427a86f65122d1eed3ced3a59af49fd06f26f70df2b`

## Recovery and rollback

The copied metadata is evidence; copying it back by itself is **not** a
complete restore.

To verify the genuine pre-R6 recovery set without changing runtime state:

```powershell
py tools\restore_kira_pre_r6_live_body.py --verify-only
```

An actual rollback is mutating and was deliberately not run. If Robert later
chooses to roll back:

1. Deactivate Kira.
2. Stop all Kira World Shell and related browser/server processes.
3. Preserve a fresh snapshot of current selection metadata.
4. Run `Restore_Kira_Pre_R6_Live_Body.bat`.
5. Re-run the verification command and the bounded inactive browser checks
   before any later activation.

Do not copy an R4-v8 or R4-v9 artifact into a runtime path. They are rejected
and inactive. Do not export, bind or promote R4-v10 without Robert's review and
a separately documented authorization.

## Package verification

To verify a payload file manually:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath "<package-file>"
```

Compare the result with its row in `SHA256SUMS.tsv`. To audit provenance,
compare both hashes and the byte count in `COPY_VERIFICATION.tsv`.
