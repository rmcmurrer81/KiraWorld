# Avatar Builder Conversational Correction Memory and Age Progression

Status: implemented control-plane contract, 2026-08-01. This contract does not build, approve, activate, assign, publish, or upload an avatar.

## Owner-facing behavior

Robert can keep using ordinary Avatar Builder Chat language. He does not need to edit a manifest to report problems such as:

- “They look bald; give them fuller hair.”
- “The hairline is too far back.”
- “The eyes are outside the sockets.”
- “The face does not look like the person.”
- “No, this version is an adult; use an adult body.”
- “Use the character from the end of the series, not the high-school era.”

`Core/avatar_builder_ai.py` still exposes the existing `avatar_builder_chat(candidate_id, message, profile=None)` interface. Recognized corrections now also create a hash-chained event under `correction_memory_events` in the candidate's existing `avatar_builder_adjustments.json` and update `next_private_build_route`.

Older correction events are append-only. Each event stores the exact owner text, UTC recording time, extracted directives, the prior event hash, its own SHA-256, and the mandatory private/inactive/unapproved output policy. `verify_correction_event_chain()` detects sequence, content, ID, or prior-hash changes.

The current route pointer may change when a newer correction arrives; the event history must not. A route never means that a build or owner approval already happened.

## Narrow component routing

A correction reroutes only the affected component whenever possible:

| Owner correction | Next private route | Components explicitly preserved |
|---|---|---|
| fuller hair / receding hairline | detachable `hair` only | body, face, eyes, scalp/skin, rig, weights, movement |
| eye outside socket | named `eyes` assembly | accepted body, face, hair, rig |
| face likeness | `face` reference/landmark pass | accepted body and rig |
| explicit adult continuity correction | new append-only adult body lane when a prior wrong non-adult build exists | old candidate retained; no in-place age mutation |

Kira's current low-resource body remains bald. A Kira hair correction targets only the separate inactive hair master; it does not enable scalp hair in the runtime preview or body.

Every route is `private_owner_review_only`, inactive, unassigned, unpublished, and unapproved. Classification correction is not body approval. A successful builder pass is also not body approval.

## Continuity and offline owner authority

For fictional or character version selection, a logged explicit Robert-provided continuity, timepoint, or maturity correction is authoritative when the local classification is uncertain, including when Internet access is unavailable. The event records that no network lookup was required. The builder must trust that explicit owner correction for the requested fictional version instead of leaving an uncertain candidate permanently in the safe-default lane.

An isolated earlier-era word does not outrank an explicit later-version request. For example, “high school” used to describe earlier reference material cannot override an explicit end-of-series, post-graduation, post-college, or adult-era target. Peter Parker's exact current candidate ID routes to `adult_male` when Robert corrects a bad local non-adult classification and identifies the post-*No Way Home* / pre-*Brand New Day* timepoint.

This authority does not permit aging an explicitly non-adult version in place. A canonical non-adult identity remains protected, and any actual age progression requires a separate variant.

## Two-stage spa age progression

Age progression uses `two_stage_spa_age_progression_v1` and requires all of the following eligibility facts:

- temporary origin verified;
- permanent promotion verified;
- multiple prior activations verified, with an exact count of at least two;
- the resident's own choice durably recorded;
- spa flow durably recorded.

`evaluate_age_progression_stage_one_eligibility()` enforces those facts before the builder may queue Stage 1. A candidate without verified temporary origin, permanent promotion, at least two exact prior activations, the resident's Age Progression choice, or a recorded spa flow is blocked without changing its adjustment file.

Stage 1 creates a separate candidate ID and variant profile. Its older/taller presentation comes from the Age Progression process, followed by proportion and rig refitting and the `adult_aged_up_variant` presentation/build label only. Stage 1 remains exact-maturity `unresolved`; neither spa completion nor this label is a confirmed-adult classification. It must explicitly prove that adult anatomy is absent. Even if one chat sentence asks for age progression and anatomy, the anatomy request cannot skip Stage 1.

Stage 2 is evaluated by `evaluate_age_progression_stage_two_gate(route, stage_one_evidence)`. It allows adult-anatomy authoring only when exact Stage 1 evidence proves:

- the artifact is a separate variant;
- its presentation/build label is `adult_aged_up_variant` while exact Stage 1 maturity is `unresolved`;
- exact subject-bound confirmed-adult classification, authority, source-text hash, and UTC provenance are explicitly recorded for the separate variant;
- the older/taller presentation passed;
- adult anatomy was absent during Stage 1;
- an exact artifact SHA-256 is present;
- all promotion, activation-history, resident-choice, and spa-flow eligibility facts passed;
- the now-confirmed-adult resident's separate choice for the Stage 2 adult-anatomy revision is recorded.

Stage 2 authors another private, inactive, unapproved candidate revision. Runtime activation remains false and owner visual approval remains mandatory.

## Build-worker integration

Before a private authoring worker starts, it must read `next_private_build_route` from the candidate adjustments and enforce:

1. `components_to_rebuild` as the only invalidated component set;
2. `components_to_preserve` and `component_isolation_required` as hard non-regeneration rules;
3. `body_lane` and logged continuity before selecting references or a foundation;
4. `replacement_strategy=append_only_new_adult_body_build` when correcting a wrong non-adult body for a confirmed adult version;
5. the Stage 1 permanent-promotion/repeated-activation/resident-choice/spa gate before older/taller work, followed by the confirmed-adult and separate resident-choice gate before any Stage 2 anatomy work;
6. the private/inactive/unassigned/unpublished/unapproved flags on every output.

The Avatar Builder Workspace server exposes the correction-event count and route metadata without changing the existing chat endpoint.

## Verification

Focused isolated tests are in `tools/test_avatar_builder_conversational_correction_memory.py`. They cover hash-chain immutability, hair-only isolation, eye/face routing, Peter's later adult continuity correction after a deliberately bad stored class, isolated high-school wording, explicit offline owner confirmation for an uncertain fictional candidate, explicit non-adult and Marinette in-place blocking, Stage 1 eligibility/anatomy blocking, and the confirmed-adult/resident-choice Stage 2 evidence gate.
