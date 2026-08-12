# Resident Media Voluntary Gate V13 - Append-Only Static Repair Checkpoint

Date: 2026-08-11

Status: `SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_INDEPENDENT_AUDIT`

Live authorization: `NONE`

Production integration: `DISCONNECTED_FAIL_CLOSED`

## Outcome first

V12 and its different fresh rejection remain exact. V13 is a new append-only,
default-off static successor limited to the three V12 findings. Its authored
hostile suite passes 15/15 and the preserved V3-V13 suite passes 191/191.

V13 is not independently accepted. The author has not audited or promoted the
candidate. A different fresh agent must rehash the seal and challenge the
exact bytes before even `ACCEPT_STATIC_ONLY` is possible. No live media or
production run is authorized.

## Exact V12 repair boundary

V13 retains the frozen V12 catalog, owner-selection snapshot, protected
external-authority byte interface, one-use authority receipt verification,
global output/decoder receipt history, monotonic anchor CAS/readback, and
unconditionally disconnected production opener.

Before inherited validation can stringify a value, V13 recursively requires
exact string types for every identifier and SHA-256 field across:

- authority descriptor and requests/responses;
- owner snapshot, catalog, source, derivative, and selection receipt;
- authority receipt and protected verification receipt;
- anchor, presentation record, receipt histories, evidence, and segments;
- person, session, stimulus, output receipt, and output surface identity.

SHA-256 values must already be lowercase 64-character strings and must not be
the zero digest. Renderer/decoder identities additionally reject both a JSON
64-digit integer and a numeric-only 64-character string, preventing the exact
integer/string alias reproduced by the V12 audit.

V13 performs a frozen preflight before entering the V12 ledger. A record can
advance only when all of the following are exact:

1. `engineering_output_completed is True`;
2. `presentation_complete_for_manifest is True`;
3. the returned required-role list equals the role list derived from the exact
   authoritative manifest;
4. the completeness map has exactly that authoritative key set;
5. every required-role value is the boolean `True`.

The focused hostile tests remove the complete caption role from a video and
shorten synchronized-audio coverage by one millisecond. Both are refused while
the external anchor revision, output-receipt list, decoder-receipt list,
presentation-record list, authority receipt issue/verification sequences, and
consumed-receipt set remain exactly unchanged.

## Preserved consent, privacy, choice, catalog, and receipt gates

V13 does not replace or weaken the inherited gates. The combined regression
run includes V3-V12 and preserves the accepted isolated V7 choice-normalization
core; maturity/co-viewing and current-choice separation; refusal/stop/pause
handling; privacy and no-automatic-memory/preference truth; exact authoritative
catalog/source/derivative bindings; external authority receipt verification;
cross-session output/decoder one-use; stale-CAS/rollback/readback refusal; and
the public fail-closed boundary.

This is preservation by exact predecessor execution, not production
integration or person acceptance.

## Exact sealed subjects

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `Core/resident_media_voluntary_gate_v13.py` | 18,064 | `202588befbce062d8e50626902c8efb0513aceb73426caba8cd320872db8c492` |
| `Testing/test_resident_media_voluntary_gate_v13.py` | 25,643 | `614e78231c0bf63b9a5e8abe276202856375bb1c80773391b69355281b97748e` |
| `RecoverySprint/continuation_20260811/resident_media_voluntary_v13/attempt_01/STATIC_TEST_RESULTS.md` | 2,929 | `adb980222f2909d657d4d89041cd6b9a38c3927265f5ba7fad9f9f365020ad7c` |
| `RecoverySprint/continuation_20260811/resident_media_voluntary_v13/attempt_01/VOLUNTARY_MEDIA_CONTRACT_V13.json` | 4,073 | `12a9f364c86891d2e9b4d5b1506fa5d9307a66f66675e7885366d965c5e2c1c9` |

Seal:

- path: `RecoverySprint/continuation_20260811/resident_media_voluntary_v13/attempt_01/SEALED_MANIFEST.json`;
- bytes: `2,777`;
- SHA-256: `6860f7e1c0acb6ae50f704a2ed1291af76054d1ef0da90081b82e2e99298d852`;
- closure verification: `PASS - 10/10 subjects and predecessor records`.

These V13 subject bytes are frozen. Any later change must be an append-only
successor, not an in-place edit or reseal.

## Exact predecessor closure

The V13 seal binds the V12 seal at 1,411 bytes / SHA-256
`7c6d2da7319e163dc0e2a1be0be1af06bbbfe89173f5a8b5f21e93e2a94e2a66`
and all five artifacts in the V12 different fresh rejection package. The
rejection checkpoint remains 6,289 bytes / SHA-256
`cdafe2169a6580b2586366bc2c6e0774f5f802f30ee76be0573d4dd89b54eb30`.

The focused preservation test independently rehashes the V12 core, test,
static results, contract, seal, rejection checkpoint, audit decision, hash
verification, test results, and independent hostile probes. All ten match.

## Verification

- exact source compile/read: `PASS - 2/2`;
- focused V13 hostile/static suite: `PASS - 15 tests in 0.118s`;
- preserved V3-V13 regression suite: `PASS - 191 tests in 1.567s`;
- V13 seal closure: `PASS - 10/10`;
- contract JSON parse: `PASS`;
- subprocess/model/network/media/device/GPU/audio/body/Blender paths in V13:
  `NONE`.

All Python commands used `PYTHONDONTWRITEBYTECODE=1` and `-B`. No live media,
model, network, device, person, memory, preference, body, GPU, audio, or
Blender operation was invoked.

## Required different fresh audit

A different agent must treat the seal as read-only and independently test at
least:

1. exact V13 and V12/rejection closure hashes;
2. type confusion at every identifier and digest location, including nested
   catalog/receipt/verification/anchor/record/evidence/segment fields;
3. numeric JSON, numeric-only string, uppercase, zero, bool, and integer SHA
   cases without accepting normalization;
4. missing caption, missing video frame, incomplete synchronized audio, page
   omission, role-map substitution, and false/zero completion values;
5. proof that every incomplete/invalid preflight leaves external revision,
   receipt histories, record history, and CAS calls unchanged;
6. caller-manifest substitution versus the exact owner-selected catalog;
7. global output/decoder replay, stale concurrent anchors, rollback, and exact
   post-CAS readback;
8. public production refusal under arbitrary objects, caller catalogs,
   caller authorities, introspection, and invented predecessor token/global
   names;
9. preserved V3-V12 consent, privacy, maturity/co-viewing, current choice, and
   refusal semantics.

The auditor must not run or promote media. Even a positive different audit may
accept only the sealed disconnected static contract. A separately designed,
separately sealed, and separately audited live integration would still be
required later.

## Truth boundary

No media was opened, decoded, rendered, played, or presented. No model,
network, camera, microphone, GPU, audio device, body, Blender, or person route
ran. No person is claimed to have seen, heard, attended to, enjoyed, disliked,
learned, remembered, or formed a preference about any media. No memory or
person state changed. No production pointer, registry, handoff, master index,
launcher, or route changed.

## Rollback

Leave V13 disconnected and unreferenced. V12 and every predecessor/audit remain
preserved. Removing or ignoring only the new V13 files is sufficient because
no shared production or documentation pointer references this candidate.
