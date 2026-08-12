# Kira R24 one-shot author transaction v2 independent rejection — 2026-08-09

Status: **V2 PRESERVED, INERT, AND REJECTED FOR EXECUTION.**

V2 materially improved process ordering and passed `27/27` focused tests
(`41/41` with preserved v1), but a new independent audit found remaining
native cleanup and append-only gaps. No Blender process or `attempt_01` ran.

Preserved hashes:

| Artifact | SHA-256 |
|---|---|
| v2 worker | `620b76f55d445376103da5e9a46cea2a2c1a36e20229b49548a47c5fb646a24a` |
| v2 controller | `131c61358309b4fba3aea4fe2040ceef90c7611bcf499c19ffdcdc9dcc62a6f6` |
| v2 tests | `c0514872f866f8779499268b7191a8d57df51ef8430fdb7104f493daa5cc265b` |
| v2 checkpoint | `9f5ecfc637a9abc02cc5f9a4c480961db7f14d78cd801abc9bbb139844ec4676` |

Remaining blockers:

1. `CreateProcessW` can succeed and then inheritability restoration can fail
   before the child mapping returns. Outer cleanup then has no process/thread/
   stream handles and cannot prove termination/wait of the suspended child.
2. Pre-create stream/inheritability errors can leak handles, and later cleanup
   failures are suppressed instead of becoming acceptance failures.
3. The nonce staging Blend still uses check-then-save with
   `check_existing=False`; the separate reservation sentinel does not reserve
   the actual staging target. Final `MoveFileExW(..., 0)` publication is safe,
   but staging is not.
4. Worker paths are resolved before leaf reparse inspection, so alias identity
   can be erased before the promised early rejection.
5. The suite relies on fabricated child/native records and does not exercise a
   harmless real suspended-process lifecycle, the post-create failure window,
   or integrated reservation lifetime.

Verified v2 strengths include suspended launch before Job assignment/resume,
exact resume count, distinct role/PID/nonce/command records, empty Job and
post-close PID checks, one author plus one reopen with no retry, atomic
no-replace final publication, and authority failure before source/Bpy/process
use. These do not cure the blockers.

Any correction must be append-only v3. Do not edit or run v2.
