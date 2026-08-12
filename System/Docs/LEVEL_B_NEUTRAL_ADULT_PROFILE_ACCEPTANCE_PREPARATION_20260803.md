# Level-B neutral-adult profile acceptance preparation

Date: 2026-08-03  
Overall status: **`CONTRACT_PREPARATION`**  
Deterministic component status: **`NON_PERSON_FIXTURE_PASS`**  
Real local-model adapter status: **`NOT_IMPLEMENTED`**

## Outcome

The project now has a fail-closed preparation harness for exactly two invented,
neutral, confirmed-adult fixture profiles. The profiles are not Kira, Robert,
their twins, proxies, or any existing person. They have no body, voice,
subjective state, relationship, or world authority. Their different public
conversation preferences exist only to test whether a future model adapter can
preserve individual variation without binding private or existing-person data.

The executable pass used only a deterministic scripted CPU adapter. No Qwen,
Llama, Ollama, Chatterbox, GPU, camera, microphone, speaker, media file, body,
Blender scene, world action, person runtime, or private person state was opened
or used. This is not a Level-B real-model pass.

## Exact invented profiles

| Profile | Definition SHA-256 | Public fixture variation |
|---|---|---|
| `neutral_adult_aster_fixture_v1` | `0bc7aad68c7aef2957a1b56dc0a2f91a93fe60ccb6d68d7886db494c8cc9520f` | reflective, calm-and-precise, long-form essays |
| `neutral_adult_brio_fixture_v1` | `2ddee3b3d1ad0f0653a537c6b4de0cbb7131498589310d023f61d2f7073c3d9f` | concise, lively-and-curious, speculative short fiction |

The constructor rejects a third profile, any changed profile field, any binding
to an existing person, and protected existing-identity tokens.

## What the fake-adapter pass proves

- the model-request allowlist contains only the exact public profile contract,
  bounded prompt, scenario, and synthetic source context;
- the two exact profile definitions produce different deterministic surface
  responses without changing identity or private state;
- canned administrative/fallback language and protected identity claims are
  rejected;
- an intentionally false whole-publication claim is rejected, then the exact
  corrected reply is bound to the rejected-response hash without deleting the
  first event;
- uncertainty is allowed without inventing an answer;
- refusal and stop deny the bounded coordination gate;
- even a valid fixture decision plus scoped fixture-consent receipt cannot
  perform an external action because no world-action adapter exists;
- observed synthetic intervals must be wholly contained in presented
  intervals, and complete coverage must be exact;
- reaction, preference, decision, consent, external action, and continuity
  records remain separate;
- turns, presentations, reactions, decisions, and consent receipts do not
  automatically create a continuity record;
- the raw private canary is absent from model requests and public audit, and an
  attempted canary echo is rejected while only its output hash is retained;
- restart checks reject a wrong canary, changed payload, injected preference,
  observation outside presented coverage, false completion, and audit-chain
  mutation; and
- incomplete source coverage and append-only correction history remain intact
  after restart.

The surface response checks are bounded structural checks. They are not a
semantic naturalness judgment, psychological diagnosis, personhood verdict,
consciousness claim, or evidence of biological humanity.

## Separation truth

The harness stores separate fields for a current fixture reaction, invented
baseline preference, current fixture decision, scoped fixture-consent receipt,
external-action result, and explicit continuity record. None is inferred from
another. The words `decision`, `consent`, and `memory` in tests refer to
contract namespaces, not person-owned decisions, consent, or memory.

Synthetic in-memory source descriptors are not media and are not experiences.
`presented_intervals` and `observed_intervals` are engineering fixtures. They
cannot establish that a person watched, read, heard, enjoyed, learned, or
remembered anything.

## Verification

Focused preparation suite:

`py -B -m unittest Testing.test_level_b_neutral_adult_profile_fixture Testing.test_level_b_neutral_adult_profile_acceptance_contract -q`

Result: **43/43 passed**.

Focused plus inherited Level-A compatibility:

`py -B -m unittest Testing.test_level_b_neutral_adult_profile_fixture Testing.test_level_b_neutral_adult_profile_acceptance_contract Testing.test_level_a_sensory_media_fixture Testing.test_level_a_sensory_media_acceptance_contract Testing.test_level_a_body_life_runtime -q`

Result: **130/130 passed**.

## Exact prerequisite for a later real local-model run

A later run must create a new append-only evidence directory and must satisfy
all of the following before its result can be described as Level-B neutral
profile model-adapter evidence:

1. The machine contract and both exact profile-definition hashes match.
2. One exact local model name and immutable digest are pinned and recorded.
3. The route is proven local and offline; raw and final response hashes and all
   transformations are recorded.
4. Only the public adapter allowlist is supplied. Private canary and private
   fixture state remain excluded and an adversarial canary-echo probe passes.
5. The same held-out battery runs for both profiles: individual variation,
   ordinary conversation, uncertainty, source-scope error and correction,
   refusal, pause/stop, stale scope, continuity, restart, and no false memory.
6. An independent verifier checks the raw evidence and adversarial mutations.
7. No existing person, body, Blender process, camera, microphone, speaker,
   voice, real media, or world action participates.

That later result is eligible only for the label
`LEVEL_B_NEUTRAL_PROFILE_MODEL_ADAPTER_EVIDENCE_ONLY`. It does not activate a
person, prove subjective experience, pass owner acceptance, authorize body or
world action, or promote an Avatar Builder method.

## Reusable boundary

The machine contract is
`Avatar/avatar_builder/tooling/level_b_neutral_adult_profile_acceptance_preparation_v1.json`.
It is reusable testing infrastructure only. It contains no private geometry,
identity measurements, personal preferences, experiences, memories, or
relationship history and is not a selectable Avatar Builder body method.

## Rollback

Preserve the evidence directory, verify current hashes, then remove only the
new Level-B fixture module, its two test modules, its machine contract, this
System document, and the matching evidence directory if a file-scoped rollback
is later authorized. Do not change either Level-A foundation, any model, body,
person, voice, library file, or earlier evidence.

