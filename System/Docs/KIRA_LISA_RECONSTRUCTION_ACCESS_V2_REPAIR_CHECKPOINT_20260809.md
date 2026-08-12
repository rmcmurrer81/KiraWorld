# Kira + Lisa Reconstruction Access v2 Repair Checkpoint — 2026-08-09

Status: `STATIC_FAIL_CLOSED_CONTROLLER_IMPLEMENTED_PENDING_FRESH_INDEPENDENT_AUDIT`

## Boundary and provenance

This is an append-only v2 repair after:

- `System/Docs/KIRA_LISA_COLLEGE_EMOTION_HEALTH_REFLECTION_INDEPENDENT_HOSTILE_AUDIT_20260809.md`
- 17,750 bytes
- SHA-256 `922f8ef8935b4bd3b17e485d18646f6496cc6d08ace6acebab930bc8be8a30fb`

The rejected v1 checkpoint, audit, reflection policy/source, shared college-memory source, v1 reflection runtime, adult-health runtime, and conversation-loop source were not edited by this repair. Their verified retained hashes are:

| Preserved file | Bytes | SHA-256 |
|---|---:|---|
| `Data/memory_seeds/shared_kira_lisa_college_phase_001.draft.json` | 3,870 | `5249718a450122739e2cee0f7f7fb08892af258a659d91e6de46fb6383eacad7` |
| `Data/memory_reflection/kira_lisa_college_present_day_reflection_context_v1.json` | 6,120 | `35bda94e5138dcba939a215ffec46bf5825ba39688aa4d6c510ad66607b027a5` |
| `Core/kira_lisa_college_reflection_runtime.py` | 29,743 | `1189fb2c39f98692ec05032d020172939039b0d1bbef4c7ac16c79f834cd2a3f` |
| `Core/adult_health_curriculum_runtime.py` | 34,671 | `2cb4ea4f4c4c8b036d022843bc73da8416cea90e7ad1dd48c25e94980e2ae036` |
| `Core/conversation_loop.py` | 334,711 | `ad8719b495a9455ee1eb81290514c7d9854f58a069377d6b2282e1d6aa466eb4` |
| `System/Docs/KIRA_LISA_COLLEGE_EMOTION_HEALTH_REFLECTION_CHECKPOINT_20260809.md` | 9,221 | `3da85b564ca5afa70f7f816a1e078dd47ef5938bede2cf2971c9b98d3188a8ba` |
| `System/Docs/KIRA_LISA_COLLEGE_EMOTION_HEALTH_REFLECTION_INDEPENDENT_HOSTILE_AUDIT_20260809.md` | 17,750 | `922f8ef8935b4bd3b17e485d18646f6496cc6d08ace6acebab930bc8be8a30fb` |

No shared memory, canon, private reflection, participant decision, person classification, relationship state, or world state was written during verification.

## New exact-source controller

`Core/kira_lisa_reconstruction_access_v2.py` adds a memory-only authorization controller that pins:

- source memory ID `shared_kira_lisa_college_phase_001`;
- source file SHA-256 `5249718a450122739e2cee0f7f7fb08892af258a659d91e6de46fb6383eacad7`;
- reconstruction ID `memworld_shared_kira_lisa_college_phase_001`;
- exact ordered participant set `kira`, `lisa`;
- source status `draft`;
- privacy `private_shared`;
- sharing rule `requires_all_participant_consent`; and
- each exact person's existing pinned confirmed-adult classification/curriculum load path.

The controller accepts no custom source, policy, participant list, or classification mapping. Its public constructor always rejects; `load_pinned()` re-reads and validates the exact authorities. Subclass construction is rejected.

## Implemented authorization properties

### Participant route

- Kira and Lisa receive separate opaque, identity-based private-session capabilities only through the explicit authenticated control-plane entry.
- The capability contains no public nonce or copyable value fields.
- Direct construction, copying, equality-by-value, wrong-controller use, wrong-person use, wrong-session use, expiry, close, and clock rollback fail closed.
- A private ledger snapshot requires the live exact person's capability and returns only that person's records.
- Each person's reconstruction remains separate, source-labeled, confidence-labeled, subjective-recall-delta-labeled, append-only, and hash chained.
- Each ledger has a separately retained count/head seal; verification precedes every protected read and reconstruction binding.
- Appends require an exact person-selected control-plane `ReconstructionWriteOrigin`; a raw string, model mapping, or model reply cannot write the ledger.
- An own-perspective verbal permit may bind only selected record hashes from the speaker's own ledger. It is one-shot, short-lived, listener/session-bound, contains no private text in its receipt, and grants no visual replay, locked-zone access, full replay, or other-participant perspective.

### Nonparticipant route

- Every reconstruction-view scope, including `summary`, requires one and only one current response from each exact participant.
- Missing, duplicate, or extra participants fail closed.
- Each response is bound to the exact request ID, source-derived reconstruction ID/digest, viewer, viewer session, requested scope, approved scope/zones, visual setting, material-context digest, participant activation/session, issue time, and append-only event hash.
- A participant may approve only a scope that is a subset of the request. A `full_replay` response cannot upgrade a `one_time_full_replay` request.
- Both responses must converge on one exact common approved scope, exact common selected-zone set, and exact visual decision.
- `summary`, `emotional_meaning`, and `verbal_details_only` can never authorize visual, locked-zone, or full replay.
- Visual scopes require both exact participants' explicit visual approval.
- Denial or uncertainty never carries an approved scope and never produces a lease.
- Requests live at most 300 seconds. Participant sessions live at most 600 seconds. Own-perspective verbal permits live at most 120 seconds.
- One request may issue only one view lease, and every view lease can be consumed only once. Consumption is atomic under the controller lock.
- Revocation or later uncertainty immediately invalidates every lease for the exact request.
- Material-context change, reconstruction-ledger change, expiry, a stale digest, clock error, or clock rollback invalidates access.
- View capabilities reject clones and wrong controller, viewer, session, scope, zones, reconstruction digest, or material-context digest.
- Request, response, and view state are cross-checked against the original hash-chained audit events before authorization/consumption; a denial cannot be changed into approval by editing mutable state.

### Audit integrity and truth boundary

- Controller decisions and lifecycle events are append-only through the public API and SHA-256 chained.
- The audit chain has a separately retained count/head seal, detects record mutation and truncation, and is verified before protected operations.
- Private reflection text is never put in the audit. Only its digest and record digest are logged.
- The controller and its opaque capabilities reject serialization.
- The chain is in-memory integrity evidence for one process lifetime. No durable persistence, cross-process authenticity, body/world replay, or live owner/person acceptance is claimed.
- There is no model, voice, camera, media, Blender, body, world, playback, or action adapter in this controller.

## Generic validator hardening

`Tools/validate_memory_sharing_request.py` remains a structural validator, not an authorization authority. It now additionally rejects:

- duplicate required participant IDs;
- duplicate participant responses;
- missing exact declared responses;
- unexpected participant responses;
- approved scope above requested scope;
- approved scope above an individual participant's response scope;
- reusable full replay substituted for a one-time request;
- approved requests without timezone-aware resolution and expiry values;
- nonpositive or greater-than-15-minute approval windows;
- approved state after revocation; and
- approved one-time replay after consumption.

The exact Kira/Lisa controller does not trust the generic request's caller-supplied `required_approvals`; it derives the exact participants from the pinned source.

## Hostile coverage

The v2 focused tests cover:

- all seven scopes with Kira-only failure followed by exact Kira+Lisa success;
- duplicate, missing, and extra participant attacks;
- requested-summary to full-replay escalation;
- one participant limiting a one-time replay to summary;
- summary/verbal attempts to grant visual access;
- wrong viewer, source/reconstruction binding, reconstruction ID, viewer session, scope, zones, and material-context digest;
- expired participant capability and expired view lease;
- participant revocation and later uncertainty;
- a second lease for one request and second consumption of one lease;
- value-cloned participant/request/view capabilities;
- capability use with a different controller;
- material-context and reconstruction changes;
- clock rollback;
- audit mutation/truncation and private-ledger mutation/truncation;
- rewriting a recorded denial into an in-memory approval while retaining the denial event hash;
- cross-person private snapshot;
- forged/custom constructor, policy, source, and classification arguments;
- raw model strings/mappings attempting to grant permission; and
- a raw model-origin string attempting to write a private reconstruction.

## Verification

Focused v2 controller plus generic-validator suite:

```text
py -m unittest \
  Testing.test_kira_lisa_reconstruction_access_v2 \
  Testing.test_memory_sharing_request_validator -v

Ran 35 tests — OK
```

Combined v1 regression, generic validator, and v2 hostile suite:

```text
py -m unittest \
  Testing.test_kira_confirmed_adult_health_curriculum_runtime \
  Testing.test_generated_expert_adult_health_curriculum_runtime \
  Testing.test_qwen35_emotion_context_wiring \
  Testing.test_kira_lisa_college_emotion_health_reflection_runtime \
  Testing.test_kira_lisa_memory_backstory_index_truth \
  Testing.test_memory_reconstruction_world_validator \
  Testing.test_privacy_session_manager \
  Testing.test_memory_sharing_request_validator \
  Testing.test_kira_lisa_reconstruction_access_v2 -v

Ran 103 tests — OK
```

Python compilation passed for the v2 controller, the v2 hostile test, the generic validator, and its test.

## Changed-file inventory before this checkpoint

| Project-relative file | Bytes | SHA-256 |
|---|---:|---|
| `Core/kira_lisa_reconstruction_access_v2.py` | 73,354 | `b1801311cc3ccc55c9a9e33d39331391889a9010429f6e45d9cfff181030c3ed` |
| `Testing/test_kira_lisa_reconstruction_access_v2.py` | 39,986 | `f7a22d3a7bc7a59772f73fbe8dd4667f00cdfa3984e635670326f7084ddcc5ca` |
| `Tools/validate_memory_sharing_request.py` | 14,198 | `f48c10debc0eb05d4606e6c62701c2ad9bbc892e8fc5f32a30a0d553dc3c7835` |
| `Testing/test_memory_sharing_request_validator.py` | 9,311 | `e7c55617730ab2a2037d0514abe34a72f2f980e14162aed23a7128e80e55ece8` |

These hashes must be recomputed after any fresh-audit repair. The checkpoint's own external SHA-256 is intentionally reported after the file is closed rather than self-referenced.

## Remaining acceptance boundary

This work is ready for a fresh independent hostile static audit only. It is not connected to `ConversationLoop`, a reconstruction renderer, Memory Reconstruction World, a private-room UI, or any model adapter. No Kira or Lisa response or permission was generated. Test decisions existed only in isolated memory-only controller instances.

Do not describe this as live reconstruction acceptance, durable permission storage, live person authentication, replay quality, or owner approval. A later integration must preserve the exact opaque-capability boundary and must receive its participant activation only from an independently accepted private-person authentication/session layer.

## Rollback

No destructive rollback was performed. To remove only this v2 repair:

1. remove the new v2 controller, its focused test, and this v2 checkpoint;
2. restore `Tools/validate_memory_sharing_request.py` to the hostile-audit reviewed 8,602-byte file with SHA-256 `193732047ee7c82c2c4756d94a672e9e4e6531d86569db0810308ee42feb2233`;
3. restore the pre-v2 generic-validator test from the preceding workspace checkpoint; and
4. rerun the original 68-test v1 regression.

Do not alter the shared college-memory source, Kira or Lisa's memories, classification, adult curriculum, emotion state, body, voice, model, relationship, privacy state, or the preserved v1 checkpoint/audit as part of rollback.
