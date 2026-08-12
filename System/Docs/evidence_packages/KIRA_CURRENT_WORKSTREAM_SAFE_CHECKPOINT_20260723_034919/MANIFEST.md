# Checkpoint manifest

Package: `KIRA_CURRENT_WORKSTREAM_SAFE_CHECKPOINT_20260723_034919`

Scope: current-workstream evidence and recovery only. This package does not begin or modify Kira Labs Video Studio v2.

## Package status

| Item | Status at checkpoint | Evidence boundary |
|---|---|---|
| Exact source-to-backup copy verification | PASSED | 75 of 75 SHA-256 comparisons matched |
| Current R6 candidate preservation | PASSED | Exact GLB and full candidate directory copied |
| Pre-R6 genuine rollback verification | PASSED | Rollback manifest and all five named files matched |
| Eye v3.3 asset preservation | PASSED | Candidate, staged, and public GLBs are byte-identical |
| Eye v3.3 automated browser evidence | PASSED | Preserved `evidence.json` reports all current checks true |
| Eye v3.3 visual approval | AWAITING ROBERT REVIEW | Screenshots are preserved; automation cannot approve realism |
| Blink | BLOCKED | No approved skinned eyelid geometry; no fake lids were added |
| Movement/posture snapshot | PASSED AS RECOVERY SNAPSHOT | Deterministic evidence only; owner visual review remains separate |
| Same-mouth/audio snapshot | PASSED AS RECOVERY SNAPSHOT | Deterministic evidence only; owner visual/listening review remains separate |
| Runtime pre-change rollback | NOT AVAILABLE | Runtime changes predate this package; snapshot is post-change |
| Kira activation or life loop | NOT PERFORMED | This checkpoint did not activate Kira |
| Publishing | NOT PERFORMED | No upload or publish action occurred |

## Key immutable hashes

| Asset | SHA-256 | Size |
|---|---|---:|
| Current R6 candidate GLB | `ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77` | 5,105,808 bytes |
| R7-v3 eye source candidate GLB | `b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5` | 1,994,524 bytes |
| Staged eye v3.3 GLB | `b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5` | 1,994,524 bytes |
| Public Home World eye v3.3 GLB | `b79ba1a3ad593d13b41f16c2c83af96913ec82fa27a6b63f959f816f8be897e5` | 1,994,524 bytes |
| Genuine pre-R6 original-live GLB backup | `3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e` | 4,559,016 bytes |
| Genuine rollback manifest | `557b509c7671a016bd8352453458657b691ea0da304ea05495fa5f68eda9e7f7` | 1,865 bytes |
| Kira World shell server snapshot source | `28cf54a24c4499682c2dc7ec5674230c85d9442e992960121555bc965fea9590` | 361,145 bytes |
| Home World `main.js` snapshot source | `41fb94394a97e4ad1c96dce5f70560cb7e428692aaa0a5b65f1bf48ee6304bdd` | 942,882 bytes |

## Verified genuine R6 rollback

Original repository path:

`Avatar/state/body_selections/backups/kira_pre_r6_live_trial_20260719_001839/`

Checkpoint duplicate:

`genuine_rollback/kira_pre_r6_live_trial_20260719_001839/`

The rollback manifest’s five internal expectations were checked:

- original live GLB backup: matched
- pre-trial runtime body selection: matched
- pre-trial R6 review staging: matched
- pre-trial temporary-person state: matched
- R6 trial asset: matched

The current `Avatar/models/temp_ai/kira/avatar.glb` also retained the exact pre-trial original-live hash `3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e` at checkpoint time. The R6 trial remains a selection pointer and was not copied over that original asset.

## Current eye evidence

Preserved evidence:

`snapshot/eye/production_default_skin_fit/evidence.json`

Reported automated metrics:

- horizontal iris travel: 0.0025 m
- vertical iris travel: 0.00144 m
- maximum socket/sclera/cornea local motion: 0 m
- maximum head-binding distance drift: 0.0000000002 m

The preserved evidence reports `livePersonActivated: false`, `lifeLoopStarted: false`, and identical shell-state hashes before and after its browser run.

## Full mapping

Use `COPY_VERIFICATION.tsv` as the authoritative original-to-backup map. It includes every preserved file and both hashes; every `match` value was `true` when this manifest was authored.

Final package verification after authoring:

- exact original-to-copy comparisons: 75
- original-to-copy mismatches: 0
- package files covered by `SHA256SUMS.tsv`: 78
- missing, size-mismatched, or hash-mismatched package files: 0
- total package files including `SHA256SUMS.tsv`: 79
- total package size at verification: 50,972,054 bytes
