# Avatar Builder Qwen 3.5 visual intake v2 repair checkpoint — 2026-08-09

Status: `STATIC_V2_REPAIR_IMPLEMENTED_DISCONNECTED_PENDING_FRESH_INDEPENDENT_AUDIT`

This is an append-only repair successor to the independently rejected v1
prototype. It remains a static evidence-preparation and response-validation
lane. It did not call Ollama, load Qwen, use a GPU, run a video decoder, launch
Blender, create or alter geometry, touch an R25 body, activate or assign a
person, or publish anything.

V1 and its independent audit remain evidence and were not edited. The v2 route
must not be connected to Avatar Builder authoring or described as accepted
until a fresh independent audit passes and a later, separately authorized live
worker is implemented and accepted.

## Exact preserved v1 evidence

- `Core/avatar_builder_qwen35_visual_intake.py`
  - `149ae4c5018c12ddde340cf8caf17247cca29cf5ca58bc2def54e02a7dfa5b6a`
- `Avatar/avatar_builder/policies/qwen35_visual_intake_contract_v1.json`
  - `e4e4a316f146a649cb951cc2614df437fefbd79663b0db087b64aebfad8a45f4`
- `tools/prepare_avatar_qwen35_visual_intake.py`
  - `e1fc6ada595e746adb70ead20cca8eaac360b99f9e27620835a9a1545f4fc2e2`
- `Testing/test_avatar_builder_qwen35_visual_intake.py`
  - `6693bdf2c8e3baca8e455d3d1317dfe882f01cd1158967f9035e8d720f84cc74`
- `System/Docs/AVATAR_BUILDER_QWEN35_VISUAL_INTAKE_STATIC_CHECKPOINT_20260809.md`
  - `fcfd26c37605c2ca5a0c800803f4d23916612aed8eabbd531bdf73d7e440b1ff`
- `System/Docs/AVATAR_BUILDER_QWEN35_VISUAL_INTAKE_INDEPENDENT_AUDIT_20260809.md`
  - `41f925851f1b8516389f9c26fccae1e5f24d98ee1ac5bb8966947c081123f75a`

## V2 implementation and exact hashes

- `Core/avatar_builder_qwen35_visual_intake_v2.py`
  - `2faa914d2aae3165fbb5f20850d94b320200f04cc30cf9d8cd79014d371fe28b`
- `Avatar/avatar_builder/policies/qwen35_visual_intake_contract_v2.json`
  - `2dbc4e280b70efe6772ae7c25243f252cc73caa6f8b0dd8dc72e5cbd2d2d1bc0`
- `Avatar/avatar_builder/policies/qwen35_visual_intake_owner_authority_registry_v1.json`
  - `e69c845427103c8166811ee5da0b3082ce9b5d8a406b87b51c74625b5180e0ac`
- `tools/prepare_avatar_qwen35_visual_intake_v2.py`
  - `b994501c11dae0519b8dde5d5b5069dd35319c6b538ea0b780f2eef38878b1d2`
- `Testing/test_avatar_builder_qwen35_visual_intake_v2.py`
  - `630bca0330a3704f3213e92635cd00e3b4cad0c5fcaf7a30b7dabb44485c8c2a`

## Repair mapping to the nine independent-audit blockers

### 1. Protected output and no-clobber

The v2 command accepts a project-relative request document and a safe logical
output name only. Plans can be created only below:

`RecoverySprint/avatar_builder_qwen35_visual_intake_v2/plans`

Validated observations can be created only below:

`RecoverySprint/avatar_builder_qwen35_visual_intake_v2/validated_observations`

Both are JSON-only, project-confined, symlink-checked, and created with
exclusive `O_CREAT | O_EXCL`. Existing files are refused. There is no caller
output path, so a profile, policy, body, or `.blend` cannot be selected as a
destination. A sentinel `.blend` adversarial test proves its bytes remain
unchanged.

### 2. Canonical authority cannot be publicly injected

`prepare_avatar_visual_intake_v2(project_root, request)` has no evaluator or
authority callback parameter. The exact real preflight dependency is called
inside the module. Tests patch that internal dependency; callers cannot name it
in the strict six-field request schema.

The contract is loaded from a fixed path and exact digest. Owner authority is
loaded only through a fixed, contract-bound registry and an exact registered
artifact digest. Persisted plans are treated as untrusted: consumption rebuilds
the plan from current external authority and rejects even a caller-tampered
plan whose ordinary SHA-256 was recomputed.

### 3. Symmetric maturity and continuity reconciliation

Adult, confirmed-adult, non-adult, child/minor/teen, unresolved, uncertain, and
`adult_aged_up_variant` labels are normalized. Age-up presentation remains
unresolved/doll-safe at this gate. Adult-to-non-adult,
adult-to-unresolved/age-up, and non-adult-to-adult conflicts all fail closed.

The latest exact-person correction chain is reverified. Latest maturity and
continuity event IDs and hashes must agree in three places:

1. the append-only correction memory;
2. the registered owner-authority artifact; and
3. the exact canonical profile bytes under
   `qwen35_visual_intake_reconciliation`.

The selected fictional/historical version and timepoint must also agree with
the current canonical profile and the latest reconciled continuity directive.
The exact canonical profile bytes also bind the selected-subject event ID/SHA,
subject ID/kind, version, and timepoint under
`qwen35_visual_intake_subject_binding`. Authority prose alone cannot claim
that the profile selected a subject/timepoint or reconciled a correction.

### 4. Durable subject, rights, and provenance authority

The request supplies IDs only. The registered authority artifact supplies the
content-hashed Robert selection event, exact candidate/subject, underlying
selection text and its hash, selected version/era and timepoint, private-only
rights scope, and media authorization IDs. Subject kind is derived from and
cross-checked against the canonical profile identity class. A model never
establishes face identity.

Every media item carries a content-hashed durable provenance record and binds
to the exact selected-subject event SHA. Bare booleans and caller-authored
rights/provenance strings are rejected by the request schema.

The production owner-authority registry intentionally contains zero active
entries and reports `NO_OWNER_AUTHORITY_ARTIFACTS_REGISTERED_FAIL_CLOSED`.
Therefore no real profile or media can use v2 yet. Registration remains a
separate owner-authority workflow and was not fabricated in this repair.

### 5. Bounded images and verified sampled video frames

Images must pass a real bounded Pillow decode, format/suffix agreement, 24 MiB
byte limit, 8192-by-8192 dimension limits, and 40-million-pixel limit. A PNG
signature plus junk is rejected.

A video sample is accepted only as a decoded image plus a registered,
exact-hashed extractor receipt recording extractor name/version/binary hash,
exact options, parent path/hash and container, stream ID, time base, requested
time, actual PTS/time, frame index, duration, dimensions, pixel format, frame
hash, and an independently re-extracted byte match. Times outside duration,
PTS/time-base conflicts, and re-extract mismatch fail. The module itself does
not decode video and never claims unsampled intervals or full-video viewing.

### 6. Source/profile/contract/correction drift

Preparation hashes external state. Before response consumption it reloads the
exact contract and owner registry/artifact, reruns canonical profile preflight,
rehashes the registry/profile/creation request/correction chain/media/receipts,
and deterministically rebuilds the plan. It then opens each exact image once,
checks stat-before/stat-after plus hash and real decode, and returns those exact
in-memory bytes as the only bytes a future encoder may use. After response
validation, it revalidates the external state again. Any drift invalidates the
prepared plan; no persistent source copy is created.

### 7. Model free text is non-executable

Every free-text field in the typed response—observation description and
uncertainty, contradiction field and summary, morph/material/hair suggestion
description and uncertainty, and global uncertainties—is bounded and receives
a defense-in-depth semantic scan for identity, maturity, authoring, activation,
publication, filesystem, tool, and instruction-override meanings. The contract
explicitly says regex is not semantic proof. All text remains untrusted,
non-executable evidence. No model-to-authoring translator exists here.

### 8. Genuine physical-source contradictions

Image physical identity is based on the exact bytes SHA, not a caller alias or
path. Byte-identical copies and aliases are rejected during preparation. Video
sample identity binds parent SHA, stream, PTS, frame index, and frame SHA. A
contradiction must cite at least two distinct physical source identities.

### 9. Complete inert structured descriptor

The inert Ollama descriptor contains the exact subject binding ID, exact
Qwen model, required digest preflight, required `vision` capability, no
alternate model/digest, full JSON Schema in `format`, temperature zero,
non-streaming/non-thinking settings, `keep_alive: 0`, per-source hashes, and
exact video sample metadata. It also records that timeout, exact unload/VRAM
release, and post-response revalidation are future worker requirements and are
not implemented or executed here.

## Official capability basis, and what it does not prove

- The official [Qwen/Qwen3.5-9B model card](https://huggingface.co/Qwen/Qwen3.5-9B)
  classifies the model as image-text-to-text and gives image-plus-text examples.
- Ollama's official [Qwen 3.5 library page](https://ollama.com/library/qwen3.5)
  lists the 9B tag as Text + Image.
- Ollama's official [Vision documentation](https://docs.ollama.com/capabilities/vision)
  says REST image input is supplied in the message `images` array as base64.
- Ollama's official [Structured Outputs documentation](https://docs.ollama.com/capabilities/structured-outputs)
  documents a JSON Schema in `format`, including vision output, and recommends
  temperature zero for more deterministic output.
- Ollama's official [Show model details documentation](https://docs.ollama.com/api-reference/show-model-details)
  documents the capability list, and its [List models documentation](https://docs.ollama.com/api/tags)
  documents exact model digests.

These sources establish a supported design basis only. They do not prove that
the local exact digest passed a visual request, that any output is accurate, or
that this lane is safe to connect. No such run occurred in this checkpoint.

## Verification

Focused command:

```text
py -m unittest Testing.test_avatar_builder_qwen35_visual_intake_v2 -v
```

Final result: `24 total; 23 PASS; 1 environment-dependent SKIP`, including the
bounded age-up classification subcase. The skip is the live file-symlink
fixture because this Windows account cannot create a symlink; traversal and
ordinary escape tests passed, and both the CLI and core contain explicit
pre-resolution symlink rejection. A fresh auditor should rerun a real symlink
probe where the audit account has that capability.

Related command:

```text
$env:PYTHONDONTWRITEBYTECODE='1'; py -m unittest \
  Testing.test_avatar_builder_qwen35_visual_intake \
  Testing.test_avatar_builder_qwen35_visual_intake_v2 \
  Testing.test_avatar_profile_preflight \
  Testing.test_avatar_builder_orchestration \
  Testing.test_avatar_builder_orchestration_cli -v
```

Result at this checkpoint: `68 total; 66 PASS; 1 pre-existing unrelated
coverage failure; 1 environment-dependent symlink SKIP`. The unchanged failure is
`test_current_batch_covers_all_22_real_profiles`, caused by the already-known
unexpected directory
`TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716`.
This task did not create, edit, register, or remove that directory.

Static compile and CLI-help checks passed. A source scan found no network,
Ollama client, subprocess, Blender, or `bpy` execution import/call; the words
appear only in boundary documentation and semantic-ban patterns.

## Acceptance boundary

- `V1_PRESERVED`: PASS
- `STATIC_V2_AUDIT_REPAIR_EXISTS`: PASS
- `NO_MODEL_GPU_VIDEO_DECODER_OR_BLENDER_EXECUTION`: PASS
- `NO_BODY_R25_OR_PROFILE_MUTATION_BY_THIS_TASK`: PASS
- `PRODUCTION_OWNER_AUTHORITY_REGISTERED`: NO — FAIL CLOSED
- `LIVE_QWEN_VISION_ACCEPTANCE`: NOT RUN
- `MODEL_OUTPUT_ACCURACY_ACCEPTANCE`: NOT RUN
- `CONNECTED_TO_AVATAR_BUILDER_AUTHORING`: NO
- `READY_FOR_LIVE_OR_BODY_AUTHORING_USE`: PENDING FRESH INDEPENDENT AUDIT AND LATER LIVE-WORKER AUTHORIZATION

Rollback is additive: leave v1 and its audit unchanged; remove or disconnect
only the five v2 implementation artifacts listed above and the two v2
documents if v2 is rejected. There is no live route or body state to roll back.
