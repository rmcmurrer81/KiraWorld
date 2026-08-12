# Resident Media Voluntary Gate V12 - Different Fresh Static Audit

Recorded UTC: `2026-08-11T07:38:16.3160182Z`

Verdict: `REJECT`

Live authorization: `NONE`

Production integration: `DISCONNECTED_FAIL_CLOSED`

## Outcome first

The sealed V12 package and its V10/V11/rejection closure match exactly, and
the production opener remains unconditionally disconnected. The authored V12
suite (14 tests), preserved V3-V12 suite (176 tests), and different fresh
hostile suite (20 tests) all execute successfully with bytecode/cache writes
disabled.

V12 is nevertheless rejected because the different fresh probes reproduce
three deterministic over-acceptance classes. Two are closely related scalar
type failures, while one contradicts the sealed completeness claim.

No media, model, network, device, person, memory, body, GPU, audio, or Blender
path ran. No production pointer or route changed.

## Blocking finding 1: incomplete required roles are committed

V12 delegates to V9's truth validator, which permits an incomplete output when
the caller declares both `engineering_output_completed` and
`presentation_complete_for_manifest` false. V12 never adds a completion gate
before consuming the output/decoder identities and committing the new anchor.

The fresh probes therefore obtained successful committed records for:

- a video interval with every caption segment removed; the returned
  `complete_by_required_role.caption_text_utf8` is false and revision advances
  from 0 to 1;
- an audio interval whose synchronized-audio coverage ends one millisecond
  early; the returned role completeness is false and revision advances from
  0 to 1.

This contradicts the sealed test-result statement that incomplete roles are
refused and the sealed V12 contract's required video-frame/audio/caption and
audio-role completeness claims. An honest incomplete-progress record might be
a useful separate design, but it cannot be accepted by the exact completion
gate while that gate claims required-role completeness.

## Blocking finding 2: identifier types are coerced

`_nonzero_identifier()` delegates to `v8._identifier()`, which converts the
input through `str(value or "")` before applying its regular expression.
Consequently the exact schema does not require a JSON string.

The fresh probes show successful construction or commit with:

- `snapshot_id: true`;
- `owner_selection_receipt_id: 1`;
- `person_id=True`, normalized to the string `"True"`;
- `session_id=True` when evidence contains `"True"`;
- `output_receipt_id: true`, normalized to `"True"`;
- `output_surface_id: true`, retained as a boolean inside accepted evidence.

This is not exact person/session/output receipt binding. It creates bool/int to
string aliases at a boundary whose sealed contract claims bool/integer
confusion is refused.

## Blocking finding 3: SHA-256 types are coerced

`_nonzero_sha()` similarly delegates to an inherited helper that stringifies
the value. A JSON number consisting of 64 decimal `1` digits is accepted as a
renderer/decoder SHA-256 identity. The accepted evidence retains the integer
inside its canonical presentation segment while the derived receipt list
contains the string version. That is two scalar representations for one
receipt identity, not an exact canonical SHA-256 string schema.

The same V12 helpers are used throughout snapshot, anchor, authority-receipt,
and presentation validation, so the repair must be applied at every nested
boundary rather than only to the three demonstrated call sites.

## Positive findings retained

The rejection does not erase the V12 repairs that did work:

- the public production opener ignores and rejects caller catalogs,
  authorities, copied V11 tokens, explosive proxies, invented module globals,
  and even a monkeypatched private harness;
- no issuer token/key/factory or trusted owner-catalog global exists in V12;
- external objects require strict canonical exact bytes; duplicate JSON keys,
  spacing/order variants, non-finite numbers, trailing bytes, and non-bytes
  fail;
- snapshot identity, selection receipt, source path/bytes/digest/time, and all
  derivative identities remain bound and immutable on reread;
- receipt and verification authority/epoch/purpose/context/digest/sequence
  bindings fail closed, as do local and cross-adapter receipt replay;
- initial/append CAS, stale concurrency, rollback, readback drift, and an
  ambiguous post-commit exception do not return false acceptance;
- complete page, video-frame, video-audio, caption, and audio positive controls
  pass;
- ordinary session/person/manifest substitutions and output/decoder replay
  across sessions and reopen fail.

## Exact evidence

| Audit artifact | Bytes | SHA-256 |
|---|---:|---|
| `INDEPENDENT_HOSTILE_PROBES.py` | 27,281 | `9bf904044295ca1aa796f17f891f4f58cd73a50cee16df6bddeabf9804c9306a` |
| `HASH_VERIFICATION.md` | 1,730 | `536b662d9a883c336df4304413623ff3b3b405e8901210128f4a74642bec554b` |
| `TEST_RESULTS.md` | 3,224 | `21e1b5b1bafc07f73657f5f9d078f36a37d60778537649d8db9f89dd5c2c1c34` |
| `AUDIT_DECISION.json` | 4,546 | `26c26d2d119e802e7333f6088ec610987a51a096c7b31beb894c094ccdbbb239` |

The original V12 seal remains 1,411 bytes, SHA-256
`7c6d2da7319e163dc0e2a1be0be1af06bbbfe89173f5a8b5f21e93e2a94e2a66`.
All four seal subjects and the seal-bound V11 rejection checkpoint match.

## Required append-only repair

Do not edit or retry V12. A V13 successor must:

1. require `type(value) is str` before every identifier and SHA-256 validator,
   including nested snapshot, receipt, verification, anchor, record, evidence,
   segment, session, person, output, and surface fields;
2. reject bool/integer coercion at all of those fields and add direct hostile
   tests for each demonstrated value;
3. require completion booleans and every required-role result to be exact true
   before any output/decoder receipt is consumed or any anchor CAS occurs;
4. prove honest incomplete video/audio/caption evidence leaves the external
   revision, receipt histories, and record history unchanged;
5. preserve V12 and this rejection package byte-for-byte and stop for another
   different fresh static audit.

Even a later acceptance remains static-only and disconnected. This audit
grants no live media or production authority.
