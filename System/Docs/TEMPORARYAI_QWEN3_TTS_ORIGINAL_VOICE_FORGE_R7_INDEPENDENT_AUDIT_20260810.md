# TemporaryAI Qwen3-TTS Original Voice Forge R7 - independent hostile audit

Date: 2026-08-10

Audit boundary: fresh independent exact-byte and static-only correctness audit.
No launcher, parent, worker, predecessor execution graph, evaluator, model,
Torch, Torchaudio, GPU, person, body, Blender, network, audio generation, or
audio playback operation ran.

## Decision

`REJECT`

`R7_NOT_AUTHORIZED_FOR_SYNTHESIS_OR_ANY_BOUNDED_REAL_RUN`

The R7 append-only repair closes the five R6 findings in the selected hostile
regression probes, and every sealed payload row matches. It is nevertheless
not correct enough to become an execution authority. Fresh independent probes
reproduced three successor blocker classes: unbounded authorization lifetime,
physically inconsistent CUDA telemetry, and internally contradictory or
negative resource-accounting evidence.

This report is not an `ACCEPT_STATIC_ONLY` decision and must not be named by an
execution authorization as accepted audit evidence. No canonical R7 audit
decision JSON was created. Do not create an R7 authorization, run its parent or
worker, synthesize an audition, or infer hearing/voice acceptance from this
static audit.

## Exact package and preservation verification

All six lineage manifests strict-parsed with duplicate-key and non-finite
constant rejection. Across 131 manifest rows, each byte count and SHA-256
matches, every manifest has a unique row inventory, no row escapes the project
or resolves through a symlink/alias, and the manifests bind 56 unique current
artifacts without contradictory bindings.

| Manifest | Rows | Unique | Drift | Bytes | SHA-256 |
|---|---:|---:|---:|---:|---|
| R2 harness | 23 | 23 | 0 | 5,557 | `682d95880d93fffa68a7c9bbf6005ca52e59f1ab241be827c3f0c1d2938844a4` |
| R3 harness | 14 | 14 | 0 | 5,033 | `3116650bf4937c77af9937fede8ee187f16165ab3a3d21ee3c2e08e6579bcada` |
| R4 harness | 22 | 22 | 0 | 6,819 | `576d1a64db85d3b783ed6186fa3332daf54ed94381c5cf5a44600b875494f038` |
| R5 payload | 18 | 18 | 0 | 3,922 | `92de1f2f770892e0bb09a6a0b2fb44ac1acf4206282bda6124dc84c54d10901b` |
| R6 payload | 24 | 24 | 0 | 5,433 | `e32eb5dadfe80cc94cf1b57a98bf9220c8f7a5809d251b056d72fc02d2408a0e` |
| R7 payload | 30 | 30 | 0 | 6,646 | `509d2b802310b1c0e075039da28e18744dad59bccd816f7623a8b0963169e6eb` |

The R7 closure is exactly the 24 R6 payload rows plus the R6 manifest, rejected
R6 audit, R7 repair boundary, R7 guard, R7 worker, and R7 parent. The five
separately sealed R6 rejection-evidence artifacts listed by the R6 audit also
remain exact (`5/5`, zero mismatch).

The exact R7 scope reviewed is:

| Path | Bytes | SHA-256 |
|---|---:|---|
| `TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v7.json` | 6,646 | `509d2b802310b1c0e075039da28e18744dad59bccd816f7623a8b0963169e6eb` |
| `TemporaryAI/config/qwen3_tts_voice_forge_external_acceptance_binding_v7.disabled.json` | 1,444 | `6b350f9ca2e6e450c34c468623d2ec7d4b4c8502cb8f49ed71a1dd3f0165e94e` |
| `tools/qwen3_tts_voice_forge_r7_guards.py` | 79,259 | `a92c9cf4fd7d6058a1a0f901725480a13380004478577b543b69475d56b5fc60` |
| `tools/qwen3_tts_original_voice_forge_worker_v7.py` | 26,850 | `8e7497dd6101040003ab17e8b79c4f57deedffb31df21de3cbd001ce6b391ca9` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v7.py` | 71,846 | `e4f99a0d315c41e9b23de0bee70cff3c460f1dd13f32f49b888f3af3007dd79b` |
| `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v7.py` | 26,326 | `ac2514d7778a76e0a26f3561006faeb6cc0681781a4c4db7c3e057babef82b10` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7/attempt_01/HOSTILE_PROBES.py` | 5,328 | `288d22dde6a683d275c8394761cb146dca57e750b33582dea8b035b693492b3e` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7/attempt_01/RESULT.json` | 1,712 | `b7d014ba9a98208db918b6853cef774e374761bb62dff34b3e27ee738df2a7db` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7/attempt_01/CHECKPOINT.md` | 2,355 | `5522f827d93bb770257b651aee014b76027eb25e67944e4c01b9284d25996d69` |
| `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R7_REPAIR_BOUNDARY_20260810.md` | 6,902 | `1fcab62f02e9f598ac69a0ddacbc48870f72bcf05e5f1f5eddf47bbcb320d2cc` |

The one historical R1 checkpoint discrepancy already recorded by the R6 audit
is unchanged: `tools/create_temporary_ai_candidate.py` is 49,233 bytes at
`12067aa17979df53f3ea1791c3a059dada202e07f59fc7b615c8ce73c3823706`,
not its R1 checkpoint hash. That file is outside the R7 payload and execution
graph, so it remains a preservation disclosure rather than an R7 finding.

## Inertness and controls that passed

- The R7 payload says `execution_allowed=false` and
  `self_authorization_allowed=false`.
- The distributed binding says `execution_allowed=false` and remains outside
  the append-only authorization root.
- The R7 authorization, ledger, parent-reservation, worker-claim, and
  private-review roots did not exist after the audit.
- Four R7 Python sources compile directly from their exact bytes.
- The authored focused suite reran `18/18 PASS`.
- The authored static hostile probe reran `9/9 PASS`.
- Fresh probes confirmed that an audit whose canonical decision is `REJECT`
  cannot be laundered; sealed evaluator thresholds and nonempty complete
  collision rows are enforced; zero CUDA activity and unstructured event
  sequences are rejected; the authorization-owned worker nonce survives the
  ledger comparison; file-identity substitution is rejected; and acceptance
  commit is structurally inside the held Windows lease scope.
- The current exact collision corpus has zero voices. Source inspection
  confirms that the parent rejects this before `run_contained_worker_v7`.
  Thus this exact payload cannot reach a worker launch even apart from this
  rejection.

These results establish useful static progress. They do not prove Windows Job
behavior, telemetry authenticity, model loading/unloading, audio quality, GPU
behavior, or runtime containment because no real process was permitted.

## Blocker 1 - a supposedly short-lived authority may last millennia

The distributed binding requires `expires_utc` to be short-lived, but
`verify_execution_authorization()` checks only this ordering:

`audit completed <= issued <= observed <= expires`

It imposes no maximum on `expires - issued` and no freshness bound between the
audit and issuance. The independent probe constructed a fully canonical,
hash-exact audit decision and authorization with issuance at
`2026-08-10T00:00:01Z` and expiry at `9999-12-31T23:59:59Z`. Verification at
`2026-08-10T12:00:00Z` accepted it.

Observed result:

`successor_long_lived_authorization_accepted=true`

One-use storage limits reuse after reservation, but it does not make an
unconsumed bearer authority fresh. Repair requires a sealed maximum lifetime
and rejection when `expires_utc - issued_utc` exceeds it. If audit freshness is
part of the authority policy, that interval also needs a sealed maximum.

## Blocker 2 - physically impossible CUDA allocated/reserved states pass

The R7 resource validator checks `reserved >= allocated` after each model
load and for Torch peaks. It does not check the same physical invariant at the
baseline or final samples, despite the repair boundary's claim of consistent
reserved/allocated values.

The independent probe supplied positive synthesis allocations and otherwise
valid evidence, but set:

- baseline CUDA allocated = 50 bytes, reserved = 0;
- post-design-unload allocated = 50 bytes;
- final CUDA allocated = 50 bytes, reserved = 0.

The exact R7 validator accepted the evidence.

Observed result:

`successor_impossible_cuda_relationships_accepted=true`

Repair requires `reserved >= allocated` at every paired observation, including
baseline and final state. The unload observation should include and validate a
reserved-memory sample if it is part of the claimed unload proof.

## Blocker 3 - contradictory timestamps and negative Job counters pass

R7 separately requires an ordered RSS interval and a positive elapsed value,
but never reconciles the parsed timestamp delta with `elapsed_seconds`. The
independent probe used identical start/end timestamps with a claimed elapsed
duration of 999 seconds. The validator accepted it.

Observed result:

`successor_contradictory_rss_clock_accepted=true`

The R7 parent observation adds `total_processes` and
`total_terminated_processes`, but only checks that the former is at least one
and the latter is not greater. It does not require integer, non-boolean,
nonnegative counters. A value of `-1` for total terminated processes was
accepted by the complete resource reconciliation validator.

Observed result:

`successor_negative_job_counter_accepted=true`

These are the same evidence-coherence class that made R6 unsafe: individually
plausible field assertions are not enough when their cross-field
relationships can be impossible. Repair requires timestamp/elapsed
reconciliation with an explicit tolerance, bounded sample-count relationships,
and exact nonnegative-integer validation for all parent Job accounting fields.

## Append-only independent audit evidence

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7_independent_audit/attempt_01/INDEPENDENT_REHASH.py` | 9,804 | `b8e21af5fd5e8e64b13077ef92c7cb4d08ed5be2a909c9cc9c4eed8c645724ef` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7_independent_audit/attempt_01/INDEPENDENT_HOSTILE_PROBES.py` | 12,968 | `f7fcea592b45e6a1cf351e5909a3e6bb156e5d88555205ab2f4c87ad7b37ea19` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7_independent_audit/attempt_01/EXACT_BYTE_REHASH_RESULT.json` | 4,154 | `76593b84a5632b336d5098f03eb90bd764d9aa749e96faa37a53501a647b0125` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7_independent_audit/attempt_01/AUTHORED_STATIC_TESTS_RESULT.json` | 520 | `1ab925fdac6d4389cee7c39eef0aaef4a9f83d0dfbf9b9086c505afd6eb56c96` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7_independent_audit/attempt_01/AUTHORED_HOSTILE_PROBES_RESULT.json` | 511 | `9a149f64bc7a1140a8841f300d7263a05aedce519c614e435fb6fbcd6f0d345a` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r7_independent_audit/attempt_01/INDEPENDENT_HOSTILE_PROBE_RESULT.json` | 1,232 | `96aeb6b3ea87cb4c4a03c9c7e6eb15f5432a33eb6c8fa01e5b0a7c5582060f56` |

## Required successor boundary

Preserve R1-R7, the R6 rejection, this R7 rejection, and every audit artifact
append-only. A successor must repair the three blocker classes above without
editing R7; add exact hostile tests that first reproduce each current
acceptance and then prove rejection; rehash the complete predecessor closure;
and receive another fresh independent static audit.

Even a later `ACCEPT_STATIC_ONLY` result would not authorize synthesis. A
separate owner-authorized, one-use, genuinely short-lived authority would
still be required, and the current empty sealed collision corpus would still
prevent a run.

## Rollback

No runtime rollback is required. No runtime, model, audio, GPU, person, body,
Blender, route, assignment, activation, publication, authorization, ledger,
claim, or private-review state changed. Rollback is to ignore R7 for execution,
retain all evidence append-only, and continue using only already approved voice
paths.
