# Kira R25 execution-plan validation V3r24 consumed-run checkpoint

Recorded UTC: `2026-08-11T18:35:24.1077055Z`

Decision used:
`ACCEPTED_FOR_ONE_BOUNDED_DIAGNOSTIC_PURE_BUILD_EXECUTION_PLAN_VALIDATION_V3R24_ONLY`

Invocation count: `1/1`  
Exit code: `1`  
Terminal state: `FAILED_CONSUMED_NO_RETRY`  
Authority: consumed; `DO_NOT_RERUN_V3R24`

## Exact precheck

- seal subjects: `273/273` exact, 273 unique, zero drift;
- frozen author artifacts: `10/10` exact, zero drift;
- audit TSV: 1,795 bytes, SHA-256
  `fc2d1a78d7d9f843349c4beb1ec7dc0af4d0cb4a7e7a8b481a7b1416c36da101`;
- audit sidecar: 65 bytes, file SHA-256
  `b7711e2a111d38b687b83097bc14f632a1241f5d28fc85d79d62251f0b140b37`;
- both output paths were absent before the no-argument invocation;
- exact executable: 264,704 bytes, SHA-256
  `281d427482657a73096fa6b44e2092e6e54b760e59c73c37f562e24ad6b03bb9`;
- exact working directory: `C:\Users\robmc\Kira`.

## Durable result

`RUN_EVIDENCE.jsonl` is 1,450 bytes, SHA-256
`310c8d16fdf433de22ecee9dc326c34fd8f1efcbbdc86ada382e7088e42745a7`.

`EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin` is 1,320 bytes, SHA-256
`2665dd31b2c561a728a3b14449b6d79e821494e9b5792682bc1399fd5edb5b34`.

`RUN_OUTCOME.json` is 4,426 bytes, SHA-256
`850769324423d08278303a2aaae7bcff0e655bfb103b8b66ee47fe13211ca656`.

The detailed telemetry is exact:

- checkpoint `110`;
- plan attempts/returns `0/0`;
- operation enters/returns `0/0`;
- native SHA calls `0`;
- exception type `ValueError`;
- exception message `unmarshallable object`;
- exception was not truncated;
- all 15 same-handle contract gates passed;
- Python finalized with result 0, the DLL was freed, and module inventory
  proved the old base and exact Python path absent;
- the retained/fixed recheck passed.

No controller instance was constructed, `_build_execution_plan` was not
called, and no bootstrap, broker, process, AFES, Blender, body, save, render,
or export operation occurred.

## Exact root cause

Checkpoint 110 is immediately after locked module-origin capture and before
helper capture completes. V3r24 fingerprints helper/controller code with
`marshal.dumps(code, 4)`. The locked runtime is Python `3.14.4`, whose
`marshal.version` is `5`. Python 3.14 compiler output contains constant `slice`
objects for expressions such as `raw[:3]`; marshal format 4 cannot encode these
code objects and raises exactly `ValueError: unmarshallable object`.

A read-only exact-source reproduction compiled the 18,870-character embedded
validator and checked all 20 nested code objects. Format 4 failed on exactly
four code objects (`<module>`, `_v3_strict`, `_v3_validate_controller`, and
`_v3_glue_object`); format 5 encoded all 20 with zero failure. The three named
helpers contain 2, 1, and 2 slice constants respectively.

This is an exact native/Python fingerprint-format defect, not an anatomical or
Blender failure.

## Required append-only repair

Preserve all V3r24 bytes and outputs. Author V3r25 only. Bind the complete
consumed V3r24 audit/run closure; require exact Python 3.14 marshal version 5;
use format 5 for code-object fingerprints (or a separately exact structural
fingerprint); reproduce V3r24 format-4 failure and V3r25 format-5 success for
every validator/controller/helper code object; retain all telemetry, cleanup,
stop-before, and no-body-claim gates; reseal; and require a different audit
before any new bounded invocation.

This checkpoint is not body approval and creates no positive Avatar Builder
method.
