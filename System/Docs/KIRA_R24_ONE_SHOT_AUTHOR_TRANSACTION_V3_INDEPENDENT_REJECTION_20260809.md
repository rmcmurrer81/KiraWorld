# Kira R24 one-shot author transaction v3 independent rejection — 2026-08-09

Status: **V3 PRESERVED, INERT, AND REJECTED FOR EXECUTION.**

V3 passed `20/20` focused and `61/61` combined v1–v3 tests, including harmless
real Windows suspended-process/Job lifecycle checks. An independent read-only
audit nevertheless found two strict boundaries unresolved. No Blender process
or `attempt_01` ran.

Preserved v3 hashes:

| Artifact | SHA-256 |
|---|---|
| worker | `df50a0b4729aae33aaa4abd571b053062d0af194606d7ec3b4b8544e018e674c` |
| controller | `6c5f01bd73a50dddd4372385265ce198191a7659aa09dcf114af0402b939bd8f` |
| tests | `2e6c0e025257ca959ea35cd12f7630400ed2b8446fae95ed28001cdd466a6f03` |
| checkpoint | `92849d4f2bf6ed003b4f7f6a709e9f1e4f9d50a5d40b93c774f106a381431683` |

Remaining blockers:

1. `CreateProcessW` writes process/thread handles into a local structure, then
   Python copies them into the cleanup context. An asynchronous/BaseException
   during those immediate assignments can still leave some live handles
   outside the cleanup owner. The tested injected failure occurs later.
2. Blender's private save remains absence-check followed by
   `save_as_mainfile`. `check_existing=True` is not Win32 `CREATE_NEW` and the
   held reservation covers a JSON sentinel, not the actual staging Blend. A
   raced file/reparse target can therefore be overwritten before the two later
   `MoveFileExW(..., 0)` no-replace publications.

Verified closures include real suspended Job assignment/resume/cleanup,
propagated cleanup failures, no injectable production runner, raw junction
rejection before resolution, reservation across both child lifetimes, distinct
role/PID/nonce/command evidence, post-Job PID checks, atomic no-replace final
publication, one author plus one reopen, and zero retries.

The staging race has now survived two bounded controller successor repairs.
Do not start another minor controller variant automatically and do not weaken
the claim. V3 remains useful inert infrastructure; execution requires a
genuinely different staging mechanism or an explicit owner decision to narrow
the accepted threat boundary after review.
