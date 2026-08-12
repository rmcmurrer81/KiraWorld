# Kira R25 AFES Python/controller validation V3r21 runtime-control checkpoint

Status: `STATIC_CONTROL_ONLY_NO_EXECUTION_AUTHORITY`

Control: `STOP_BEFORE_PLAN_BUILDER_BROKER_PROCESS_AFES_BLENDER_BODY_SAVE_RENDER`

## Purpose

V3r21 is the append-only repair for the rejected V3r20 native candidate.
V3r20 was never executed. A different fresh reviewer found two real C6385
out-of-bounds literal reads in durable reservation and terminal receipt fields:
the 34-byte reservation copy read two bytes past a 32-byte string object, and
the 31-byte terminal copy read two bytes past a 29-byte string object. The
sealed executable layout independently showed the first copy consuming its
terminator plus `KI` from the adjacent literal.

This candidate changes only the native validation control plane. It does not
change Kira's body, anatomy, dimensions, face, rig, source mesh, materials,
physiology, movement, or Avatar Builder production state.

## Exact repair semantics

- Reservation and terminal receipt magic values are named arrays whose copy
  bounds are `sizeof(array) - 1U`.
- C17 `_Static_assert` checks prove each literal payload fits its destination
  field.
- Large final-path scratch buffers are allocated from the process heap, wiped,
  and released; copied paths receive explicit terminators.
- The Python module path is bounded by `MAX_PATH`, and handle cleanup admits
  only handles that are neither `NULL` nor `INVALID_HANDLE_VALUE`.
- An independent MSVC `/analyze` pass must produce zero unsuppressed warnings.
- V3r20's rejected bytes and all five rejection-evidence files remain frozen as
  a 15-file negative-control closure and are not edited, retried, or run.

## Candidate run boundary

Even after a different exact-byte review, at most one no-argument invocation
may:

1. verify the exact V3r21 executable, every subject that the native runtime
   binds, and the exact different-reviewer audit that externally rehashed all
   91 sealed subjects;
2. retain the exact V3r21 authority contract before accepting the exact V3r21
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

The candidate contains no process creation, broker launch,
`_build_execution_plan` call, AFES invocation, Blender invocation, body
mutation, save, render, or export path. Static preparation grants no execution
authority. A different fresh reviewer must either reject the exact sealed
bytes or issue the exact V3r21 one-shot decision. No V3r19 or V3r20 decision can
be replayed.

## Truth boundary

Passing this native stage would prove only its exact granular contract and
Python/controller-definition checks. It would not prove a body, internal or
external anatomy, physiology, movement, rendering, activation, or owner
acceptance.
