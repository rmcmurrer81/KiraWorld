# Kira provisional R6 private review bundle

This directory and its bound state/evidence files preserve Kira's exact R6
body as a **reversible private owner-review trial**. It is not currently
running merely because the files are present, but the exact historical
selection is activation-capable when Kira is explicitly activated. It is not
a permanent body selection.

## Exact body identities

- Original rollback body:
  `Avatar/models/temp_ai/kira/avatar.glb`
  (`3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e`).
- R6 review candidate:
  `Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6/r6_20260718_163658/kira_provisional_body_r6.glb`
  (`ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77`).
- Evidence-bound staged eye:
  `Avatar/models/staged/kira/eyes/kira_brown_eye_rig_v3_2/kira_brown_eye_rig_v3_2.glb`
  (`fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413`).

The selection, staging record, browser evidence, and complete rollback files
are preserved at the paths named by those records. The original body is not
overwritten by R6.

## Source attribution and adaptation notice

The original cage/rig source is **Women/Female Body Base Rigged** by
[camilooh](https://sketchfab.com/camilooh), distributed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The source page is
<https://sketchfab.com/3d-models/womenfemale-body-base-rigged-45caea510e4b4b65bf4ef9bbb4d2045c>.
The R6 GLB is an adapted derivative with bounded body-surface/material work;
it is not the unmodified source. This attribution and adaptation notice must
remain with any private copy of the bundle.

## Required truth boundary

R6 passed bounded exact-hash technical checks for its 79-joint rig, walking,
sitting, turning, reaching, ground contact, staged-eye binding/blinks, and
existing-mouth deformation. Those checks do **not** prove complete external or
internal anatomy, final appearance, natural long-duration motion, correct eye
fit, clothing, hair, permanent acceptance, physical robot control, or medical
function.

Clothing and hair remain separate components. Nothing in this bundle permits
baking clothes or a rigid hair/scalp cap into the body mesh.

The existing authoritative requirements remain:

- `System/Docs/AVATAR_SEPARATE_SHAREABLE_CLOTHING_v1.md`;
- `System/Docs/AVATAR_BUILDER_RUNTIME_HAIR_REQUIREMENTS_20260729.md`;
- `System/Docs/AVATAR_BALD_LOW_RESOURCE_AND_DETACHABLE_HAIR_POLICY_20260801.md`;
- `System/Docs/KIRA_CONFIRMED_ADULT_INTERNAL_PELVIC_ANATOMY_MODULE_CONTRACT_20260809.md`;
- `System/Docs/BIOLOGICAL_ROBERT_CONFIRMED_ADULT_MALE_INTERNAL_EXTERNAL_ANATOMY_AND_BODY_FUNCTION_CONTRACT_20260809.md`.

## Verification

From the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B -W error -m unittest Testing.test_kira_runtime_body_selection Testing.test_kira_r6_portable_review_bundle -v
py -B -W error tools\restore_kira_pre_r6_live_body.py --verify-only
```
