# V3r26 consumed successful pure-plan diagnostic checkpoint

Recorded UTC: `2026-08-11T22:50:24.9828387Z`

## Exact outcome

After exact installation of the different-review evidence, root rehashed
312/312 unique sealed subjects, 10/10 author-package artifacts, and 6/6 audit
artifacts with zero mismatch. The V3r26 evidence and receipt paths were absent.

Root invoked the exact installed V3r26 executable once with no arguments. It
started at `2026-08-11T22:47:39.5725820Z`, ended at
`2026-08-11T22:47:40.8781976Z`, and exited `0`.

Authority is consumed. `DO_NOT_RERUN_V3R26`.

## Durable success evidence

The evidence stream records every bounded stage passing:

- entry;
- subject/manifest/audit gate;
- outcome reservation;
- isolated Python runtime;
- restricted twin-controller code/global gate;
- exactly one pure `_build_execution_plan` call and data-only plan validation;
- Python finalization, DLL unload, and retained recheck;
- bounded telemetry at checkpoint 230;
- all fifteen granular same-handle contract gates;
- terminal complete with the plan destroyed.

Exact plan/control telemetry:

- manifest rows: 137;
- plan attempts/returns: 1/1;
- guarded operation enters/returns: 21/21;
- forbidden helper calls: 0;
- completion state: `2 = RECORD_SUCCESS`;
- terminal stage: 90;
- contract passed mask: 32767; failure gate: 0; Win32 error: 0;
- controller contract snapshots/final bytes: 78,942 / 78,942 / 78,942;
- finalization result: 0;
- `FreeLibrary` result: 1;
- module snapshot succeeded with eight checked modules;
- old module base present: 0; exact DLL path present: 0;
- marker present: 1; native SHA calls: 223;
- Python error captured: 0; retained recheck passed: 1.

Exact evidence:

- `RUN_EVIDENCE.jsonl`: 2,056 bytes, SHA-256
  `2383eebde2fbc6d3336c1db8901cfc19ac8e45c15c9948ed5c084836c8f0ee49`;
- `EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin`: 1,320 bytes, SHA-256
  `cd22fd75175f2eee23d08e3d97f2ab763fca5dd7e758e6a6b1c874d160af8e06`;
- `RUN_OUTCOME.json`: 3,146 bytes, SHA-256
  `3fbce021b5dffa713afa75714be0fe40a0fb8a25b18312beaaa458a8ca067c4c`.

## Honest boundary

This is an accepted consumed pure-plan/control result. It is not a body.
Bootstrap, broker, process launch, AFES, Blender, body construction, internal
or external anatomy, materials, regional pigmentation, bald/hair variants,
save, render, export, activation, and Avatar Builder promotion did not run and
are not proven.

A later append-only body-execution successor may consume this result only as
control evidence. It requires its own bounded source/contract, static seal,
different review, exact one-shot authority, and actual Blender/body/save/render
evidence before any body or Avatar Builder claim.
