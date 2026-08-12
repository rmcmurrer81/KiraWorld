# TemporaryAI Qwen3-TTS Original Voice Forge R5 - Independent Hostile Audit

Date: 2026-08-09  
Audit type: fresh independent hostile static audit plus stdlib-only synthetic
adversarial probes  
Execution boundary: no installation, environment creation, download, network
access, Torch/Torchaudio import, Qwen3-TTS import, evaluator/model import, GPU
work, inference, voice generation, audio creation, audio playback, activation,
assignment, publication, upload, or runtime-route change

## Verdict

`REJECT_FOR_BOUNDED_REAL_EXECUTION`

R5 materially improves the rejected R4 boundary. The exact immutable payload
is externally hash-pinned, the shipped binding is disabled, duplicate JSON
keys fail, complete parent-derived Torch/Torchaudio file maps are reconciled
across five phases, final WAV/prompt bytes receive a parent-owned finalization
and held-handle commit, and failure-record collisions no longer disappear.

Those repairs are not sufficient when the R5 child profile/manifest, the
authorization ledger, and inherited evaluator/telemetry evidence are treated
as hostile. This audit independently reproduced four execution blockers:

1. the parent does not semantically bind the R5 profile and manifest to the
   parent-derived candidate, `ai_type`, owner authorization, job, predecessor
   profile, permission state, or profile artifact seals;
2. the worker's authorization-ledger check is read-only and accepts the same
   consumed ledger repeatedly, so direct worker retry/replay of an early
   failed exact pending attempt is not rejected by the R5 worker gate;
3. the mandatory later-use helper preserves bytes but does not semantically
   validate the held R5 profile/manifest, re-run the full trust validators, or
   reopen the authorization ledger and rejected R4 audit; and
4. the R5 parent acceptance does not independently validate or bind the R2
   ASR/speech/originality/collision/watermark evidence or runtime resource
   telemetry when those worker-produced objects are hostile.

The shipped payload and binding must remain inert. This document is a rejected
audit and must not be cited by any execution authorization as an accepted R5
audit.

## Exact audited scope and stable seal

The immutable payload manifest was strict-parsed with duplicate-key rejection
and independently reopened twice during this audit. It contained exactly 18
rows; all 18 byte counts and SHA-256 values matched on both observations. It
does not contain itself.

Principal R5 files:

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `tools/qwen3_tts_voice_forge_r5_guards.py` | 29,861 | `c2792fd8009d78055c5e0d750713e4d104f468db20d258776d468953f6c09885` |
| `tools/qwen3_tts_original_voice_forge_worker_v5.py` | 26,785 | `2714e29525a64e59ffa38cee6cbcd5f07538492c9c3e768f762e13d7de24c842` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v5.py` | 47,436 | `253ca43a809ce29dd02036b36ced63cdc1222109bc6369499eed238d946f1453` |
| `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v5.py` | 29,841 | `49539c8735274928c9882390bb424e0f623265acd10020630dcd6c12a6e4c1e7` |
| `TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json` | 3,922 | `92de1f2f770892e0bb09a6a0b2fb44ac1acf4206282bda6124dc84c54d10901b` |
| `TemporaryAI/config/qwen3_tts_voice_forge_external_acceptance_binding_v5.disabled.json` | 1,012 | `4222979540b97757a2b8dd9c684c3f9736428abedacf0d775a5abd485d995917` |

The payload inventory contains 11 Python sources, six JSON trust/configuration
files, and the preserved rejected R4 audit. All 11 Python sources compiled
from their exact bytes in memory; all six JSON payloads strict-parsed; the
remaining audit row matched its hash.

The R4 rejection anchors still matched:

- rejected R4 audit: 14,378 bytes,
  `04073b96cd4d514aaa5e60b75783d0e2a1c024782fce591fc83fcfe3e2befe9b`;
- R4 manifest: 6,819 bytes,
  `576d1a64db85d3b783ed6186fa3332daf54ed94381c5cf5a44600b875494f038`.

## Quiescence and disabled external binding

At the audit boundary:

- payload `execution_allowed` was `false`;
- payload `self_authorization_allowed` was `false`;
- disabled-binding `execution_allowed` was `false`;
- the disabled binding remained under `TemporaryAI/config/`, outside the only
  accepted `Data/voice/authorizations/qwen3_tts_voice_forge_v5/` root;
- its audit, nonce, bundle, run, issue time, and expiry remained non-authorizing
  placeholders;
- `Data/voice/authorizations/qwen3_tts_voice_forge_v5/` did not exist;
- `Data/voice/runtime/qwen3_tts_voice_forge_authorization_ledger_v5/` did not
  exist;
- `Voice/voice_forge/private_review_v5/` did not exist;
- the trusted bundle registry contained no owner-authorized entries;
- the isolated environment remained `SPECIFIED_NOT_CREATED_OR_ACCEPTED`;
- the evaluation corpus remained
  `PENDING_REAL_LOCAL_SPEAKER_EMBEDDING_CORPUS` with no voices; and
- no R5 execution was launched by this audit.

The shipped disabled binding was independently presented to the parent
bootstrap with its exact hash and was rejected. The exact current 18-row
payload cannot pass its inherited real preflight. Making the environment,
corpus, or registry ready would change sealed payload bytes and therefore
requires a new payload hash and a new independent audit before any separate
authorization could be considered.

## Controls that passed independent review

### External manifest split and strict JSON

Both parent and worker verify the externally supplied payload-manifest hash and
separate authorization hash before loading the R5 guard dependency. The
manifest cannot set either permission field true. The authorization schema is
exactly scoped to the manifest, fresh audit, preserved R4 rejection, bundle,
run, nonce, and time interval, and its path is constrained to the append-only
authorization root.

Every R5 parser uses nested duplicate-key rejection. The strict reader is
installed into the predecessor modules for their ordinary file-backed JSON
reads. Child stdout is one canonical compact object followed by exactly one
LF; duplicate keys, CR/LF variation, pretty JSON, extra fields, and extra
records fail.

This remains an operational external-trust design: the expected manifest and
authorization hashes are caller-supplied command arguments, not a signature
or locally pinned authority key. A real invocation therefore still depends on
a trusted invoker supplying previously reviewed values. No such authorization
exists now.

### Torch, Torchaudio, wheel, RECORD, and provenance maps

R5 independently derives complete Torch and Torchaudio capsules containing
the sealed environment distribution-spec hash, complete installed RECORD file
map, complete wheel archive member map, and strict R4 wheel-to-installed
binding. R3 performs actual path/size/hash equality for wheel members and
installed files. R4 permits only exact `.dist-info/INSTALLER`,
`direct_url.json`, or `REQUESTED` installer differences and rejects package
payload, bytecode, executable, arbitrary metadata, `.pyd`, DLL, source, or
`.pth` extras.

R5 requires canonical equality across parent preflight, parent reservation,
worker pre-model, worker post-execution, and fresh parent postflight. The
shipped tests reject forged flags, injected package payloads, complete worker
map substitution, arbitrary metadata extras, and changed postflight maps.
This static audit found no new bypass in that five-phase reconciliation.

### Final WAV, persisted clone prompt, finalization, and failure evidence

The parent reserves a new attempt, uses a suspended Windows Job Object child,
terminates the Job after the primary worker exits, then performs a non-
overwriting same-parent rename into `finalized_attempt_NNN`. It reopens the R4
and R5 manifests/profiles and the three exact final artifacts. The acceptance
commit holds no-write/no-delete handles for both WAVs, the persisted clone
prompt, R4/R5 manifests/profiles, payload, authorization, ledger, fresh audit,
and rejected R4 audit while it revalidates and writes the append-only
acceptance.

Byte mutation of a snapshotted final artifact is detected by the later-use
helper. A preoccupied finalization target is rejected without overwrite.

Bootstrap failures reserve a random 128-bit incident slot before external
trust verification. Later failures use numbered exclusive-create records;
preoccupied names advance, and total preservation loss raises a distinct
error. The supplied collision and write-loss tests passed.

The shipped containment test is only a static source-string check for the Job
APIs. Under this audit's no-execution boundary no independent descendant-
survival process probe was run, so the claim that the entire Job is quiescent
before rename remains unproven here and must not be upgraded from static
evidence.

### No-network truth and original-synthetic boundary

The inherited chain truthfully labels its network boundary
`OFFLINE_FLAGS_ONLY_NO_PROCESS_LEVEL_NETWORK_DENIAL` and states that network
nonuse is not proven. R5 adds offline cache flags but does not falsely claim an
OS-level denial. No network action occurred in this audit.

The parent and worker both bind the sealed job to
`ORIGINAL_SYNTHETIC_TEXT_DESIGN_NOT_PERSON_CLONE` and
`original_trait_description`. The inherited R2 gates require an eligible
`expert_temp_ai` or `generated_original_temp_ai`, canonical candidate profile
and creation request, owner authorization, static and live identity analyzer
clearance, and rejection of named-person/imitation language. Those gates are
sound in the sealed predecessor source, but Blocker 1 means their identity is
not fully reconciled into the final R5 profile accepted by the parent.

## Blocker 1 - hostile R5 profile/manifest identity and permission substitution

After finalization the parent strict-reads the hash named by child stdout, but
strict JSON and a child-chosen hash establish only byte identity. In the R5
parent, the only R5 profile field semantically inspected is
`exact_provenance_sha256`. The parent never reads the R5 profile's:

- `candidate_id`;
- `ai_type`;
- `opaque_voice_id`;
- `job_sha256`;
- `owner_authorization_sha256`;
- canonical profile/creation-request hashes;
- artifact seals or persisted-prompt evidence;
- `assignment_allowed`, `activation_allowed`, or
  `publication_or_upload_allowed`; or
- `owner_hearing_acceptance` and independent-audit state.

The R5 manifest receives only four substantive reads: artifact-seal hash,
provenance hash, worker pre-model capsule, and worker post-execution capsule.
Its schema, status, bundle/run/auth/ledger fields, predecessor hashes,
permission state, and owner-hearing state are not validated as an exact
object. The canonical R5 child result also omits candidate, `ai_type`, opaque
voice ID, owner authorization, job, and canonical candidate hashes.

An independent synthetic probe supplied a hash-exact R5 profile containing an
attacker candidate, an ineligible/person-clone `ai_type`, a different owner
hash, `assignment_allowed: true`, `activation_allowed: true`, publication
allowed, and owner hearing `ACCEPTED`. It satisfied every explicit R5 parent
profile condition when the provenance hash matched. The later-use helper also
accepted the snapshotted unsafe profile; changing its bytes afterward was
correctly rejected. This proves byte immutability without semantic safety.

Required repair: the parent must validate an exact R5 manifest/profile schema
and exact keys; derive and compare every R4 execution-binding field; require
the R5 profile to be one exact safe extension of the already validated R4
profile; compare profile and manifest artifact/prompt seals; require every use
permission false and owner hearing pending; and bind those parent-derived
values into the canonical child result and final acceptance.

## Blocker 2 - worker can reuse an already consumed authorization ledger

The parent consumes an authorization by exclusive-creating a hash-named
ledger, so a second parent invocation collides. The R5 worker does not perform
a second single-use claim. `_verify_ledger()` only reopens and compares the
existing parent ledger; it never creates or mutates a worker-launch claim.

An independent stdlib fixture called the exact worker `_verify_ledger()` twice
with the same immutable ledger, reservation, authorization hash, bundle, run,
and attempt. Both calls passed. Consequently a direct worker retry using the
same exact pending attempt after an early failure can pass the R5 authorization
gate again while the authorization remains unexpired. Existing append-only
outputs may make some retries collide, but that is not a one-use execution
proof, particularly before the first output/snapshot creation.

Required repair: before predecessor/model work, the worker must atomically
claim one exact parent-authorized launch with its own exclusive, globally
unique append-only receipt bound to authorization, nonce, run, bundle,
attempt, parent reservation, and worker identity. A second worker process must
collide before any predecessor import or runtime work. Parent acceptance must
reopen and bind that receipt.

## Blocker 3 - later-use reopening is byte-exact but semantically incomplete

`reopen_acceptance_for_later_use()` verifies the acceptance hash and its top-
level pending/disabled state, hash-reads the payload and authorization, checks
the independent-audit file hash, and compares a seven-file snapshot. It does
not:

- call `verify_payload_manifest()` or `verify_execution_authorization()`;
- reopen the one-use authorization ledger (the acceptance contains only its
  hash, not its path);
- reopen the preserved rejected R4 audit;
- semantically validate R4/R5 manifests and profiles;
- re-run R4 exact-artifact/persisted-prompt checks; or
- revalidate candidate, owner, job, originality, evaluator evidence,
  telemetry, and permission fields.

The independent unsafe-profile probe passed this exact helper. Therefore its
claim to be a mandatory hearing/assignment/use gate is not yet sufficient.

Required repair: acceptance must carry every immutable trust path/hash,
including ledger and rejected audit, and the later-use helper must invoke the
same full strict manifest, authorization, identity, profile, artifact,
evaluator, telemetry, and permission validators before returning anything to
a hearing or assignment consumer.

## Blocker 4 - evaluator/originality/watermark evidence and resource telemetry are not parent-reconciled

The sealed R2 worker contains substantive real gates for:

- exact local ASR and word-error rate;
- a separate real speech classifier;
- actual PCM16 pure-tone rejection;
- exact reloaded speaker-embedding input artifacts;
- reference-to-clone identity similarity;
- recomputed collision-corpus embeddings and resident/generic collision
  rejection;
- static and live named-person/imitation analysis;
- bounded watermark documentation scans with an explicitly limited status;
  and
- sampled process RSS, OS peak RSS, Torch peak CUDA allocated/reserved bytes,
  phase observations, unload return bounds, and timings.

Those controls cannot run in the current pending environment/corpus. More
importantly for a hostile-output audit, the R5 parent source never references
`audio_acceptance` or `telemetry`. It does not reopen the R2 manifest, validate
the telemetry object, compare it with parent/Job observations, validate the
ASR/speech/collision result structure, or bind their exact hashes into the R5
child result and parent acceptance. The R5 Job structure declares peak memory
fields but the parent never queries or records them; only worker elapsed time
is parent-owned.

The inherited profile carries some evaluator and identity summaries, and the
R4 validator protects three final artifact bytes, but neither substitutes for
parent validation when child evidence is hostile. Blocker 1 also permits those
R5 profile summaries to be changed or dropped.

Required repair: define exact schemas and parent validators for R2/R3
evaluator, identity, watermark, collision, and telemetry evidence; reopen the
hash-bound predecessor manifests/files after clean process-tree exit; compare
all WAV-linked evidence to the final held WAV hashes; collect independent
parent/Job resource observations where possible; and bind canonical evidence
hashes into the R5 child result, profile, acceptance, held snapshot, and
later-use gate.

## Verification counts

All executed Python commands used `-B`/
`PYTHONDONTWRITEBYTECODE=1` and stdlib-only fixtures.

- exact payload rows: `18/18 MATCH`, observed twice;
- sealed Python source compile from exact bytes: `11/11 PASS`;
- sealed JSON duplicate-rejecting parse: `6/6 PASS`;
- shipped focused R5 suite: `41/41 PASS`;
- frozen-suite collection: R1 `25`, R2 `60`, R3 `22`, R4 `21`, R5 `41`,
  total `169`;
- unsafe hash-exact R5 profile/later-use probe: blocker reproduced;
- repeated worker authorization-ledger verification: blocker reproduced;
- post-snapshot byte mutation: rejected;
- disabled shipped binding: rejected;
- manifest/auth bootstrap before R5 guard load in parent and worker: confirmed;
- source quiescence: all six principal byte counts/hashes unchanged after the
  probes.

The full 169-test frozen run was not executed in this audit because predecessor
tests create synthetic WAV fixtures and this assignment explicitly prohibited
audio creation. Collection and import were performed without running those
fixtures. The already recorded R5 checkpoint's 169/169 result was treated as
historical evidence, not as a fresh result of this audit.

## Re-audit boundary

Do not create an R5 execution authorization from this verdict. Preserve the
exact R1-R5 evidence and disabled binding. An append-only successor must, at
minimum:

1. close all four blockers above with hostile tests not authored by the repair;
2. include exact candidate/`ai_type`/owner/job/profile/permission/evaluator/
   telemetry bindings in parent acceptance;
3. prove worker-side one-use launch consumption and safe retry behavior;
4. make the later-use gate re-run the complete semantic trust boundary;
5. independently prove descendant quiescence before finalization; and
6. receive a fresh independent static audit of the new exact payload before a
   distinct external authorization can exist.

## Rollback

No runtime rollback is needed. R5 was not executed. Leave both shipped
permission fields false, create no external authorization, preserve this
rejected audit append-only, and continue using only already approved voice
paths. No TemporaryAI profile, current voice, Chatterbox route, avatar route,
or hearing state changed.
