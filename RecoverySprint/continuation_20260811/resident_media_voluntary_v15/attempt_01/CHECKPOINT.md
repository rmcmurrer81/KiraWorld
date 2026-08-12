# Resident-media V15 author checkpoint

Date: 2026-08-11

Status: **SEALED NO-COMMIT STATIC CANDIDATE; PENDING A DIFFERENT FRESH INDEPENDENT AUDIT**

## Why V15 exists

The different V14 audit rejected V14. Its public validation method closure
exposed a `WeakKeyDictionary` whose value was mutable `_SnapshotStateV14`; that
state retained a mutable V4 `StimulusCatalog`. `state.verify()` compared only
the catalog object's cached `sha256` with the cached state digest. Changing
`catalog._manifests` therefore changed the manifest used by validation without
changing the reported catalog digest.

The V15 test suite reproduces that exact V14 stale-digest result on a disposable
in-memory V14 validator. V12, V13, V14, their seals, and the V14 rejection are
preserved byte-for-byte.

## Append-only V15 repair

V15 retains only an exact immutable tuple of:

1. an identity marker;
2. exact person identifier string;
3. canonical owner-selected snapshot bytes; and
4. the exact snapshot SHA-256 string.

There is no V15 weak registry, state object, catalog object, manifest
mapping/list, lock, authority, adapter, ledger, receipt history, anchor,
compare-and-swap callable, or commit surface. Every public operation decodes
and fully revalidates the exact snapshot bytes, constructs a fresh local
catalog, derives canonical catalog bytes and their SHA-256, and discards the
catalog before return. Caller mutation of the original catalog cannot change
the V15-bound bytes.

`validate_static_evidence_plan` returns an exact built-in tuple pair whose items
are the complete canonical JSON plan bytes and the SHA-256 derived from those
bytes before emission. Built-in tuple items are immutable, and Python refuses a
caller attempt to add or replace a member on the exact built-in tuple class.
`decode_static_plan_envelope_v15()` rechecks the byte/digest invariant and
returns a fresh decoded copy. Replacing that module helper after return cannot
change the already-emitted pair. A mismatched pair refuses.

This is a static integrity/no-commit repair, not protected authority. The
caller-supplied snapshot is not authenticated truth. Python is not claimed as
an operating-system trust root. A future commit still requires a separately
reviewed protected external/native broker enforcing checks at its actual commit
boundary with exact post-commit readback.

## Final author verification

- strict in-memory compile: **2/2 PASS**;
- focused V15 static/mocked tests: **20/20 PASS**;
- preserved V3-V14 regression tests: **210/210 PASS**;
- combined V3-V15 tests: **230/230 PASS**;
- final failed tests: **0**;
- seal closure: **9/9 exact byte/hash rows PASS**.

The static-results file preserves the two failed test-authoring iterations and
the one wrong-working-directory combined run. None is presented as a pass.

## Exact sealed package

- `Core/resident_media_voluntary_gate_v15.py` — 29,602 bytes —
  `c14cb0e76a17de76f6fe072a0e3e1662c005dc24eb9faac1b3fcba8ab099e944`
- `Testing/test_resident_media_voluntary_gate_v15.py` — 27,275 bytes —
  `e9eb8ba181eaf510ac68e09f9b6f77c39a83cb94765038ffaa30fa372b6c33d1`
- `EXECUTION_BINDING_V15.json` — 916 bytes —
  `4313d8460fdac5b024d698cf15a3c33c738246681d4091a92af74b8f8ee410b9`
- `STATIC_TEST_RESULTS.md` — 5,408 bytes —
  `849bf07e4b32baa46f5f807dde027ea656089f51c6259344f1276f825e6dee60`
- `VOLUNTARY_MEDIA_CONTRACT_V15.json` — 6,362 bytes —
  `286349edd612de22c25ac1604861b6e7e6e5e03791654beb06761c8106141aaa`
- `SEALED_MANIFEST.json` — 3,156 bytes —
  `9ca92ea13cff61cd0681abd9aae6244071eaac6bfb3e97e2bfab6034d447148b`

The V15 execution binding seals the exact V15 source. Its bootstrap uses the
preserved V14 bootstrap chain to close V14/V13/V12/V9/V4 while retaining only
the predecessor verifier function, type, code identity, and bootstrap identity
integer—not the predecessor bootstrap object—inside the V15 guard.

## Negative truth boundary

No production route or pointer changed. No authority protocol, receipt, anchor,
compare-and-swap, durable record, media, model, network, camera, microphone,
GPU, audio device, body, Blender workflow, person state, memory, relationship,
or Sarah file was used or changed. No person is claimed to have seen, heard,
attended, enjoyed, learned, preferred, remembered, felt, or become conscious of
anything.

V15 is **not accepted by this author checkpoint**. A different fresh independent
reviewer must rehash the sealed package, inspect the closure/state/envelope
invariants adversarially, and decide acceptance or rejection before any further
use. No live or production run is authorized.
