# TemporaryAI Qwen3-TTS Original Voice Forge R7 static repair checkpoint

Date: 2026-08-10

## Current truth

`R7_STATIC_REPAIR_CANDIDATE_SEALED_AWAITING_FRESH_DIFFERENT_AUDITOR`

R7 is not authorized for synthesis. It is not an engineering execution pass,
an owner-hearing pass, a voice approval, an assignment, or an activation.
The example authorization binding is disabled and outside the required
append-only authority root. No machine audit decision was authored by the R7
author.

No launcher, parent, worker, predecessor Python graph, model, Torch,
Torchaudio, audio generation, playback, GPU, network, synthetic person, body,
or Blender process ran. Only exact-byte reads, Python source compilation,
stdlib validator tests, and static source inspection occurred.

## Preserved rejected predecessor

R6 remains rejected and unchanged:

- payload manifest: 5,433 bytes at
  `e32eb5dadfe80cc94cf1b57a98bf9220c8f7a5809d251b056d72fc02d2408a0e`;
- independent rejection: 13,590 bytes at
  `9094838509d115091da568dab55db8d6ab0a73c2642063f59f173da80cb56d10`;
- exact R6 payload rehash: 24 rows, 24 unique paths, zero mismatches.

No R1-R6 artifact was edited by this repair. The R7 payload is exactly the 24
R6 payload rows plus the R6 manifest, R6 rejection, R7 guard, R7 worker, R7
parent, and R7 repair-boundary note: 30 rows and 30 unique paths.

## Repair 1: accepted audit decision is parsed and bound

R7 defines one exact canonical machine-audit schema. The shared guard requires
`ACCEPT_STATIC_ONLY`, final static-only status, no audit-time runtime
execution, no unresolved blockers, `audit_authorizes_execution=false`, exact
payload and inventory subject binding, the exact rejected-R6 anchor, a hashed
human report, an opaque auditor identity, and explicit fresh-process author /
auditor separation. Duplicate keys, non-finite constants, noncanonical bytes,
subject drift, report drift, a `REJECT` decision, or an auditor claiming to
have authored the subject sources fail closed.

The parent and worker both invoke this same exact validator before predecessor
module import. Authorization, semantic evidence, acceptance, and later-use
reopening require exact decision, subject, auditor, and report equality.

## Repair 2: finite evaluator values and sealed limits

R7 binds all limits to the exact R2 contract:

- WER maximum `0.05`;
- speech probability minimum `0.90`;
- pure-tone probability maximum `0.10`;
- reference/clone similarity minimum `0.80`;
- resident/generic collision similarity maximum `0.72`.

Numbers must be finite and within their closed physical ranges. Collision
evidence must contain every unique expected corpus subject, exact row bytes,
an exact digest, and the recomputed maximum. Empty results, omitted/duplicate
subjects, a forged maximum, worker-selected limits, NaN, infinity, and
out-of-range probabilities/similarities fail closed.

The currently sealed corpus contains zero voices. The parent explicitly checks
and rejects that condition before the contained worker call. The worker also
requires nonempty results. This is an intentional fail-closed prerequisite,
not a passing collision result and not permission to mutate the sealed corpus.

## Repair 3: real finite resource evidence and closed events

R7 requires a closed RSS sampler schema, positive ordered sampling, positive
model/generation CUDA allocation above baseline, consistent allocated/reserved
and peak values, bounded unload return, positive finite phase timings, an
additive bounded worker total, and exact predecessor plus instrumented runtime
phase sequences. The worker instrument records design load, generation,
unload, base load, clone prompt, clone generation, and base unload without
altering the sealed runtime's phase methods.

Parent reconciliation binds the exact claimed worker PID, parent PID, entry
worker path/hash, canonical command hash, authorization, worker nonce, Job
configuration/query truth, Job accounting, primary exit, termination request,
quiescence, and held stdout/stderr size/hash. A normal clean worker with no
remaining descendants may legitimately report zero Job limit-terminated
processes; total processes must still be positive and all active processes
must be zero before finalization.

## Repair 4: later-use authority identity

The semantic subject now contains the worker-instance nonce, authorization
path/hash/nonce, audit decision/report identity, evaluator-corpus hash, entry
worker path/hash, and canonical command hash. The authoritative R7
reservation, ledger, worker claim, generated evidence, parent acceptance, and
later-use reverified authorization must all match those values. The later-use
path never chooses the worker nonce from the ledger. Acceptance time cannot
precede authorization verification.

The sealed R6 compatibility reservation exists only to let the inherited R6
evidence graph hash its expected predecessor-format record. It points to the
authoritative R7 ledger and is itself retained and revalidated; it is not a
second authority.

## Repair 5: held Windows file identity through commit

The R7 parent opens all accepted files without write/delete sharing and their
ancestor directories without delete sharing after the atomic final path exists.
It records Windows `FILE_ID_INFO`, normalized final-path hash, size, and
SHA-256. Under those same held handles it reruns the complete output and
resource validators, creates the acceptance, reopens and revalidates it, and
creates/reopens the separate identity-commit token. After handle release it
runs the complete later-use reopen again. An identical-byte replacement with
a different file ID is rejected.

## Static verification

- R7 focused tests: `18/18 PASS`.
- R7 authored independent-style hostile probes: `9/9 PASS`.
- Guard, worker, and parent compile from exact bytes.
- R7 manifest closure: 30 rows, 30 unique paths, zero mismatches.
- R7 canonical payload-file inventory SHA-256:
  `e737131ec596269189b61c7421589e070152a07b3ead28428b54ee796491b7c8`.
- R6 preservation rehash: 24 rows, 24 unique paths, zero mismatches.

The tests cover rejected-audit laundering, subject author/auditor confusion,
duplicate JSON keys, NaN/infinity/out-of-range values, substitute thresholds,
empty/incomplete collision rows, forged maxima, zero CUDA activity, zero
timings, reordered/unstructured events, parent PID/log substitution,
authorization-owned worker nonce, file-ID substitution, claim-before-
predecessor ordering, empty-corpus-before-worker ordering, and held commit /
later-reopen source ordering.

## Exact authored files

| Path | Bytes | SHA-256 |
|---|---:|---|
| `TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v7.json` | 6,646 | `509d2b802310b1c0e075039da28e18744dad59bccd816f7623a8b0963169e6eb` |
| `tools/qwen3_tts_voice_forge_r7_guards.py` | 79,259 | `a92c9cf4fd7d6058a1a0f901725480a13380004478577b543b69475d56b5fc60` |
| `tools/qwen3_tts_original_voice_forge_worker_v7.py` | 26,850 | `8e7497dd6101040003ab17e8b79c4f57deedffb31df21de3cbd001ce6b391ca9` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v7.py` | 71,846 | `e4f99a0d315c41e9b23de0bee70cff3c460f1dd13f32f49b888f3af3007dd79b` |
| `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v7.py` | 26,326 | `ac2514d7778a76e0a26f3561006faeb6cc0681781a4c4db7c3e057babef82b10` |
| `TemporaryAI/config/qwen3_tts_voice_forge_external_acceptance_binding_v7.disabled.json` | 1,444 | `6b350f9ca2e6e450c34c468623d2ec7d4b4c8502cb8f49ed71a1dd3f0165e94e` |
| `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R7_REPAIR_BOUNDARY_20260810.md` | 6,902 | `1fcab62f02e9f598ac69a0ddacbc48870f72bcf05e5f1f5eddf47bbcb320d2cc` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7/attempt_01/HOSTILE_PROBES.py` | 5,328 | `288d22dde6a683d275c8394761cb146dca57e750b33582dea8b035b693492b3e` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7/attempt_01/AUTHORED_STATIC_TESTS_RESULT.json` | 495 | `6c117484585b10ddaad91600554c1202dbeca7faa473d5d7a64585c3ca1c57fb` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7/attempt_01/HOSTILE_PROBE_RESULT.json` | 659 | `9e95c7b39a04e7743950074df02fb72ebc542ca3c30b6049f702804ebf7f5576` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7/attempt_01/RESULT.json` | 1,712 | `b7d014ba9a98208db918b6853cef774e374761bb62dff34b3e27ee738df2a7db` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7/attempt_01/CHECKPOINT.md` | 2,355 | `5522f827d93bb770257b651aee014b76027eb25e67944e4c01b9284d25996d69` |

Generated `__pycache__` bytecode is not part of the payload or evidence seal.

## Required next step

A different agent must perform a fresh exact-byte static audit, reproduce the
hostile tests independently, and issue either `REJECT` or a canonical machine
`ACCEPT_STATIC_ONLY` decision bound to the exact manifest and inventory. The
author must not self-issue that decision. Static acceptance, if obtained,
would still not authorize execution. A separately owner-authorized, one-use,
short-lived authority and a newly sealed nonempty real collision corpus would
both be required before any bounded run could be considered.

## Rollback

No runtime state changed. Rollback is to ignore R7 for execution and retain
R1-R7 source, evidence, and audit history append-only. Existing approved voice
routes remain unchanged.
