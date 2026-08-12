# Avatar Builder Qwen 3.5 visual-intake static checkpoint — 2026-08-09

Status: `STATIC_INERT_ROUTE_IMPLEMENTED_NOT_LIVE_ACCEPTED`

This checkpoint adds a bounded way for Avatar Builder to prepare pictures and exact sampled video frames for the approved local Qwen 3.5 model. It stops at structured private reconstruction observations and suggestions. No Ollama request, GPU workload, video decode, Blender process, mesh change, body build, activation, assignment, publication, or owner approval occurred in this task.

## Capability basis

The official [Qwen/Qwen3.5-9B model card](https://huggingface.co/Qwen/Qwen3.5-9B) identifies the model as image-text-to-text and describes multimodal/image and video capability. Ollama's official [Vision documentation](https://docs.ollama.com/capabilities/vision) says vision models accept images with text and that its REST API receives base64-encoded image data in an `images` array. Ollama also documents [structured outputs for vision](https://docs.ollama.com/capabilities/structured-outputs), the digest returned by [`/api/tags`](https://docs.ollama.com/api/tags), and advertised capabilities returned by [`/api/show`](https://docs.ollama.com/api-reference/show-model-details).

These sources justify a future local-image route; they do not prove that this exact installed local artifact passed a new live Avatar Builder run. A later authorized worker must recheck both:

- model name: `qwen3.5:9b`;
- exact digest: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`;
- `/api/show` advertises `vision` for that exact installed artifact;
- every source still matches its recorded SHA-256 immediately before encoding.

There is no alternate model and no Llama fallback in this route.

## Implemented boundary

The new core route verifies all of the following before producing an inert plan:

- the canonical candidate and exact subject through the existing read-only avatar profile preflight;
- Robert's selected subject binding, while explicitly treating that binding as selection rather than model-performed face identification;
- fictional or historical continuity and timepoint, including equality with a required canonical selected version;
- maturity from the canonical profile only;
- an adult canonical lane routes to `confirmed_adult_template`;
- a non-adult or maturity-uncertain canonical lane routes to `non_adult_doll_safe_template`;
- an unresolved profile remains authoring-blocked even though observation intake may be prepared safely;
- the model is forbidden to infer adult/non-adult status, anatomy eligibility, or identity from appearance;
- every source stays below an explicit project-private allowlisted root under `Avatar`, `TemporaryAI`, or `RecoverySprint`;
- every image has an allowed extension, matching file signature, byte bound, exact project-relative path, exact SHA-256, source/rights/provenance, and owner-authorized private-use record;
- sampled video is represented only by a pre-extracted image plus exact parent-video SHA-256, frame SHA-256, sample index, and timestamp in seconds;
- no sampled-frame result may claim complete video viewing or knowledge of unsampled intervals;
- existing Avatar Builder correction memory remains hash-chained and append-only;
- a new exact-person maturity correction that conflicts with the canonical profile blocks intake until the canonical profile/registry authority is reconciled; visual appearance cannot resolve that conflict.

The inert plan contains no image bytes. A separate future worker would rehash and encode verified stills, but this checkpoint does not implement or authorize that worker.

## Structured observation contract

A future model reply must be strict JSON and pass local validation. The validator requires:

- coverage exactly `BOUND_STILLS_AND_EXACT_VIDEO_SAMPLE_FRAMES_ONLY`;
- identity status exactly `USER_SELECTED_SUBJECT_BINDING_ONLY_NOT_MODEL_IDENTIFIED`;
- `maturity_inference: false`;
- `mutation_requested: false`;
- per-observation category, description, confidence, uncertainty, and exact source bindings;
- sampled-frame bindings include the exact parent-video hash and timestamp;
- contradictions cite at least two distinct exact source bindings;
- suggestions are limited to `morph`, `material`, and `hair` groups and cite validated observation IDs;
- no face-identity assertion, maturity inference, direct mesh/body mutation, activation, assignment, upload, or publication language;
- the intact source-plan SHA-256 and exact Qwen model identity.

The validator adds the profile-authoritative template lane after validation. The model never chooses that lane. Suggestions are not geometry, measurements, likeness approval, or instructions to Blender.

## Natural-language corrections

`record_exact_person_owner_correction()` delegates to the existing Avatar Builder correction parser and append-only hash chain. It can record Robert's exact-person continuity or classification correction without editing a body. The Avatar Builder chat remains responsible for persisting the returned correction-memory object durably. The latest correction does not become body approval, and a classification correction does not by itself mutate a canonical profile or body.

## Files and hashes

- `Core/avatar_builder_qwen35_visual_intake.py`
  - SHA-256 `149ae4c5018c12ddde340cf8caf17247cca29cf5ca58bc2def54e02a7dfa5b6a`
- `Avatar/avatar_builder/policies/qwen35_visual_intake_contract_v1.json`
  - SHA-256 `e4e4a316f146a649cb951cc2614df437fefbd79663b0db087b64aebfad8a45f4`
- `tools/prepare_avatar_qwen35_visual_intake.py`
  - SHA-256 `e1fc6ada595e746adb70ead20cca8eaac360b99f9e27620835a9a1545f4fc2e2`
- `Testing/test_avatar_builder_qwen35_visual_intake.py`
  - SHA-256 `6693bdf2c8e3baca8e455d3d1317dfe882f01cd1158967f9035e8d720f84cc74`

## Verification

Commands run:

```text
py -m py_compile Core\avatar_builder_qwen35_visual_intake.py tools\prepare_avatar_qwen35_visual_intake.py
py -m unittest Testing.test_avatar_builder_qwen35_visual_intake -v
```

Result: `12/12 PASS`.

The focused hostile tests cover exact model/digest enforcement, adult/non-adult/uncertain routing, allowlist and hash failures, fictional-version conflict, sampled-video temporal truth, identity and maturity claims, unbound sources, direct mutation language, plan tampering, append-only Robert corrections, pending classification reconciliation, and the absence of Ollama/Blender execution imports in the preparation harness.

A related five-suite regression command ran 52 tests. `51 PASS`; one pre-existing repository-state failure remained in `Testing.test_avatar_profile_preflight.AvatarProfilePreflightTests.test_current_batch_covers_all_22_real_profiles` because the test reported unexpected directory `TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716`. This visual-intake task did not create, edit, register, or remove that directory.

## Honest remaining work

The route is not connected to the owner-facing Avatar Builder chat and has not been live-run. Later work requires separate authorization and evidence for:

1. an exact-digest `/api/tags` and `/api/show` preflight;
2. one bounded live still request with captured request/response and unload evidence;
3. one exact sampled-frame set with source/time truth and no complete-viewing claim;
4. owner review of the usefulness and accuracy of the structured observations;
5. a separate, reviewed translation from accepted suggestions to authoring controls;
6. independent body/rig/render gates before anything can become a private candidate;
7. separate owner approval and runtime activation gates.

## Rollback

The route is disconnected and inert, so the safest rollback is to leave it unused. If source rollback is required, revert only the four files listed above. No model, profile, correction-memory file, body, R25 artifact, Blender file, runtime setting, or active person state needs restoration because none was changed here.

