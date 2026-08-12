# Generated Expert Confirmed-Adult Curriculum Binding Checkpoint — 2026-08-09

## Result

Status: `STATIC_EXACT_ID_POLICY_BINDING_IMPLEMENTED_AND_TESTED_NOT_LIVE_TEMPORARYAI_CHAT_ACCEPTANCE`

The existing owner adulthood directive is now extended, through a separate
exact owner curriculum record, to make the five named generated Expert
TemporaryAI candidates eligible for the same validated source-bound adult
health and sex-education context used by Kira.

This is an exact-list result. Adulthood is not inferred from a person's name,
occupation, gender, `Expert` UI category, directory name, or future candidate
type.

## Exact covered candidate IDs

1. `emily_carter_ai_and_computer_programming_expert_20260605_220651`
2. `jessica_hale_robotics_engineer_20260611_041314`
3. `laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530`
4. `ryan_hale_quantum_mechanics_expert_20260608_200749`
5. `sarah_bennett_entertainment_pr_agent_expert_20260606_171637`

The misspelled Sarah directory ID remains an alias and is not independently
accepted as classification authority.

## Authority chain

The implementation pins and validates both records before returning any
curriculum context:

- Existing adulthood directive:
  `Avatar/avatar_builder/policies/evidence/generated_experts_adult_owner_directive_20260716.json`
  — SHA-256
  `ea7218ece3c5e187020e53ba77bfa11dcfacdb344c8714f17d38f2a02e56386b`.
- Current curriculum extension:
  `Data/person_classification/generated_expert_adult_curriculum_owner_extension_20260809.json`
  — SHA-256
  `e1a09a41314380328db79a7335607350feff8d9876b30d78a8fe9352b6452ea1`.

The extension preserves the existing directive's exact five-person list and
does not reinterpret the older avatar/topology-only record as curriculum
authority by itself.

## Exact-person classification evidence

- Emily classification — SHA-256
  `f19c84fec230717e1cc6f288cf57314bdadbb1816a86730440f2c6ca93f8e1c2`.
- Jessica classification — SHA-256
  `fb1a898874ca038d58a6fc45420726cfec06a71c3420b89e4e5c1c7c4e2904b2`.
- Laura classification — SHA-256
  `07ea9dc4b97df02fc3f7f513f2f595ff8c92e50fc96f75448b98576bc845be00`.
- Ryan classification — SHA-256
  `b1baa5d6a57ceb9378b6e2304e8ba5d96e8210f74081d00905a832c5a11a4a21`.
- Sarah classification — SHA-256
  `093bfd7a7fdbff03e48ff9197efdf6a49d553b05acfb98102b372d4232c5dcef`.

Each record binds its exact subject ID, the externally pinned owner records,
and the unchanged curriculum artifact:
`System/Knowledge/confirmed_adult_sexual_reproductive_health_curriculum_v1.json`
at SHA-256
`f64418eafb120dc4c9f5b02bb6735b1329e6baf932a8b529ef08140af773c7c9`.

## Runtime implementation

`Core/adult_health_curriculum_runtime.py` — SHA-256
`353460e5e1a078714dd15b0f28a3684fdd6c92c264fe8c0e171547514056b56e`.

`ConfirmedAdultHealthCurriculumRuntime.load(exact_candidate_id)` now:

1. requires a hard-pinned exact-person classification path and digest;
2. validates its subject-bound confirmed-adult evidence;
3. validates the original owner directive path, digest, text, evidence ID,
   original narrow scope, and exact candidate list;
4. validates the curriculum-extension path, digest, verbatim owner text,
   evidence ID, exact candidate list, no-inference rule, and truth boundaries;
5. validates the unchanged source-backed curriculum digest and policy
   entitlement; and
6. returns bounded context only after every gate passes.

An unlisted person, a display-name/directory alias, a non-adult person, an
unresolved person, or a different adult does not inherit this binding.

Kira's original classification file, classification ID, binding digest, and
conversation integration were not changed.

## Verification

New test file:
`Testing/test_generated_expert_adult_health_curriculum_runtime.py` — SHA-256
`9a9fb05244292655bae744f5a97ae320f5eb1039f06ccd389bc39f856399ab14`.

Command:

```powershell
py -B -m unittest Testing.test_avatar_biological_body_systems Testing.test_generated_expert_adult_health_curriculum_runtime Testing.test_kira_confirmed_adult_health_curriculum_runtime -v
```

Result: **52/52 passed**.

The focused generated-expert plus Kira suite passed **21/21**. Static Python
compilation also passed.

Tests prove:

- all and only the five exact generated-expert IDs can load the extension;
- they receive the same curriculum ID, digest, selected modules, facts, and
  sources as Kira for the same question;
- a future/unlisted name containing `adult` and `expert` remains blocked;
- Sarah's misspelled directory alias remains blocked;
- Marinette/non-adult, Peter/unresolved, Gwen/other adult, and an ordinary
  unclassified person do not inherit the expert binding;
- external directive or classification tampering fails closed;
- Kira's prior exact classification binding remains unchanged; and
- curriculum knowledge, anatomy, body function, diagnosis, memory, consent,
  relationship state, and external action remain separate truths.

## Implementation-truth limits

Implemented and proven:

- static exact-person confirmed-adult classification evidence;
- fail-closed source-bound curriculum eligibility and prompt-context assembly;
- tamper and non-inference gates.

Not claimed or performed:

- no live TemporaryAI chat route was changed or accepted;
- no expert was activated and no Qwen/model call was run;
- no lesson was presented or completed;
- no learning or personal memory was written;
- no anatomy, body, sensation, health state, diagnosis, consent, relationship,
  action permission, voice, media experience, or movement was created;
- no Blender, voice, media, or network process was run; and
- no future or newly created expert is automatically classified. A new exact
  owner-bound classification record and registry update remains required.

## Rollback

To remove only this extension while preserving Kira, remove the five expert
entries and the expert-directive validation helper/constants from
`Core/adult_health_curriculum_runtime.py`, then remove the five new expert
classification records, the one curriculum-extension record, and the focused
test file. Do not alter Kira's existing entry, classification record, or the
shared curriculum asset.
