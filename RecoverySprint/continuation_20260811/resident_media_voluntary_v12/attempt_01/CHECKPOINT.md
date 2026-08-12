# Resident Media Voluntary Gate V12 - Static Successor Checkpoint

Date: 2026-08-11

Status: `SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_INDEPENDENT_AUDIT`

Live authorization: `NONE`

Production integration: `DISCONNECTED_FAIL_CLOSED`

## Outcome first

V10, V11, and both predecessor rejection packages remain unchanged. V12 is an
append-only static successor for the two deterministic V11 caller-authority
failures.

V12 does not contain or export an issuer token, issuer key, authority factory,
owner-selected catalog digest, selection receipt global, or mutable authority
registry. It does not treat Python `Final` annotations, module privacy, class
identity, or an in-process object as an operating-system trust root.

The public production opener accepts neither a caller catalog nor a caller
authority and unconditionally refuses because no separately reviewed protected
external authority exists. Inventing or rebinding token/catalog module
attributes therefore cannot open a production path.

The disconnected static harness takes no catalog argument. It obtains the
owner-selected catalog only as exact canonical bytes from an injected external
authority interface. The authenticated snapshot binds:

- exact catalog and selection revision;
- exact owner-selection receipt identity and digest;
- exact authoritative-source policy identity;
- every source path, byte count, digest, and time/page coordinate;
- every derivative path, byte count, digest, set digest, and individual
  derivative identity.

Every snapshot read, anchor readback, and atomic compare-and-swap response has
an exact context-bound receipt. The external interface must verify and consume
each receipt once, and the adapter independently rejects local receipt and
verification replay. CAS requires a fresh exact readback. Complete V9 evidence,
per-role page/video/audio/caption coverage, chained history, and global
cross-session output/decoder receipt one-use remain enforced.

The test-only external authority lives in the test module. It demonstrates the
protocol and global replay behavior but is explicitly not production authority
and not an OS trust root.

## Exact sealed subjects

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `Core/resident_media_voluntary_gate_v12.py` | 50849 | `2cc9e588affde3c0dd1e127baef31fd2183cc2d188d61afdf2899df06bd6bf5c` |
| `Testing/test_resident_media_voluntary_gate_v12.py` | 32717 | `9e9441564eaf6415b19c100b678430f425b0b29003a003b2954af093693291b8` |
| `RecoverySprint/continuation_20260811/resident_media_voluntary_v12/attempt_01/STATIC_TEST_RESULTS.md` | 2127 | `e3d87c7e09384582145d69d955f3b9f5c525264b02344aca22b02fb4bfec5542` |
| `RecoverySprint/continuation_20260811/resident_media_voluntary_v12/attempt_01/VOLUNTARY_MEDIA_CONTRACT_V12.json` | 3600 | `362a9a833d324ab53b8eebf90cc4a05308fde2ff3e70fbd989c6ec8ad14f81f8` |

Seal:

- `RecoverySprint/continuation_20260811/resident_media_voluntary_v12/attempt_01/SEALED_MANIFEST.json`
- 1411 bytes
- SHA-256 `7c6d2da7319e163dc0e2a1be0be1af06bbbfe89173f5a8b5f21e93e2a94e2a66`

These bytes are now frozen. Do not edit or reseal them. Any repair after a
different audit must be an append-only V13 successor.

## Verification

- strict `py_compile`: PASS for V12 core and test;
- focused V12 static/hostile suite: PASS, 14 tests;
- preserved V3-V12 regression suite: PASS, 176 tests;
- static execution scan: no subprocess, model, network, media decoder,
  renderer, camera, microphone, GPU, audio playback, body, or Blender path.

Hostile coverage includes:

- exact reproduction of V11 token/global rebinding classes through the public
  opener, with no authorization possible;
- invented V12 token/catalog globals and caller catalog/authority arguments;
- catalog and source path/byte/digest/coordinate changes;
- derivative path/byte/digest, derivative-set, and derivative-identity changes;
- owner-selection receipt and snapshot changes after binding;
- authority receipt replay in one adapter and across a fresh adapter;
- incomplete page/video/audio/caption required-role coverage;
- global output and decoder receipt replay across sessions and reopen;
- stale concurrent ledger, signed-old rollback, CAS mismatch, readback TOCTOU;
- unknown fields, zero sentinels, and bool/integer confusion;
- exact V10/V11/rejection evidence preservation.

## Required different fresh audit

A different auditor must rehash every sealed subject and independently test:

1. no V12 issuer secret/factory or trusted catalog/selection module global;
2. public production refusal under introspection, rebinding, proxies, arbitrary
   interface objects, caller catalogs, and copied V11 token fields;
3. strict canonical bytes, duplicate-key/noncanonical encodings, exact snapshot
   schema, every source-time and derivative field, and immutable reread;
4. receipt purpose/context/authority/epoch/sequence/authenticator binding,
   verification response binding, local and cross-adapter replay;
5. initial and append CAS, stale CAS, rollback/splice/reorder, receipt-list
   derivation, exact post-CAS readback, and ambiguous/failing external calls;
6. V9 exact per-role page/video/audio/caption completeness and full evidence;
7. global output/decoder replay across sessions and reopen;
8. exact predecessor and rejection-evidence preservation.

Even `ACCEPT_STATIC_ONLY` would not authorize live media, production
integration, a model call, device access, or person acceptance testing.

## Truth boundary

No media was opened, decoded, rendered, played, or presented. No model, device,
person state, memory, preference, body, GPU, or Blender path ran. No person is
claimed to have seen, heard, attended to, enjoyed, disliked, learned, or
remembered anything. No production pointer, route, or launcher changed.

## Rollback

Leave V12 disconnected and unreferenced. V3-V11 and all prior audits remain
the operative preserved evidence. Deleting or ignoring the new V12 package is
sufficient to roll back because no production pointer references it.
