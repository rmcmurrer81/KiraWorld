# Kira R25 AFES V3r17 runtime-control checkpoint

Status: `NO_EXECUTION_AUTHORITY`  
Author: `codex_r25_afes_v3r17_static_author_agent`  
Predecessor: `V3r15 CONSUMED_FAILURE_NO_RETRY`

V3r16 remains `REJECT_NO_EXECUTION_AUTHORITY`. Its outer seal, later drifted
bytes, and different-auditor rejection evidence are preserved exactly. V3r17
repairs only the outer-closure freeze discipline and the future-audit binding.

## Exact single stage

`RESERVATION_FIRST_GRANULAR_CONTRACT_LOCK_DIAGNOSTIC_ONLY`

After exact self, sealed-subject, different-auditor, and output-parent gates,
V3r17 must reserve its fixed `RUN_EVIDENCE.jsonl` and binary outcome receipt
with `CREATE_NEW` and write-through. Only then may it open the exact V3r15
contract for read using the documented diagnostic sharing flags.

It records the exact first failing subgate and Win32 error, or an exact success,
for:

1. target open;
2. regular/non-reparse attributes;
3. first exact size;
4. first normalized final path;
5. first file ID;
6. first same-handle snapshot and SHA-256;
7. second same-handle size/path/file-ID checks;
8. second same-handle snapshot and SHA-256;
9. final same-handle size/path/file-ID checks;
10. equality of both snapshots and the sealed expected size/digest.

The target handle remains the same for the entire diagnostic. The broader
share mask is diagnostic-only; stability is accepted only if both complete
snapshots and every same-handle identity/path/size recheck agree.

## Absolute stop

V3r17 contains no retained Python stage. It must not load a Python DLL,
initialize an interpreter, read or evaluate the controller, read the execution
contract, call a plan builder, start a broker or child, access AFES or Blender,
open a Blend, touch a body, or save/render/export anything.

Starting the future executable or creating either fixed output consumes the
one-shot authorization regardless of exit or evidence completeness. There is
no automatic retry and no V3r15 retry.

## Static preparation only

The author may create, compile, inspect, and seal V3r17 without executing it.
One different fresh exact-byte static audit must explicitly issue
`ACCEPTED_FOR_ONE_BOUNDED_CONTRACT_LOCK_DIAGNOSTIC_ONLY` before any later run.
The only exact audit location is
`RecoverySprint/continuation_20260811/kira_r25_afes_contract_lock_diagnostic_v3r17_fresh_static_audit/attempt_01`.
The audit must bind the exact executable, source, identity anchor, contract,
static test, this checkpoint, V3r15 postmortem/recheck, V3r15 contract expected
identity, and preserved V3r15 audit checkpoint.

No production pointer, registry, handoff, body, model, person, voice, media, or
launcher state may be changed by this preparation.
