# Kira R25 AFES v3r18 sealed static checkpoint

Status: `SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT`

Decision: `STOP_FOR_DIFFERENT_FRESH_EXACT_BYTE_AUDITOR`

Execution authority: `NONE`

## Exact successor

V3r18 is the smallest append-only successor combining two previously bounded
pieces without retrying either predecessor:

- the V3r17 reservation-first, one-handle, granular observation of the exact
  6174-byte V3r15 contract, which was accepted, ran successfully once, and is
  now consumed with no retry; and
- V3r15's isolated Python/controller-definition validation stage, which never
  reached Python because its earlier aggregate contract gate failed before its
  reservation and was consumed.

The controlling aggregate path gate is not reused. After exact static/audit
checks, V3r18 first reserves fixed evidence and receipt paths with `CREATE_NEW`,
write-through, exact final-path checks, flush, and same-handle readback. It then
opens the exact V3r15 contract once with the V3r17-proven share policy. Fifteen
granular gates cover open, attributes/non-reparse, first size/path/file ID/hash,
second size/path/file ID/hash, final size/path/file ID/hash equality, and close.
The same handle remains retained across the bounded Python stage. Gate mask,
failure gate, Win32 error, access/share/open flags, sizes, identity, and all
snapshot hashes are copied into the durable terminal receipt. Every path after
a successful reservation attempts the same-handle terminal write/readback;
post-stage failures do not depend on reopening mutable subjects to populate it.

Only after the contract's first two exact same-handle snapshots may V3r18 lock
the retained manifest, Python DLL, stdlib zip, controller, and execution
contract. It proves the exact manifest rows, delayed-loads only the retained
`C:/Python314/python314.dll`, initializes isolated Python with environment/user
site/site import/bytecode/signals/argv parsing disabled, and uses only the
retained stdlib zip. It evaluates the exact controller's inert definitions,
verifies exactly five callable exports, and validates a strict projection of
the exact retained execution contract. It then finalizes Python, unloads the
DLL, rechecks all retained handles and the original contract handle, commits a
terminal success-or-failure record, and stops.

It never calls `_build_execution_plan`. No bootstrap, broker, shell, process,
AFES child, Blender, Blend, body, mesh, armature, anatomy, movement, mutation,
save, render, export, activation, assignment, publication, or upload path is
present.

## Preservation

The exact V3r17 candidate, seal, checkpoint, accepted audit TSV and sidecar,
audit checkpoint, `RUN_EVIDENCE.jsonl`, binary terminal receipt,
`RUN_OUTCOME.json`, and `POST_RUN_CHECKPOINT.md` are all listed by byte count
and SHA-256 in the V3r18 seal. The V3r17 consumed-success files were not edited.
The exact V3r15 Python-stage candidate and its failure/recheck closure are also
listed. The retained manifest, Python DLL, stdlib zip, controller, and execution
contract are exact-bound in both source and seal.

## Static verification

- Strict native compile: `PASS` with `/W4 /WX /O2 /MT /guard:cf`, x64 C17.
- Hostile source/contract test: `V3R18_HOSTILE_STATIC_TESTS_PASS` with bytecode
  disabled.
- Read-only PE inspection: x64, CFG, dynamic base, NX; imports are only
  `bcrypt.dll` and `KERNEL32.dll`. There is no static Python or process/shell
  import.
- Candidate executable was not run. Python, controller, AFES, Blender, body,
  media, person, device, and production paths were not run.
- Runtime evidence and receipt do not exist at freeze.
- The required future audit directory does not exist at freeze.
- No main registry or handoff file was edited.

Exact seal:

`RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r18_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json`

- bytes: `10851`
- sha256: `25902b27005076878e577e594916748793ca7eea0614fbe76316a217dcd85ee4`
- verified entries: `43/43`

Required future audit path:

`RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r18_fresh_static_audit/attempt_01`

Required exact decision, if and only if a different fresh auditor independently
accepts every byte and boundary:

`ACCEPTED_FOR_ONE_BOUNDED_GRANULAR_CONTRACT_AND_PYTHON_CONTROLLER_VALIDATION_ONLY`

This author does not create that audit and cannot authorize execution.

`NO_EXECUTION_AUTHORITY`

`V3R17_CONSUMED_SUCCESS_NO_RETRY`

`STOP_BEFORE_PLAN_BUILDER_BROKER_PROCESS_AFES_BLENDER_BODY_SAVE_RENDER`
