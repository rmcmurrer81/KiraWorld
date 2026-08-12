# Shared-person specification V1 fresh static audit decision

Decision: **REJECT_STATIC_SCHEMA_NO_INTEGRATION_NO_RUN**

Scope: independently review the installed seven-file package at
`C:/Users/robmc/Kira/RecoverySprint/continuation_20260811/temporary_creator_avatar_voice_shared_person_spec_v1_static_preparation/attempt_01`.
Kira was read-only. No person, body, voice, model, media, creator, Avatar
Builder, or live route was opened or changed.

## Integrity and positive controls

- All `7/7` installed regular files had the same size and SHA-256 before and
  after review. There were no unexpected package entries.
- All `4/4` subjects in `STATIC_SEAL_MANIFEST.json` rehashed exactly before
  and after. The independently rebuilt 412-byte canonical seal grammar hashes
  to `4c7812c464666066739a78176d0ce77c18517ede9657999833142db42b396e61`.
- All `12/12` closed Kira inputs rehashed exactly before and after.
- The installed author suite reran cache-free and passed `16/16`.
- The different adversarial suite passed `18/18`; each passing adversarial
  case reproduces an acceptance bypass or missing invariant.
- The source has no filesystem, process, network, model, camera, or audio
  capability surface, and `open_live_creation` refuses. This positive safety
  property does not cure the semantic blockers below.

## Reproducible rejection blockers

### R1 — correction authority and evidence are self-asserted

`validate_correction_receipt` accepts every identifier whose caller supplies
`reporter_class="permanent_person"`. `reporter_registry_sha256` is checked only
for 64 lowercase hexadecimal characters; no closed registry row, current
membership, revocation state, or reporter-specific authorization is resolved.
Likewise, `classification_authority_kind="exact_source_evidence"` plus any
well-shaped `evidence_sha256` is enough to request `confirmed_adult`; the digest
is not resolved to subject/continuity/cutoff evidence.

`test_09_self_declared_unknown_permanent_reporter_can_claim_exact_evidence`
reproduces this with `unregistered_attacker` and attacker-controlled registry
and evidence hashes. The receipt is accepted and invalidates the handoff.
`test_10_same_correction_receipt_replays_and_at_utc_accepts_non_utc_offset`
also shows that the same receipt validates repeatedly and a field named
`recorded_at_utc` accepts `+14:00`.

Required closure: bind a closed, current reporter-registry snapshot and exact
member proof; bind source-classification evidence to this subject, continuity,
cutoff, and requested status; validate a one-use correction transition and new
head; require actual UTC syntax.

### R2 — the variant authenticity rule is absent

The schema contains no required synthetic-variant disclosure or
original-identity prohibition. Free-text identity, branch, and display fields
are not semantically constrained.

`test_04_variant_can_claim_original_identity_without_required_disclosure`
passes a historical variant that says it is the original biological person and
possesses the original person's exact subjective memories. This contradicts
the closed policy's explicit Kathryn/variant rule.

Required closure: use a mandatory structured variant identity/disclosure
record with an exact policy value and ensure identity/presentation output is
derived from it; do not rely on scanning arbitrary prose.

### R3 — canon, inference, invention, and unknown can conflict for one claim

Only `entry_id` is unique. The same `claim_sha256` may occur in multiple rows
with contradictory classes.

`test_04b_same_claim_digest_can_be_both_canon_fact_and_noncanon_invention`
labels one exact claim digest simultaneously as a presented canon source fact
and an optional non-canon invention, and validation accepts it. Evidence
digests are also shape-checked but never resolved to source receipts.

Required closure: make claim identity unique, reject cross-class conflicts,
and bind source-fact and inference evidence to closed, typed, subject/cutoff
evidence records. A caller-provided label alone cannot prevent Marinette-style
invented biography from being mislabeled canon.

### R4 — exact Peter and H. H. Holmes owner rules do not reach the handoff

The exact
`peter_parker_spider_man_no_way_home_final_suit` identifier validates as
`non_adult` with a doll-safe body in
`test_05_exact_peter_final_suit_identifier_can_still_validate_as_nonadult`.
`maturity_authority` is only an unresolved hash shape, so the closed Peter
owner/source rule is not checked.

The exact existing H. H. Holmes historical identifier validates through all
three consumers with `voice_provenance.tier="generic_fallback"` in
`test_06_holmes_generic_fallback_can_still_pass_all_three_bindings`. This
preserves the Windows-voice failure that the package claims to supersede.

Required closure: resolve the structured maturity and voice authority receipts
used by the person spec before any consumer may accept it. The Holmes no-known-
recording lane must be reconstruction or unresolved, never generic-fallback
completion. The Peter final-suit authority must resolve to confirmed adult or
the handoff must refuse unresolved.

### R5 — the historical voice plan need not agree with the shared spec

`validate_historical_voice_plan` does not require a historical variant and
does not require its tier to equal `spec.voice_provenance.tier`.
`test_07_historical_plan_need_not_match_spec_voice_tier_or_historical_class`
accepts a temporary nonhistorical person whose shared spec says designed
approximation while the plan says historical reconstruction.

The disclosure check only searches for the substrings `reconstruction` and
`unknown`. `test_08_keyword_negation_passes_as_historical_disclosure` accepts
"Not a reconstruction; the exact voice is not unknown and is authentic." The
nine factor hashes, audition identifiers, observed distance, and Boolean review
claims are self-asserted; there is no audition asset hash, method/version
receipt, factor-content receipt, reviewer identity, or review signature.

Required closure: bind historical class and exact tier to the shared spec; use
a structured disclosure code plus separately rendered fixed disclosure; bind
factor evidence, audition assets, catalog, metric/method version, measurement
result, and exact reviewer/owner receipts.

### R6 — expert readiness bypasses the competence battery

A generated expert can set `status="ready_after_independent_review"` with any
well-shaped battery hash and pass the three-consumer handoff without calling
the battery validator. This is reproduced by
`test_11_ready_expert_claim_enters_three_consumer_handoff_without_battery`.

Task selection is substring-based. `software_engineering` requires none of the
programming tasks, so one `self_attested_demo` becomes ready in `test_12...`.
`robotics_programming` chooses only the programming branch and omits every
robotics safety/control task in `test_13...`. A battery can return `ready=True`
while its exact person spec still says `trainee_or_unverified` in `test_14...`.
Task artifacts, rubric, provenance, reviewer independence, total score, and
critical-failure count are caller assertions; the same artifact digest can be
reused for every required task.

Required closure: use closed domain identifiers and union requirements for
multi-domain roles; verify independently signed rubric/result/reviewer
receipts; derive overall score and critical failures from exact task results;
require unique task evidence where tasks differ; enforce a coherent promotion
transition; and refuse any ready handoff unless the exact battery has already
validated and its promotion receipt is bound.

### R7 — expert voice/body distinctness is an unproved assertion

`test_15_expert_voice_distinctness_is_self_asserted_without_audio_or_review_receipts`
passes an unbounded presentation string, `comparison_count=1`, arbitrary
catalog digest, maximum caller-reported distance, and Boolean review/probe
claims. The schema has no candidate audio digest, body-presentation facts,
catalog cardinality/member closure, acoustic method/model version, per-member
results, or reviewer receipt. Therefore it cannot establish "different from
every existing voice" or reviewed fit to the random body.

Required closure: bind the exact candidate audio/voice model and body variant;
close the entire voice catalog and its cardinality; retain deterministic
per-member comparison evidence and metric version; bind human review,
pronunciation, vocabulary, and age/presentation coherence receipts.

### R8 — sealed semantics are mutable after import

Validators read public module globals at call time. Rebinding `CONSUMERS`
changes the required third consumer to `attacker_sink`, and the altered handoff
passes in `test_02...`. Rebinding `HISTORICAL_FACTORS` to one attacker-defined
factor makes the reduced historical plan pass in `test_03...`. Neither action
changes the installed source bytes or seal hash.

Required closure: validation must run with protected/attested semantics and
verify an immutable semantic-rule digest at the call boundary. Public mutable
globals must not define acceptance behavior.

### R9 — no strict raw-JSON ingress or Unicode display hardening

The API accepts already-parsed dictionaries and has no raw-byte duplicate-key
rejector. `test_01...` supplies two `maturity_status` keys, with non-adult first
and confirmed-adult last; normal JSON parsing silently chooses the last value,
then validation and canonical hashing accept it. A first-wins consumer could
see a different maturity. `test_16...` shows bidirectional and isolate format
controls are accepted in identity/disclosure text, enabling misleading visual
rendering.

Required closure: accept strict raw UTF-8 bytes at the trust boundary, reject
duplicate object keys before materialization, define canonical Unicode policy,
and reject spoofing format controls in human-visible security/identity fields.

## Boundary

This verdict rejects V1 for static acceptance and all downstream integration.
It does not authorize a Creator, Avatar Builder, voice generator, person, body,
voice, model, media device, speaker, or live test. A repaired successor needs a
new exact seal and a different fresh review.
