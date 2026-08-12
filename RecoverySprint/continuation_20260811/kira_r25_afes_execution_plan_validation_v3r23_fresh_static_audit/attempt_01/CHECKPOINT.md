# Kira R25 AFES execution-plan validation V3r23 different software-quality review

Recorded UTC: `2026-08-11T16:44:09.8847084Z`

Decision: `REJECTED_NO_EXECUTION_AUTHORITY`

Auditor: `codex_r25_afes_v3r23_quality_reviewer`

Author: `codex_r25_afes_v3r23_static_author`

## Outcome

V3r23 is rejected without execution. Its static seal, independent rebuild,
MSVC analysis, PE mitigations/imports, non-calling `__annotate__` fingerprint,
bounded counters/checkpoints/exception buffers, post-Python retained rechecks,
cleanup, and stop-before boundary all pass review. The supplied PowerShell
suite was run exactly once in `PostSeal` mode and returned
`V3R23_HOSTILE_STATIC_TESTS_PASS`.

The blocking defect is the sealed package's stated V3r22 failure diagnosis.
Both V3r22 and V3r23 compile the retained controller with
`flags=0x1000000, dont_inherit=True`. The locked CPython 3.14 header defines
that bit as `CO_FUTURE_ANNOTATIONS`; the exact retained stdlib's
`__future__.py` says it makes annotations strings, and the installed locked-
version CPython test requires a future-compiled function's `__annotate__`
value result and `__annotations__` to contain annotation strings. Thus
V3r22's reads cannot resolve the missing `Any`, `Mapping`, `Sequence`, or
`BaseException` globals into the claimed `NameError`. The authored suite
checks only for a future import in controller text and overlooks the explicit
compile flag.

V3r23's non-evaluating thunk binding is itself sound, and its new telemetry
would be useful. Those facts do not make the incorrect root-cause narrative
acceptable for a success-or-failure-consumed one-shot candidate. The exact
actual V3r22 stage-40 cause remains unknown.

## Exact static closure

- Seal: 137,189 bytes, SHA-256
  `44061c604c795b5715f17669fdc82df927d5900b1da835f335b7c262aae83aef`.
- Rehash: 257/257 subjects, 257 unique paths, zero missing files, zero byte
  mismatches, zero SHA-256 mismatches.
- Role counts: 8 current artifacts, 120 runtime fixed bindings, 137 retained
  manifest rows; overlapping roles agree.
- V3r22 closure: 20/20 unique rows, canonical 3,779 bytes, SHA-256
  `7057deb657f5e235892180e5d694f139450d44897f9353ac3bdb1f15d730aec0`.
- V3r22 remains `CONSUMED_FAILURE_DO_NOT_RERUN`: one invocation, exit `1`,
  completion state `3`, terminal stage `40`; no exact plan-call count is
  claimed.

## Independent build and PE result

The exact 138,833-byte C source at SHA-256
`6345fc66582ec65d00a5b175f35371dec6d76d3c5408ad29b08e86292d69b947`
was compiled directly from Kira with outputs isolated under this review root.

- Strict `/W4 /WX /O2 /MT /guard:cf /std:c17`: exit `0`, zero warnings,
  zero errors.
- Rebuild object: 216,005 bytes, SHA-256
  `314c7a4417026a343e91095570dd6b42568666ad637cd8e042589bd3d1d0fe35`.
- Rebuild executable: 253,952 bytes, SHA-256
  `10e769e6d1048231170ecd2a5b2b22f02bd4f5fc4621c6745c12b824e0371e38`.
- Independent `/analyze /W4 /WX`: exit `0`, zero unsuppressed diagnostics,
  no suppressions.
- Analyzer object: 147,657 bytes, SHA-256
  `9f4fbf5f870a17d76bb49c70d1923b3a88557cadc7fb84d1ba73a40bb74dc0e6`.
- Analyzer XML: 59 bytes, SHA-256
  `ba052e3b011b8f8a3e59a7b5c3120d3c9496a6c3e2fd73c55013bde5e2642bc5`;
  its defect list is empty.
- Rebuilt PE: x64/PE32+, high-entropy VA, ASLR, NX, CFG, CF instrumented,
  FID table present.
- Exact direct DLL imports: `bcrypt.dll`, `KERNEL32.dll`; no static Python or
  process/shell import.

The sealed and scratch executables were not invoked.

## Exact rejection artifacts

- `INDEPENDENT_AUDIT.tsv`: 1,376 bytes, SHA-256
  `8420cef3dd9015c6924fb84f5e361e7a6c6f639aa30737adbf2a42a8628919f1`.
  It is exactly 22 LF-terminated lines with no CR or NUL. Its rejection
  decision intentionally cannot satisfy V3r23's acceptance grammar.
- `INDEPENDENT_AUDIT.sha256`: 65 bytes, SHA-256
  `0bf5987d62c741eaa8b6e2a0f815e517bf86c362c1533602eadfb9bcd5893fbb`.
- `AUDIT_DECISION.json`: 5,990 bytes, SHA-256
  `ab376b6ae6b251895dfb9199a1dd7a7f01b92c50cf1d6d71282a492f231753b6`.
- `HOSTILE_STATIC_PROBES.txt`: 8,130 bytes, SHA-256
  `682820476c78fe3ef01e87601852408251c262a73ffe583b2a58031ac7fe1727`.

## Scope and next step

No V3r23 or V3r22 executable, Python runtime/controller, plan callable,
bootstrap, broker/process path, AFES, Blender, body, anatomy, save, render, or
export operation was invoked. V3r23 evidence and receipt paths remain absent.
No Kira file was edited.

Preserve V3r23. An append-only successor must correct the
`CO_FUTURE_ANNOTATIONS` truth, identify the actual V3r22 stage-40 cause or
honestly leave it unknown, retain the useful bounded telemetry and stop-before
controls, create a new exact seal, and obtain another different fresh audit
before any bounded execution can be considered.
