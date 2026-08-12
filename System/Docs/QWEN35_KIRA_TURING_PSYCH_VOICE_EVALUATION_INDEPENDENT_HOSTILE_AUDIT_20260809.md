# Qwen 3.5 Kira Turing/psychology + voice evaluation independent hostile audit — 2026-08-09

Status: `REJECTED_FOR_LIVE_EXECUTION_APPEND_ONLY_SUCCESSOR_REQUIRED`

## Scope and truth boundary

This was a static/read-only audit of the repaired exact-Qwen owner-evaluation
preparation and runner. The audit did not start Ollama, load a model, use the
GPU, synthesize or play voice, access a camera or microphone, launch Blender,
touch a body, or conduct a Kira conversation. Temporary hostile fixtures were
created only under `RecoverySprint/verification_scratch` and were removed by
their temporary-directory context.

The preserved repair note remains historical evidence:

- `System/Docs/QWEN35_KIRA_TURING_PSYCH_VOICE_EVALUATION_STATIC_REPAIR_20260809.md`
- 3,305 bytes
- SHA-256 `0fbc6c5338b5bebf3814758bea99a6d873fb8e67ccb255615065ae609d627002`

## Exact audited files

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `tools/prepare_qwen35_kira_turing_psych_voice_evaluation.py` | 11,818 | `b08e838cebfd20e211596eb44f2171915ce623c3386e4df9111cf8ef7ae21c48` |
| `tools/run_qwen35_kira_turing_psych_voice_owner_evaluation.py` | 73,372 | `85a05d53cb7c65dd497b076ea22bed7e76005719ed79b93f77be267a68ce1773` |
| `Testing/test_qwen35_kira_turing_psych_voice_evaluation_preparation.py` | 5,385 | `0cb317113b44a4d66370445b0c4a01ed2479f2477875f291f3e1673f1270ef66` |
| `Testing/test_qwen35_kira_turing_psych_voice_owner_evaluation.py` | 34,357 | `0b480fb67edc568b9d54e28ec433c802d6b70cf73cfd56ea9882465c8c115160` |
| `RecoverySprint/continuation_20260809/kira_qwen35_turing_psych_voice_owner_evaluation_preparation/attempt_02/EVALUATION_CONTRACT.json` | 9,701 | `f9d1e0992f7829619e3787385339ec409b97e747e7e97372e2ab6aa332462b59` |

## Verification result

The documented combined static command now reports **29 passed and 2
failed**, not 31 passed. Both ordinary failures correctly expose source drift:
Attempt 02 binds `Core/conversation_loop.py` at
`b2bf956372c55e894020a9fb9d69de276bfc0c8448fac7f26ed5b497f4d7f9db`,
whereas the current exact college-reflection/adult-curriculum wiring is
`ad8719b495a9455ee1eb81290514c7d9854f58a069377d6b2282e1d6aa466eb4`.
Attempt 02 must remain unchanged as historical append-only evidence.

## Blocking hostile findings

### 1. Live entry functions do not consume the claimed execution capabilities

The source defines `_mint_parent_capability`, `_consume_parent_capability`,
`_mint_child_capability`, and `_consume_child_capability`, but each symbol
occurs only at its own definition. `main()` calls `parent_run()` and
`child_run()` without a capability, and those public functions accept no
capability parameter. A direct Python call to `parent_run("attempt_01")`
reached the mocked `reserve_attempt` boundary immediately. Therefore the CLI
confirmation gate is not structurally bound to either live entry function.

### 2. The preparation artifact parser accepts ambiguous duplicate-key JSON

A temporary artifact containing an attacker-first
`"schema_version": 999` followed later by the canonical
`"schema_version": 1` parsed to the expected object. The current
`load_preparation_contract()` and `preparation_contract_issues()` returned no
issues. The runner validates the last-key-wins object rather than one exact,
unambiguous canonical byte representation.

### 3. Final acceptance trusts caller-authored `passed` claims

A fabricated report containing only:

- `consent.classification = CLEAR_CONTINUE`;
- six rows with the expected turn IDs and `passed = true`;
- `voice_release_clean = true`;
- `protected_unchanged = true`; and
- `ollama_final_absence.passed = true`

returned an empty issue list from `final_run_contract_issues()`. The final
validator does not independently rederive each turn's raw/displayed/spoken
bindings, transformations, exact question hash, model-call count, telemetry,
WAV, route, playback, serialization, release, and GPU evidence.

### 4. Naive/non-UTC timestamps pass the telemetry validator

Every otherwise valid timestamp was changed from UTC `...Z` form to a naive
timestamp with no timezone. `required_telemetry_issues()` still returned an
empty issue list. The module already has `parse_utc_timestamp()`, which rejects
missing timezone information, but the required-turn validator does not use it.

### 5. The declared persistent-v2 environment reconciliation is stale

`PERSISTENT_V2_ENVIRONMENT_RECONCILIATION` claims a prepared value of `0` and
runtime value of `1` for `KIRA_DISABLE_BLACKWELL_GPU_VOICE`. The current
preparation's actual required value is already `1`. The constant is not used
or validated, so the evidence description can contradict the actual restricted
environment without failing.

## Positive controls retained

The static source still pins exact `qwen3.5:9b` and digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`,
selects persistent Blackwell-v2 CUDA, disables Llama/SAPI/generic/CPU fallback,
keeps camera/microphone/media/Blender out of scope, distinguishes technical
playback from Robert's later exact hearing self-report, and contains a bounded
six-turn behavior-observation battery with a voluntary-stop path. Those
positive properties do not overcome the blockers above.

## Required append-only successor

Do not overwrite Attempt 02 and do not run the current runner. An append-only
Attempt 03 must:

1. bind one-use parent and child capabilities inside the actual entry
   functions before reservation, imports, or live work;
2. read the preparation bytes once, reject duplicate keys, and require the
   exact canonical UTF-8 byte representation derived from the current sealed
   source graph;
3. rederive final per-turn acceptance from the raw evidence instead of
   trusting `passed` booleans;
4. require timezone-aware UTC timestamps in exact order;
5. remove or exact-validate the stale environment reconciliation; and
6. bind the current stable conversation/runtime source hashes only after the
   memory-permission work stops changing them.

The successor must receive a fresh independent hostile audit. Even an accepted
static successor may run only while Robert is present to choose whether to
participate, stop after any turn, hear the synchronous public playback, and
personally provide the separate post-playback hearing acknowledgment.
