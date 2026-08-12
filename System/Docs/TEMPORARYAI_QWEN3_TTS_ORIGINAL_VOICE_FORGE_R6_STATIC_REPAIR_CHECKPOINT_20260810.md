# TemporaryAI Qwen3-TTS Original Voice Forge R6 static repair checkpoint

Date: 2026-08-10

Status: `SEALED_STATIC_CANDIDATE_REQUIRES_DIFFERENT_FRESH_INDEPENDENT_AUDITOR`

## Decision and execution truth

R6 is an append-only static successor to the independently rejected R5
candidate.  It is **not accepted for a real bounded run**.  Its 24-row payload
sets `execution_allowed=false` and `self_authorization_allowed=false`; its
separate shipped binding is explicitly disabled and is outside the accepted
authorization root.

This repair did not install, download, import, load, or run Qwen3-TTS, Torch,
Torchaudio, an evaluator, or any model.  It did not launch the worker, create
or play audio, use a GPU, change a voice route, touch a person, or perform
body/Blender/live-media work.

Only a different fresh independent auditor may assess the exact sealed R6
payload.  Even a favorable static audit would not authorize execution.  A
separate hash-pinned, one-use authorization under
`Data/voice/authorizations/qwen3_tts_voice_forge_v6/` would still be required.

## Four bounded R5 repairs

1. **Exact semantic output binding.**  Closed schemas bind the parent-derived
   candidate, eligible original-design `ai_type`, opaque voice ID, owner/job/
   queue/bundle/run/attempt identities, canonical profile and creation-request
   hashes, R4/R5 predecessor hashes, final artifact/transcript/prompt hashes,
   seed/model revisions, evaluator/resource hashes, owner hearing pending, and
   all assignment/activation/publication permissions false.  R5 and R6
   profiles must be exact safe extensions; a hash-exact unsafe substitution is
   rejected on meaning.
2. **Worker-side one-use claim before predecessor/model import.**  The R6
   worker bootstrap verifies the exact 24-file payload and a stable external
   parent reservation, then exclusive-creates and reopens a hash-named worker
   launch claim before its first predecessor loader call.  The claim binds the
   authorization and nonce, worker-instance nonce, payload, bundle/run/
   attempt, stable reservation, parent ledger, exact worker bytes, and PID.
   Retry/collision stops before the predecessor loader.
3. **Complete later-use reopening.**  The acceptance inventory holds exact
   payload/authorization/audit, stable reservation, parent ledger, worker
   claim, R4-R6 profiles/manifests/child, final artifact/transcript/prompt,
   evaluator/resource evidence, identity/watermark records, bundle/job/owner/
   canonical records, corpus, and model manifests.  Later use re-verifies the
   payload and authorization at its recorded trusted start time, rejected R5
   audit, exact file inventory, reservation/ledger/claim, semantic profile
   chain, artifacts, evaluator evidence, parent resource reconciliation, job
   meaning, and disabled permissions.  A mandatory semantic callback prevents
   byte stability from laundering unsafe meaning.
4. **Parent evaluator/resource reconciliation.**  Closed validators cover
   exact-WAV-bound ASR/speech, pure-tone, speaker identity, collision corpus,
   named-person/originality, watermark ceiling, worker timing/telemetry, and a
   parent-owned Windows Job observation.  Parent finalization requires zero
   active descendants, quiescence before finalization, stdout/stderr hashes,
   parent wall time no shorter than worker total, and parent Job peaks that do
   not understate worker high-water memory.

The stable parent reservation intentionally lives under
`Data/voice/runtime/qwen3_tts_voice_forge_parent_reservations_v6/`, not inside
the pending attempt directory, so an atomic attempt rename cannot invalidate
the reservation path later bound by the ledger and worker claim.

## Static verification

Commands used `py -B` and stdlib-only fixtures.

- focused R6 suite: `26/26 PASS`;
- mandatory hostile probes: `14/14 PASS`;
- sealed payload reopen: `24/24 MATCH`;
- payload execution flags: both `false`;
- Python source compile from exact bytes: pass;
- strict duplicate-key rejection, path escape, stale authorization, and
  append-only collision: pass;
- hash-exact unsafe profile and ineligible `ai_type`: rejected;
- second worker claim and retry after early failure: rejected before loader;
- missing, forged, or WAV-unbound evaluator evidence: rejected;
- child-only telemetry, live descendant, premature finalization, and
  parent-understated peak memory: rejected;
- exact disabled binding: non-authorizing;
- R5 principal files and rejected R5 audit: unchanged;
- `git diff --check` on the R6 scope: pass.

The predecessor test suites were not freshly run because they create synthetic
WAV fixtures and this static repair prohibited audio creation.  Their sealed
historical evidence is preserved; the R6 suite independently rechecks the
principal R5 byte seals.

## Exact R6 seals

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `tools/qwen3_tts_voice_forge_r6_guards.py` | 63,032 | `8bf13ed57c3c19e729d586ed0196e8530de9c5d419b2b6c394a557fa6a05262a` |
| `tools/qwen3_tts_original_voice_forge_worker_v6.py` | 40,056 | `606734e3581ec73b8fa8b56e663f7f290102c43314bdbb0ab9d7aeff09d08f88` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v6.py` | 51,184 | `6ba4e5f6282d98b62466c38739eb2080d046f7a0bb021fbff0afd0c7053ec63b` |
| `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v6.py` | 23,709 | `8a8690c1d9a14d1311a157e3f56613b577441cb7c2de1e2d8e8e4ae3dd0c54d7` |
| `TemporaryAI/config/qwen3_tts_voice_forge_payload_manifest_v6.json` | 5,433 | `e32eb5dadfe80cc94cf1b57a98bf9220c8f7a5809d251b056d72fc02d2408a0e` |
| `TemporaryAI/config/qwen3_tts_voice_forge_external_acceptance_binding_v6.disabled.json` | 1,146 | `107fe73aa98e54f6f47c80fbfcbaa0aa1340f57c9bc6a78dd2c74f7b39f35133` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r6/attempt_01/HOSTILE_PROBES.py` | 2,409 | `3b2c476167fd6713c15431e9d110150f92e18d66c970fdfb3ea6d98f7e64fb06` |
| `RecoverySprint/continuation_20260810/temporaryai_qwen3_tts_voice_forge_r6/attempt_01/RESULT.json` | 758 | `93cd9a44ccb6354a9a4f176b109b8c8983fb21f0010098dedbd405ebc4820910` |

Rejected predecessor anchor:

- `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R5_INDEPENDENT_AUDIT_20260809.md`
  - 18,599 bytes
  - SHA-256 `82ea5a0a543fde40f7a1d05dc166798f98acbd9ae120c11ba8fb7f9ffbb5f43a`

## Rollback

Rollback is non-destructive: ignore all R6 paths, leave its payload and
disabled binding inert, and continue treating R5 as rejected.  Do not delete
R1-R5 or their audits.  No runtime/model/audio/person state changed, so there
is no runtime rollback to perform.
