# Blackwell voice V16 different fresh static audit checkpoint

Recorded UTC: `2026-08-11T18:24:01.7062503Z`

Decision: `REJECT_STATIC_NO_EXECUTION_AUTHORITY`

V16 status: `REJECTED_UNINVOKED_APPEND_ONLY_REPAIR_REQUIRED`

Execution authority: `NONE`

Exact instruction: `DO_NOT_RUN_V16`; `DO_NOT_RERUN_V15`.

## Outcome

The exact 41-row Kira closure is intact and independently rebuilds cleanly,
but the exact compiled V16 seal parser fails four required hostile refusals.
It accepts terminal dot segments, accepts trailing non-JSON bytes, and accepts
a valid 42-subject JSON seal containing a whitespace-formatted logical
duplicate while the original exact row remains accepted once. That directly
contradicts the structural/canonical, duplicate-rejecting, wrong-total-row
contract.

No static acceptance or disconnected one-shot validation authority is issued.
This result proves no synthesis, playback, audible speech, or latency
improvement.

## Exact evidence

- `INDEPENDENT_AUDIT.tsv`: 912 bytes,
  `b0be9d89730bf864978fef5e33740e0f34399150f177b47b2841edab7ca94371`.
- `INDEPENDENT_AUDIT.sha256`: 65 bytes,
  `be75c341c5df0ea0aea545eda21a3278f245559ae429820bfb9b465145a06c90`.
- `AUDIT_DECISION.json`: 7,023 bytes,
  `eb8cf761a7821df044a45f81062f7accc7832e2e3b8b993124b4dca63d0fd412`.
- `CLOSURE_REHASH.tsv`: 10,360 bytes,
  `d6af2190a12efb57a9c794582ada027d9a9dc0fb6116a996c0a4cc07189ddf5f`.
- `PARSER_PROBE_RESULTS.txt`: 3,613 bytes,
  `1a8a57469e770d5bb16f78619a09777741deec7069cfd31d124f525836113d72`.
- `REVIEW_PROBES.md`: 7,234 bytes,
  `517541cb2e47eab433148f00eba23fc02181deae9bc39d46cc2d92b4df38fe94`.

The V16 author seal remains 9,065 bytes,
`b02ecdace1727a5ab9e8dba9a580932fe886e9ae05561f5241b1fbbffc21acd4`.
All 41 subjects and 41 unique paths rehashed exact before and after, with zero
mismatches and closure-table aggregate
`25e17ef12188944d23615cdf6fd4118d9433cb88270052cef0eca13c23ad9b7a`.

## Independent controls

- V15 mismatch reproduced exactly: 0/21 old spaced path matches, 21/21
  compact path matches, and 21/21 exact compact complete rows.
- Independent strict x64 `/W4 /WX /O2 /MT /guard:cf` build: pass, zero
  diagnostics.
- Independent strict `/analyze /W4 /WX`: pass, zero diagnostics and empty
  59-byte defect report.
- Sealed and independent PE: x64 PE32+, High Entropy VA, ASLR, NX, CFG,
  CF-instrumented, FID table, `0x33` Guard CF functions; imports only
  `bcrypt.dll` and `KERNEL32.dll`.
- Scratch harness includes the exact V16 C source but renames and never calls
  candidate `wmain`; only three static parser functions were tested in memory.

## Blocking repairs

Preserve V16 unchanged and author V17 append-only. V17 must parse the whole
manifest or an equivalently exact bounded grammar, count actual expected
unique subjects, reject trailing bytes and every extra/duplicate/whitespace
row, reject dot and dot-dot in every path-segment position, give audit/seal/
binary-receipt fields exact V17 provenance, and execute the exact compiled
parser in hostile tests. The four V16 bypasses must become negative controls.

A new V17 seal and another different fresh audit are mandatory before any
later bounded disconnected static-control decision.

## Boundary

- Kira edits by reviewer: `0`.
- V15/V16 candidate invocations: `0/0`.
- Python/model/GPU/synthesis/audio/playback/latency/network calls: `0`.
- Person/body/Blender/production calls: `0`.
- V16 run evidence and terminal receipt created: `false/false`.
