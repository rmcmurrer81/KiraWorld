# Blackwell voice V14 fresh independent static audit checkpoint

Recorded UTC: `2026-08-11T15:31:12.7553998Z`

Reviewer task: `/root/resident_media_v15_author`

Decision: `REJECT`

V14 remains sealed static evidence with no execution authority. The native
executable and V14 Python candidate were not invoked. No model, GPU, voice,
synthesis, audio, playback, latency, network, person-state, body, Blender, or
production operation occurred. The reviewer made no Kira workspace edit.

## Exact seal closure

- Before review: `30/30` exact rows; `30/30` unique paths; zero drift.
- After review: `30/30` exact rows; `30/30` unique paths; zero drift.
- Seal: `6425` bytes,
  `f995cf68ba1b82de0f56acb11c1b1bf73667602beae0a1e685c8eebde13cc4e8`.

## Independent native evidence

MSVC x64 `19.50.35730` rebuilt the exact source in reviewer scratch with
`/W4 /WX /O2 /MT /guard:cf /DUNICODE /D_UNICODE /std:c17`; exit `0` and zero
diagnostics. A separate `/W4 /WX /analyze /c` pass exited `0` with zero
diagnostics.

- independent object: `109055` bytes,
  `43efd6abf8a5a865dbaebff79df6a8a37dc02c7ebc9acec023c0952d6bf32baf`
- independent executable: `179712` bytes,
  `13b3e5c32914d73bcbd18c00f93f803c3c74110d655eb28d01535938f2b586cb`
- independent analyzer object: `66740` bytes,
  `e10df672ebd79e78b688476ec93627b85d774eb1e5a50db1234fd755dd38b07d`

Static PE inspection of both sealed and independent images found x64 PE32+,
High Entropy VA, ASLR, NX, CFG, CF instrumentation and a FID table. Imports are
only `bcrypt.dll` and `KERNEL32.dll`; there is no static Python, process, or
shell import.

The sealed PostSeal author suite passed. Fresh isolated static/mock probes
reproduced all four V13 rejection controls (`4/4`) and passed ten V14 hostile
checks (`10/10`) without importing, executing, or invoking V14.

## Blocking findings

1. `BLOCK_V14_SNAPSHOT_STATE_MUTABLE_NOT_ORIGIN_BOUND`

   `Core/persistent_blackwell_voice_integration_v14.py:839-872` defines writable
   snapshot slots with no mutation guard. Lines `883-921` validate an admissible
   shape but never compare `_subjects` or `_graph` to creation-time values. The
   native validator at `tools/native/kira_blackwell_voice_control_anchor_v14_validator.py:301-345`
   never compares either field to its original native input/result. Two distinct
   forged 15-row subject tuples pass the reproduced predicate, as do positive
   graph counts `1` and `999999`.

2. `BLOCK_V14_LOADER_GRAPH_STATE_NOT_EXACT_TYPED`

   V14 source `890-906` and validator `326-341` rely on equality and a positive
   graph count, not origin-bound exact typed values. A safe independent mock
   with `__eq__ -> True` makes the loader inequality check accept a non-tuple.
   The graph label is also not exact-str checked.

3. `BLOCK_V14_COMPLETE_GRAPH_OMITS_MUTABLE_INSTANCE_STATE`

   V14 `_typed_snapshot` at `330-348` records unknown objects only by type name;
   validator `_typed`/`_typed_cross` at `14-75` records type plus identity or
   type. Mutable `_StaticImportNamespace` and `_StaticPath` instance fields are
   not recursively sealed, so the claim of a complete exact graph is unproved.

4. `BLOCK_V14_POSTCALL_V12_PARENT_ATTRIBUTE_NOT_RECHECKED`

   Validator `_slots_clean` at `205-219` includes the V12 module slot but checks
   package attributes only on `Core`. It omits the V12 parent package attribute
   `Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12.canonical_typed_memory_binding`
   after stored calls.

## Boundary and next step

No `INDEPENDENT_AUDIT.tsv` or digest sidecar is created because those fixed
files are accepted one-shot input to the native controller and this review
rejects V14. V14 must not be run. Preserve it byte-for-byte, repair append-only,
and require a different fresh independent audit of the successor.
