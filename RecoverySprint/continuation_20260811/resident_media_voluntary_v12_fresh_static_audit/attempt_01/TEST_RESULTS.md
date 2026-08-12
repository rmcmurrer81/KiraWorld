# Resident Media V12 different fresh static audit test results

Recorded UTC: `2026-08-11T07:38:16.3160182Z`

Live/model/media/person/device/GPU/body/Blender execution: `NONE`

All commands used `PYTHONDONTWRITEBYTECODE=1` and Python `-B`. No pytest or
bytecode cache was requested or created by these commands.

## Sealed authored V12 suite

Command:

`py -B -m unittest Testing.test_resident_media_voluntary_gate_v12 -q`

Result: `PASS - 14 tests in 0.106s`

## Preserved V3-V12 regression suite

Command:

`py -B -m unittest Testing.test_resident_media_voluntary_gate_v3 Testing.test_resident_media_voluntary_gate_v4 Testing.test_resident_media_voluntary_gate_v5 Testing.test_resident_media_voluntary_gate_v6 Testing.test_resident_media_voluntary_gate_v7 Testing.test_resident_media_voluntary_gate_v8 Testing.test_resident_media_voluntary_gate_v9 Testing.test_resident_media_voluntary_gate_v10 Testing.test_resident_media_voluntary_gate_v11 Testing.test_resident_media_voluntary_gate_v12 -q`

Result: `PASS - 176 tests in 1.307s`

## Different fresh hostile probes

Subject:

- `INDEPENDENT_HOSTILE_PROBES.py`
- 27,281 bytes
- SHA-256 `9bf904044295ca1aa796f17f891f4f58cd73a50cee16df6bddeabf9804c9306a`

Command:

`py -B RecoverySprint/continuation_20260811/resident_media_voluntary_v12_fresh_static_audit/attempt_01/INDEPENDENT_HOSTILE_PROBES.py -q`

Result: `PASS - 20 tests in 0.162s`

The independent probe suite is audit-oriented: its blocker tests pass only
when they deterministically reproduce an unexpected V12 acceptance. It found:

1. a video missing its caption role and an audio interval with incomplete
   synchronized-audio coverage are both committed when the caller truthfully
   sets the two completion booleans to false;
2. boolean/integer snapshot, person, session, output-receipt, and
   output-surface identities are accepted through string coercion;
3. a JSON numeric 64-digit renderer/decoder digest is accepted, retained as an
   integer inside the canonical presentation segment, and separately
   normalized to a string in the derived receipt list.

Positive hostile controls passed for:

- unconditional public production refusal with arbitrary positional and
  keyword caller objects, invented V11-style globals, and a monkeypatched
  private harness;
- no public catalog argument and no exported static harness;
- strict canonical external bytes, duplicate-key/noncanonical/nonfinite
  rejection;
- exact authority/epoch/purpose/context/sequence/digest receipt bindings and
  exact verification-response bindings;
- local and cross-adapter authority-receipt replay;
- exact snapshot selection/source-time/derivative bindings and immutable
  reread;
- initial and append CAS, stale concurrency, signed-old rollback, post-CAS
  readback drift, and ambiguous post-commit failure;
- complete page/video/audio/caption positive controls;
- exact normal session/person/manifest binding and cross-session/reopen output
  and decoder receipt replay;
- disconnected truth summaries and absence of heavy runtime imports.

## Compile/read check

The independent probe compiled the exact sealed V12 core and test bytes with
the built-in `compile()` function. Result: `PASS - 2/2`, with no bytecode
write.
