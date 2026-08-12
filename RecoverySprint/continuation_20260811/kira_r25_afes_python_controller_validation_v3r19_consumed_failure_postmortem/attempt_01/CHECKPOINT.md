# Kira R25 AFES Python/controller validation V3r19 consumed-failure postmortem

Recorded UTC: `2026-08-11T09:45:27.3458392Z`

Status: `CONSUMED_FAILURE_NO_RETRY`

## Exact outcome

The one independently authorized V3r19 invocation was made once from
`C:\Users\robmc\Kira` with no arguments. It exited with code `4` and emitted:

```text
V3R19_SUBJECT_REFUSED:source
```

The invocation is consumed and will not be retried. V3r19 remains sealed and
unchanged.

## Proven stop boundary

The executable stopped at the first fixed-subject gate. It did not open the
V3r19 authority contract, parse the future audit, reserve evidence or a
receipt, load Python, evaluate controller definitions, build an execution
plan, start a broker or process, enter AFES, start Blender, or perform any
body, anatomy, save, render, or export operation.

Both fixed outputs remain absent:

- `RUN_EVIDENCE.jsonl`
- `PYTHON_CONTROLLER_VALIDATION_OUTCOME.receipt.bin`

`READ_ONLY_RECHECK.json` binds the current exact candidate, audit, and
checkpoint bytes and records each unentered boundary explicitly.

## Reproduced root cause

This is a native file-identity initialization defect, not an anatomy or body
result. `hash_path_exact` zero-initialized a `FILE_ID_INFO` value and passed it
to `verify_handle_exact` as an output slot. `verify_handle_exact` first required
that zero value to equal the current file identity:

```c
ok = strcmp(hex, expected_sha) == 0 &&
    (identity == NULL || same_identity(identity, &current));
```

Only after that comparison passed did the function attempt to populate an
empty identity. That assignment was unreachable for a real file. Consequently
every fixed subject checked through `hash_path_exact` with a local identity
output was refused even when its exact size and SHA-256 matched. The first row
was the unchanged V3r19 source, which explains the observed label and exit
code.

## Append-only repair boundary

V3r20 must use distinct operations for:

1. validating exact path/size/digest and capturing the observed identity; and
2. validating exact path/size/digest against an identity that is already
   bound.

Its hostile/static test must reproduce the V3r19 zero-identity failure and
prove the V3r20 capture path succeeds without weakening later same-handle
identity comparisons. V3r20 requires its own exact seal and a different fresh
review before any one-shot invocation. Static success will still stop before
the plan builder, broker/process, AFES, Blender, body, save, render, and export.

No body or anatomy completion is claimed.
