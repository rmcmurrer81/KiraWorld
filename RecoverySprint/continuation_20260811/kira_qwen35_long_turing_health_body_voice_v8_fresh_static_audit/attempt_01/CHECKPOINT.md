# Kira long Turing / health / body / voice V8 fresh static audit

Date: 2026-08-11

Decision: `REJECT_NO_V8_UNATTENDED_ATTEMPT_AUTHORIZED`

Live authority: `NONE`

## Outcome first

The frozen V8 compatibility design is substantially correct under ordinary
single-call static execution, but it is rejected because its exact attempt
binding and scoped V1-loader substitution are not hostile-input safe.

No V8 unattended attempt, authorization, model, voice, CUDA, playback, person,
body, media, or Blender operation was created or run.

## Passing exact-byte and contract findings

- The exact frozen V8 plan, controller, test, author result, seal, and author
  checkpoint match their supplied byte counts and SHA-256 identities.
- All four V8 seal subjects rehash exactly.
- All eight V8-bound V7/rejection subjects rehash exactly.
- All thirteen V7-bound V6/rejection subjects rehash exactly.
- The frozen V1 plan is still 15,633 bytes, SHA-256
  `88ab1e53f3924302256abc6ab9c4909167057e6863d31743bf3602b101fc42ea`.
- Its ten project bindings have exactly one reviewed mismatch: the legacy shell
  row is
  `69594a9917b55dbca4992c12c357f79d81c0ccb7028ca8f2cc46e4f18789ecdd`,
  while the current 606,696-byte shell is
  `72e4fc403e00a2c4e7ac84e7a87a3c925fc9ce475a8afc90e17ac9e0b6b19fb4`.
  The other nine project bindings match exactly.
- The exact current shell, fast-end test, and fast-end checkpoint rehash
  correctly.
- The real nested V8 -> V7 -> V6 -> V5 -> V4 -> V3 -> V1-compatible loader
  executed successfully. Its normal single-call control restored the exact V1
  loader.
- The author V8+V7 suite passed 86/86 cache-free before and after the independent
  hostile run, proving the audit restored every mutation.
- All four independently reproduced V7 semantic false accepts remained closed.
  Exact terminal aggregate fields, exact dictionary recursion, Boolean/numeric
  separation, finite-number checks, and duplicate/non-finite JSON rejection
  remained active.
- The retained contract remains exact Qwen `qwen3.5:9b`, digest
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`,
  35 measured turns plus one voluntary invitation/cap 36, Blackwell-v2 CUDA,
  no CPU/SAPI/generic fallback, speaker playback requested, bounded cleanup,
  unattended log-only truth, and no owner-hearing inference.
- Wrong shell/evidence, all nine possible second project-binding substitutions,
  shell read/check TOCTOU, pre-existing output roots, and strict JSON hostile
  controls failed closed.

## Blocking finding 1: split duplicate-argument interpretation

V8's `validate_attempt_binding` searches for the first value following each
flag and does not reject duplicates. The retained `argparse` parser accepts
duplicates and uses the last value.

The independent probe supplied:

`--attempt-label attempt_01 --attempt-label attempt_02`

V8 accepted it, then the actual retained parser selected `attempt_02`.

The child equivalent supplied first exact `attempt_01` evidence/generated paths
followed by duplicate `attempt_02` paths. V8 accepted the first values, while
the executed child parser selected both `attempt_02` paths.

This invalidates the exact-only `attempt_01` and at-most-one append-only attempt
boundary. Finding ID:
`BLOCK_V8_DUPLICATE_ARGUMENT_ATTEMPT_BINDING_BYPASS`.

## Blocking finding 2: mutable/global V1 loader authority

The compatibility helper captures whatever mutable
`v1.load_and_validate_plan` object happens to be installed, replaces it with a
lambda, and restores the captured object in `finally`.

Two hostile controls failed:

1. A pre-existing hostile loader was accepted. The real V7 chain passed under
   the temporary reviewed lambda, then V8 restored the hostile loader rather
   than rejecting noncanonical identity.
2. Two deliberately overlapping validation calls restored out of order. Both
   calls returned, but the second `finally` left the first reviewed-shell lambda
   globally installed. The audit then restored the canonical loader and proved
   cleanup by rerunning all 86 author tests.

This invalidates exact canonical-loader restoration and no-monkeypatch-leak
truth. Finding ID:
`BLOCK_V8_V1_LOADER_IDENTITY_AND_CONCURRENCY_LEAK`.

## Test evidence

- Authored V8+V7 suite: 86 passed, 0 failed, cache disabled.
- Independent hostile suite: 20 run; 16 passed; 4 failed.
- Independent probe:
  - 21,512 bytes
  - SHA-256
    `7935aebc5eb90a6e4d58c0603b414d8a6a707c5acb939e9c075d9e5228462b95`
- Hostile result:
  - 2,697 bytes
  - SHA-256
    `0f2f5d16e4ecd30a6489b33b84fba47bd542ee7c745ee4a41bb292a46d8269a2`
- Static audit result:
  - 7,713 bytes
  - SHA-256
    `2323341c8166b9f62af758d311b5d62fbdc3c05cba5be506e460d34bd285e1f9`
- Audit decision:
  - 2,331 bytes
  - SHA-256
    `3a927d99171586b07dc95769ce37451346abf62f6db59a273dfcf13413911cc5`

## Required successor

Preserve V8 and this rejection byte-for-byte. An append-only successor must:

1. parse critical arguments exactly once under a closed schema and reject every
   duplicate singleton flag before either parent or child execution;
2. prove the values validated are exactly the values consumed by the retained
   parser, or pass a canonical parsed object without reparsing;
3. bind and verify the exact canonical original V1 loader, rejecting
   pre-existing drift;
4. avoid process-global loader mutation where possible, or serialize a
   non-reentrant installation and verify exact canonical restoration after
   success and every exception;
5. retain every passing V7/V8 exact-byte, semantic, terminal, Qwen, Blackwell,
   playback, cleanup, unattended, no-hearing, and output-replay control;
6. receive another different fresh exact-byte hostile static audit.

No V8 authorization file may be created, and V8 must not be run live.
