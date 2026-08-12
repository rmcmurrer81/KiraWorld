# TemporaryAI Qwen3-TTS Original Voice Forge R4 - Independent Hostile Audit

Date: 2026-08-09  
Audit type: fresh independent hostile static audit plus stdlib-only synthetic adversarial probes  
Execution boundary: no installation, download, network access, Torch import,
Qwen3-TTS import, evaluator/model import, GPU work, inference, voice generation,
audio playback, environment creation, registry change, or runtime route change

## Verdict

`REJECT_FOR_BOUNDED_REAL_EXECUTION`

R4 closes the two concrete R3 blocker classes at the direct guard layer:

- arbitrary package payloads such as `torch/injected.pyd` are rejected under
  every allowed installer-difference reason; and
- candidate/job/profile substitutions, stale hashes, extra or multiple stdout
  records, fixed-artifact substitutions, and post-child WAV changes fail the
  supplied R4 guards.

However, the complete parent acceptance boundary is still not safe when the
manifest and worker-produced evidence are treated as hostile, as required by
this audit. Four independently reproduced defects remain:

1. the mutable R4 manifest is its own unauthenticated trust root and can
   authorize changed guard/worker hashes while also changing its audit status;
2. the parent accepts self-asserted post-worker Torch/Torchaudio binding maps
   containing prohibited package payloads and does not compare those maps to
   its own preflight result or independently recompute them;
3. the supposedly exact single child JSON object accepts duplicate keys and
   silently applies Python's last-key-wins interpretation; and
4. the final artifact decision and failure evidence are not atomic: artifacts
   can change after the last reopen but before/after the acceptance write, and
   failure-record collisions are silently swallowed.

The R4 manifest must remain
`IMPLEMENTED_REQUIRES_INDEPENDENT_AUDIT` with `execution_allowed: false`.
No bounded real run is authorized by this audit.

## Exact audited scope

The R4 manifest was independently parsed and every one of its 22 rows was
reopened. All 22 byte counts and SHA-256 values matched.

Principal R4 files:

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v4.json` | 6,819 | `576d1a64db85d3b783ed6186fa3332daf54ed94381c5cf5a44600b875494f038` |
| `tools/qwen3_tts_voice_forge_r4_guards.py` | 19,537 | `6f7973ebbc186847f1d9aa3839d0a5d6a7b7ec68f2e568f13f623a88e1cc10c0` |
| `tools/qwen3_tts_original_voice_forge_worker_v4.py` | 16,885 | `88fba85bce7e9110d8a76db01cec33db72465d776e77070dbd330bdac5399353` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v4.py` | 21,285 | `728ead7ac976c30d2efc29ccf3438dbffddc713447f7ee870c7e5466a8dcdac2` |
| `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v4.py` | 27,476 | `9e863604d8fdf6b6f710d9f39d7f39927c6527379d33bc8563f429c05f64a054` |

The rejected R3 audit remained 13,273 bytes with SHA-256
`30d82546cdea8ba874ee552ab684fc0404249f6d2635a0aa3831727a28384efb`.
Its independent hostile probe remained 36,017 bytes with SHA-256
`e9fc2a209dcb422ea7279fc4fc787204fb59698a06298b4085f0d02b55c84b13`.

The current R4 manifest is still inert. The environment specification says
`SPECIFIED_NOT_CREATED_OR_ACCEPTED`, the trusted bundle registry says
`NO_OWNER_AUTHORIZED_BUNDLES_REGISTERED`, and the evaluation corpus says
`PENDING_REAL_LOCAL_SPEAKER_EMBEDDING_CORPUS`.

## Verification performed

All Python commands used `-B`/`PYTHONDONTWRITEBYTECODE=1` and only stdlib
temporary fixtures. No model or speech implementation was imported.

The complete frozen R1, R2, R3, and R4 suites were rerun:

```text
Ran 128 tests in 4.435s
OK
```

The prior independent R3 probe was rerun unchanged. It again reproduced R3's
arbitrary executable-extra acceptance and post-exit identity/artifact binding
failure. Separate R4 probes then confirmed that the direct R4 replacements
reject those exact old cases.

Passing R4 hostile outcomes included:

```json
{
  "extra_stdout": "REJECTED:R4GuardError",
  "multiple_json_stdout": "REJECTED:R4GuardError",
  "post_child_wav_mutation": "REJECTED:R4GuardError",
  "rehashed_manifest_job_substitution": "REJECTED:R4GuardError",
  "rehashed_profile_candidate_substitution": "REJECTED:R4GuardError"
}
```

The R4 package-payload probe supplied `torch/injected.pyd` separately under
`INSTALLER_METADATA`, `DIRECT_URL_METADATA`, `REQUESTED_METADATA`, and
`INSTALLER_GENERATED_BYTECODE`. All four were rejected with `R4GuardError`.
The clean exact-wheel fixture and the exact non-executable `.dist-info/INSTALLER`
fixture passed.

## Passing retained controls

### Fixed candidate, job, profile, and artifact identity

The parent requires exact child-returned hashes for
`worker_manifest_v4.json` and `voice_profile_candidate_v4.json`, reconciles the
bundle/candidate/voice/job/authorization fields to the parent-verified bundle,
and requires three distinct exact artifact paths:

- `original_design_reference.wav`;
- `runtime_clone_test.wav`; and
- `runtime_clone_prompt.pt`.

Rehashed candidate and job substitutions failed. Duplicate, swapped,
arbitrary, missing, and post-handoff-mutated artifact fixtures failed.

### Persisted prompt and evaluator mutation guards

The frozen R3 worker still persists, flushes, reopens, deserializes, and
semantically compares the runtime clone prompt before passing only the reloaded
object to clone generation. Corrupt bytes and a parseable substitution are
rejected. Both final WAVs are checked before and after each guarded evaluator
operation and again before worker acceptance.

This passing implementation control does not make a synthetic post-exit
evidence dictionary independently trustworthy; that distinction is central to
Blocker 2 below.

### Truthful offline and watermark boundaries

R4 retains the narrow label
`OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL` and explicitly records
`network_nonuse_proven: false`. It does not claim process-level network denial.

R4's watermark status is only
`NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK`. It does not claim that generated
audio is detector-proven watermark-free, and it requires a separate later
audit for any stronger status. No removal or circumvention was attempted.

### Model, installation, Torch, CUDA, and output-quality truth

The frozen R2/R3 path contains hash-bound environment, model-manifest,
site-packages, exact-wheel, eager-CUDA, ASR, speech-probability, pure-tone,
speaker-embedding, collision-corpus, RAM, and VRAM gates. Static source review
confirmed those gates remain in the sealed dependency inventory.

No present evidence can mark them passed on this computer: the exact R4
environment and corpus remain uncreated/pending and no owner-authorized bundle
exists. This audit therefore makes no claim that Qwen3-TTS, Torch, CUDA,
speech quality, originality, latency, or any generated voice passed a real
execution.

## Blocker 1 - the mutable manifest is a circular trust root

`verify_r4_harness()` in both the parent and child reads
`qwen3_tts_voice_forge_harness_manifest_v4.json`, requires its status and
`execution_allowed` fields, and then trusts the file hashes declared by that
same JSON.

The manifest does not include or authenticate its own bytes. No separate
append-only execution authorization is required to name:

- the exact audited manifest hash;
- the exact independent audit document and hash;
- the exact one-run authorization transition; and
- the unchanged audited rows.

Consequently, one hostile edit can simultaneously change the status to
accepted, replace guard/worker hashes with hashes of changed files, and satisfy
the loader. The required-file check is only a subset check; it does not bind an
exact immutable inventory to a separate authority.

This is not cured by this audit document recording the current manifest hash,
because neither runner nor worker verifies this document or an external
signature/seal.

Required repair: keep an immutable payload manifest for the exact audited
inventory and use a separate append-only execution authorization record that
contains the immutable manifest SHA-256, independent audit path/hash, exact
authorized status transition, bundle/run scope, and one-use authorization.
Both parent and worker must verify that external authorization before loading
any executable dependency.

## Blocker 2 - hostile worker provenance maps are accepted by flags alone

The real R4 installer-difference validator correctly rejects package payloads.
The post-worker parent validator does not run that validator on the maps it
accepts.

`_require_strict_binding_map()` in the parent checks only that each Torch and
Torchaudio row:

- is a dictionary;
- says `exact_wheel_to_installed_files_bound_r4: true`;
- says `unbound_installer_generated_package_bytes_allowed: false`; and
- contains any list named
  `bounded_non_executable_installer_metadata_differences`.

It does not validate the list members, wheel/RECORD hashes, installed members,
package counts, or equality to the parent-computed preflight bindings. It also
does not recompute the environment after worker exit.

The independent probe supplied all three worker-manifest maps with these
values:

```json
{
  "exact_wheel_to_installed_files_bound_r4": true,
  "unbound_installer_generated_package_bytes_allowed": false,
  "bounded_non_executable_installer_metadata_differences": [
    "torch/attacker_payload.pyd"
  ]
}
```

The child hash, worker-manifest hash, and profile/artifact hashes were all
recomputed. The complete post-exit R4 guard flow accepted the manifest. The
same occurred for Torchaudio and for the preflight, worker-pre-model, and
worker-post-execution map positions.

Observed result:

```json
{
  "full_parent_postexit_guard_accepts_forged_binding_maps": true,
  "forged_paths": [
    "torch/attacker_payload.pyd",
    "torch/attacker_payload.pyd",
    "torch/attacker_payload.pyd"
  ],
  "parent_claim": true
}
```

`parent_claim` is R4's
`all_parent_acceptance_fields_derived_not_self_asserted` field. That claim is
false for this accepted fixture.

The exact sealed honest worker is expected to create stricter maps. That is
not enough under the required hostile-output boundary: the parent labels the
maps independently accepted without deriving or reconciling them.

Required repair: require canonical equality between the parent preflight map,
the exact parent reservation, worker pre-model evidence, worker postflight
evidence, and a fresh parent recomputation after clean worker exit. Apply the
real R4 installer-difference validator to every accepted row and bind the
canonical hashes of these maps into the exact child result.

## Blocker 3 - duplicate keys make the exact child JSON ambiguous

`parse_child_result()` decodes one nonblank line and calls ordinary
`json.loads()`. Python accepts duplicate object keys and silently retains the
last value.

The hostile stdout object contained two `candidate_id` keys: an attacker value
first and the expected reserved value second. It was accepted:

```json
{
  "duplicate_json_key_stdout": {
    "accepted": true,
    "resolved_candidate_id": "candidate-r4-a"
  }
}
```

This violates the claimed exact, unambiguous one-object result. A different
parser or evidence reviewer may interpret the same bytes differently.

Required repair: parse every acceptance-critical JSON object with a duplicate-
key-rejecting `object_pairs_hook`, including child stdout, manifest, profile,
bundle, authorization, job, ledger, and acceptance evidence. For child stdout,
also require its bytes to equal one canonical serialization plus the exact
permitted newline policy.

## Blocker 4 - final acceptance and failure evidence remain raceable

The parent performs its second artifact reopen, compares the two reads, and
then writes `parent_acceptance_v4.json`. It does not hold the artifacts against
mutation, terminate/contain possible descendant processes, or reverify the
accepted artifacts and acceptance record after the write.

A synthetic fixture passed both parent reopens. The clone WAV was then changed
before any further guard. The result was:

```json
{
  "post_final_reopen_mutation": {
    "parent_had_passed_twice": true,
    "artifact_now_matches_child_seal": false
  }
}
```

The acceptance JSON would still describe the earlier bytes. Rechecking at a
later consumer may detect this, but R4 itself currently returns success without
that postcondition.

Failure preservation has a related append-only gap. `preserve_failure()`
silently catches every exception from its one fixed failure-path write. With a
pre-existing `parent_preflight_failure_v4.json`, the function returned and
left the hostile bytes unchanged:

```json
{
  "preexisting_failure_evidence_path": {
    "preserve_failure_returned": true,
    "content_unchanged": true
  }
}
```

Also, `reserve_attempt()` runs before the launcher's `try` block, so an attempt-
reservation failure produces no R4 failure record.

Required repair: contain the entire child process tree, move completed outputs
into a parent-owned finalization area, verify content-addressed artifacts after
the acceptance record is durably written, and require every later hearing/use
consumer to reopen the exact seals. Reserve append-only failure slots before
risky work, use a collision-safe sequence, and never silently claim preserved
failure evidence when the evidence write failed.

## Re-audit boundary

Do not change the R4 manifest to an accepted/executable status and do not run
the real forge on this verdict. Preserve R1 through R4 byte-for-byte.

Any successor should be append-only and must, in a fresh independent audit:

1. bind an immutable audited payload manifest to a separate exact execution
   authorization and audit hash;
2. reject forged Torch/Torchaudio post-worker maps and prove exact equality to
   parent preflight plus fresh parent postflight recomputation;
3. reject duplicate JSON keys at every acceptance-critical layer;
4. demonstrate descendant-process containment and post-acceptance artifact
   integrity; and
5. guarantee append-only early-failure evidence without silent loss.

It must also rerun every R1/R2/R3/R4 suite and all prior R3 executable,
candidate/profile/job, prompt, evaluator-mutation, fixed-artifact, offline,
watermark, model-identity, environment, Torch/CUDA, and failure-path probes.

