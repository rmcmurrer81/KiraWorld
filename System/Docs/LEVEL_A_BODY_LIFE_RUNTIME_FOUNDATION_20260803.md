# Level-A body/life runtime foundation

Date: 2026-08-03  
Current status: **NON_PERSON_FIXTURE_PASS**  
Runtime status: **disconnected; no body or person was activated**

## Outcome

The project now has an executable deterministic Level-A foundation for testing
body/life state contracts without using Kira, Robert, a body asset, private
person state, or a world-action adapter. This is real running code with
state-transition, route, conservation, negative, restart, privacy-boundary,
and no-false-memory tests. It is not a claim that a biological body system,
person-owned experience, or person decision has been implemented.

The capability ceiling for this work is exactly `NON_PERSON_FIXTURE_PASS`.
`BODY_HOOKS_VERIFIED`, `PHYSIOLOGY_STATE_VERIFIED`,
`PERSON_DECISION_INTEGRATED`, `PRIVACY_AND_CONTINUITY_PASS`, owner acceptance,
generalization, and Avatar Builder method promotion remain unimplemented.

## Three separate executable layers

| Layer | Executable responsibility | Explicitly absent |
|---|---|---|
| Avatar Builder hooks | neutral non-intimate surface-zone names; exact semantic urinary, bowel, and menstrual fixture routes; disjoint endpoint checks | mesh, private coordinates, body binding, internal geometry, physiology, identity, preference, consent, memory |
| Body Systems Runtime | neutral signal receipts; urinary/bowel storage, threshold, delay, controlled release, interruption, recovery, and conservation; menstrual/cycle fixture progression and conservation; observation/test-versus-diagnosis boundary; generic controlled lifecycle | biological-function proof, subjective experience, person volition, consent, diagnosis, treatment, world action |
| Person/World boundary | content-free locked-context access; exact proposal/context/participant fixture responses; fresh-response enforcement; stop/interrupt/recovery; action and memory blocking | person privacy content, person consent, relationships, private memory, runtime action, active people |

`Core/level_a_body_life_fixture.py` composes those layers while retaining an
independent hash for each one. Every event may change only its selected layer;
the receipt records the two untouched sibling-layer hashes. Avatar Builder
hooks are immutable inside a running fixture.

## Executed capabilities

The following have reached only `NON_PERSON_FIXTURE_PASS`:

- exact three-layer separation and Level-A capability ceiling;
- neutral touch/pressure/temperature routing at non-intimate hook zones;
- distinct urinary, bowel, and menstrual material names and endpoints;
- bladder/bowel fixture storage, capacity, derived threshold state, delay,
  release, interruption, resume, completion, recovery, and exact conservation;
- deterministic cycle phase progression, irregular/uncertain fixture state,
  menstrual material generation/output conservation, and wrong-route blocking;
- health observations and test results that remain explicitly non-diagnostic;
- generic fixture-controlled lifecycle ordering:
  `available -> considered -> voluntarily_selected -> begun -> continued`,
  followed by stop, completion, or interruption, then recovery;
- content-free privacy locks, entry request/grant/denial, and exact participant,
  activity, context, and current-response coordination;
- serialization/restart with stable hashes, incomplete-state preservation,
  globally unique event IDs, monotonic time, and audit receipts that remain
  non-memory and non-experience evidence.

The lifecycle includes the framework's `voluntarily_selected` state name, but
Level A reaches it only through an explicit `fixture_control_signal`. The code
and evidence keep `person_volition_claimed`, `person_consent_claimed`, and
`external_action_performed` false. It therefore tests ordering without
pretending a neutral fixture made a personal choice.

## Fail-closed boundaries exercised

The focused suite rejects:

- person identity, private mind, memory, relationship, preference, desire,
  consent, maturity, voice, or likeness fields anywhere in an event payload;
- a body asset or private geometry attached to Level-A hooks;
- merged or wrong urinary/bowel/menstrual routes;
- storage above fixture capacity or output above stored/generated state;
- bladder/bowel release transitions without an explicit fixture-control signal;
- skipped cycle phases and menstrual output outside the menstrual fixture phase;
- observations or tests being relabeled diagnosis or treatment;
- an old fixture response being reused for a new proposal;
- a fixture response being relabeled person consent;
- action authorization/performance and audit-to-person-memory conversion;
- active-person IDs or exact subject-bound adult evidence inside Level A;
- any capability status above `NON_PERSON_FIXTURE_PASS`.

Existing exact subject-bound confirmed-adult gates remain unchanged and passed
their adjacent tests. Level A intentionally stores no adult-evidence record,
because no adult person or adult body is used here. This is not a bypass for an
adult lane, a non-adult lane, body activation, curriculum delivery, or private
activity.

## Robert avatar proxy permission

Robert's exact permission sentence is recorded at:

`Data/governance/robert_avatar_codex_nonperson_proxy_permission_v1.json`

Permission-text SHA-256:
`9c7172b5808760923a2c6ee1c2701981c5f4580fd32b8a3e57874d32f0690711`.

It is recorded only as future permission for a Codex-controlled, non-person,
private engineering proxy using one exact owner-approved Robert avatar asset.
It does not authorize impersonation, Synthetic Robert activation, a claim that
Biological Robert participated, inheritance of Robert's mind/memory/voice/
relationships/preferences/consent, or writing proxy actions into either
Robert history.

The permission remains `RECORDED_NOT_BOUND_NOT_INSTANTIATED_NOT_USED` because
no exact avatar asset and hash, append-only proxy instance, person-level test
plan, or separate authorization has been bound. Robert's asset permission is
not Kira's permission. A future Kira person-level test would require the exact
proxy disclosure and Kira's fresh, specific, revocable decision for that test.
No proxy or person was instantiated in this work.

## Verification

Focused command:

`py -m unittest Testing.test_level_a_body_life_runtime -v`

Result: **33/33 passed**. The final adversarial cases also reject an unknown
serialized reservoir phase, a broken orchestration hash chain, and a corrupted
child-event receipt.

Focused plus adjacent body-system, adult-policy, body-eligibility, and
biological-movement command:

`py -m unittest Testing.test_level_a_body_life_runtime Testing.test_avatar_biological_body_systems Testing.test_avatar_body_policy_gate Testing.test_body_runtime_eligibility Testing.test_avatar_builder_biological_movement_requirements -v`

Result: **93/93 passed**. No test opened Blender or bound a body/person.

Adjacent dialogue and privacy-session command:

`py -m unittest Testing.test_dialogue_privacy Testing.test_kira_robert_dialogue_privacy Testing.test_privacy_session_manager -v`

Result: **40/40 passed**. Total unique relevant checks in the recorded runs:
**133/133 passed**. This does not raise the Level-A capability ceiling or claim
that its content-free lock is person-private storage.

## Exact implementation bindings

| Path | Bytes | SHA-256 |
|---|---:|---|
| `Core/level_a_runtime_common.py` | 9,337 | `55cfe52370f47db60c0be04ebea9c367df221ae873a7856ba2b9ee4175ac0bb1` |
| `Core/avatar_builder_level_a_hooks.py` | 7,191 | `88edca17e563d2e022bb80974d47d93d0702f4ec9db210cd92dc4f8097754385` |
| `Core/body_systems_level_a_runtime.py` | 33,101 | `ad3e0ce9f5bb3ad6ed0cae5f0f974d67ea0f896020d1c0b50f39489f3bf06297` |
| `Core/person_world_level_a_runtime.py` | 21,651 | `f5158c8d23bf687a0812c8ca05beb36974c8629f976cc766cdbd271adb5df4e2` |
| `Core/level_a_body_life_fixture.py` | 14,960 | `c4ad94686128ee5e4e3d0100060ce6e45a7e75a48fb3b96f9dafeedc31af4590` |
| `Testing/test_level_a_body_life_runtime.py` | 28,237 | `a3468c938e715037fa8b6045c1ee8ad27e828ef382a1eeabf964012a04a369dc` |
| `Avatar/avatar_builder/body_systems/level_a_body_life_runtime_contract_v1.json` | 6,451 | `76c4b60deae8bafb3d7e6fff7d5b93a63809ec3bf6a340fbc8b1cc2e1f1c94c6` |
| `Data/governance/robert_avatar_codex_nonperson_proxy_permission_v1.json` | 3,638 | `6fae71e68def48dcbba12e14a24fbfe9d8e56030b181db546451cb1614376b45` |

The machine contract binds the uploaded 2026-08-03 acceptance framework
(`f4883920c473aed2b9b83172306860f5b2edf249fbf95ad43f80820a5dc92595`),
the current body-system modeling plan, and its acceptance matrix.

## Current false claims and next gates

Semantic route names do not prove that a mesh contains those routes or that
they are patent. Reservoir arithmetic does not prove urinary, bowel, menstrual,
pelvic-floor, continence, reproductive, pregnancy, or other biological
function. Neutral signals do not prove sensation. A fixture response is not
consent. A content-free lock is not person-private storage. An audit receipt is
not memory. No body hooks, physiology, person decisions, privacy continuity,
owner acceptance, generalization, or Avatar Builder method promotion have
passed.

The next valid stages remain separate and require new evidence: exact accepted
body hooks; actual state models; privacy/continuity infrastructure; and only
then voluntary person-level integration. This foundation does not authorize
those stages.

## Rollback

Rollback is additive and exact: remove only the five new `Core/` modules, the
focused test, the Level-A machine contract, the unbound proxy-permission
record, this System document, and the matching append-only evidence package.
Do not roll back or edit any Blender body, body candidate, person state,
memory, relationship, maturity record, runtime selector, or prior evidence.
