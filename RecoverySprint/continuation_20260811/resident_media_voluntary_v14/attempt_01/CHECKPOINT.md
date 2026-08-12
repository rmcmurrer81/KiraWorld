# Resident Media Voluntary Gate V14 - Append-Only No-Commit Checkpoint

Date: 2026-08-11

Status: `AUTHOR_SEALED_NO_COMMIT_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_INDEPENDENT_AUDIT`

Live authorization: `NONE`

Production integration: `DISCONNECTED_NO_COMMIT_SURFACE`

## Outcome first

V13, its seal, and its different fresh rejection remain exact. V14 is a new
append-only static successor. It is deliberately narrower than the requested
commit repair: V14 can bind caller-supplied canonical bytes in the preserved
owner-selection snapshot schema and produce a complete, exact, explicitly
non-authoritative static validation plan. It cannot read an authority anchor,
consume a receipt, record evidence, or commit.

The exact authored hostile suite passes 19/19. The preserved V3-V13 suite
passes 191/191, and the combined V3-V14 suite passes 210/210. The seal closure
passes 9/9. V14 is not independently accepted, promoted, connected, or live.
A different fresh reviewer must rehash and attack the exact sealed bytes.

## Why V14 is no-commit

The V13 different audit proved that the returned V13 wrapper exposed its
rejected V12 ledger through `_inner`; direct invocation bypassed V13's checks.
An initial V14 author design moved the V12 adapter and commit state into a
method closure. Hostile review caught that ordinary Python closure inspection
could traverse `method.__func__.__closure__`, recover the state and adapter,
and reproduce the same bypass under a less obvious name. That scratch design
was deleted before any Kira byte changed and before any live or authority run.

The V12 snapshot-read protocol is also stateful: it issues and globally
consumes one-use authority receipts. V14 therefore does not use that protocol
even for snapshot acquisition. Its factory accepts exact caller-supplied bytes
and an exact caller-supplied SHA-256, validates canonical/schema/catalog
self-consistency, and labels the input unauthenticated and non-authoritative.

V14's returned slot-only validator retains canonical snapshot data and a
validated static catalog only. It retains no authority, V12 adapter, V12/V13
ledger, durable anchor, receipt history, or compare-and-swap callable. A real
future commit requires an append-only protected external/native broker that
enforces exact type/completeness checks at its actual commit boundary and
performs exact post-commit readback. No such broker exists in V14.

## Exact Python trust wording

The sealed entry points revalidate the exact V14/V13/V12/V9/V4 file, module,
package, global, function, class, member, code, default, keyword-default,
referenced-global, and closure bindings before returning a plan. This is
defence in depth, not an operating-system trust root.

An ordinary Python class method is substitutable by same-process caller code.
V14 does not claim otherwise. The hostile suite replaces the validator's class
record method and proves the replacement can return only caller-authored data:
it reaches no retained authority/adapter/ledger/CAS capability, creates no
durable record, and leaves the supplied mock authority state exactly unchanged.
After restoration, the exact sealed record method refuses as authored.

## Validation boundary

For the exact sealed plan method, V14 requires:

1. exact nonempty snapshot bytes and matching lowercase SHA-256 text;
2. strict canonical JSON and self-consistent preserved snapshot/catalog schema;
3. exact-string identifiers and exact lowercase SHA-256 fields throughout;
4. no bool/int/string identifier alias, numeric JSON digest, numeric-only
   decoder digest, uppercase digest, changed key set, or tuple-for-array alias;
5. expected manifest equality with the bound static catalog manifest;
6. exact required-role list and exact completeness-map key set;
7. every required-role completion value exactly `True`;
8. `engineering_output_completed is True` and
   `presentation_complete_for_manifest is True`;
9. repeated exact validation before returning a non-authoritative plan.

No result is an authority receipt, presentation record, durable commit, live
experience, memory, preference, or person-state claim.

## Hostile evidence

The focused suite covers:

- missing video caption and false completion;
- complete page, video-frame/audio/caption, and audio-track static plans;
- boolean output/surface identifiers, integer permit/digest, and numeric-only
  decoder digest;
- changed snapshot bytes, changed expected digest, bytearray input, and nested
  boolean snapshot identifiers;
- direct `_inner`/adapter/authority/proxy/catalog/anchor/ledger/instance-dict
  attribute inspection;
- recursive closure/container/weak-map/slot traversal proving no V12/V13
  ledger instance, V12 adapter instance, authority instance, or CAS bound
  method is reachable from the returned validator;
- preflight/type-walker rebinding, predecessor `sys.modules` replacement,
  Core package-attribute replacement, and non-guard closure-cell mutation;
- class-method substitution with no retained capability and no authority-state
  change;
- exact production refusal and no heavy/live import path.

## Exact sealed subjects

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `Core/resident_media_voluntary_gate_v14.py` | 46,445 | `4ac4d63cde6a2535549f404021e999fc925914f1a1296dff490af674b97afa8b` |
| `Testing/test_resident_media_voluntary_gate_v14.py` | 24,843 | `474f299c8da88313fd70b8c1372ed4a5b1629ba92dae25926db1cc81ade3cd02` |
| `RecoverySprint/continuation_20260811/resident_media_voluntary_v14/attempt_01/EXECUTION_BINDING_V14.json` | 2,203 | `f0b0ef37318ac3b04a2b02b902a50690e2c0d1f8334872bae1f46691ba84f693` |
| `RecoverySprint/continuation_20260811/resident_media_voluntary_v14/attempt_01/STATIC_TEST_RESULTS.md` | 4,272 | `d9fa403e79a03968575dd0722018ce012ed438983cee7a011220a327d921da50` |
| `RecoverySprint/continuation_20260811/resident_media_voluntary_v14/attempt_01/VOLUNTARY_MEDIA_CONTRACT_V14.json` | 5,314 | `31fc3b3ed84bf0b416c66fb5424a7c3d86027a98c14159103d45c17968073ec5` |

Seal:

- path: `RecoverySprint/continuation_20260811/resident_media_voluntary_v14/attempt_01/SEALED_MANIFEST.json`;
- bytes: `2,894`;
- SHA-256: `7699ff183c24bcbf2fb580b5d9fcb119c19dd36e71503c22bd5b3720ef723736`;
- closure verification: `PASS - 9/9 current and predecessor records`.

These five V14 subject bytes are frozen. Any later code, test, binding, result,
or contract change requires an append-only successor and a new audit; do not
edit or reseal V14 in place.

## Preserved predecessor closure

The seal binds the V13 seal at 2,777 bytes / SHA-256
`6860f7e1c0acb6ae50f704a2ed1291af76054d1ef0da90081b82e2e99298d852`
and the three current V13 rejection records:

- checkpoint: 2,005 bytes / `3516f4f43b4b2211f5d39e28f837fdff3fd1db2ff2ebd6f64340d6231385a70c`;
- decision: 2,732 bytes / `f0b9c14b08562f71634ed7d262bdd4b2ba5119efad1130a41a9b29bb5ef1cd12`;
- hostile probes: 2,920 bytes / `49e4ce8893263237472976ddd743b3622d724f16ac91717932b904233f03ea65`.

## Verification

- strict in-memory source compile: `PASS - 2/2`;
- focused V14 hostile/static suite: `PASS - 19 tests in 0.225s`;
- preserved V3-V13 regression suite: `PASS - 191 tests in 1.544s`;
- combined V3-V14 suite: `PASS - 210 tests in 1.827s`;
- seal closure: `PASS - 9/9`;
- JSON parse: `PASS - 3/3`;
- bytecode/cache writes requested: `NO`;
- live/model/network/media/device/person/body/Blender/Sarah paths: `NONE`.

The first preserved-suite draft command ran from the isolated draft directory,
so three historical tests could not find relative evidence files. That harness
working-directory error was retained in the static results. Running the exact
same 191 tests from the Kira project root passed 191/191.

## Required different fresh audit

A different reviewer must treat the seal as read-only and independently test:

1. all 9 exact closure hashes and config/contract/manifest JSON;
2. closure traversal and class-member substitution, including proof that no
   commit-capable instance or authority state is reachable;
3. module/package/global/function/code/default/kwdefault/closure mutation;
4. every exact-type, numeric-digest, incomplete-role, and false-completion
   probe without accepting normalization;
5. proof that V14 calls no authority method, consumes no receipt, reads no
   anchor, and attempts no CAS or durable record;
6. proof that caller snapshot bytes and returned plans are never described as
   protected authority truth, presentation, memory, preference, or experience;
7. preserved V3-V13 consent/privacy/choice/catalog regressions;
8. unconditional production refusal and absence of a live route.

Even a positive audit may accept only this no-commit static validator. It
cannot authorize a media run or production integration.

## Truth boundary

No authority protocol was called, no receipt was consumed, no anchor was read,
and no durable commit was attempted. No media was opened, decoded, rendered,
played, or presented. No model, network, camera, microphone, GPU, audio device,
body, Blender, Sarah, person, memory, preference, production pointer, registry,
handoff, launcher, or route ran or changed. No person is claimed to have seen,
heard, attended to, enjoyed, disliked, learned, preferred, or remembered media.

## Rollback

Leave V14 disconnected and unreferenced. V13 and all predecessor/audit bytes
remain preserved. Removing or ignoring only the new V14 files is sufficient;
no production or shared documentation pointer references this candidate.
