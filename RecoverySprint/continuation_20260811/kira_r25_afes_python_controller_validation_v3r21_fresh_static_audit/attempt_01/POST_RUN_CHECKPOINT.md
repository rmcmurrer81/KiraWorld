# Kira R25 AFES V3r21 consumed-run outcome

Recorded UTC: `2026-08-11T11:30:05.0722650Z`

Outcome:
`PYTHON_CONTROLLER_DEFINITION_VALIDATION_SUCCESS_AUTHORITY_CONSUMED_NO_RETRY`

## Result

The exact one-shot command ran once from `C:\Users\robmc\Kira` with no
arguments:

```powershell
.\tools\native\kira_r25_afes_python_controller_validation_v3r21.exe
```

Exit code: `0`

Candidate standard output: empty.

Candidate standard error: empty.

The shell reported `V3R21_EXIT_CODE=0` after the process returned. The
authorization is consumed and V3r21 must never be invoked again.

## Durable evidence

- `RUN_EVIDENCE.jsonl`: 1,312 bytes, SHA-256
  `76ce1202eb11b0e5d7a9473800179b9f01665cfd235e89558bcfd55aa723d8e4`;
  exactly nine valid JSON lines in the required order, ending in exact terminal
  success detail `no_bootstrap_plan_builder_afes_blender_body`.
- `PYTHON_CONTROLLER_VALIDATION_OUTCOME.receipt.bin`: 1,016 bytes, SHA-256
  `7c53fc7beef0a350a2c15f8e0dd6c82730c6dea48f56cf24324a78145ecad31a`;
  exactly one 424-byte reservation and one 592-byte completion with no trailing
  byte.
- `RUN_OUTCOME.json`: 2,142 bytes, SHA-256
  `ce26d16412c8e90d752af9f4182368db45241146dedd26b5cdee9ec55de68f6d`.
- The accepted audit TSV embedded in both receipt records is exactly SHA-256
  `235e13793ed4112c9dfaa7173125b31712cb84323d46224932f5fda135f69fd5`.
- Reservation and completion magic/version/type/byte/state fields are exact;
  completion state is success and terminal stage is 60.
- Executable, audit, manifest, controller, execution-contract, and retained
  V3r21 authority-contract digests match exact expected subjects. Receipt and
  evidence file IDs/volumes cross-bind exactly across both records. The random
  reservation nonce is nonzero.
- The completion record's reservation digest exactly matches the first 424
  receipt bytes.

## Granular contract evidence

- passed mask: `32767` (all fifteen gates);
- failure gate and Win32 error: `0`;
- snapshot-one, snapshot-two, and final sizes: `6,174` bytes each;
- all three snapshot digests exactly match the expected V3r15 contract:
  `ad33386d767b516425dcbed073e22dfc9747a963a64dc5d205483d210acac79d`.

## Isolated Python/controller evidence

- isolated Python runtime initialized and finalized;
- five exact controller exports were verified callable;
- strict inert execution-contract projection passed;
- no controller callable, including `_build_execution_plan`, was invoked;
- finalize was called and returned 0;
- `FreeLibrary` was called and succeeded;
- fail-closed process-module inventory succeeded over 8 modules;
- neither the old Python module base nor exact Python DLL path remained;
- every retained subject and retained V3r21 authority contract passed terminal
  same-handle identity/digest recheck.

## Meaning and boundary

This closes only the bounded granular-contract plus isolated Python/controller-
definition validation layer. It proves that exact static/native control path
and its durable output—not a body.

It did **not** invoke the plan builder, bootstrap, broker, child process, AFES,
Blender, a Blend file, mesh, external or internal anatomy, physiology,
movement, activation, save, render, export, voice, media, or production
routing. No body was created or changed, no owner render was produced, and no
body completion is claimed.

Any next body step must be a new append-only successor with its own exact
static boundary and different fresh audit. V3r21 success never authorizes a
V3r21 retry or automatic expansion of capability.
