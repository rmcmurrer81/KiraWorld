# Kira R25 AFES Python/controller validation V3r20 runtime-control checkpoint

Status: `STATIC_CONTROL_ONLY_NO_EXECUTION_AUTHORITY`

Control: `STOP_BEFORE_PLAN_BUILDER_BROKER_PROCESS_AFES_BLENDER_BODY_SAVE_RENDER`

## Purpose

V3r20 is the append-only repair for the consumed V3r19 fixed-subject identity
failure. V3r19 exited `4` at `V3R19_SUBJECT_REFUSED:source`; it created no
evidence or receipt and entered no Python, controller, AFES, Blender, body,
save, render, or export path.

This candidate changes only the native validation control plane. It does not
change Kira's body, anatomy, dimensions, face, rig, source mesh, materials,
physiology, movement, or Avatar Builder production state.

## Exact identity semantics

- A newly opened exact file is validated and its observed `FILE_ID_INFO` is
  captured only after regular-file, expected byte count, exact final path, and
  expected SHA-256 checks pass.
- A retained file is revalidated into a fresh observed identity and then
  compared with its already-bound identity.
- No zero-filled identity value is used as a sentinel for two different
  operations.
- V3r19's compare-before-capture predicate remains frozen as a negative
  control and is not edited or retried.

## Candidate run boundary

Even after a different exact-byte review, at most one no-argument invocation
may:

1. verify the exact V3r20 executable and all 76 sealed subjects;
2. retain the exact V3r20 authority contract before accepting the exact V3r20
   audit;
3. reserve fixed append-only evidence and outcome files with `CREATE_NEW` and
   write-through semantics;
4. exercise the already-scoped granular V3r15 contract gate;
5. retain the exact manifest, Python DLL, stdlib zip, controller, and execution
   contract;
6. initialize isolated Python and evaluate controller definitions only;
7. verify five callable exports and an inert contract projection without
   calling any controller export;
8. finalize Python, release the DLL, prove its old base and exact path absent
   from a fail-closed process-module inventory, revalidate every retained file,
   write terminal evidence, and stop.

The candidate contains no process creation, broker launch, `_build_execution_plan`
call, AFES invocation, Blender invocation, body mutation, save, render, or
export path. Static preparation grants no execution authority. A different
fresh reviewer must either reject the exact sealed bytes or issue the exact
V3r20 one-shot decision. No prior V3r19 decision can be replayed.

## Truth boundary

Passing this native stage would prove only its exact granular contract and
Python/controller-definition checks. It would not prove a body, internal or
external anatomy, physiology, movement, rendering, activation, or owner
acceptance.
