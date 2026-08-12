# Kira R24 one-shot author transaction v2 static preparation — 2026-08-09

Status: **INERT APPEND-ONLY V2 STATIC PREPARATION; NO BLENDER OR BODY AUTHORITY.**

The first one-shot controller proposal remains preserved as rejected evidence.
This v2 successor closes the controller-boundary findings without changing the
v1 worker, controller, test, or checkpoint. It has not launched Blender, opened
or saved a Blend, created `attempt_01`, mutated a body, rendered a gallery, or
accepted, activated, assigned, exported, or published a candidate.

## Preserved rejected v1 identities

| Project-relative file | Bytes | SHA-256 |
|---|---:|---|
| `tools/blender_author_kira_r24_one_shot_candidate.py` | 20,166 | `3cad1c2fb5a9fff9f52e8ed2e7051955dfa3ad1953b32362669661b441e9d631` |
| `tools/run_kira_r24_one_shot_author_transaction.py` | 27,897 | `cb59960f8a48dd82de2dbd65c313c6df05d4c26176989c5c5e82fe92e18157c8` |
| `Testing/test_kira_r24_one_shot_author_transaction.py` | 15,282 | `bb4cd25d331880537b81f78c444465518a2da2622f377dcf35550576ddba39fa` |
| `System/Docs/KIRA_R24_ONE_SHOT_AUTHOR_TRANSACTION_STATIC_PREPARATION_20260809.md` | 2,255 | `bc118f2be708cd0da30181b59a9427abb2802c746e7ca63fd31448c444554f84` |

## New append-only v2 identities

| Project-relative file | Bytes | SHA-256 |
|---|---:|---|
| `tools/blender_author_kira_r24_one_shot_candidate_v2.py` | 17,085 | `620b76f55d445376103da5e9a46cea2a2c1a36e20229b49548a47c5fb646a24a` |
| `tools/run_kira_r24_one_shot_author_transaction_v2.py` | 50,353 | `131c61358309b4fba3aea4fe2040ceef90c7611bcf499c19ffdcdc9dcc62a6f6` |
| `Testing/test_kira_r24_one_shot_author_transaction_v2.py` | 30,300 | `c0514872f866f8779499268b7191a8d57df51ef8430fdb7104f493daa5cc265b` |

## Controller-boundary corrections

- The controller calls Win32 `CreateProcessW` with `CREATE_SUSPENDED`. It then
  creates and configures a kill-on-close Job, assigns the exact still-suspended
  process, writes a bound authorization gate, and calls `ResumeThread`. The gate
  says `resume_authorized`; it does not falsely claim that resume already
  happened. The controller-owned evidence records the actual return value.
- Failure while creating/configuring the Job, assigning the process, writing
  the gate, or resuming terminates and waits the exact direct child and any
  assigned Job tree before attempting to close every thread, process, stream,
  and Job handle.
- Child evidence is checked from exact records rather than trusted as a caller
  summary: role, nonce, invocation index, command digest, PID, suspended state,
  assignment-before-resume, exact resume count, direct exit, zero exit code,
  Job PID inventory, handle close, exact stdout/stderr paths and hashes, and
  empty pre-close/post-close PID inventories must all validate.
- The author and fresh-reopen children must have distinct PIDs, nonces, command
  digests, roles, and invocation indices. One-author/one-reopen counts and the
  zero-retry value are derived from those two validated records.
- After the Job reports no active processes and its handle is closed, a separate
  bounded `tasklist.exe` inventory checks every observed PID. Any active PID is
  an immediate failure.
- One controller-held Win32 `CREATE_NEW` reservation allows reading but denies
  write/delete sharing for the whole two-child transaction. The v2 test performs
  a real Windows lock check proving write and delete fail until close.
- Blender may save only once to a fresh 256-bit nonce staging name. It rechecks
  that the output is absent and that every parent is a regular non-reparse
  directory immediately before `save_as_mainfile`. It never writes the final
  candidate name.
- Only after the author Job is closed and independently quiescent may the
  controller publish staging with `MoveFileExW(..., 0)`, which cannot replace an
  existing destination. A real Windows test proves byte preservation and
  no-replace behavior.
- Candidate, staging, extraction, log, reservation, and result boundaries are
  append-only and fail closed on existing, symlinked, or reparse paths. R19
  Attempt 06 is rehashed against all 49 manifest entries plus the manifest and
  exact source identity.
- The worker retains one exact `open_mainfile(..., load_ui=False)` call and one
  exact staging `save_as_mainfile` call. It restores neutral pose/action state,
  marks the candidate private/inactive/unassigned/unpublished, and rejects any
  author-operation evidence that claims a save, render, export, activation,
  assignment, or publication.

## Static verification

Command:

`py -B -m unittest -v Testing.test_kira_r24_one_shot_author_transaction_v2`

Result: **27 tests passed; 0 failures; 0 errors.** The suite includes injected
child-record tampering, strict bool/integer confusion, wrong log path/hash,
reparse paths, preexisting targets, Job/assignment/resume failures, active PIDs
after Job close, duplicate PID/nonce/command identity, invalid author evidence,
real reservation sharing, and real no-replace publication tests.

`py -m py_compile` also passed for the v2 worker, controller, and test.

## Remaining blockers

`EXECUTION_AUTHORITY_GRANTED` remains exactly `False` in both v2 programs. The
accepted R5 contract, R5 author-operation callable, R5 gate, and R5 read-only
extractor bindings intentionally remain symbolic (`bytes: None`,
`sha256: None`). Those future files must be sealed, this controller must be
resealed to their exact identities, and a new independent static audit must
accept the combined boundary before a separately authorized bounded run.

There is no runtime attempt at
`RecoverySprint/continuation_20260808/kira_r24_one_shot_runtime_attempts_v2/attempt_01`.
Do not create it from this checkpoint.

Rollback is deletion of only the three v2 files and this v2 checkpoint. Do not
edit, delete, or reinterpret the preserved v1 artifacts, R4 package/audit, R19
Attempt 06, or any accepted body/source evidence.
