# TemporaryAI Qwen3-TTS Original Voice Forge R6 - independent hostile audit

Date: 2026-08-10

Audit boundary: fresh independent exact-byte and static-only correctness audit.
No launcher, parent, worker, predecessor execution graph, evaluator, model,
Torch, Torchaudio, GPU, person, body, Blender, network, audio generation, or
audio playback operation ran.

## Decision

`REJECT`

`R6_NOT_AUTHORIZED_FOR_SYNTHESIS_OR_ANY_BOUNDED_REAL_RUN`

The shipped R6 payload and disabled binding remain inert. The static repair
does close the four specifically documented R5 defects at a useful structural
level, and every one of the 24 R6 payload rows matches. It is nevertheless not
correct enough to become an execution authority. Independent hostile probes
reproduced three new fail-open evidence/authority defects, and source review
found two later-use identity/durability gaps.

This rejection must not be named by an execution authorization as an accepted
audit. Do not create an R6 authorization, run the parent or worker, synthesize
an audition, or infer hearing/voice acceptance from this static work.

## Exact package and historical-byte verification

The R6 payload manifest strict-parsed with duplicate-key rejection and has an
exact 24-row, 24-unique-row inventory. Every listed byte count and SHA-256
matches. Its expected closure is exactly the 18 R5 payload rows plus the R5
manifest, R6 guards, R6 worker, R6 parent, rejected R5 audit, and R6 repair
boundary. No row escapes the project, is a symlink, is duplicated, or refers
to the R6 manifest itself.

Recursive historical manifest verification also passed:

| Manifest | Rows | Unique | Drift | Bytes | SHA-256 |
|---|---:|---:|---:|---:|---|
| R2 harness | 23 | 23 | 0 | 5,557 | `682d95880d93fffa68a7c9bbf6005ca52e59f1ab241be827c3f0c1d2938844a4` |
| R3 harness | 14 | 14 | 0 | 5,033 | `3116650bf4937c77af9937fede8ee187f16165ab3a3d21ee3c2e08e6579bcada` |
| R4 harness | 22 | 22 | 0 | 6,819 | `576d1a64db85d3b783ed6186fa3332daf54ed94381c5cf5a44600b875494f038` |
| R5 payload | 18 | 18 | 0 | 3,922 | `92de1f2f770892e0bb09a6a0b2fb44ac1acf4206282bda6124dc84c54d10901b` |
| R6 payload | 24 | 24 | 0 | 5,433 | `e32eb5dadfe80cc94cf1b57a98bf9220c8f7a5809d251b056d72fc02d2408a0e` |

Across those manifests, all 50 unique directly bound artifacts match every
binding that names them. The R5 rejected-audit anchor remains 18,599 bytes at
SHA-256
`82ea5a0a543fde40f7a1d05dc166798f98acbd9ae120c11ba8fb7f9ffbb5f43a`.

The exact R6 scope remains:

| Path | Bytes | SHA-256 |
|---|---:|---|
| `tools/qwen3_tts_voice_forge_r6_guards.py` | 63,032 | `8bf13ed57c3c19e729d586ed0196e8530de9c5d419b2b6c394a557fa6a05262a` |
| `tools/qwen3_tts_original_voice_forge_worker_v6.py` | 40,056 | `606734e3581ec73b8fa8b56e663f7f290102c43314bdbb0ab9d7aeff09d08f88` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v6.py` | 51,184 | `6ba4e5f6282d98b62466c38739eb2080d046f7a0bb021fbff0afd0c7053ec63b` |
| `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v6.py` | 23,709 | `8a8690c1d9a14d1311a157e3f56613b577441cb7c2de1e2d8e8e4ae3dd0c54d7` |
| `TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v6.json` | 5,433 | `e32eb5dadfe80cc94cf1b57a98bf9220c8f7a5809d251b056d72fc02d2408a0e` |
| `TemporaryAI/config/qwen3_tts_voice_forge_external_acceptance_binding_v6.disabled.json` | 1,146 | `107fe73aa98e54f6f47c80fbfcbaa0aa1340f57c9bc6a78dd2c74f7b39f35133` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r6/attempt_01/HOSTILE_PROBES.py` | 2,409 | `3b2c476167fd6713c15431e9d110150f92e18d66c970fdfb3ea6d98f7e64fb06` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r6/attempt_01/RESULT.json` | 758 | `93cd9a44ccb6354a9a4f176b109b8c8983fb21f0010098dedbd405ebc4820910` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r6/attempt_01/CHECKPOINT.md` | 1,450 | `00ca97c161ae5713033a56180a259ad27b1eb218e4f3fe26706aedbbc8fee9f0` |
| `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R6_STATIC_REPAIR_CHECKPOINT_20260810.md` | 6,613 | `5b5f7f4941853a2362c9da288a6835d454874434ae888620dbc01ade598a600f` |

One separate historical R1 checkpoint seal does not match the current tree:
`tools/create_temporary_ai_candidate.py` is currently 49,233 bytes at
`12067aa17979df53f3ea1791c3a059dada202e07f59fc7b615c8ce73c3823706`,
not the R1 checkpoint's
`1ed3be42609480b91e86530679222f99fa0728bf81279dd00b01050e874b11dc`.
The other eight R1 checkpoint seals match. This file is not in the R6 payload
or execution graph, and this audit did not modify it, so it is reported as a
historical preservation discrepancy rather than attributed to R6. A blanket
claim that every historical R1 byte remains unchanged is not currently true.

## Inertness and controls that passed

- R6 payload `execution_allowed=false`.
- R6 payload `self_authorization_allowed=false`.
- shipped binding `execution_allowed=false`, is outside the authorization
  root, and both parent and worker bootstraps reject it;
- the R6 authorization, parent ledger, parent reservation, worker claim, and
  private-review output roots do not exist;
- exact schemas reject duplicate JSON keys and path escape;
- R5 unsafe profile/permission substitution is rejected;
- a second worker claim and retry after an early claim collide before the
  supplied predecessor loader callback;
- missing evaluator sections and direct WAV-hash substitution are rejected;
- active Job descendants, premature finalization, and parent memory peaks
  below worker-reported peaks are rejected; and
- the three R6 Python sources compile from exact bytes.

The authored focused suite reran `26/26 PASS`; its selected hostile suite reran
`14/14 PASS`. These are useful regression results but did not include the
independent probes below.

Static Windows Job inspection confirms that the source creates a Job with
kill-on-close, creates the primary worker suspended, assigns it before resume,
terminates the Job after primary exit, queries basic accounting and extended
limits, and requires zero active processes before finalization. No real child
was permitted in this audit, so descendant containment and actual OS
telemetry remain runtime-unproven. The serialized validator cannot by itself
prove that a purported parent observation came from that code.

## Blocker 1 - an audit named REJECT is accepted as execution authority

`verify_execution_authorization()` constrains the audit path to a filename
pattern under `System/Docs`, requires a nonzero hash, and checks those bytes.
It never parses an audit schema, independent-auditor identity, decision, or
explicit static acceptance state. Parent and worker bootstrap contain the
same filename/hash-only boundary.

The independent probe created an isolated temporary project, copied the exact
rejected R5 audit anchor, and created a hash-exact file named like an R6
independent audit whose complete decision was `REJECT`. It then created an
otherwise exact, in-window authorization that claimed the audit was accepted.
The exact R6 guard returned that authorization as valid.

Observed result:

`rejected_audit_accepted_as_execution_authority=true`

This means a claimant-controlled authorization status can launder a rejecting
audit. Repair requires one closed, machine-readable audit-decision object with
an exact `ACCEPT_STATIC_ONLY` decision, exact audited payload hash, exact
auditor separation/identity evidence, and an explicit statement that the audit
does not itself authorize execution. Parent, worker, and later-use code must
all parse and compare the same object rather than trust its filename.

## Blocker 2 - impossible and self-selected evaluator thresholds pass

The evaluator validator checks only finite nonnegative numbers and compares
each observation to threshold values supplied inside the same worker evidence.
It does not bind those thresholds to the sealed contract and does not cap
probabilities or similarities to their physical `[0,1]` range.

The independent probe supplied, while preserving every exact schema and WAV/
text/subject binding:

- word-error rate `999.0` with worker-selected maximum `999.0`;
- speech probability and minimum `2.0`;
- pure-tone probability and maximum `2.0`;
- reference/clone similarity and minimum `2.0`; and
- collision maximum `2.0`.

The exact validator accepted the evidence.

Observed result:

`physically_impossible_evaluator_values_accepted=true`

Repair requires parent-owned thresholds derived from the exact sealed contract,
closed `[0,1]` bounds where applicable, a bounded WER contract, and validation
of the actual maximum collision result rather than only a child boolean and
digest.

## Blocker 3 - zero GPU activity and meaningless event telemetry pass

The worker-resource validator checks field presence, nonnegative integers,
self-hashes, a nonempty RSS-sampler object, finite nonnegative timings, and a
list of nonempty event strings. It does not require model/GPU allocation,
expected phase names or order, nonzero load/generation activity, unload return,
or consistency between phase timings and total time.

The independent probe set every RAM/CUDA numeric field to zero, every timing to
zero, the RSS sampler to an unbound string-bearing object, and the entire event
sequence to `hostile-unstructured-event`. A syntactically valid parent Job
record still reconciled it and the exact resource validator accepted it.

Observed result:

`zero_gpu_and_unstructured_worker_events_accepted=true`

Parent Job RAM/IO accounting is valuable but cannot establish CUDA activity or
unload. Repair requires a closed event sequence; exact model phase bindings;
positive observed GPU allocation during the required phases; bounded final
CUDA return; timing relationships; and an independently authenticated parent
observation linked to the exact primary process/Job and exact stdout/stderr.

## Blocker 4 - later-use authorization identity is incomplete

The complete semantic binding omits `worker_instance_nonce_sha256`.
During later-use reopening, the authorization is reverified, but only its
authorization nonce and generation seed are compared to the semantic object.
The reservation, ledger, and claim are then validated using the worker nonce
read back from the ledger itself. There is no comparison between that chain's
worker nonce and the reverified authorization's worker nonce.

The acceptance's separately named independent-audit path/hash are also hashed
but not required to equal the audit path/hash inside the reverified
authorization. `accepted_utc` is not parsed or ordered against the trusted
authorization verification time.

Repair requires these values in the canonical semantic object and exact
cross-object equality among authorization, reservation, ledger, claim,
acceptance, and later-use reopening.

## Blocker 5 - R6 dropped the held-handle identity commit used by R5

R5 contains a Windows read-only/no-delete handle boundary for the exact files
while acceptance is validated and committed. R6's parent does not call that
boundary and defines no equivalent retained-handle/final-file-identity logic.
It path-resolves, stats, hashes, closes, and later reopens files. Ancestor
reparse identities and final Windows file IDs are not retained through the
acceptance write.

Later-use rehashing will detect ordinary drift, but it does not make the
original acceptance commit race-free or prove that every validation read
referred to the same Windows file object. Repair must retain exact handles or
equivalent final file identities across output validation, resource
reconciliation, acceptance creation, and immediate reopen, and must keep the
later-use revalidation.

## Append-only audit evidence

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r6_independent_audit/attempt_01/INDEPENDENT_HOSTILE_PROBES.py` | 7,359 | `898949b3624789557010612f75223e258c8fa1802b40067444b3b6de205ed60a` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r6_independent_audit/attempt_01/INDEPENDENT_REHASH.py` | 7,437 | `1b04f84504373f947ab15d1bcaa1c2e6c1c384e992107d36afbdb7c01ef9dfde` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r6_independent_audit/attempt_01/HOSTILE_PROBE_RESULT.json` | 472 | `356c76cf83a32fb0ec77aa9b34cbc4c7f44e576e87f54688cde961faccda13c5` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r6_independent_audit/attempt_01/EXACT_BYTE_REHASH_RESULT.json` | 2,205 | `66f3306deb63d0cbe217b5ea4ed127221f48219b29abb238e1a27db6301a6cfb` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r6_independent_audit/attempt_01/AUTHORED_TESTS_RESULT.json` | 415 | `ee0b234d74c7a3340bb9bd12ca02f55a501b1daa389dbbad67101a66c9c6d390` |

## Required successor boundary

Preserve R1-R6 and this rejection append-only. A successor must repair all
five blockers without editing R6, add hostile tests that reproduce each exact
failure before proving rejection, and receive another fresh independent audit.
Static repair and static acceptance would still not authorize synthesis. Any
future bounded run would require a separate owner-authorized one-use authority
after that audit.

## Rollback

No runtime rollback is required. No runtime, model, audio, GPU, person, body,
Blender, route, assignment, activation, or publication state changed. Rollback
is to ignore the R6 payload and this audit's probe files for execution, retain
all evidence append-only, and continue using only already approved voice paths.
