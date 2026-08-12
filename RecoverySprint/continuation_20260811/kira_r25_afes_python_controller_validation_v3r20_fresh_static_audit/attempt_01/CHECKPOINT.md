# Kira R25 AFES Python/controller validation V3r20 different fresh audit

Recorded UTC: `2026-08-11T10:27:11.8795146Z`

Decision: `REJECTED_NO_EXECUTION_AUTHORITY`

## Outcome

The different reviewer rehashed all 76 unique V3r20 sealed subjects with zero
drift, independently rebuilt the exact source under strict x64 MSVC flags, and
confirmed the sealed and rebuilt PE images are x64 PE32+ with high-entropy VA,
ASLR, NX, CFG, and only `bcrypt.dll` plus `KERNEL32.dll` imports. The exact
V3r19 zero-identity failure reproduced in a native negative probe. V3r20's
capture/bound split passed correct capture, retained identity recheck,
zero/wrong-identity refusal, failed-hash no-output-mutation, and hostile audit
grammar checks.

V3r20 is nevertheless rejected and must not be run. Independent MSVC
`/analyze` proved two real out-of-bounds literal reads:

1. source line 851 copies 34 bytes from
   `"KIRA_R25_AFES_V3R20_RESERVATION"`, a 31-character object with only 32
   readable bytes including its terminator;
2. source line 894 copies 31 bytes from
   `"KIRA_R25_AFES_V3R20_TERMINAL"`, a 28-character object with only 29
   readable bytes including its terminator.

Both are `C6385` diagnostics and both read two bytes beyond the C string object
into durable receipt magic. Sealed executable inspection confirms the first
overread consumes the terminator plus `K`,`I` from the adjacent terminal
literal; the second consumes its terminator and two adjacent layout bytes.
This is undefined behavior, not merely a theoretical warning.

## Other analyzer guidance

The analyzer also reported two large stack frames, conservative termination
reasoning in `exact_final_path`, and a conservative possible-NULL handle at
cleanup. These are not separate V3r20 rejection findings, but V3r21 must remove
them without suppressions: heap-allocate the two 32,768-wide-character buffers,
set path terminators explicitly, and use one exact valid-handle helper.

## Scope truth

V3r20 was not invoked. The independent rejection TSV and its digest sidecar
are preserved in this directory; their rejection decision cannot satisfy the
candidate's exact accept grammar. No evidence or receipt was reserved. No
Python, controller, plan, broker/process, AFES,
Blender, body, anatomy, save, render, or export path ran. This is a native
control-plane rejection and proves no body result.

## Required next step

Preserve all V3r20 bytes. V3r21 must be append-only, copy receipt magic using
`sizeof(literal) - 1`, assert each magic fits its zero-initialized destination,
make the analyzer guidance exact, and pass `/analyze` with zero unsuppressed
warnings in addition to the inherited strict build and hostile suite. It then
requires a new exact seal and another different fresh audit before any one-shot
invocation.
