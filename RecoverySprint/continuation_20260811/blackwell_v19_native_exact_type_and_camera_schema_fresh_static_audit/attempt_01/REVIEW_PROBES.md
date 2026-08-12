# Voice V19 different fresh static review probes

Recorded UTC: `2026-08-12T00:27:55.1151742Z`

Verdict supported: `ACCEPT_STATIC_ONLY_NO_EXECUTION_AUTHORITY`

## Exact package and closure

- The frozen transplant inventory is the exact 2,676-byte, 16-row inventory
  with SHA-256
  `499116237275626947a7efc7d840503e2f3cf1ff24cba1f5818ac68f88ffe7e3`.
- All 16 installed author artifacts matched their expected byte counts and
  SHA-256 values before and after review. Their stable file identities also
  matched before and after.
- The canonical compact seal is 23,616 bytes, SHA-256
  `1247fce7561f9d47ab0f013b6b98ef0a12ff33eb627bd874c28caa9c94d66713`.
  All 110 declared rows were present, byte/hash exact before and after, used
  110 unique canonical paths and 110 unique file identities, and contained no
  reparse-point subject. There was zero before/after drift.
- The seal's ordered closure binds the V19 source, header, executable,
  configuration, contract, and README; the complete V18 closure and remaining
  author artifacts; all six V18 rejection records; and root attempts 44/51.
  V17 remains consumed and V18 remains rejected/uninvoked.

## V18 blocker 1: exact Python result types and identities

The V19 result gate resolves the exact built-in type objects through the exact
sealed Python DLL and checks `PyObject_Type(value)` identity before any tuple,
Unicode, truth, or integer value conversion. It then enforces the exact `True`
or `False` singleton address and signed-64-bit conversion/error/value gates.
The gate contains no `PyObject_IsTrue` or equivalent generic-truth call.

The provided non-candidate harness passed 100/100 and covered all 25 refusal
codes/stages, seven wrong truthy/falsey object cases, two wrong-but-convertible
integer cases, integer overflow, singleton identity, bounded exception text,
and receipt layout. A separate independently written native harness passed
31/31. It proved:

- an exact tuple of ten with exact built-in fields is accepted by the isolated
  gate;
- tuple and Unicode subclasses/impostors are refused before tuple-size or text
  conversion;
- truthy non-Booleans and exact-Boolean-type non-singletons are refused;
- index-convertible/non-exact predecessor and graph objects are refused before
  their integer conversion hooks can run;
- wrong false-field type and wrong Boolean singleton identity are refused; and
- the candidate entrypoint and Python were both unreachable/uninvoked.

The exact 25-predicate contract list has digest
`ed5f1c4cc6491dee07def1eefc0b7d22562e6dc21167221a98114d0fac14902e`.
An independent semantic-order source probe refused 16/16 removals/additions,
including every type export, type gate, singleton gate, both integer
conversions, and an injected generic-truth conversion.

Conclusion: V19 closes V18's result-field type-predicate blocker at the static
native-control boundary.

## V18 blocker 2: matched camera timing schema and enforcement

The sealed contract now defines exactly four conditions:

1. camera off, ordinary conversation;
2. camera on with preview/local cues only;
3. camera on with one explicit still and a sensory question; and
4. the post-still follow-up after the cue was consumed.

It binds 51 monotonic timestamp names covering user speech/transcript,
permission/open/preview, capture/draw/JPEG/handoff/local cue, vision
lock/load/inference/first output/unload, chat queue/text load/generation/first
token/unload/display, voice queue/load/ready/synthesis/first sample/audio ready,
playback, camera close, and trial completion. It binds 42 metadata fields for
matched prompt/state/history/limits, exact Qwen and voice identities, queue
depths, residency, GPU/VRAM/CPU samples, in-flight state, permission,
frame/cue handling, event-sequence integrity, and raw-frame retention. It also
binds 30 named durations and 15 ordering/condition requirements.

The five exact ordered-list digests are:

- conditions:
  `21e4ee72284e09b5c5d3f087db8ffdebc5e6e397294336d51c8436f3645db21d`;
- timestamps:
  `4949adcee0379ad1a1b9a7b0e86b1115cccff21ef94b83c50a593a084736781d`;
- metadata:
  `9cc49ae4da566ee9d2b42dad46e9f7375b85e571345a057be80588f2c244d8f9`;
- durations:
  `435b48a7e724e34eec2ed6410ad8c74bdad9d3ca608b3b1ad6971970eaec46b0`;
- ordering:
  `322b7b8d1cfb70bbbcf2f1d69157fca74c6c68f956b3a36d688b38ae3d25d55a`.

The installed PostSeal test parses and asserts every ordered member, not only
the counts or the contract file hash. The independent digest/type validator
refused 15/15 in-memory contract mutations: missing, duplicate, and reordered
members; stale model identity; nonzero Qwen keep-alive; executable/live claims;
raw-frame retention; private-state inclusion; and camera authorization.

The schema is explicitly non-executable and contains no measurements. It is a
requirements catalog for a later executor, not proof that a runtime recorder
exists or that camera lag improved. Current face recognition, identity
inference, enrollment, and image/template persistence remain off under the
separate owner-discussion hold; that later topic is not a V19 blocker.

Conclusion: V19 closes V18's incomplete-and-untested schema blocker at the
static requirements/test boundary.

## Manifest, provenance, and substitution attacks

An independently written native whole-document parser harness passed 20/20.
Starting from the exact installed seal, it refused a wrong expected count,
trailing newline, truncation, trailing junk, declared-count mutation,
subject-digest mutation, subject-path mutation, duplicate expected path,
reordered actual rows, and duplicated actual row. It also accepted an ordinary
canonical relative path and the single allowed Python-DLL absolute path while
refusing parent/dot/empty segments, a leading slash, backslashes, and colons.

Source inspection confirms the candidate locks the seal, exact header/image,
and all 108 other closure subjects with stable handles and file identities,
parses the exact canonical document and EOF, requires ordered set equality,
and rechecks handles before and after the isolated control. Its fixed audit
input grammar is separate from this review. This review deliberately did not
create the candidate-consumable V19 audit TSV or sidecar, because a static
acceptance must not create live authority.

## Build, analysis, and boundary

The exact installed source independently rebuilt with MSVC x64 19.50.35730
under `/W4 /WX /O2 /MT /guard:cf /std:c17`. Candidate, provided hostile, and
both independent harness analysis passes produced zero defects. Installed and
rebuilt PE inspection shows x64 PE32+, high-entropy VA, ASLR, NX, CFG/CF
instrumentation and FID table, with imports only from `bcrypt.dll` and
`KERNEL32.dll`.

The V19 candidate, V17, V18, Python, model, GPU, synthesis, audio, playback,
camera/device, live timing, person/private state, body/Blender, production,
network, and Sarah routes were not invoked. Fixed V19 run evidence/outcome
paths and the Kira V19 audit directory remained absent. No latency or speed
improvement is claimed.

## Review decision

There is no remaining V18 repair blocker in the exact static package reviewed.
The decision is `ACCEPT_STATIC_ONLY_NO_EXECUTION_AUTHORITY`. It accepts the
V19 bytes as a faithful static repair and nothing more. A separate append-only
execution-authority package and another different audit are required before
any bounded Python control, model, camera, voice, audio, playback, or latency
operation can be considered.
