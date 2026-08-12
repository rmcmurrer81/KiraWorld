# Voice V18 local quality review results

Recorded UTC: `2026-08-11T23:42:52.5776722Z`

Decision: `REJECT_STATIC_NO_EXECUTION_AUTHORITY`

## Boundary

Kira was read-only. Voice V18 and Voice V17 were not invoked. Python, model,
GPU, synthesis, audio, playback, camera/device, person, body, Blender, Sarah,
network, and production routes were not invoked. The isolated rebuilt V18
image is named `kira_blackwell_voice_control_anchor_v18_rebuild_DO_NOT_RUN.exe`
and was not invoked.

## Exact package and closure

- Frozen author package before/after: `16/16` exact.
- Static seal before/after: `86/86` exact, `86` unique canonical paths,
  `86` unique file identities, zero reparse subjects, zero byte/hash mismatch.
- Seal: `18,517` bytes, SHA-256
  `9206d5b719f7edaf9be3036877814459ff02cb90a704b76452dabc13774f14a5`.
- Author rehash: `AUTHOR_PACKAGE_REHASH.tsv`, `2,870` bytes, SHA-256
  `0bf9f11cdc45bc9c90dfbcb2b51fc6af8dd41835c32e088cee43cff3c43bd9f4`.
- Closure rehash: `CLOSURE_REHASH.tsv`, `16,381` bytes, SHA-256
  `c6a9195dea29c24cb56718f9513c8c51b38629c3c7d5e84c429d07fa8a900690`.
- V18 run evidence, V18 receipt, and the fixed future Kira audit TSV/sidecar
  remain absent before and after review.

## Passing quality checks

- Installed PostSeal: pass; reported `62` compiled mock checks, `12` source
  token-removal checks, and `86` sealed subjects.
- Provided non-candidate mock: pass, `62/62`, with candidate entry point and
  Python both uninvoked.
- Isolated strict x64 build: pass with `/W4 /WX /O2 /MT /guard:cf /std:c17`.
- Isolated `/analyze /W4 /WX`: pass; analyzer XML is empty.
- Installed and rebuilt PE files are x64 PE32+ console images with high-entropy
  VA, ASLR, NX, CFG/CF instrumentation, a 32-entry FID table, and imports only
  `bcrypt.dll` and `KERNEL32.dll`.
- The four documented broad result categories are present in source: null call
  with exception, null call without exception, non-null result refusal, and
  post-validation recheck failure. Pre-call, call-return, result-validation,
  and post-validation pass stages are present.
- Bounded error text uses 64-byte type and 192-byte message arrays, replaces
  non-ASCII, folds CR/LF/tab, and always leaves a terminator.
- Retained validator identity is exact: 21,931 bytes, SHA-256
  `2bf232b07b0b7b93de8776f5210bd2d89068ad76cb4ee46555b861ad2818d16a`,
  `_kira_blackwell_v15_private_native_validator`,
  `validate_static_control_graph_v15`, schema
  `kira.blackwell.v15.native_validator_result.v1`.
- V17's consumed failure evidence is exact. Its source assigns stage 50 before
  one combined call/result gate, and its receipt contains no substage or error
  text, so `UNRESOLVED_WITH_CURRENT_TELEMETRY` is reproduced. V17 must not run.
- V18 does not claim Llama as the current text route.

## Blocking mismatch 1: documented field types are not enforced by V18

The contract names `success_boolean_true`, `predecessor_count_integer`,
`graph_count_integer`, and six Boolean-false fields. The native checker does
not perform a Boolean-type or integer-type test:

- source line 1197 and lines 1227-1234 use generic `PyObject_IsTrue` behavior;
- source lines 1204 and 1216 use conversion through `PyLong_AsLongLong`;
- the source contains no exact Boolean, integer, tuple, or Unicode type guard.

Generic truth conversion accepts non-Boolean truthy/falsey objects. Integer
conversion can accept integer subclasses or index-convertible objects. The
provided mock does not cover those cases: its helper itself refuses every
kind except `FAKE_BOOLEAN` or `FAKE_LONG`, and its Boolean cases only change
the truth value of an object already labeled `FAKE_BOOLEAN`. Therefore the
mock can pass while V18's documented type predicates remain absent.

Required append-only repair: add explicit type checks before value conversion,
give type and value failures unambiguous receipt codes/stages, and extend the
provided mock with wrong-but-convertible integer fixtures and non-Boolean
truthy/falsey fixtures.

## Blocking mismatch 2: future timing schema is incomplete and untested

The current required matched evaluation includes camera OFF, preview-only,
one explicit still, and the following turn. It requires timestamps for camera
start/preview, capture/draw/JPEG/upload/local cue, vision first output, text
model load/unload and display, voice model ready/first sample, and playback
completion, plus prompt/response/queue/residency/GPU/VRAM/CPU/in-flight
metadata.

V18's contract contains only one `explicit_one_still_only` list of 16
timestamps. It omits the items above and has no matched-condition identifiers.
The PostSeal script does not parse or assert the timing contract; it only seals
the file as bytes. This schema remains non-executable, but it does not yet
preserve the complete current requirement.

Required append-only repair: complete the schema and add exact static checks
for all conditions, timestamps, derived durations, and metadata. This must
remain non-executable and grants no camera or latency run.

## Build identities

- Rebuilt object: `160,118` bytes, SHA-256
  `d1cb0f246fcc0dfd610112e4557dacfbbdd52cc4d991882f1b4a12c850990c78`.
- Rebuilt do-not-run image: `171,520` bytes, SHA-256
  `826a1075ed3ef608b24ff8dafd78901b0c1930893d3ab353e357b43708cbe338`.
- Analyzer object: `92,769` bytes, SHA-256
  `7f931e7ab13070617974a0ab42c8efd0b9578f608bf8015c782b9d55615cda46`.
- Analyzer XML: `59` bytes, SHA-256
  `ba052e3b011b8f8a3e59a7b5c3120d3c9496a6c3e2fd73c55013bde5e2642bc5`.

This rejection does not authorize a V18 run and proves no voice or latency
improvement.
