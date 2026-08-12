# Kira R20 local pelvic-retopology read-only authority

Date: 2026-08-02  
Status: **PLAN COMPLETE; AUTHORING NOT STARTED**

## Current decision

The next bounded Kira body correction is one local replacement of the rejected
R19 attempt-06 pelvic insert. Preserve the current face/head and body
proportions, native rig, all nonpelvic weights, skin and eye systems, brows,
hands, feet, nails, movement actions, and every separate mesh exactly. This is
a repair scope, not owner approval of the whole body.

Use method
`R20_BLACKPROJECT_CLAMPED_CURVILINEAR_QUAD_PATCH_V1`: a new three-dimensional,
seam-clamped, all-quad retopology solved inside the exact existing 34-vertex
interface. Delete only the exact 376 rejected faces and 172 old interior
vertices. Copy no donor interior vertex or face.

BlackProject supplies the licensed seam and current rig lineage, not a usable
interior donor: its source interior has 298 exact nonadjacent intersection
pairs. MakeHuman and MB-Lab do not share the exact seam or current rig.
`adult_surface_v3` supplies only semantic order and bounded-relief guidance.
Plate, paint-only, Boolean, floating, radial-fan, centroid-ring, global-XZ-fit,
and donor-shrinkwrap approaches remain rejected.

## Expected topology

The future replacement uses two 34-vertex C1 collar rings, a pure-quad
34-to-102 perimeter transition, and a 21 x 32 feature-aligned core:

- new vertices: 740;
- new faces: 756 quads;
- replacement incident vertices including the reused seam: 774;
- expected joined primary surface: 13,180 vertices, 38,517 edges, and 25,316
  faces;
- expected connected components: 1;
- new patch boundary, nonmanifold, and exact intersection counts: 0.

The connected external surface must preserve the medically sourced relationship
from mons and paired labia through the vestibule, distinct external urethral
meatus and vaginal opening, posterior fourchette and continuous perineum, to a
separate anal region. Openings are shallow blind-cap surface geometry, not
internal canals.

## Truth boundary

R20 may prove externally visible anatomy and pose clearance only. It does not
implement or prove internal urinary, vaginal, reproductive, rectal, pelvic
floor, continence, elimination, pregnancy, or intimate-behavior function. The
controlling medical note remains:

`System/Docs/KIRA_R18_MEDICAL_EXTERNAL_ANATOMY_AND_BATHROOM_READINESS_BOUNDARY_20260801.md`

## Controlling evidence

- Full read-only audit:
  `RecoverySprint/continuation_20260802/kira_r20_local_pelvic_retopology_read_only_audit/R20_READ_ONLY_LOCAL_RETOPOLOGY_AUDIT.md`
- Exact mask, topology, construction, gates, and review views:
  `RecoverySprint/continuation_20260802/kira_r20_local_pelvic_retopology_read_only_audit/R20_PELVIC_MASK_TOPOLOGY_AND_ACCEPTANCE_PLAN.json`
- Exact nonpelvic freeze ledger:
  `RecoverySprint/continuation_20260802/kira_r20_local_pelvic_retopology_read_only_audit/R20_NONPELVIC_FREEZE_LEDGER.json`
- Source hashes and donor decisions:
  `RecoverySprint/continuation_20260802/kira_r20_local_pelvic_retopology_read_only_audit/R20_SOURCE_HASH_AND_DONOR_DECISION_LEDGER.json`
- Rollback:
  `RecoverySprint/continuation_20260802/kira_r20_local_pelvic_retopology_read_only_audit/ROLLBACK.md`

The immutable input Blend is R19 targeted attempt 06, SHA-256
`dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f`.
Its 49-entry package manifest was rehashed with zero mismatch during this
audit. Never overwrite that directory.

No Blender process, render, GPU job, body mutation, R20 Blend, activation,
assignment, clothing, export, publication, or upload is authorized by this
document. A future authoring run must use a new append-only attempt and abort
without save on any hash, mask, seam, or preservation mismatch.
