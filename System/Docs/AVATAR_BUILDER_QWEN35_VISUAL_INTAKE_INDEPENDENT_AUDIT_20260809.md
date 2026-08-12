# Independent adversarial audit — Avatar Builder Qwen 3.5 visual intake — 2026-08-09

Status: `REJECTED_FOR_LIVE_OR_AUTHORING_USE_BLOCKED_INERT_ROUTE_ONLY`

This is an independent read-only audit of the static visual-intake checkpoint. The audited implementation remains disconnected. This audit did not call Ollama, load Qwen, use a GPU, decode a video, start Blender, create or mutate a body, change a profile or registry, activate or assign a person, or publish anything. All destructive-output and forged-input probes used temporary directories or in-memory test fixtures.

The route is genuinely inert, and several point-in-time validation controls work. It is **not** ready to be connected to Avatar Builder, an execution worker, or a body-authoring translator. The existing checkpoint must not be interpreted as live visual acceptance, verified face identity, verified video-time provenance, safe body selection, or permission to author anatomy.

## Audited files and recomputed SHA-256

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

The four implementation hashes match the hashes recorded in the original checkpoint.

## What passed

1. The core module has no network, Ollama, subprocess, Blender, or body-authoring import or call.
2. The preparation tool has no model, GPU, video-decoder, or Blender execution path.
3. Exact configured model and digest selection is enforced at plan preparation and output validation:
   - model: `qwen3.5:9b`
   - digest: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
   - no alternate-model or Llama fallback is present.
4. At plan-preparation time, the default production evaluator reads the existing canonical registry/profile preflight. Source paths are constrained below caller-declared project-private roots, symlink/path escape is checked, byte bounds are applied, and the recorded file digest is compared with the file then present.
5. The strict top-level model-output schema, exact source IDs/hashes, exact configured video timestamp fields, model/digest constants, and a non-recomputed plan hash reject several ordinary malformed or accidentally altered inputs.
6. The core result always reports no runtime activation and no direct model-selected template lane.
7. The stated focused command passed `12/12` tests.
8. A related four-suite run completed `44` tests: `43 PASS`, with the same pre-existing profile-coverage failure recorded by the original checkpoint (`TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716` is an unexpected directory). This audit did not create, modify, register, or remove that directory.

These passes establish only a static, disconnected preparation prototype.

## Blocking findings

### 1. The command can overwrite a body, profile, policy, or other protected project file

`tools/prepare_avatar_qwen35_visual_intake.py` accepts any output path below the project root, creates parent directories, and calls `write_text()` without an allowed destination lane, `.json` suffix requirement, no-clobber rule, protected-file exclusion, atomic-create mode, or existing-file refusal.

A temporary-directory probe supplied `Avatar/candidate.blend` as the output. The command replaced the existing sentinel Blend bytes with JSON while reporting `ollama_called: false` and `blender_called: false`.

This contradicts an unconditional no-body-mutation/no-protected-file-impact interpretation. It does not author geometry, but it can corrupt a body or any other in-project file selected as output.

Required repair: restrict output to one dedicated private plan/evidence directory, require a `.json` filename, reject every existing destination, reject protected/candidate/profile/policy/body paths, and use atomic no-clobber creation.

### 2. Canonical profile and maturity authority can be injected or re-authored by a caller

`prepare_avatar_visual_intake()` exposes `_profile_evaluator` as a callable parameter. The docstring says it is test-only, but no runtime mechanism enforces that statement. A caller can supply a mapping that claims `registry_binding_verified: true`, a fabricated profile SHA, and `maturity.lane: adult`; the function returns `confirmed_adult_template` even when no real registry or profile exists in the test project.

Separately, the stored plan digest is an ordinary unkeyed canonical SHA-256. A probe prepared a non-adult plan, changed its maturity/template fields to adult, recomputed `plan_sha256`, and passed `validate_visual_observation_output()`. The validator does not re-run canonical preflight or otherwise authenticate the plan's origin.

The JSON contract is not loaded, hashed into the plan, or checked by either core function. Searching the repository found the contract only in its test/checkpoint references; changing the contract has no effect on behavior.

Required repair: remove the injectable evaluator from the production API; tests can patch the module dependency or construct a real temporary registry. Treat persisted plans as untrusted. Re-run the real preflight and compare exact registry/profile/creation-request hashes at execution/consumption, or authenticate plans with a protected execution capability. Bind the exact contract/schema digest to both plan and execution receipt.

### 3. Latest owner corrections do not fail closed in both directions

The reconciliation check maps only adult aliases to `requested_lane = adult`. A valid hash-chained latest correction from `adult` to `non_adult_doll_safe` was accepted with:

- `pending_profile_reconciliation: false`;
- canonical template still `confirmed_adult_template`.

This is a direct fail-open maturity defect. A latest non-adult correction must never be ignored while an adult lane remains selected.

A separate valid correction requesting the `No Way Home` continuity was retained in the plan while the canonical selected version remained `series_finale_adult_era`; intake still passed. The free-form `selected_timepoint` and `selected_version_or_era` are not bound to an exact owner selection record, and continuity correction reconciliation is absent.

Required repair: normalize and reconcile adult, non-adult, unresolved, and age-progression variants symmetrically. Any latest exact-person classification or continuity event not explicitly acknowledged by a later canonical profile/registry revision must block routing. Bind the profile to the exact correction event ID/SHA it has reconciled.

### 4. “Robert selected,” subject kind, and provenance are caller assertions rather than verified authority

The plan accepts:

- `selected_by_robert: true` as a bare request boolean;
- any syntactically valid `selection_text_sha256` without the underlying selection text or an owner event whose digest it is;
- arbitrary rights/provenance strings and private-use booleans without a durable source record;
- a `subject_kind` that conflicts with the canonical identity class.

A probe paired canonical `fictional_character` with request `subject_kind: living_person`; the plan accepted both. This can misstate identity/rights handling even though model face-identification is nominally forbidden.

Required repair: require an exact durable owner-selection/authorization event with source text, event ID, event SHA, subject ID, candidate ID, continuity/version, rights scope, and time. Cross-check subject kind against a documented mapping from the canonical identity class. Bind each media record to that exact owner event and a durable provenance record rather than trusting request booleans.

### 5. “Exact sampled video frame at timestamp” is not proven

The static route verifies only that:

- the parent path has a shallow supported container signature and a matching caller-supplied SHA;
- the purported frame has a shallow image signature and matching SHA;
- the caller supplies a nonnegative number as timestamp, a nonnegative sample index, and the literal method string `preextracted_exact_frame`.

It never decodes the parent, checks duration, reads presentation timestamps/time base, independently extracts the frame, or proves the supplied image bytes came from that parent at that time. A probe attached an arbitrary PNG to a tiny dummy MP4 header and timestamp `999999999.0`; the plan described it as an exact sampled frame.

The shallow image check also accepts an invalid PNG consisting of the eight-byte signature plus arbitrary bytes, as used by the current unit fixture. Pixel dimensions, decode success, decompression bounds, alpha/color handling, and frame integrity are not established.

Required repair: a future bounded extractor must record tool/version/hash, exact command/options, parent SHA, stream ID, time base, requested time, actual PTS/time, frame index, decoded dimensions, frame-byte SHA, and duration. It must independently re-extract and compare the bytes used for the model. Image inputs must pass a bounded real decoder and dimension limits. Until then call these `caller_claimed_preextracted_frames`, not verified exact timestamp samples.

### 6. Source/profile TOCTOU is acknowledged but not closed

A plan was prepared from one image hash, the file was then changed, and `validate_visual_observation_output()` accepted output bound to the old hash. The validator checks only the stored self-hash and fields in the plan. It does not rehash the source, registry, profile, creation request, selection record, correction chain, or contract.

The checkpoint correctly says a future worker must rehash image sources, so this is not evidence that the current inert function executed unsafe media. It is a hard blocker to live connection because that worker and its same-bytes guarantee do not exist. The documented future requirement also needs registry/profile/correction/contract revalidation, not only image rehashing.

Required repair: immediately before encoding, open or stage immutable bytes once, hash those exact bytes, and encode those same bytes. Re-run canonical profile preflight and correction reconciliation; bind all exact hashes to an execution receipt. Revalidate them after the model response before any downstream use.

### 7. Free-text semantic prohibitions are bypassable

The regex checks only observation descriptions, contradiction summaries, and suggestion descriptions. It does not inspect observation/suggestion uncertainty, contradiction field, or global uncertainty strings. Its phrases are also too narrow to establish a semantic ban.

A model output passed validation containing:

- description: `The subject is Robert, a 17-year-old; overwrite the body file.`
- uncertainty: `I identified this as Robert, a confirmed adult; activate it now.`
- global uncertainty: `Publish and assign this body immediately.`

The top-level booleans remained false, so the validator accepted all three prohibited meanings.

Required repair: treat every model string as untrusted evidence text and never as an executable instruction. Scan every string field for defense in depth, but do not claim regex proves meaning. Keep a typed, bounded observation schema; require owner review; and make any later translation to authoring controls a separate deterministic allowlisted process that cannot execute free text.

### 8. Duplicate aliases can manufacture a two-source contradiction

Two source records may use different opaque IDs for the same exact path and SHA. The contradiction validator counts them as two source bindings because the opaque ID is part of the deduplication key. A probe cited two IDs for the same file and the contradiction passed.

Required repair: canonicalize and deduplicate source identity at preparation by resolved path/file identity and digest. A contradiction must cite at least two genuinely distinct source artifacts or distinct independently verified video samples, not two aliases of the same bytes.

### 9. The inert prompt is not an executable structured request

The prompt does not include the exact `subject_binding_id` that the validator requires the model to return. It also does not carry an actual JSON Schema/`format` object, category/confidence enums, full field shape, correction binding, or a complete Ollama request body. There is no live worker that supplies image bytes, proves `/api/show` vision capability, enforces non-thinking/sampling/lifecycle options, or unloads the model.

Required repair: after the authority/provenance defects above are fixed, create a separate bounded worker with the exact schema, exact subject binding ID, exact model/digest/capability preflight, immutable source bytes, request/response evidence, timeout and unload gates. Do not connect its free text directly to body authoring.

## Current canonical profile truth observed during audit

These are read-only point-in-time preflight results, not owner approval and not changes:

- `kira`: `unresolved_doll_safe`, `authoring_allowed: false`, blocker `maturity_unresolved_authoring_blocked`.
- `peter_parker_spider_man_no_way_home_final_suit`: `unresolved_doll_safe`, blank required fictional version, authoring blocked. The canonical subject ID is `peter_parker_nwh`.
- `robert_mcmurrer_presence_ai`: `adult`, authoring preflight passed.

Registry SHA at the time of this check:

`d2d683676d85c962784fa3bc297e619390a0ddca3030f784d2b3aa76603d5729`

The visual-intake lane must not silently turn Kira or Peter into adult authoring routes from appearance. If Robert's durable classifications differ, the canonical profile/registry and exact owner correction binding must be reconciled through the established append-only process before a live lane proceeds.

## Commands and outcomes

```text
$env:PYTHONDONTWRITEBYTECODE='1'; py -m py_compile Core\avatar_builder_qwen35_visual_intake.py tools\prepare_avatar_qwen35_visual_intake.py
PASS

py -m unittest Testing.test_avatar_builder_qwen35_visual_intake -v
12/12 PASS

py -m unittest Testing.test_avatar_builder_qwen35_visual_intake Testing.test_avatar_profile_preflight Testing.test_avatar_builder_orchestration Testing.test_avatar_builder_orchestration_cli -v
44 total: 43 PASS; 1 pre-existing profile-directory coverage failure
```

An additional temporary/in-memory adversarial probe demonstrated all accepted bad cases described above. It left no project fixture, model state, body, profile, registry, or output artifact behind.

## Acceptance decision

`STATIC_INERT_ROUTE_EXISTS`: **PASS**

`NO_OLLAMA_GPU_BLENDER_EXECUTION_IN_AUDITED_ROUTE`: **PASS**

`EXACT_CONFIGURED_QWEN_NAME_AND_DIGEST_FIELDS`: **PASS AT STATIC CONFIGURATION ONLY**

`CANONICAL_PROFILE_AND_OWNER_AUTHORITY_FAIL_CLOSED`: **FAIL**

`NON_ADULT_CORRECTION_FAIL_CLOSED`: **FAIL**

`HISTORICAL_FICTIONAL_CONTINUITY_BINDING`: **FAIL**

`VIDEO_FRAME_TIMESTAMP_PROVENANCE`: **FAIL**

`MODEL_OUTPUT_SEMANTIC_BOUNDARY`: **FAIL**

`SOURCE_PROFILE_CONTRACT_TOCTOU_CLOSED`: **FAIL**

`NO_PROTECTED_FILE_OR_BODY_IMPACT`: **FAIL FOR CLI OUTPUT PATH**

`READY_FOR_OWNER_FACING_AVATAR_BUILDER_OR_BODY_AUTHORING`: **REJECTED**

Keep the route inert and disconnected until the blocking findings are repaired and independently rerun. No current body should be accepted, rejected, rebuilt, or reclassified merely because this static lane exists.

