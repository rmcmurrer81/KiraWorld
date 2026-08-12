# Root multi-lane continuation checkpoint — attempt 10

Date: 2026-08-11 (America/New_York)

Status: `V3R22_DIFFERENT_ACCEPTANCE_CONSUMED_FAILURE_DO_NOT_RERUN`

## Different fresh audit

A different reviewer accepted at most one no-argument V3r22 pure execution-
plan validation. Before granting that narrow decision it independently proved:

- exact seal rehash 237/237 with zero drift;
- strict x64 rebuild and zero-diagnostic MSVC `/analyze`;
- x64 PE32+, high-entropy VA, ASLR, NX, CFG/FID 34, and only `bcrypt.dll`
  plus `KERNEL32.dll` imports;
- both V3r20 C6385 negative controls reproduced;
- exact V3r21 and retained-history canonical closures;
- authored PostSeal pass and 78/78 independent hostile static/mocked probes.

Accepted audit TSV: 1,265 bytes, SHA-256
`b29812ed25f40f83671b532ba46e1d09266844abe02a7dae3b07994f2cba9138`.
Different-review checkpoint: 4,437 bytes, SHA-256
`9a084d40c66dec597ebe5e59f66e2e170a29f7ba5d5adfd21bbf6672c46827cc`.

No candidate, Python, controller, plan, body, or Blender path ran during the
audit.

## Consumed invocation

Immediately before invocation, all 237 seal rows and all five audit records
rehash-exact, the executable was exact, and both fixed output paths were absent.
The sealed V3r22 executable was invoked once with no arguments. It exited `1`.
The single authority is permanently consumed: `DO_NOT_RERUN_V3R22`.

Durable outputs:

- `RUN_EVIDENCE.jsonl`: 607 bytes, SHA-256
  `4f9707fadf2092ecb28da4d9683e01690c5102cc1aac7236cc68ebd622d4b314`;
- `EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin`: 1,016 bytes, SHA-256
  `cf2409244de8a42981e62667e5607e8912bd1d94220bbb09dfd0a79f3a4540bd`;
- exact run outcome: 3,167 bytes, SHA-256
  `83a85c40f630f342d66b3b3dfaa2a864b87b1751533e727e98d5c5d453e9910d`;
- read-only recheck: 2,233 bytes, SHA-256
  `c43e4766e51dd962c6e79f4ec87a724fe830029f7fb265f054a85a1a5784ea52`;
- failure postmortem checkpoint: 2,915 bytes, SHA-256
  `2276f60864f6a5ce31e423081fff3b564fb63c838485397cbdf96d02615da584`.

## Proven failure boundary

The authority contract passed all 15 gates (`32767`) with no gate failure or
Windows error. The completion record has failure state `3` and terminal stage
`40`. Python finalized with result `0`; `FreeLibrary` succeeded; enumeration
checked eight modules and found neither the old module base nor exact Python
DLL path.

Stage 40 is assigned immediately before the embedded validator executes. That
validator contains the pure `_build_execution_plan` call plus many later
checks. Because V3r22 does not persist the Python exception or an internal
checkpoint, durable evidence cannot distinguish failure before, during, or
after that pure call. No exact call count and no successful plan validation is
proven.

The bounded source has no route to bootstrap, broker, process creation, AFES,
Blender, body access/mutation, save, render, or export. None ran. Kira still has
no accepted finished internal or external body.

## Next boundary

Preserve every V3r22 byte and never retry it. Continue only append-only as
V3r23, adding bounded sanitized Python-exception and validator-checkpoint
telemetry sufficient to identify the exact failing predicate. V3r23 requires
new author tests/build/seal and a different fresh audit before any invocation.
