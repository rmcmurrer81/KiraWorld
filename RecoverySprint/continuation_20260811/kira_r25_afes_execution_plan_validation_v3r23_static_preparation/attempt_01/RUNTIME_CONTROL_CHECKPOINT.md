# Kira R25 AFES execution-plan validation V3r23 runtime control

Status: `STATIC_AUTHOR_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT_NO_EXECUTION_AUTHORITY`

V3r22 is a consumed bounded failure and is `DO_NOT_RERUN`. Its exact 20-file author, audit, consumed evidence/receipt/outcome, and postmortem closure is fixed by the V3r23 contract, identity anchor, and native subject gate.

No V3r23 candidate has been invoked. Author validation is limited to scratch-only x64 compilation/linking, `/analyze`, PE/import/CFG inspection, and static or mocked text probes. Author validation must not initialize Python, evaluate the retained controller, call `_build_execution_plan`, invoke a candidate executable, or access bootstrap, broker, process creation, AFES, Blender, body, save, render, or export paths.

## Bounded purpose

If and only if a different fresh reviewer accepts exact sealed bytes, at most one no-argument V3r23 invocation may:

1. create its own absent append-only evidence and outcome files with `CREATE_NEW` and write-through semantics;
2. validate the exact fresh-audit grammar and all fixed closure subjects;
3. parse, lock, read, and retain all 137 exact manifest rows;
4. initialize the exact isolated retained CPython runtime;
5. evaluate the exact retained controller twice in restricted dictionaries;
6. fingerprint the controller, harness, modules, helpers, code, defaults, keyword defaults, globals, closures, and deferred annotation thunks without reading or evaluating `function.__annotations__`;
7. attempt the pure `_build_execution_plan` expression at most once;
8. validate and destroy only its data-only returned plan;
9. record fine-grained checkpoint, plan-attempt, plan-return, marker, and native-SHA counts;
10. capture only a bounded sanitized exception type and message if Python raises, without traceback, private state, or path collection;
11. finalize Python, free the DLL, prove its old base and exact path absent, recheck retained handles and the complete fixed closure, commit success or failure, and stop.

## Static diagnosis and repair boundary

The V3r22 durable record proves only that failure occurred somewhere inside stage 40. Static inspection establishes that the exact controller contains annotations using `Any`, `Mapping`, `Sequence`, and `BaseException` without importing those names, and that V3r22 reads `function.__annotations__` while using CPython 3.14 deferred annotations. That makes annotation evaluation a likely pre-plan `NameError`, but this is not runtime proof.

V3r23 removes every read of `function.__annotations__`. It retrieves `function.__annotate__` only as an object and fingerprints its exact type, globals, code bytes and identity, defaults, keyword defaults, closure identity/cells, module, name, and qualified name without calling it. Fine-grained checkpoints then distinguish pre-plan fingerprint failure, plan attempt, plan return, validation, and post-call seal failure.

## Checkpoints

- `100`: validator entered
- `110`: exact locked module origins snapshotted
- `120`: harness helper closure snapshotted
- `130`: exact 137-row retained dictionary validated
- `140`: twin controllers constructed
- `150`: controller and deferred-annotation seals passed before plan
- `160`: plan-attempt counter incremented immediately before the sole call expression
- `170`: plan-return counter incremented immediately after return
- `180`: exact helper counts passed
- `190`: exact plan shape passed
- `200`: identity and projection checks passed
- `210`: recursive data-only check passed
- `220`: post-call controller/helper/module/native seals passed
- `230`: terminal validator marker committed

## Truth boundary

- Static preparation and scratch build are not candidate execution.
- The likely V3r22 cause is a reasoned diagnosis, not observed proof.
- An accepted bounded validation would not prove a body or anatomy.
- No bootstrap, broker, process, AFES, Blender, body, save, render, or export authority exists here.
- Success or failure consumes the one possible V3r23 authority; no retry is authorized.
