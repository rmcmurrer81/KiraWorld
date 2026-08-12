# TemporaryAI Qwen3-TTS Original Voice Forge R7 repair boundary

Date: 2026-08-10

Status: `STATIC_REPAIR_CANDIDATE_ONLY`

R7 is an append-only successor to the independently rejected R6 package. R1
through R6 and all prior audit evidence remain historical, sealed inputs. No
R7 execution authorization exists. The shipped example binding is disabled.

No model, audio generation, audio playback, GPU, synthetic person, body,
Blender, network, launcher, parent, worker, or embedded predecessor execution
was performed while authoring this repair. Static parsing, source compilation,
and local hostile guard tests are the only permitted author checks. A different
auditor must inspect the final exact bytes before any later owner-authorized
one-use run can even be considered.

## Exact predecessor boundary

- R6 payload manifest:
  `TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v6.json`
  at SHA-256
  `e32eb5dadfe80cc94cf1b57a98bf9220c8f7a5809d251b056d72fc02d2408a0e`.
- R6 independent rejection:
  `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R6_INDEPENDENT_AUDIT_20260810.md`
  at SHA-256
  `9094838509d115091da568dab55db8d6ab0a73c2642063f59f173da80cb56d10`.
- R6 remains rejected and unauthorized. R7 does not relabel that report as an
  acceptance and does not edit any R6 byte.

## Five bounded repairs

### 1. Independent-audit decision and subject binding

R7 has one strict canonical machine decision schema. The guard requires all of
the following before it will accept a later external execution authorization:

- exact `ACCEPT_STATIC_ONLY` decision;
- final, static-only state;
- no runtime execution by the auditor;
- an explicit statement that the audit itself does not authorize execution;
- an empty unresolved-blocker list;
- exact R7 payload-manifest path, hash, and inventory digest;
- exact rejected-R6 audit path and hash;
- exact separately hashed human-readable audit report;
- an opaque auditor identity hash and explicit author/auditor separation; and
- canonical UTF-8 JSON bytes with duplicate keys and non-finite constants
  rejected.

The parent bootstrap, worker bootstrap, semantic binding, acceptance, and
later-use reopening all use the same R7 parser and require exact audit identity
equality. A filename or an authorization writer's claim cannot turn a `REJECT`
report into accepted audit evidence.

### 2. Sealed limits and complete evaluator evidence

R7 reads evaluator thresholds from the exact sealed R2 contract, SHA-256
`8ae41050fcb5cef73d6dfc65a60a97302b0e8d7278f1dd40cc1cc9908233bab1`:

- maximum word-error rate: `0.05`;
- minimum speech probability: `0.90`;
- maximum pure-tone probability: `0.10`;
- minimum reference/clone similarity: `0.80`; and
- maximum resident-or-generic collision similarity: `0.72`.

All observations and limits must be finite and range-bounded. The child must
preserve every collision row, its exact digest, complete unique subject
coverage, and the recomputed maximum. Worker-selected substitute thresholds,
NaN, infinity, values outside the closed probability/similarity ranges,
omitted collision rows, duplicates, and inconsistent maxima fail closed.

The presently sealed evaluation corpus has status
`PENDING_REAL_LOCAL_SPEAKER_EMBEDDING_CORPUS` and contains no voices. R7
requires a nonempty exact collision result set. Therefore the shipped static
candidate cannot pass a future synthesis run merely by comparing against an
empty corpus. Creating and separately sealing a real corpus is outside this
repair.

### 3. Finite real resource telemetry and closed events

R7 requires the exact RSS sampler schema, positive sampling duration, at least
two samples, a bounded interval, ordered timestamps, generation/evaluation
coverage, and consistent baseline/sampled/OS high-water values. It requires
positive CUDA allocation above baseline during both model loads and both
generation phases, consistent reserved/allocated and Torch peak values,
bounded post-unload CUDA return, finite positive phase timings, an additive
bounded total, and exact predecessor plus instrumented runtime event sequences.

Parent evidence is bound to the exact worker PID, parent PID, claimed worker
path/hash, canonical command hash, authorization, worker nonce, Windows Job
state, accounting-query results, termination/quiescence state, and exact held
stdout/stderr bytes and hashes. Child telemetry alone remains insufficient.

These validators specify evidence required from a later real run. This static
repair does not claim that Windows Job containment, CUDA use, unloading, or
timing has occurred.

### 4. One-use nonce and audit identity through later use

The canonical semantic binding adds the worker-instance nonce, authorization
path, audit-decision path/hash/subject, auditor identity, audit-report
path/hash, evaluation-corpus hash, exact entry-worker path/hash, and canonical
worker-command hash. Reservation, ledger, claim, child artifacts, parent
acceptance, reverified authorization, and later-use reopening must all equal
that semantic authority. The nonce is not selected from a ledger during later
use. `accepted_utc` cannot precede the authorization verification time.

### 5. Held Windows object identity through commit

R7 restores a Windows-only held-handle boundary. Accepted files are opened
without write or delete sharing and their ancestor directories are opened
without delete sharing. The guard records `FILE_ID_INFO`, normalized final-path
hash, size, and SHA-256 from the held objects. Handles remain open through
evidence validation, acceptance creation, immediate acceptance reopening,
validation of that reopened object, and creation/reopening of a separate
identity-commit token. Later use requires the same file identities and bytes.

This design rejects non-Windows durable acceptance instead of silently
downgrading the identity promise. Static tests may inject a deterministic fake
identity provider to test comparison logic; production acceptance cannot.

## Inertness and future authority

The R7 payload manifest must say `execution_allowed=false` and
`self_authorization_allowed=false`. The distributed example binding must stay
outside the append-only authorization root and say `execution_allowed=false`.
An independent `ACCEPT_STATIC_ONLY` result, if one is later issued, would mean
only that the exact static package passed that audit. It would not authorize
synthesis. A separate, short-lived, exact, append-only, one-use owner authority
would still be required, and the empty real collision corpus remains an
independent fail-closed prerequisite.

## Rollback

No runtime rollback is required because this candidate performs no runtime
change. Rollback is to ignore the R7 payload, disabled example binding, and
R7 author-test evidence for execution while retaining all files append-only.
Existing approved voice routes and R1-R6 historical evidence remain unchanged.
