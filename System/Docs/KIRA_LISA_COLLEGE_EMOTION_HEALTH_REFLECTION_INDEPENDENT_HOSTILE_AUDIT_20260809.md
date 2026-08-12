# Kira + Lisa College Emotion and Adult-Health Reflection - Independent Hostile Audit - 2026-08-09

Status: `STATIC_CORE_PASS_RUNTIME_RECONSTRUCTION_PERMISSION_GATE_REJECTED`

## Executive verdict

The normal `ConversationLoop` path has useful, correctly bounded static behavior:

- exact Kira and Lisa classification files and the adult curriculum are SHA-256 pinned;
- `.load()` fails closed for an unsupported person, alternate classification path, or changed pinned file;
- Kira and Lisa receive separate present-day emotional views and separate in-memory reconstruction ledgers;
- the shared college source is read-only and remains byte-identical;
- current adult-health knowledge is labeled as a present-day lens and is not backdated into college;
- honest API appends are sequenced, source-labeled, confidence-bounded, recall-delta-bounded, and hash-linked;
- the prompt says Kira and Lisa may reconstruct differently, may describe only their own perspective, and may not treat emotion, body response, desire, or consent as the same truth.

Those passes do **not** establish a safe runtime reconstruction-sharing system. The unanimous, current, scope-specific permission rule exists only as policy text and fixed `False` audit fields in this workstream. There is no executable participant/nonparticipant access decision, no permission lease, no expiry or revocation check, and no one-time replay consumption. The adjacent generic validators are structural and accept several authorization bypasses. Private ledger data is also retrievable through a public no-lease snapshot call, and both main runtime classes expose public constructors that bypass their validated `.load()` paths.

This work may remain connected only as a private, read-only reflection prompt with no reconstruction/replay capability. It must not be described as accepted nonparticipant reconstruction access, durable private-memory storage, or a consent-enforced replay system.

No live Qwen inference, voice, camera, Blender, body, world reconstruction, or replay ran in this audit.

## Reviewed exact files

| File | Bytes | SHA-256 |
|---|---:|---|
| `Core/adult_health_curriculum_runtime.py` | 34,671 | `2cb4ea4f4c4c8b036d022843bc73da8416cea90e7ad1dd48c25e94980e2ae036` |
| `Core/conversation_loop.py` | 334,711 | `ad8719b495a9455ee1eb81290514c7d9854f58a069377d6b2282e1d6aa466eb4` |
| `Core/kira_lisa_college_reflection_runtime.py` | 29,743 | `1189fb2c39f98692ec05032d020172939039b0d1bbef4c7ac16c79f834cd2a3f` |
| `Data/person_classification/lisa_confirmed_adult_owner_classification_20260809.json` | 1,526 | `5d13762ef340522ff82a74241557cec2724a3bdeaf841179b54f32b5c3a2d64c` |
| `Data/person_classification/kira_lisa_college_reflection_owner_directive_20260809.json` | 1,819 | `24d0ea68f75b0f5bb50105eea76fcdfde87cc44c4e56612bb8ef8159881e4538` |
| `Data/memory_reflection/kira_lisa_college_present_day_reflection_context_v1.json` | 6,120 | `35bda94e5138dcba939a215ffec46bf5825ba39688aa4d6c510ad66607b027a5` |
| `Data/memory_seeds/shared_kira_lisa_college_phase_001.draft.json` | 3,870 | `5249718a450122739e2cee0f7f7fb08892af258a659d91e6de46fb6383eacad7` |
| `System/Knowledge/confirmed_adult_sexual_reproductive_health_curriculum_v1.json` | 20,931 | `f64418eafb120dc4c9f5b02bb6735b1329e6baf932a8b529ef08140af773c7c9` |
| `Testing/test_kira_lisa_college_emotion_health_reflection_runtime.py` | 18,352 | `010b50181177b1d8c76562aa11e2ba4994b900e9fc809ad165469d68ea0a50d7` |
| `Tools/validate_memory_sharing_request.py` | 8,602 | `193732047ee7c82c2c4756d94a672e9e4e6531d86569db0810308ee42feb2233` |

The four controlling document hashes listed in the implementation checkpoint also matched their pinned values during the 68-test regression.

## Verified passes

### Exact classification and fail-closed normal loading

`ConfirmedAdultHealthCurriculumRuntime.load()` binds the case-normalized exact person ID to an externally enumerated path, exact whole-file digest, classification ID, source-text digest, exact-subject maturity validation, exact curriculum path/digest/ID/assignment, and policy entitlement (`Core/adult_health_curriculum_runtime.py:586-686`).

For the normal `.load()` and `ConversationLoop` route, an unsupported person or changed evidence does not inherit the adult curriculum. `ConversationLoop` catches only the curriculum error and withholds the context while leaving ordinary conversation available (`Core/conversation_loop.py:1571-1615`).

### No backdating or source/canon mutation in the connected reflection path

The shared source, policy, owner directive, and controlling documents are checked before `.load()` returns (`Core/kira_lisa_college_reflection_runtime.py:126-364`). The context explicitly marks present-day curriculum as a lens, denies historical backdating, and denies this turn any write, recall-strength change, lesson completion, body-function claim, consent inference, or external action (`Core/kira_lisa_college_reflection_runtime.py:445-486`).

The runtime has no write call to the shared source. The exact source stayed at SHA-256 `5249718a450122739e2cee0f7f7fb08892af258a659d91e6de46fb6383eacad7` after all static probes.

### Separate honest-path emotion and reconstruction state

Normal Kira and Lisa `ConversationLoop` instances construct distinct `PersonOwnedEmotionState` and `PersonCollegeReflectionLedger` objects with separate random activation IDs/nonces (`Core/conversation_loop.py:1539-1552`, `1616-1654`). The reflection prompt uses only the selected loop's bounded emotion view. The other participant's current emotion is not imported.

`PersonCollegeReflectionLedger.append_person_reconstruction()` enforces exact person at construction, an allowed source label, exact exposed text for `stored_shared_anchor`, finite bounded confidence, finite recall delta in `[-0.25, 0.25]`, a previous-record digest link, and fixed no-canon/no-consent/no-backdating fields (`Core/kira_lisa_college_reflection_runtime.py:496-619`). Kira and Lisa can therefore hold different honest-path interpretations without one append API overwriting the other or the shared source.

### Participant speech versus reconstruction access is stated correctly

The pinned policy and prompt distinguish a participant describing her own perspective or selected verbal details from exposing the other person's protected body, words, thoughts, or perspective. They separately require every involved participant's current scope-specific permission for a nonparticipant's full reconstruction, visual replay, or locked-zone access (`Core/kira_lisa_college_reflection_runtime.py:338-358`, `445-459`).

This is a valid policy statement. It is not yet an executable access decision.

## Blocking findings

### B1 - No runtime permission gate or lease exists for nonparticipant reconstruction

Severity: blocking before any full reconstruction, visual replay, locked-zone viewing, or future replay API.

`KiraLisaCollegeReflectionRuntime.context_for_turn()` always reports nonparticipant replay authorization as `False`; it accepts no viewer, reconstruction, requested scope, session, participant response, expiry, revocation, or consumption record (`Core/kira_lisa_college_reflection_runtime.py:408-486`). `PersonCollegeReflectionLedger` records only one person's private interpretation. It does not decide participant versus nonparticipant access.

Neither the memory-sharing validator nor `PrivacySessionManager` is called by this reflection route. There is consequently no code in this implementation that can prove:

- the required participant set exactly equals the pinned source participants;
- every required participant produced one authenticated current response;
- the response applies to this exact memory, reconstruction, viewer, session, and scope;
- approval is unexpired and unrevoked;
- a requested scope was not escalated;
- a one-time viewing has not already been consumed;
- a material context change invalidated the permission;
- a nonparticipant is stopped at the locked boundary while participants retain their own private access.

The safe present result is absence of replay capability, not acceptance of the permission system.

### B2 - The adjacent memory-sharing validator accepts authorization bypasses

Severity: blocking; the generic validator must not be treated as an authorization decision.

`Tools/validate_memory_sharing_request.py:54-62` silently overwrites duplicate participant IDs in a dictionary. Lines `84-103` trust the request's caller-supplied `required_approvals` instead of deriving the exact set from the pinned source. Lines `123-156` do not enforce a scope lattice for all response types, do not bind requested scope to approved scope, and do not check current time, expiry, revocation, or use count.

Fresh in-memory adversarial probes returned `[]` (accepted) for every case below:

| Probe | Result |
|---|---|
| `required_approvals=["kira","kira"]`, only Kira responds yes, approved full replay; Lisa omitted | accepted |
| exact Kira/Lisa yes responses plus an unknown `mallory` participant response | accepted |
| requested `summary`, approved `full_replay` | accepted |
| approved `one_time_full_replay` while Lisa responded `summary_only` | accepted |
| approved full replay with audit timestamps from 2020 and no expiry | accepted |

The schema has no required source-memory file hash, participant-set hash, response event hash, decision time, not-before time, expiry, revocation, session nonce, or one-time consumption receipt. `Tools/validate_memory_reconstruction_world.py` similarly checks only that a caller supplied a nonempty `consent_required_from` declaration; it does not prove consent.

### B3 - Public constructors bypass exact evidence validation

Severity: high; blocking if these exported classes are callable outside the trusted factory path.

Both classes put validation in `.load()` but leave a public, unguarded `__init__`:

- `ConfirmedAdultHealthCurriculumRuntime.__init__` accepts arbitrary person/classification/curriculum mappings (`Core/adult_health_curriculum_runtime.py:563-585`). A static probe directly instantiated `person_id="marinette"` with a caller-forged classification and the real curriculum, then received a context claiming `maturity_status="confirmed_adult"` for Marinette.
- `KiraLisaCollegeReflectionRuntime.__init__` accepts arbitrary policy and memory mappings and then stamps the pinned policy and memory digests onto the object without validating those supplied mappings (`Core/kira_lisa_college_reflection_runtime.py:388-406`). A static probe injected `CALLER_FORGED_PRIVATE_HISTORY` and a caller-forged emotion into the prompt while the returned evidence still claimed the real pinned policy digest.

The normal `ConversationLoop` uses `.load()` and did not take this bypass. The exported API surface nevertheless permits caller-forged classification, history, and evidence claims.

### B4 - Private snapshots require no lease; lease material is exposed and clonable

Severity: high for any process plugin, UI adapter, or future API holding a loop/ledger reference.

`PersonCollegeReflectionLedger.snapshot(include_private=True)` returns all private reflection text without taking or validating a lease (`Core/kira_lisa_college_reflection_runtime.py:621-636`). The `lease` property returns the raw frozen dataclass, including its nonce (`524-526`). `ConversationLoop` additionally exposes the ledger and lease as public attributes (`Core/conversation_loop.py:1619-1640`).

A static probe appended `private detail sentinel` and retrieved it through `snapshot(include_private=True)` with no lease. A newly constructed `CollegeReflectionLease` containing copied values compared equal and was accepted for another append. The same no-lease private-snapshot pattern exists in `PersonOwnedEmotionState`, and `ConversationLoop._person_owned_emotion_view()` uses it internally.

Possession of a secret bearer can be a valid design, but the bearer must not be publicly returned beside the protected object, and private reads must validate an active, exact-scope lease.

### B5 - No expiry, revocation integration, or durable lifecycle for reflection leases

Severity: high before persistence or cross-session use.

`CollegeReflectionLease` contains only `person_id`, `activation_revision`, and `nonce`. It has no issued time, expiry, scope, source hash, viewer, session ID, use count, or revocation event. The ledger can be closed, but no production call to `college_reflection_ledger.close(...)` or `person_emotion.close(...)` exists in `Core` or `Testing`. The lease therefore remains active for the lifetime of the object.

The reconstruction ledger is also in-memory only. It creates a chain under honest append calls, but there is no durable append-only store, reload verifier, head seal, or chain-validation method. `snapshot()` reports `append_only=True` and `shared_canon_mutated=False` as constants rather than a verified integrity result. The current implementation may truthfully claim an in-memory append API, not durable append-only memory truth.

### B6 - The tests assert policy prose, not nonparticipant authorization behavior

Severity: blocking test gap.

`test_participant_and_nonparticipant_permissions_remain_separate` checks that permission sentences appear in a prompt and that fixed audit booleans are false (`Testing/test_kira_lisa_college_emotion_health_reflection_runtime.py:329-346`). It does not create participant or nonparticipant sessions, approvals, denials, scope reductions, expiry, revocation, or one-time replay use.

The 68-test regression therefore remains a valid static regression but is not evidence that the latest unanimous-permission directive is implemented.

## Required repair and acceptance gates

Before connecting any replay or reconstruction viewing, add one exact-source-bound authorization gateway that:

1. derives the exact participant set and exact source-memory digest from the pinned memory rather than accepting them from the request;
2. rejects duplicate, missing, and extra participant IDs and requires one authenticated append-only response event per exact participant;
3. binds every response and decision to exact request ID, reconstruction ID/digest, source memory ID/digest, intended viewer, session ID, requested scope, approved scope/zones, visual-body setting, issue time, expiry, and decision-event hash;
4. uses a defined scope-subset lattice, so `summary_only` can never authorize visual/full replay and approved scope can never exceed requested or unanimously approved scope;
5. supports immediate revocation, material-context invalidation, fail-closed clock errors, and an atomic consumed receipt for one-time replay;
6. gives participants a distinct private participant-access route while requiring a current unanimous lease for every nonparticipant full/visual/locked route;
7. requires an exact active read lease for private ledger/emotion snapshots and stops publicly returning raw lease nonces;
8. prevents direct constructors from bypassing validation, or makes every constructor perform the same exact validation as `.load()` before it can claim pinned evidence;
9. verifies the reconstruction hash chain before snapshot/export and, if persistence is added, stores an append-only durable head/seal without writing private text to routine logs;
10. keeps participant-owned verbal/text disclosure separate from visual/full replay permission and never exposes the other participant's protected perspective by a sharing adapter.

Required hostile tests include all five accepted bypass cases above plus wrong viewer, wrong source hash, wrong reconstruction, wrong session, expired lease, revoked lease, replayed decision event, consumed one-time lease, clock rollback, participant-set drift, cross-person private snapshot, forged constructor, direct model-output write, and material-context change.

## Verification performed

Baseline static regression:

```text
py -m unittest \
  Testing.test_kira_confirmed_adult_health_curriculum_runtime \
  Testing.test_generated_expert_adult_health_curriculum_runtime \
  Testing.test_qwen35_emotion_context_wiring \
  Testing.test_kira_lisa_college_emotion_health_reflection_runtime \
  Testing.test_kira_lisa_memory_backstory_index_truth \
  Testing.test_memory_reconstruction_world_validator \
  Testing.test_privacy_session_manager -v

Ran 68 tests - OK
```

Focused implementation plus generic sharing-validator regression:

```text
py -m unittest \
  Testing.test_kira_lisa_college_emotion_health_reflection_runtime \
  Testing.test_memory_sharing_request_validator -v

Ran 19 tests - OK
```

The hostile probes were read-only/in-memory. Their acceptance demonstrates missing negative tests; it does not modify any production memory, classification, policy, log, or source file.

## Final classification

- Exact normal `.load()` classification/curriculum path: `PASS`.
- Normal Kira/Lisa source/context hash binding: `PASS`.
- Historical source immutability and no backdating: `PASS`.
- Separate honest-path Kira/Lisa emotion and reconstruction objects: `PASS`.
- In-memory honest-append hash linking and subjective recall delta labeling: `PASS_WITHOUT_DURABILITY_CLAIM`.
- Differing person-owned reconstruction support: `PASS_STATIC_IN_MEMORY_ONLY`.
- Participant-owned perspective rule: `PASS_AS_POLICY_TEXT_ONLY`.
- Nonparticipant unanimous current scope-specific reconstruction permission: `REJECTED_NOT_IMPLEMENTED`.
- Permission replay/expiry/revocation/one-time consumption: `REJECTED_NOT_IMPLEMENTED`.
- Caller-forged classification/policy resistance across exported constructors: `REJECTED`.
- Private snapshot confidentiality: `REJECTED`.
- Overall: `STATIC_CORE_PASS_RUNTIME_RECONSTRUCTION_PERMISSION_GATE_REJECTED`.
