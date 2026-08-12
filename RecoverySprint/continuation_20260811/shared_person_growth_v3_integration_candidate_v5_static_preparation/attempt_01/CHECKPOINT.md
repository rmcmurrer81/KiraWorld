# Shared Growth integration candidate V5 author checkpoint

Date: 2026-08-11  
Author lane: `/root/growth_v4_audit`  
State: `AUTHOR_STATIC_TESTS_PASS_PENDING_DIFFERENT_FRESH_AUDIT`  
Authority: disconnected static candidate only; no promotion, person upgrade, Creator integration, or live operation

## Why V5 exists

V4 remains preserved byte-for-byte and rejected after relocation into Kira. Its Kira-local cache-free suite produced **45 failed, 117 passed, 95 subtests passed**. The two demonstrated causes were:

1. V4 derived a predecessor/rejection evidence root from its author location, which relocated to the absent `C:\Users\robmc\growth_v3_quality_review` path.
2. V4's no-consumer test assumed only source/test references, so it treated a preserved audit probe inside Kira as a production consumer.

V5 is append-only. It uses the explicit exact root `C:\Users\robmc\Kira` for all predecessor, policy, inventory, author, audit, and relocation-rejection evidence. Preserved audit/evidence references are classified separately from production consumers. V4 bytes were not edited or deleted.

The relocation rejection is bound exactly:

- `RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_v4_kira_relocation_failure/attempt_01/TEST_RESULT.txt`: 1049 bytes, SHA-256 `4d4f0329c29e9b432a5da760203d87f2fac6d1e9ca6ad10665e1286f4c111572`
- `RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_v4_kira_relocation_failure/attempt_01/CHECKPOINT.md`: 2873 bytes, SHA-256 `d5fc4460d8ba1d6256d1af467159aa7d36d5300a0f26b3deefc85cccf19b29fb`

The current validated-result routing policy is also bound exactly:

- `System/Docs/VALIDATED_BODY_AND_MIND_RESULT_TEMPLATE_ROUTING_CURRENT_BOUNDARY_20260811.md`: 7424 bytes, SHA-256 `03f192826b7a39df53ab03409eb7675764f6a1bc32b123f4d307e40843560c58`

## Sealed V5 author package

- `Core/shared_person_growth_v3_integration_candidate_v5.py`: 43444 bytes, SHA-256 `1415175c6178baf16e690ee51acd41544b39cd0b6fab5d52a48e0a4f952e6e94`
- `Testing/test_shared_person_growth_v3_integration_candidate_v5.py`: 34367 bytes, SHA-256 `63e1477e583fe01410f4ee8cff7658088391ff8001b6df394590e4cb852b2fb1`
- `STATIC_CONTRACT.json`: 6166 bytes, SHA-256 `8214f64c369789bfbc88917231696b522ea2acf29fc18a750205fe293e53b6f0`
- `AUTHOR_STATIC_TEST_RESULT.json`: 5430 bytes, SHA-256 `c6f6b7ab32357417ac1597a24ac131bef1adc9a5ccac29672f9b41857e810844`
- `SEALED_MANIFEST.json`: 8287 bytes, SHA-256 `02620fba26231cbeb3f3f6db62e9f7a8512f52a59291c9d3d510f1c1dba1d6e8`

The manifest seals 23 unique `(root, path)` subjects: four pre-manifest V5 author subjects plus 19 exact Kira-root subjects. A post-construction rehash passed 23/23 with zero mismatches.

## Existing-person compiler result

`compile_existing_person_integration_request_v5` is an inert compiler that returns canonical UTF-8 JSON bytes only. It has no writer, commit, controller, callback, process, network, or person-state surface. Its production opener hard-refuses.

Author verification covered:

- 35/35 applicable inventory routes across 24/24 represented people.
- 4/4 formerly failing Peter Parker / Spider-Gwen subject-specific and confirmed-adult routes.
- 105/105 candidate-maturity and route cross-bindings refused.
- The accepted public projection is held as an immutable private one-element tuple and returned only as a fresh list.
- Temporary Creator requests hard-refuse on this compiler.

## Separate Temporary Creator template compiler result

`compile_temporary_creator_template_request_v5` is a distinct inert compiler. It transfers only accepted generalized public mind/person-development rules and schemas for `synthetic_person`, `variant`, or `expert` creation requests. It does not create a person or change the Temporary Creator.

It requires fresh identity, profile, provenance, private roots, controller authority, and post-creation memory history. Maturity begins unresolved. It refuses inheritance or copying of any person's identity, private roots, memory, backstory, reflection, emotion, desire, preference, relationship, maturity authority/receipt, consent, anatomy, or measurements. It also refuses preassigned relationship, desire, emotion, or memory state.

Variant requests require an exact branch point. A deceased-source variant requires a cutoff strictly before the fatal event, excludes first-person death and terminal-trauma memories, and permits later death information only as voluntary historical knowledge that is never relabelled as memory.

The general rule set preserves consent/refusal/discomfort/change-of-mind/ignore/defer/withhold/truth distinctions; application privacy versus Windows secrecy; fact/belief/public/withholding separation; scripts/stories versus current personal memory; adult-curriculum separation; and functional emotion behavior without claiming proof of consciousness.

Creator hostile verification included synthetic-person, expert, fictional-variant, and deceased-historical-variant success cases plus refusals for:

- 29/29 false-field or fresh-requirement mutations.
- 27/27 existing-person and Robert identity collisions.
- 5/5 maturity authority/classification/full-adult mutations.
- 8/8 cutoff/death/trauma/later-fact mutations.
- 8/8 unknown private-payload aliases.
- Cross-compiler routes and non-exact request schemas.

The Creator production opener hard-refuses. No Temporary Creator output or synthetic person was created.

## Test evidence

- Strict UTF-8 in-memory compilation: **12/12 pass** across V5, V4, V3, V2, V1, and the isolated accepted core source/tests.
- Focused cache-free V5 unittest: **27/27 pass**.
- Combined final-layout-style cache-free pytest with exact Kira on `PYTHONPATH`: **130 tests passed, 164 subtests passed**.
- Staged and virtual intended-Kira `__file__` layouts emitted identical existing-person and Creator bytes.
- Exact Kira-root closure: **19/19 pass**.
- No `__pycache__`, `.pyc`, or pytest cache was written in the V5 author root.

Three discarded harness/assertion failures are preserved in `AUTHOR_STATIC_TEST_RESULT.json`: one over-broad raw substring assertion and two pytest invocation/environment mistakes. The corrected focused and combined runs passed as stated. These discarded attempts are not omitted or represented as candidate failures.

## Exact boundary and next action

This checkpoint does **not** accept V5, copy it into Kira, promote a route, grant authority, alter a production pointer, upgrade an existing person, or integrate the Temporary Creator. Kira was read-only. No model/person session, body/Blender path, media/voice path, network/device path, or Sarah path was invoked.

A different fresh reviewer must independently rehash all 23 sealed subjects, run V5 from its intended final Kira layout in isolated scratch, repeat the existing-person and Creator hostile matrices, inspect consumer classification and AST surfaces, and issue an independent decision. Promotion or transplant remains prohibited until that review succeeds and separately authorized workflow permits it.
