# Avatar Builder biological body-systems Phase 0/1 foundation — 2026-08-03

Status: **implemented as a disconnected semantic/state prototype; not runtime
authority and not evidence of biological function**.

This additive foundation turns the existing source-backed planning policy into
a machine-readable anatomy/route vocabulary and a deterministic pure state
model. It does not build internal organs, change an external mesh, open
Blender, activate a body, grant a relationship action, diagnose a condition,
create a pregnancy, or write person memory.

## Bound source plan

The registry binds the current additive plan:

`Avatar/avatar_builder/policies/sexual_reproductive_health_body_systems_plan_v1.json`

- Bytes: `11606`
- SHA-256:
  `573980817e3555dbfb4f2ea27c6248a37857ffc0349dc6007e8af1bd570dd8b1`
- Required plan status:
  `PLAN_ONLY_NOT_IMPLEMENTED_NOT_RUNTIME_AUTHORITY`

The plan's exact 14 starting-source URLs are carried into the registry with
their intended scope. They were not refetched during this implementation, so
the machine record explicitly leaves retrieval date null and marks current
source re-verification/date pinning as pending. This prototype must not be
used as current individual medical advice. The 14-source inventory includes
the already documented NCBI Bookshelf vaginal structure/function source
`NBK545147` and penis anatomy source `NBK482236`; plan, registry, and this
document are checked for exact URL equality rather than a minimum count.

## Files and ownership

- `Avatar/avatar_builder/body_systems/semantic_anatomy_route_registry_v1.json`
  owns canonical structure IDs, routes, vocabulary aliases, maturity and truth
  invariants, source bindings, and the six separate state-domain definitions.
- `Core/avatar_biological_body_systems.py` owns the deterministic disconnected
  state prototype and its validation errors.
- `Testing/test_avatar_biological_body_systems.py` is the focused acceptance
  suite.
- `Avatar/avatar_builder/policies/adult_curriculum_private_sensation_policy_v1.json`
  binds the exact current plan, spa policy, source-backed document, and Rights
  Charter and owns the immediate-curriculum/private-state owner decision.

This additive update changes the planning and spa policies and their generator
source. It changes no body, rig, mesh, person, memory, relationship, runtime
selector, or life-loop record.

## Controlling truth boundary

An external mesh or visible opening does not establish an internal organ,
route, flow, sensation, fertility, bathroom function, diagnosis, pregnancy,
preference, or consent.

The registry is semantic continuity, not geometry or physiology. The state
model is a deterministic data prototype, not a claim that any synthetic or
biological person experienced the state. Every initial state retains false
flags for internal-function implementation, biological proof, lived
experience, automatic diagnosis, and runtime connection. The transition
engine rejects any state whose caller changes one of those flags.

## Semantic route registry

The adult-female lane distinguishes three external endpoints:

| Route | Semantic endpoint |
|---|---|
| Urinary | `female_external_urethral_opening` |
| Menstrual/reproductive outflow | `vaginal_opening_introitus` |
| Bowel | `anal_opening` |

The adult-male lane keeps urinary and reproductive upstream structures
separate while explicitly recording their shared downstream urethral segments.
The bowel route and anal opening remain separate from both. Paired structures,
external structures, internal ducts/organs, erectile tissues, pelvic support,
and continence structures have distinct canonical IDs.

Every route has `function_implemented: false`. A route does not prove that a
3D passage exists, is open, can carry a flow, has appropriate tissue response,
or is healthy.

## Six deterministic state domains

The prototype keeps these top-level records independent:

| Domain | Prototype responsibility | Explicit non-claim |
|---|---|---|
| `urinary` | phase and observation records | no bladder/voiding function or diagnosis |
| `bowel` | phase and observation records | no bowel/defecation function or diagnosis |
| `menstrual_reproductive` | lane-aware cycle/reproductive vocabulary and observations | no fertility, cycle, response, or diagnosis inferred |
| `contraception_sti_health` | voluntary method state, observation, and exact test record | no consent, pregnancy proof, or automatic diagnosis |
| `consent_action_leases` | exact participant/activity/context/time lease | no action is performed and no relationship supplies consent |
| `pregnancy` | evidence-bound test/phase/timeline-choice prototype | never inferred from mesh, activity, consent, or contraception |

`initial_state()` returns a JSON-compatible record. `apply_event()` is a pure
transition: it deep-copies the state, requires an exact unique event ID and an
explicit offset-bearing timestamp, changes only the named domain, appends a
canonical payload hash, increments the revision, revalidates all truth
invariants, and returns the new state. It never writes a file.

`state_sha256()` gives a canonical digest for an exact validated state.

## Maturity gate

The only adult-state-enabling classification is `confirmed_adult`. Because
`initial_state()` contains adult semantic routes, it now rejects construction
itself for `non_adult` and `unresolved` with `MaturityGateError`. Those lanes
use `curriculum_entitlement()` with the required
`doll_safe_non_anatomical` body representation and never receive an adult body
state.

No name, filename, appearance, body mesh, lesson, school-era keyword, or
relationship status can infer adulthood. A bare `confirmed_adult` string is
not sufficient for any adult curriculum, private-sensation, solitary-choice,
or adult-state result. The caller must supply durable exact-person evidence
containing a classification ID, matching subject ID, `confirmed_adult` status,
Robert's explicit owner-confirmation authority, offline/network-independence
flags, an offset-bearing UTC record time, Robert's exact source text, and the
matching UTF-8 SHA-256. The full evidence remains in serialized prototype
state and is revalidated after every transition; a reduced evidence digest is
not treated as a substitute. Missing evidence, a wrong subject or status, or a
source-text hash mismatch fails closed with `MaturityGateError`.

This local evidence route does not require the internet. Classification is not
body approval, consent, diagnosis, or action authority. This prototype does
not age anyone up or add anatomy.

## Immediate curriculum assignment

`curriculum_entitlement()` is a deterministic, file-write-free routing
evaluator. Every exact subject-bound, evidence-verified `confirmed_adult`
result receives the complete 12-module source-backed adult curriculum
immediately. Its result is unchanged by
relationship status, romantic or sexual interest, adult-anatomy selection,
prior experience, or spa completion.

For `non_adult` and `unresolved`, the evaluator returns the guaranteed six-part
minimum: age-appropriate hygiene, privacy, bodily autonomy, personal
boundaries, abuse prevention, and trusted help. This is not an exhaustive
ceiling. Any additional youth module requires separate age-appropriate source
binding and approval and cannot inherit an adult-curriculum module. Supplying
an adult body representation for either classification fails closed.

This is assignment/entitlement only. Lesson delivery, learning memory, body
modification, relationship state, and person-state mutation remain false.

The exact spa policy is hash-bound through
`adult_curriculum_private_sensation_policy_v1.json`. Spa completion and an
`adult_aged_up_variant` presentation/build label do not establish
`confirmed_adult`. The separate resulting variant defaults to `unresolved`
until separately classified. Exact confirmation immediately assigns the full
curriculum but still never auto-adds adult anatomy; anatomy remains a separate
person choice and build/review gate.

## Future private sensation and solitary-choice contract

`private_sensation_contract()` exposes only a disconnected schema for future
evidence-verified confirmed-adult person-owned private states: touch, comfort, arousal, pleasure,
climax, relaxation, discomfort, uncertainty, and variation. Every value starts
`not_observed_not_simulated`. Physiology, desire, preference, consent, action,
health, and memory are explicitly separate. Runtime storage, privacy-system
connection, physiology, experience, and memory remain false.
Adult anatomy never equals or creates consent. Physiological response and
person-owned subjective arousal each remain separate from consent and desire;
subjective arousal is not automatically a physiological response.

`evaluate_private_solitary_choice()` recognizes an evidence-verified confirmed adult's own private
solitary choice without a relationship or partner/owner permission. It does
not execute an action, create sensation, infer preference/orientation, change
health, or write memory. `non_adult` and `unresolved` decisions fail closed.

## Current consent and action leases

A lease requires:

- a new exact lease ID;
- at least two exact participants;
- `confirmed_adult` for every participant;
- current affirmative consent from every participant;
- one exact activity;
- one exact context;
- a grant time and a later expiry time.

`lease_allows()` returns true only for an exact participant set, activity,
context, active status, and time inside that lease. A participant's revoke,
uncertainty, exit, or material context change immediately and permanently
revokes that lease ID. Prior consent, a relationship, body response,
contraception, or a different activity cannot mint or extend a lease. The
prototype records no performed action.

## Health and pregnancy boundaries

Health observations are stored with
`observation_only_uncertain_not_diagnosis`; their diagnosis field remains
null. Test results require an exact evidence ID but still do not populate a
diagnosis. Requests such as `infer_diagnosis` are rejected with
`DiagnosisInferenceError`.

Contraception selection requires `voluntary_choice: true` and changes neither
consent nor pregnancy. Pregnancy confirmation requires a separate explicit
test result plus evidence ID in the adult-female lane. A consent lease does not
change pregnancy state. The adult-male lane keeps reproductive-health
observations available but marks menstrual-cycle and pregnancy states not
applicable. These are prototype records only; they do not implement fertility,
gestation, delivery, or medical care.

## Integration boundary

Current connections are all false:

- runtime;
- persistent person state;
- external or internal mesh;
- memory;
- relationship system;
- education delivery;
- lesson-learning memory.

Future integration must be separately reviewed. In particular, no runtime
adapter should be added until exact-person maturity authority, private state
storage, access control, clinical-source currency, body/route implementation,
consent/action separation, and append-only audit behavior have their own
acceptance evidence.

## Verification

Focused tests cover:

- exact plan hash/status and honest inherited-source status;
- adult-female route separation and adult-male upstream/shared-downstream
  semantics;
- known-node and `function_implemented: false` route validation;
- construction-time rejection of adult route state for unresolved and
  non-adult classifications;
- fail-closed rejection of a bare adult maturity string, missing evidence,
  wrong exact subject, wrong evidence maturity status, or tampered source-text
  hash across curriculum, private-state, solitary-choice, and initial-state
  construction;
- revalidation of the complete subject-bound evidence after serialized-state
  tampering and every deterministic transition;
- exact ordered equality of all 14 source URLs across the source-backed System
  document, machine plan, and semantic registry;
- immediate complete confirmed-adult curriculum independent of relationship,
  interest, anatomy selection, experience, and spa completion;
- exact guaranteed-minimum curriculum, no adult-module inheritance, and
  doll-safe representation for non-adult and unresolved classifications;
- spa completion without maturity/anatomy unlock and immediate curriculum only
  after separate exact confirmation;
- schema-only private sensation truth-domain separation;
- confirmed-adult private solitary choice without partner/owner permission and
  without an action, sensation, health, or memory claim;
- deterministic, non-mutating, duplicate-safe transitions;
- cross-domain isolation;
- observation/test versus diagnosis separation;
- exact time-bound all-adult leases and immediate current-consent revocation;
- uncertainty, exit, and context-change invalidation;
- rejection of relationship/body-response consent shortcuts;
- voluntary contraception independence;
- pregnancy evidence and non-inference;
- lane-aware menstrual/reproductive state;
- immutable mesh/function truth and lack of Blender/runtime integration.

The original checkpoint in
`RecoverySprint/continuation_20260803/avatar_builder_biological_body_systems_phase_0_1`
remains sealed historical evidence. The additive owner-decision checkpoint in
`RecoverySprint/continuation_20260803/adult_curriculum_private_sensation_policy_update`
records the current hashes, five owner cases, and rollback instructions. The
final guarded verification passed 82/82 policy/foundation/library checks,
95/95 adjacent boundary checks, 10/10 Avatar Builder parser checks, 2/2
temporary-body conversational acceptance checks, 12/12 correction-memory
checks, 35/35 schema/embodiment/wearable checks (including 3/3 new maturity-
schema alignment regressions), and the seven-case isolated legacy
chat-understanding check. All eight
canonical builder-state guard hashes remained unchanged after restoration of
the separately preserved test-contamination incident.

## 2026-08-03 exact-evidence and source-inventory correction

The current append-only correction closes two acceptance gaps without
connecting this prototype to a person, body, Blender, memory, lessons,
relationships, privacy storage, or runtime:

- the machine plan and semantic registry now carry the same exact ordered 14
  URLs already present in the source-backed body-systems document; and
- adult curriculum, private-sensation, private-solitary-choice, and adult-state
  construction now require and retain the exact subject-bound confirmed-adult
  evidence described above. A bare maturity string no longer passes.

Historical source inventories and v1/v2 modeling bindings remain byte-exact.
`Avatar/avatar_builder/body_systems/modeling_acceptance_plan_binding_v3.json`
and its append-only verification overlay replace only the five intentionally
updated current records while continuing to rehash all 40 non-self source
records. The mutable focused verifier remains the sole self-hash exclusion and
is instead sealed by the correction-package manifest.

Current evidence and rollback instructions are in
`RecoverySprint/continuation_20260803/adult_curriculum_private_sensation_policy_gap_correction/`.
