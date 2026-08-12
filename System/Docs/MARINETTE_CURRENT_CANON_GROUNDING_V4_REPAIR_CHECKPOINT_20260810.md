# Marinette current-canon V4 static repair checkpoint

Date boundary: 2026-08-10 America/New_York  
Candidate: `ladybug_marinette_expanded_smoke`  
Status: **FROZEN STATIC REPAIR — OWNER TEXT DENIED PENDING A DIFFERENT-AGENT HOSTILE AUDIT**

This checkpoint records an append-only repair of the blockers in
`MARINETTE_CURRENT_CANON_GROUNDING_V3_INDEPENDENT_HOSTILE_AUDIT_20260809.md`.
It is not a person activation, body approval, conversation acceptance, or
claim that Marinette spoke. V1, V2, and V3 versioned artifacts, checkpoints,
tests, and audits remain byte-for-byte unchanged.

## Runtime truth

- Marinette remains private, inactive, unassigned, unpublished, non-adult,
  and doll-safe.
- Adult anatomy, adult curriculum, body, world, life loop, movement, voice,
  sensory input, initiative, person-event transport, autonomy, memory writes,
  chat/history writes, and owner model text are denied by the V4 contract.
- No Qwen/Ollama request, GPU work, TTS, camera, microphone, media playback,
  Blender operation, body operation, world operation, or live person turn was
  run while making or verifying V4.
- The current gate reason is exactly
  `different_agent_v4_audit_required`.
- A closed CLI or shell gate returns a clearly system-owned diagnostic with
  `person_reply: null`/empty and performs no conversation, history, JSON,
  person-mind, memory, or runtime-state write.

## V3 rejection closure

| V3 blocker | V4 repair |
|---|---|
| CLI converted a closed-gate exception into a Marinette turn and persisted it | `run_chat()` now checks the strict V4 gate before run IDs, output paths, transcript creation, input, model calls, character repair, artifact handling, or person-turn finalization. It prints only `[System] Marinette owner text is unavailable: ...` and returns no person reply. |
| Shell converted a closed-gate exception into generic first-person text | The exact candidate is checked before the broad `try`/fallback route. `temporary_ai_reply()` raises `MarinetteV4OwnerTextBlocked`; `reply_for()` is also fail-closed for this ID. No generic first-person fallback remains reachable for Marinette V4. |
| `/api/chat` could write an owner turn/system block before the deny result | The strict V4 read-only gate is evaluated before the activation block, reply lock, benchmark work, `CHAT_LOG`, life-loop logging, state repair, or owner-turn append. The HTTP response is a system-owned 409 with an empty `ai_line` and no person reply. |
| Active-candidate recovery could repair and save shell state before the gate | Exact current/last Marinette V4 IDs are returned read-only; no `save_state()` or life-loop entry is made. |
| Shell injected world, avatar, body, movement, project, and history context | The strict branch bypasses the generic shell prompt completely and, after any future audit opens the gate, would call the contract route with `history=[]` and the exact raw owner string only. |
| Live-chat fallback generation could reinsert history | V4 creates exactly two messages: one manifest-authorized system message and one verbatim current owner turn. Both chat and generate request forms exclude prior history for this candidate. |
| Nonempty but irrelevant support was accepted | Evidence binds every exact claim ID to the exact supported claim statement. Claim ID, statement, source membership, source URL, host, authority/rank, excerpt bytes/hash, and allowed scope must all equal the code-bound catalog. |
| Coordinated status/scope/profile/review/identity/maturity drift was possible | Critical artifact key sets and all status, identity, maturity, review, activation, memory, prompt, voice, and runtime capability objects require exact equality to independently coded V4 values. Extra contradictory keys fail. |
| Unsupported Season 6 order/finale/local episode/name/history claims | The seven allowed claims and four required unknowns are exact ordered catalogs. Coordinated additions to policy, pack, review, registry, and evidence still fail. Mutable TF1 and all three local/planning sources remain no-claim. |
| Resolve/open alias, junction, hardlink, or TOCTOU weakness | V4 rejects non-exact relative paths, symlinks/reparse points, junction components, non-regular files, and any file with `st_nlink != 1`; opens once; verifies pre-open/path/handle/post-open identity; verifies the Windows final handle path; hashes bytes from that same descriptor; and rechecks file, directory components, and root after reading. |

## Exact frozen V4 files

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `Core/marinette_current_canon_contract_v4.py` | 53,766 | `04d105d8dc417baec6eb98743978cc8f576a91a0d34ecedfa96ece467268b477` |
| `Data/temporary_ai_source_packs/marinette_current_canon_contract_manifest_v4.json` | 5,833 | `6df7cd311fea8a009d6e18312008557c220e694d4eb3d56a749aa36d8b42c354` |
| `Data/temporary_ai_source_packs/marinette_current_canon_official_evidence_v4.json` | 5,346 | `6a7584fb3c6047034283ba61be4766cfceacfa520f2675308763167d30c0c777` |
| `Data/temporary_ai_source_packs/marinette_current_canon_source_registry_v4.json` | 4,543 | `0ff8910c4fea7f01a51d090dc0c3091d1761abaa7521468325c3f990fe19fba4` |
| `Data/temporary_ai_source_packs/marinette_current_canon_runtime_policy_v4.json` | 5,848 | `1e864488c1b8c2ac059ef16d7be255366db1d3ca45d4edab7b9fce77bef083e6` |
| `Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_current_canon_v4.json` | 5,023 | `b34b45d675bb523ecf55b876cb2a1ca73075e8b9f48eeab1ce5d343d877bb471` |
| `TemporaryAI/candidates/ladybug_marinette_expanded_smoke/source_grounding_review_v4.json` | 6,055 | `b9392b4b9c7a0b91a862678854301717e23ed11428b11324a77a27dad36448b7` |
| `TemporaryAI/candidates/ladybug_marinette_expanded_smoke/temporary_ai_profile_v4.json` | 3,677 | `48fdc9c418dfb5c7b43bfa31f18890cb7d4953e6e6406ba198413d68be733454` |
| `Testing/test_marinette_current_canon_grounding_v4.py` | 24,958 | `9d192168a7e6700f104e2bd4c9779ec7a85437a6b752a49e7a2a6e2fd917524a` |

The V4 manifest hash is pinned directly in the V4 Python contract. The V4
manifest in turn pins every V4 JSON artifact, every V3 versioned artifact,
V3 test/checkpoint/rejection audit, and the three exact local no-claim files.

## Narrow shared-runtime changes

These two shared files necessarily changed to close the real entry-point
bypasses. No broad personality, memory, body, voice, or world behavior was
changed by the Marinette repair. The whole-file shell hash also includes
unrelated append-only workspace improvements made concurrently by another
bounded workstream; the V4 tests re-ran against the integrated bytes below.

| Project-relative path | Bytes | SHA-256 after V4 |
|---|---:|---|
| `tools/temporary_ai_live_chat.py` | 101,717 | `c83c944d5f17bf7e353ab038beb34d367181616e975ddad34a01b959bb544bf1` |
| `tools/kira_world_shell_server.py` | 602,976 | `b86ef9a8a8599218668cd7f666bb2425a01deb486e3e5ea2ce667d5e49444569` |

The pre-V4/V3-audit reference hashes were respectively
`09b4a2d18df6aa2246de1e71b8e2e41ee0de058ba768b3a523f3327647579cca`
and `b2b0570cb5d9f524e3437cf706e15dc8c025dcd4c78236b15060846c087a3b6b`.

## Verification executed

All commands used `PYTHONDONTWRITEBYTECODE=1` where Python was involved.

1. `py -m py_compile Core/marinette_current_canon_contract_v4.py tools/temporary_ai_live_chat.py tools/kira_world_shell_server.py Testing/test_marinette_current_canon_grounding_v4.py`
   - PASS.
2. `py -m unittest Testing.test_marinette_current_canon_grounding_v4 -v`
   - PASS: 24 tests run, 23 passed, 1 skipped.
   - The skipped file-symlink probe requires Windows symlink privilege, which
     this process did not hold (`WinError 1314`). The independently exercised
     internal-target and outside-root Windows directory-junction probes passed,
     as did hardlink, traversal, stable-open, and changed-path snapshot probes.
   - The real `Handler.do_POST()` chat branch was invoked with a forged strict
     active state under mocks and returned the system-owned 409 before every
     patched log, JSON/state, candidate, safe-stop, or person-reply writer.
3. `py -m unittest Testing.test_avatar_body_policy_gate -v`
   - PASS: 11/11, including Marinette non-adult lineage/body denial.
4. Direct archival V3 contract check:
   `from Core import marinette_current_canon_contract_v3 as c; c.static_contract_readiness()`
   - PASS: `(True, [])`.
5. The V4 suite recomputed and matched every listed V1/V2/V3 preservation
   hash, every V4 manifest/member hash, and all three large local no-claim
   evidence hashes.

The mocked future-request tests performed no network or model call. They only
captured the request object to prove that history and shell context are absent.

## Independent-audit handoff

A different agent should treat all V4 files and the two shared-runtime hashes
above as frozen. Recompute them before inspection. Audit direct calls as well
as the CLI and `/api/chat`; verify no write occurs from current or recovered
strict state; repeat reparse/junction/hardlink/TOCTOU probes; mutate every
status/scope/relevance/claim binding; and inspect the exact mocked future
request. Do not open the model/text gate merely because the builder tests pass.

## Rollback instructions

Rollback is not currently requested. If it later becomes necessary:

1. preserve this checkpoint and all V4 files as rejected or superseded
   evidence rather than overwriting V1-V3;
2. reverse only the V4 import/delegation, early CLI deny, strict shell gate,
   strict `reply_for()` denial, and read-only strict recovery hunks in the two
   shared tools, using the pre-V4 hashes above as comparison evidence;
3. do not replace the shared files wholesale if unrelated later improvements
   exist; and
4. rerun the preserved V3 static contract check and the then-current route
   tests. V3 remains rejected for execution and must not be reopened by
   rollback.
