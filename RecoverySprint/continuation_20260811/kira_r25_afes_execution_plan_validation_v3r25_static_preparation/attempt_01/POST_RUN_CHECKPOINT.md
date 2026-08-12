# V3r25 consumed diagnostic post-run checkpoint

Recorded UTC: `2026-08-11T20:38:49.7945087Z`

## Terminal result

V3r25 was invoked exactly once with no arguments from `C:\Users\robmc\Kira`
after root confirmed 292/292 exact sealed subjects, 10/10 exact author
artifacts, 6/6 exact independent-audit artifacts, and both fixed output paths
absent. The executable returned exit code 1. Its one-attempt authority is now
consumed: `DO_NOT_RERUN_V3R25`.

Durable evidence:

- `RUN_EVIDENCE.jsonl`: 1,511 bytes, SHA-256
  `a1dff2c1dbc2c7ddf8f8cc5d25ee7ed000ab24d1787cc0c6aca73cf0ce3dca66`
- `EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin`: 1,320 bytes, SHA-256
  `8dbfbb97a1d2413eedf56beafce4ef330a2e9e1b286afc07a4d41c30fd609540`

The plan callable was attempted once and returned once. Validation then failed
at checkpoint 218 during the post-plan controller revalidation:

`RuntimeError: controller_function_code_or_deferred_annotate_metadata:_build_execution_plan`

Exact counters were plan attempts/returns 1/1, operation enters/returns 16/15,
marker present 0, and native SHA calls 222. The exception was captured without
truncation. Python finalization, DLL release, module-absence proof, retained
rechecks, and all fifteen contract gates passed.

## Truth boundary

This failure occurred after the pure plan dictionary returned but before the
final post-call controller/helper/runtime checks and terminal validation marker.
No bootstrap, broker, child process, AFES, Blender, body, internal or external
anatomy, material, regional pigmentation, hair, save, render, or export path
ran. Nothing from this result may be given to the Avatar Builder as an accepted
body result. It is a do-not-repeat diagnostic finding only.

The only next body-diagnostic path is append-only V3r26 static diagnosis,
repair, strict build/analyze/PE inspection, sealing, and a different fresh
audit. V3r25 and every older consumed/rejected diagnostic remain non-runnable.

