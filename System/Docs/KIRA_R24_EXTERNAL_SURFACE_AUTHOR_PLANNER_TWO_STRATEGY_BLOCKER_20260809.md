# Kira R24 external-surface author planner — two-strategy blocker — 2026-08-09

Status: **NO ADMISSIBLE PLANNER AFTER TWO BOUNDED STRATEGIES; NO BLENDER RUN.**

The inert author-operation infrastructure remains useful and passes its static
contracts, but its built-in topology planner cannot yet produce an external
E* replacement that satisfies both geometry quality and intersection safety.
The fixed thresholds were not weakened.

Current files:

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `tools/blender_author_kira_r24_external_surface_operation.py` | 47576 | `134fc094694e39b943f3534d9e3eec3e10b1674445dd64f07e29105c5edb91a0` |
| `Testing/test_blender_author_kira_r24_external_surface_operation.py` | 11861 | `f9784719eda902aae4cf602d78ecb122a60b0e298a30334317b5533b9a300ffb` |
| `RecoverySprint/continuation_20260808/kira_r24_external_surface_author_operation_planner_checkpoint_20260809/SOLVER_RESULT.md` | 3363 | `f15b898b3e3aa53cd343962e4385f414e7992e79732bae0732ef09df0c009dd3` |

Static regression coverage remains `59/59` passing. The callable is lazy with
respect to Blender, never saves/renders/exports, snapshots protected state,
uses transactional stage/swap/rollback, preserves the exact outside region,
and transfers provenance, UV, normal, and native-weight data. It raises before
staging if the planner does not pass.

Bounded strategy results:

1. Fixed original 161-face topology with boundary locked and 61 interior
   vertices achieved a `17.02405225158844°` minimum angle and
   `0.001156388570500444` minimum local area, but created 372 nonadjacent
   replacement self-intersections and 259 replacement/outside intersections
   (`631` forbidden total). It is structurally unsafe.
2. A distinct structured intrinsic annular disk with 41 exact boundary, 41
   transition, 19 inner, one centre, 61 interior vertices, and 161 faces had
   no accepted quality solution. Its best minimum angle was
   `3.685361218432005°`, below the unchanged `12°` requirement.

Per the two-attempt boundary, do not start another minor variation of these
same strategies automatically and do not publish the first strategy merely
because its angles pass. A later repair needs a genuinely different topology
or qualified foundation method, followed by the same exact intersection and
quality gates. No candidate, review images, movement evidence, internal
module, or Avatar Builder entry was produced.
