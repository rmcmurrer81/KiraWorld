# Blackwell voice V17 different fresh static review probes

Recorded UTC: `2026-08-11T21:18:05.8836144Z`

Decision: `ACCEPT_STATIC_ONLY`

Candidate authority: at most one later no-argument disconnected V17 static-
control validation after exact audit installation and a new root preflight.

## Boundary honored

- Kira was read only. Compiler, analyzer, and hostile-harness outputs stayed
  under `Documents/Codex/2026-08-11/c/work/voice_v17_audit`.
- V15, V16, and V17 candidate executables were not invoked. The installed and
  independently rebuilt parser harnesses rename candidate `wmain`; their own
  entry points call only in-memory parser functions.
- Python, a model, GPU, synthesis, audio, playback, latency, network, camera,
  microphone, speaker, person state, body, Blender, Sarah, and production
  routing were not invoked.
- `RUN_EVIDENCE_V17.jsonl` and
  `STATIC_CONTROL_OUTCOME_V17.receipt.bin` remained absent.

## Controlling truth and exact package

The reviewer read the current truth supersession registry, current test-
execution boundary, handoff, newest root checkpoints including attempt 32,
the complete V17 author checkpoint/package/build/control records, config,
contract, README, 55-row seal, exact C source, identity header, executable,
PowerShell static suite, parser harness source/fixture/executable, and the
complete V16 seven-file rejection closure plus its 41-row predecessor seal.

The controlling boundary preserves V16 as rejected and authorizes V17 static
parser work and a different audit only. It grants no voice or latency run.
Attempt 32 records the exact 17-file V17 install and no invocation.

All 17 installed V17 author artifacts matched their author inventory before
and after review. The canonical inventory is 2,818 bytes, SHA-256
`a80b4ec7cca68bb3042af26d6ca59d0ce36424c7e6bcf6d4ac7b2efc7d43dee7`.
The review's explicit 17-row before/after table is
`AUTHOR_PACKAGE_REHASH.tsv`.

All 55 sealed rows matched exact sizes and SHA-256 values before and after,
with 55 unique paths and no duplicate size/digest pair. The manifest is
11,748 bytes, SHA-256
`64fad216711534d8e1e3c014ae616fc651b36f70847c6efc18d55566dc5ab75a`.
The per-row review evidence is `CLOSURE_REHASH.tsv`.

## V16 rejection closure

The preserved V16 decision is
`REJECT_STATIC_NO_EXECUTION_AUTHORITY`. The reviewer independently confirmed
that its exact closure records four blockers: raw substring parsing accepted
trailing bytes, a whitespace-form logical duplicate/extra subject, and
terminal dot segments, while binary outcome/audit/seal labels retained stale
V15 provenance.

V17 closes those defects structurally: it parses an exact canonical document
through EOF, counts actual objects, requires 55 ordered unique locked
Bindings, validates every path segment, and uses V17-only audit, receipt,
evidence, and outcome identities. V16 was not invoked.

## Installed PostSeal and exact author harness

The installed non-candidate PostSeal suite returned:

`V17_WHOLE_DOCUMENT_MANIFEST_HOSTILE_STATIC_TESTS_PASS phase=PostSeal compiled_checks=83 source_mutants=6 sealed_subjects=55`

The reviewer independently rebuilt the exact installed author harness with
MSVC x64 19.50.35730 using `/W4 /WX /O2 /MT /guard:cf /std:c17`. It compiled
without diagnostics and returned `SUMMARY checks=83 failures=0`:

- object: 180,851 bytes,
  `911795b76c9887c7ce2de92ace7615aef239d8de1e7803989f8dc143c292df70`;
- executable: 184,320 bytes,
  `5ebff26daf9cecc3b716fe4b15c30ec9133f2cfe1f5e1077ffd8dd6a6319805d`.

## Independent 153-check exact-parser harness

A separate 29,626-byte audit harness, SHA-256
`a73c62124972de32d2895bc8c38328c76400f06b08ed467e1e1599bde7dd9bd5`,
included the exact installed C source while renaming candidate `wmain`. Its
own entry point exercised only parser functions over in-memory fixtures. The
strict build was clean, and it returned `SUMMARY checks=153 failures=0`:

- object: 209,244 bytes,
  `665447e44a90d3985b121f78af345c0e6dfdec48242050c41e58aa6c33d3a7f4`;
- executable: 193,024 bytes,
  `49b8510f8972b6ddfbc249930d25e21000d0b98c8b65994bcf97868ecbcfaaa4`.

The probes cover exact top-level order/types and row order/types; EOF and all
trailing-byte classes; actual count, unique paths, exact ordinal set equality,
missing/extra/duplicate/reordered rows; every requested dot, dot-dot, empty,
backslash, colon, control, DEL, NUL, and non-ASCII path class; the sole exact
locked Python path exception and its aliases; canonical positive uint64,
maximum value, zero/type/overflow attacks; exact lowercase 64-digit digests;
whitespace logical duplicate/extra subject; and cross-row splicing.

The 11,748 manifest bytes contain zero JSON whitespace, NUL, or non-ASCII
bytes. Top-level and row property order is exact. The 53 static subject paths,
53 byte macros, and 53 digest macros map without mismatch to manifest row 0
plus rows 3 through 54; audit-bound header and self rows occupy rows 1 and 2.

## Independent candidate build, analyzer, and PE

The exact installed candidate source was independently rebuilt in scratch
with MSVC x64 19.50.35730 using `/W4 /WX /O2 /MT /guard:cf /DUNICODE
/D_UNICODE /std:c17 /I C:/Python314/include`. Build exit was zero with zero
diagnostics:

- object: 127,097 bytes,
  `6ddce9bcb11f60b18fd36017b7bcfe838ccdc4c6da3dacce90ba047e470867c8`;
- executable: 157,696 bytes,
  `8854c04f2b71ebaf661ee1e24860d2f9626fbd20e0decbeb2bd56c2c6120e07e`.

Separate `/analyze /W4 /WX /c` also exited zero with no unsuppressed
diagnostics:

- analyzer object: 76,696 bytes,
  `e95d407bd559399e711dae221d70c9fed92de7294a81a4d6bcee0fa22fa26a90`;
- empty 59-byte report,
  `ba052e3b011b8f8a3e59a7b5c3120d3c9496a6c3e2fd73c55013bde5e2642bc5`.

Both sealed and independent binaries are x64 PE32+, high-entropy-VA, ASLR,
NX-compatible, CFG/CF-instrumented with FID table and Guard CF count `0x32`.
Imports are exactly `bcrypt.dll` and `KERNEL32.dll`; there is no static Python,
process-shell, model, audio, or network import.

## Native memory, length, identity, and provenance review

No input-reachable memory, integer-length, parser, or file-alias bypass was
found. Manifest path and digest buffers are bounded; decimal accumulation
checks uint64 overflow; object and expected counts are fixed at 55; parsed
paths are unique and ordinal-bound; the current closure has no duplicate
size/digest pair; and each input is held as a regular, non-reparse, exact-
final-path handle with size, digest, and `FILE_ID_INFO` rechecks.

The executable and independent build contain the exact V17 audit magic,
decision, reservation/terminal magic, audit paths, seal path, suffixed evidence
and outcome names, and V17 JSONL schemas. They contain no V15/V16 binary
receipt magic or stale unsuffixed V16 output names. V15/V14 graph names remain
only as deliberate sealed retained-static-control provenance; they are not
mislabelled V17 audit or output records.

## Decision and strict scope

The V17 native-parser repair is accepted static-only. Root may preserve the
acceptance without running anything, or may exactly install the staged 27-line
audit transcript and 65-byte sidecar, rehash them, freshly recheck 17/17
author artifacts and 55/55 seal rows, confirm both outputs absent, and then
invoke the exact V17 executable once with no arguments from the Kira root.
Success or failure consumes that authority; there is no retry.

That one operation can only validate the retained sealed static Python control
graph. It is not synthesis, playback, audible speech, a latency measurement,
or a live voice result. It grants no V15/V16 run, model, GPU, camera, network,
person, body, Blender, Sarah, production, or other live authority.
