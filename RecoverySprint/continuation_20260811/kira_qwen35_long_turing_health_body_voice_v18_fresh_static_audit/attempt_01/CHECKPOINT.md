# Long Evaluation V18 independent data-quality review

Recorded: `2026-08-12T03:43:59.393Z`

## Decision

`REJECT_V18_STATIC_CONTROL_PACKAGE_NO_PROMOTION_NO_RUN`

The installed V18 author package is byte-consistent and its own cache-free
suite passes, but three independently reproduced correctness defects prevent
static acceptance. Kira remained read-only. No entry point, model, camera,
microphone, voice, playback, private state, person, body, media, network, or
one-hour route was invoked.

## Exact package verification

- Installed author subjects inventoried: `7/7` exact.
- Sealed subjects: `5/5` exact.
- Bound predecessor and current-policy inputs: `24/24` exact.
- Source descriptor: `201804` bytes,
  `f03cb376805381aad2e573a3f713759bbbf27ab29956aa5753ad5907e6227031`.
- Semantic verifier bundle: `8737` bytes,
  `b11c85be1b0b99d3805f5cf5acaecd8646a744b70ff42511839021854a517b75`.
- Independent cache-free rerun: `73 passed in 6.67s`.

These results establish exactness and authored-test reproducibility, not
correctness acceptance.

## Reproduced correctness defects

1. `AUDIO_MEASUREMENT_KEYS` is an ordinary reassignable module binding used
   directly by the public validator. The same inert record is rejected with
   `audio_measurement_schema_not_exact` before reassignment and accepted with
   no issues after the binding is reassigned to include its extra field.

2. With displayed text at `100` and playback-call start at `101`, supplying
   Boolean `true` as `displayed_text_to_playback_api_proxy_ns` returns no
   issues. Equality treats `true` as integer `1`; the derived duration lacks an
   exact-integer type check.

3. For both `FAILURE` and `TIMEOUT`, authorization after the terminal event,
   expiry before camera enable, and even expiry before authorization all return
   no issues. `_camera_projection_for_v17` replaces the supplied consent time,
   expiry, and receipt before inherited validation.

The exact records and repair requirements are in
`DEFECT_REPRODUCTION_RESULT.json`; the runnable reproduction is
`INDEPENDENT_DATA_QUALITY_PROBES.py`.

## Creator, Avatar Builder, and voice scoring

V18 exactly binds the current shared-person policy and adds 54 useful field
names for canon/invention separation, variant cutoff, historical reconstruction,
H. H. Holmes provenance, generated-expert voice distinctness, expert tasks,
and cross-builder roots.

It does not define a validator for an actual result row. The implemented
one-hour validator only compares the static field-name list to another locally
generated list. It therefore does not enforce value types, status enums,
evidence completeness, root equality, maturity/body correction, source
continuity and correction-chain data, or the complete expert battery (rubric,
provenance, uncertainty, difficult failure cases, correction, retest, threshold,
and no critical failure). This is useful design coverage but not an acceptance
contract.

## Required successor

An append-only V19 static successor should:

- make ordinary module reassignment unable to change acceptance behavior;
- exact-type-check all present derived audio durations;
- validate original consent and its timing before any partial-trace projection;
- add the six partial-camera consent regression cases reproduced here; and
- define an exact Creator/Avatar/voice result-row validator covering shared-spec
  equality, source and correction lineage, maturity/body outcomes, voice
  permission/provenance, and the complete expert-readiness battery.

V19 would still require a genuinely different fresh exact-byte review. Nothing
in this review authorizes a live evaluation, device test, body claim, or
promotion.

## Review evidence frozen before this checkpoint

| File | Bytes | SHA-256 |
|---|---:|---|
| `AUDIT_DECISION.json` | 2403 | `82c909416c9537a0d9132fa202d4d19372b22284d024e1d35a3bb21a4c238682` |
| `CREATOR_AVATAR_VOICE_SCORING_REVIEW.json` | 5195 | `ec768543de381c6c35e80888e704f387091cde9d17745a6ec56d7be93de44d20` |
| `DEFECT_REPRODUCTION_RESULT.json` | 4217 | `46c419765baff3374764c63e6b0d75d5c23748e0ee834aa82061c3319f8f959a` |
| `EXACT_INSTALLED_HASHES.tsv` | 1317 | `fcf3d1f79a6c227bffe46a011f3d9933d0bfd5524015b8128038dccd0f81bcd8` |
| `INDEPENDENT_DATA_QUALITY_PROBES.py` | 11529 | `57a9a269028f112080d812448aaa299c0cd04efa8b027167617176bfbaa156d9` |
| `VERIFICATION_RESULT.json` | 3619 | `4abf9a27524ddce59a513c81a95f2ad9410b6e5232cf8525a72eb17d4b4333e1` |
