# Kira R24 R4 independent-audit rejection and R5 boundary — 2026-08-09

Status: **R4 PRESERVED AND REJECTED; BLENDER AUTHORING NOT AUTHORIZED.**

The exact R4 static package passed its focused tests, but a fresh append-only
independent audit found six acceptance-boundary defects. Passing unit tests are
therefore not being treated as permission to open, mutate, save, render, or
promote a Kira body.

Preserved R4 evidence:

| Artifact | SHA-256 |
|---|---|
| worker | `7b453ca1fc0d0eaec979fccf6de732ec455c7c834157fe7c757497f4ebe57fd5` |
| test | `7a405c6cc605fd7f6d0937cece086ed2b27581870f61cabc574e42b7bbd18281` |
| contract | `f22ecd500092b83825b61fb22111d5dca4820889566c45012d883bfedb77f5d4` |
| proposal | `ec7bfea35fb57a8787a3ef62452cea1356d001b722628790beb1579e6adb875b` |
| static results | `65a2e355c30b9cc0011ee30d3dd123ca56577c4ebb6d067ac82bd3682a70e140` |
| checkpoint | `bbbc0f938f31ee7d2af3edf1aed1cd4b816a4ed9ae23f4162efff395263cdead` |
| package manifest | `cc84b86eaca7a4953565495ab8e9c91b0f041d41f2340a59109cd9b5fe1b2728` |
| `INDEPENDENT_STATIC_AUDIT.md` | `1f84a693b643b81af9200423d8fa79cfe669202b8f31e31b98c623d020912215` |

The audit rejection is append-only at
`RecoverySprint/continuation_20260808/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r4/INDEPENDENT_STATIC_AUDIT.md`.

The six blockers are:

1. A candidate/source file-replacement race exists between typed preflight and
   the later extraction phases.
2. Unlinked Blender mesh/armature datablocks are not inventoried, so an exact
   one-patch/no-extra-rig claim is not proved.
3. Body-object, collection, scene, view-layer, render, world, unit,
   color-management, and constraint preservation is only partial.
4. replacement-area validation uses local coordinates while claiming square
   metres; the exact world transform must be applied.
5. Rig/pose constraints, Action/F-curve modifiers/groups, material node-tree
   properties, and image/packed-data content are not completely represented.
6. Fresh evaluator reopen exists, but a controller-owned author PID/job clean
   exit and post-exit candidate digest are not yet proved.

Any corrected implementation must be an append-only R5 successor. R4 must not
be edited or reinterpreted as execution-ready. R5 must retain the sound R4
boundaries, add adversarial regressions for all six defects, remain
`execution_authority_granted=false`, and pass a new independent audit.

Separately, the body build requires three components that must not be conflated:

- a Blender author-operation callable that performs the bounded external
  surface edit but never saves on its own;
- a one-shot controller that starts exactly one author process, proves its
  clean exit, hashes the candidate after exit, and then starts exactly one
  read-only fresh-reopen evaluator; and
- the R5 evaluator that decides whether the resulting artifact satisfies the
  sealed structural and preservation contract.

No R24 candidate, owner gallery, movement acceptance, Avatar Builder promotion,
internal-anatomy attachment, activation, assignment, export, or publication
may begin until those components are sealed and independently audited.
