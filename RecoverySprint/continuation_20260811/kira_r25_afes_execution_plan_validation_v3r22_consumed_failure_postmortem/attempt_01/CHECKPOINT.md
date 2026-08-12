# V3r22 consumed failure postmortem

Recorded UTC: `2026-08-11T14:46:42.6580354Z`

Status: `CONSUMED_FAILURE_DO_NOT_RERUN_V3R22`

## Invocation

Immediately before execution, all 237 sealed subjects, all five different-
audit files, the exact executable, and absent output paths passed. The exact
sealed executable was invoked once with no arguments. It exited `1`. That
single attempt permanently consumed the V3r22 authority, regardless of where
the failure occurred.

`DO_NOT_RERUN_V3R22`.

## Durable evidence

- `RUN_EVIDENCE.jsonl`: 607 bytes, SHA-256
  `4f9707fadf2092ecb28da4d9683e01690c5102cc1aac7236cc68ebd622d4b314`.
- `EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin`: 1,016 bytes, SHA-256
  `cf2409244de8a42981e62667e5607e8912bd1d94220bbb09dfd0a79f3a4540bd`.
- Reservation: exact 424 bytes; completion: exact 592 bytes; no trailing byte.
- Completion state: failure (`3`); terminal stage: `40`.
- Reservation SHA-256:
  `ff2c1c5c867cd4dc6efef2431018eede55bb2cd387446943940a32c3d78ea038`,
  exactly repeated by the completion record.
- Executable, audit, manifest, controller, execution-contract, and authority-
  contract hashes match between reservation and completion.

The JSONL records show entry, exact subject/manifest/audit gate pass, durable
outcome reservation, all 15 granular authority-contract gates passed
(`passed_mask=32767`, `failure_gate=0`, `win32_error=0`), then terminal consumed
failure. No success record exists.

## Runtime cleanup

The binary receipt proves Python finalization was called and returned `0`;
`FreeLibrary` was called and succeeded; module enumeration succeeded with
eight modules checked; neither the old Python module base nor the exact Python
DLL path remained loaded. Cleanup therefore completed safely despite the
validator failure.

## Exact failure boundary

Stage `40` is assigned immediately before the embedded `PLAN_VALIDATOR` string
is executed. That validator contains the one permitted pure
`_build_execution_plan` call and numerous checks after it. V3r22 did not
durably record the Python exception or internal validator checkpoint.
Therefore the preserved evidence cannot honestly state whether the failure
occurred before, during, or after that pure call, and it cannot claim an exact
call count or a successfully validated plan.

No bootstrap, broker, process creation, AFES, Blender, body access or mutation,
save, render, or export route is called by this boundary, and none ran. This is
not a body, anatomy, render, or Avatar Builder success.

## Next step

Preserve V3r22 and every audit/run byte. Perform only read-only static
postmortem work. An append-only V3r23 may add bounded sanitized Python-exception
and internal-validator checkpoint telemetry so the exact failing predicate can
be proven without any body path. V3r23 must be rebuilt, sealed, and receive a
different fresh audit before one new bounded attempt. V3r22 is never retried.
