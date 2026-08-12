# TemporaryAI Qwen3-TTS Original Voice Forge R5 Static Repair Checkpoint

Date: 2026-08-09  
Status: `R5_STATIC_SUCCESSOR_SEALED_FRESH_INDEPENDENT_AUDIT_REQUIRED_EXECUTION_BLOCKED`

## Outcome

An append-only R5 successor closes the four blocker classes in the rejected R4
independent audit without changing R1, R2, R3, R4, their manifests, tests,
probes, checkpoints, or audits.

R5 remains deliberately inert:

- immutable payload-manifest `execution_allowed`: `false`;
- immutable payload-manifest `self_authorization_allowed`: `false`;
- disabled external-acceptance-binding template `execution_allowed`: `false`;
- no accepted R5 independent audit exists;
- no real R5 execution authorization exists;
- no environment creation, installation, download, or network access ran;
- no Torch, Torchaudio, Qwen3-TTS, evaluator, or model import/load ran;
- no GPU work, inference, voice generation, WAV creation, or playback ran;
- no TemporaryAI voice assignment, activation, publication, upload, route,
  Chatterbox, current-voice, handoff, or runtime change occurred.

This checkpoint does not authorize a bounded real run.

## Repair 1 - no circular mutable manifest trust root

`qwen3_tts_voice_forge_payload_manifest_v5.json` is an immutable payload
inventory. It can never authorize itself: its exact status requires a separate
external authorization and both permission fields are false.

A later invocation must receive two trust values from outside the mutable
payload file:

1. the exact independently published SHA-256 of the immutable payload
   manifest; and
2. the exact SHA-256 and path of a distinct append-only execution
   authorization under
   `Data/voice/authorizations/qwen3_tts_voice_forge_v5/`.

The authorization schema binds the exact:

- immutable payload path/hash;
- fresh independent R5 audit path/hash;
- preserved rejected R4 audit path/hash;
- opaque bundle ID;
- one bounded run ID;
- one-use authorization nonce;
- issue and expiry timestamps; and
- `execution_allowed: true` transition.

The parent reserves append-only failure evidence, then verifies both external
trust objects using only its already-invoked entry source. It imports no R5,
R4, R3, or R2 dependency before both exact objects pass. The child repeats the
same trust bootstrap before importing even the R5 guard module. Both then run
the complete shared guard verification again.

Every sealed dependency is compiled directly from the just-hashed source
bytes. R5 does not use timestamp-based `__pycache__` bytecode to load a sealed
module, so a stale or substituted `.pyc` cannot bypass the exact source seal.

The one-use authorization is consumed into an exact hash-named append-only
ledger before the predecessor queue nonce. A second use collides and fails;
the authorization file itself is never rewritten into a consumed state.

The shipped `.disabled.json` file is only a schema/example binding. Its status,
audit, nonce, timestamps, bundle, and run are non-authorizing placeholders; it
cannot pass the parent or worker gate.

## Repair 2 - strict JSON with duplicate-key rejection

Every R5 parser uses a duplicate-key-rejecting `object_pairs_hook`, including
nested objects. The strict reader is installed into the sealed R2/R3/R4
modules before they read bundle, owner authorization, job, queue, ledger,
environment, corpus, profile, manifest, reservation, or predecessor evidence.
R4 outputs are independently strict-parsed by R5 before parent acceptance.

Child stdout must be exactly one canonical compact UTF-8 object followed by
exactly one LF. Pretty JSON, blank lines, CR, multiple objects, missing/extra
fields, duplicate keys, and last-key-wins ambiguity fail closed.

## Repair 3 - complete parent-derived Torch/Torchaudio provenance equality

R5 no longer accepts worker flags or summary maps as proof. For both Torch and
Torchaudio it independently derives and binds a complete provenance capsule:

- canonical environment distribution-spec hash;
- complete installed RECORD map with every path, byte count, and SHA-256;
- complete exact wheel archive member map with every path, byte count,
  SHA-256, and RECORD-self designation; and
- the strict R4 wheel-to-installed binding result.

The real R4 installer-difference validator remains active during every parent
and worker derivation. Only the exact non-executable `.dist-info/INSTALLER`,
`direct_url.json`, or `REQUESTED` differences may exist. Package-root extras,
bytecode, `.pyd`, DLL, executable, source, `.pth`, or arbitrary metadata extras
fail.

Canonical byte equality is mandatory across all five trust phases:

1. actual parent preflight recomputation;
2. exact parent reservation;
3. worker pre-model recomputation;
4. worker post-execution recomputation; and
5. fresh parent postflight recomputation after clean worker exit.

The complete capsule hash is bound into the profile, worker manifest, exact
canonical child result, and parent acceptance. Tests reject an injected
`torch/injected.pyd`, a forged true-flag summary, an arbitrary `.dist-info`
extra, a changed worker file-map hash, and a changed parent postflight map.

## Repair 4 - contained child and atomic parent-owned finalization

The Windows child is created suspended, assigned to a new kill-on-close Job
Object, and only then resumed. Timeout or failure terminates that exact Job.
After the primary worker exits, the parent terminates the exact Job again to
remove any surviving descendant before it trusts or moves output.

The worker writes only inside one parent-reserved `attempt_NNN` tree. After
the process tree is gone, the parent performs a same-volume sibling rename to
a new, non-preoccupied `finalized_attempt_NNN` path. Existing target content is
never overwritten.

Before acceptance, the parent reopens the hash-bound R4/R5 profiles and
manifests, validates every exact R4 artifact seal, and performs the fresh full
provenance recomputation. It then holds Windows read-only/no-write/no-delete
handles for:

- both final WAVs;
- the persisted runtime-clone prompt;
- the R4 and R5 worker manifests/profiles;
- the immutable payload manifest;
- the exact execution authorization;
- the one-use authorization ledger;
- the accepted R5 audit; and
- the preserved rejected R4 audit.

While those handles remain held, the parent semantically validates everything,
durably writes and fsyncs the append-only acceptance, reopens that acceptance,
and repeats semantic/artifact validation. A later hearing/use consumer must
receive the exact acceptance SHA-256 and reopen both trust objects, the audit,
and every accepted artifact snapshot. Expiry governs starting the one bounded
run; it does not erase the immutable evidence of a completed run.

## Repair 5 - unambiguous early and final failure evidence

Before external trust verification or attempt allocation, the parent reserves
a random 128-bit collision-resistant append-only incident directory and
durably writes a slot record. Bootstrap trust failures are written there with
exclusive creation before any dependency import.

After the shared guards load, every preflight, attempt-reservation, worker,
finalization, postflight, or acceptance failure uses numbered append-only
failure records. A preoccupied failure name advances to the next unused name;
it is never overwritten or silently swallowed. If all preservation writes
fail, R5 raises a distinct evidence-preservation error rather than claiming
that failure evidence exists.

## Exact R5 seal

The immutable payload manifest has 18 exact runtime dependency rows. It does
not contain itself and therefore has no self-hash cycle.

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `tools/qwen3_tts_voice_forge_r5_guards.py` | 29,861 | `c2792fd8009d78055c5e0d750713e4d104f468db20d258776d468953f6c09885` |
| `tools/qwen3_tts_original_voice_forge_worker_v5.py` | 26,785 | `2714e29525a64e59ffa38cee6cbcd5f07538492c9c3e768f762e13d7de24c842` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v5.py` | 47,436 | `253ca43a809ce29dd02036b36ced63cdc1222109bc6369499eed238d946f1453` |
| `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v5.py` | 29,841 | `49539c8735274928c9882390bb424e0f623265acd10020630dcd6c12a6e4c1e7` |
| `TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v5.json` | 3,922 | `92de1f2f770892e0bb09a6a0b2fb44ac1acf4206282bda6124dc84c54d10901b` |
| `TemporaryAI/config/qwen3_tts_voice_forge_external_acceptance_binding_v5.disabled.json` | 1,012 | `4222979540b97757a2b8dd9c684c3f9736428abedacf0d775a5abd485d995917` |

Preserved R4 rejection anchors:

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R4_INDEPENDENT_AUDIT_20260809.md` | 14,378 | `04073b96cd4d514aaa5e60b75783d0e2a1c024782fce591fc83fcfe3e2befe9b` |
| `TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v4.json` | 6,819 | `576d1a64db85d3b783ed6186fa3332daf54ed94381c5cf5a44600b875494f038` |

## Static hostile verification

All verification used Python `-B`/`PYTHONDONTWRITEBYTECODE=1`, stdlib-only
temporary fixtures, and no runtime/model import.

- new focused R5 hostile tests: `41/41 PASS`;
- frozen R1 + R2 + R3 + R4 plus R5: `169/169 PASS`;
- nested/top-level duplicate-key and noncanonical stdout probes: pass;
- self-authorizing/rehashed manifest and wrong external hash probes: rejected;
- disabled, wrong-root, wrong-bundle, wrong-run, wrong-manifest, wrong-audit,
  and duplicate-key authorization probes: rejected;
- one-use authorization reuse: rejected;
- forged true-flag and injected executable/package provenance: rejected;
- complete installed/wheel file-map substitution across any phase: rejected;
- preoccupied finalization path: rejected without overwrite;
- post-validation artifact mutation: rejected;
- preoccupied failure slot: next append-only slot used without overwrite;
- total failure-evidence write loss: explicit `R5EvidenceError`;
- later-use acceptance/artifact mutation: rejected;
- R5 source AST parsing and JSON parsing: pass;
- sealed source-byte loading ignores bytecode caches: pass;
- immutable payload recomputation: `18/18 MATCH`.

The frozen R3 independent hostile probe was also rerun unchanged. It still
reproduces the historical R3 blockers, which is expected evidence; R5 rejects
their successor forms rather than rewriting that append-only probe.

## Fresh independent audit boundary

R5 is not accepted for execution. A new independent auditor must recompute the
exact seal and, without model/runtime execution, independently reproduce at
minimum:

1. mutable/self-authorizing manifest substitution and confirm the externally
   supplied manifest hash plus separate authorization reject it before any
   dependency import in both parent and worker;
2. duplicate keys at child stdout and every file-backed JSON trust layer;
3. forged worker summary/full provenance, injected `.pyd`/package extras, and
   changed parent postflight maps;
4. attempted descendant survival, occupied finalization targets, mutation
   across durable acceptance, and later-use mutation;
5. occupied/failed bootstrap and normal failure-evidence paths; and
6. every frozen R1/R2/R3/R4 suite and prior hostile probe.

Only after an independent audit accepts this exact payload hash may a distinct
append-only one-use authorization be created. That later authorization still
cannot assert an environment, corpus, evaluator, owner bundle, synthesis,
quality, originality, watermark, latency, or owner-hearing result into
existence; every predecessor real gate remains mandatory.

## Rollback

No runtime rollback is required because R5 was not executed. To decline R5,
preserve these append-only files, leave both shipped permission fields false,
create no external authorization, and continue using the already approved
voice paths. Never delete or rewrite R1-R4 evidence or any approved voice/model
environment as part of that decision.
