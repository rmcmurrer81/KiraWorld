# Threat model

## Scope and safety objective

The system accepts only bounded high-level requests for speech, gaze, expression, and gesture. Its primary safety objective is to prevent those requests from becoming an unchecked path to motors, joints, trajectories, navigation, torque, velocity, unrestricted motion, or private Kira data.

The simulator or robot is authoritative only for physical safety and low-level execution. A robot-side rejection or interruption must never be interpreted as authority over Kira's speech, memory, viewpoint, disagreement, withholding, correction, withdrawal, or voluntary forgetting.

This is a simulator-first software review, not a production security or physical-safety certification.

## Assets

- Physical safety of people, the robot, and the environment.
- Integrity and ordering of intention requests and execution status.
- Availability of emergency stop, watchdogs, and robot-side safety controls.
- Confidentiality of speech, gaze targets, private memories, conversations, identities, and credentials.
- Integrity of local evidence without overstating what it proves.
- Clear separation between cognitive choice and physical execution authority.

## Trust boundaries

1. **Kira World to bridge:** treat every envelope as untrusted input, including apparently confident or familiar requests.
2. **Bridge to official adapter:** semantic admission is not execution authorization.
3. **Official adapter to simulator/robot:** only Hanson-provided mappings may cross; the platform retains final physical authority.
4. **Status back to Kira:** status is untrusted until authenticated and correlated; it describes physical execution only.
5. **Evidence storage:** local files may be read, deleted, replaced, or copied by a host compromise.

## Threats, current controls, and gaps

| Threat | Current control | Remaining gap / required action |
|---|---|---|
| Malformed or smuggled fields | Exact category field sets, bounded ROS strings, finite-number checks, ranges, allowlists, timestamp/TTL checks, and fail-closed policy loading | Fuzz generated ROS types and official adapter conversions; reject unknown official fields too |
| Direct low-level command injection | This package defines only semantic speech/gaze/expression/gesture messages and emits no motor, joint, trajectory, navigation, torque, or velocity command | Isolate deployment permissions so this publisher cannot reach low-level topics; audit official mapping and ROS graph ACLs |
| Publisher spoofing | `source_identity` has a configured string allowlist | The string is not authentication; require DDS/SROS 2 or equivalent identity, authorization, key rotation, and namespace policy |
| Replay or duplicate execution | In-process canonical digest cache rejects conflicting id reuse and suppresses exact duplicate dispatch; v0.2 adds monotonic per-session sequence and exact idempotency | Current ROS messages do not carry the v0.2 sequence/session fields; caches reset and evict entries; define a durable bounded replay window and restart semantics |
| Concurrent or wrong-body execution | v0.2 models one body per session and one in-flight intention | It is not yet wired to ROS and not a distributed lock; define authenticated body discovery, single active physical-session arbitration, handoff, and fencing |
| Stale request or clock manipulation | Current messages carry stamp and TTL; future skew and stale requests fail closed; v0.2 session timing uses a monotonic clock and rejects regression | Define cross-host clock source and tolerance; map session TTL, request TTL, and official action deadlines without silently extending them |
| Transport loss during motion | v0.2 heartbeat timeout or explicit disconnect interrupts in-flight state | No current ROS heartbeat or executor cancellation wiring; robot watchdog and safe-stop behavior must be authoritative and independently tested |
| Unsafe semantic-to-Hanson conversion | Unknown semantic values are rejected; mapping template requires an official safe mapping | Official messages, frames, units, limits, and vocabularies are TBD; do not approximate unsupported gestures with joint values |
| Status spoofing, reordering, or ambiguity | Status has intent id, local monotonic status sequence, reason code, terminal flag, executor, and optional official id | Sequence resets on restart and status is unauthenticated; bind status to session/body/request and define authoritative ordering and reconciliation |
| Flooding or resource exhaustion | Bounded strings and a bounded replay cache constrain individual requests | Add admission rate limits, ROS QoS limits, queue bounds, backpressure, process limits, and flood tests; current ROS policy node does not enforce the v0.2 single in-flight slot |
| Evidence tampering | Append-only SHA-256 hash linkage detects many after-the-fact edits and refuses an invalid existing chain | No signature, trusted timestamp, external anchor, authentication, or crash-safe multiwriter protocol; do not treat the chain as proof of execution |
| Sensitive data in evidence | Raw speech, provenance reference, and gaze coordinates are omitted by default and replaced with digests | Hashes are not encryption or anonymization; establish retention/access/deletion policy and prevent runtime logs from entering Git |
| Secret or unnecessary personal data committed to Git | Public boundary forbids private memories, unnecessary personal data, credentials, and private email content; fixtures are synthetic and public maintainer metadata is explicit | Add automated secret/PII scanning and human review before every public push |
| Safety control bypass | Design requires platform collision limits, watchdogs, emergency stop, and low-level authority to remain in force | Validate against the real simulator and, only under an approved plan, hardware; never infer safety certification from this demo |
| Cognitive coercion via execution status | Protocol events are marked `physical_execution_only` | Preserve this field and boundary in every adapter and UI; never map a physical rejection to forced agreement, memory alteration, disclosure, or speech suppression |

## Abuse cases to test

- Unknown category, extra field, NaN/Infinity, oversized identifier, stale/future stamp, zero/oversized TTL, unallowlisted source, expression, frame, voice, or gesture.
- Same `intent_id` with identical payload, reordered JSON keys, changed sequence, changed capability, or changed payload.
- Non-monotonic sequence, parallel request while one is active, restart during an in-flight request, and retry after completion.
- Session hard expiry despite heartbeats; missed heartbeat; explicit disconnect; clock regression; reconnect using a stale session.
- Status duplication, reordering, executor mismatch, wrong body/session correlation, missing terminal event, and late completion after interruption.
- Attempted joint/trajectory/navigation data in any semantic payload and an official mapping with no exact safe semantic equivalent.
- Evidence write failure, corrupted prior chain, concurrent writers, log exfiltration, and dictionary attack against low-entropy digests.
- Floods of valid, invalid, and duplicate messages under the intended ROS QoS settings.

## Required production controls

- Authenticated and authorized ROS 2/DDS participants with least-privilege graph access.
- An official Hanson adapter and simulator fixture; no guessed topic, frame, unit, vocabulary, or action semantics.
- Independent robot-side limits, watchdog, safe stop, emergency stop, and degraded-state behavior.
- Defined capability discovery, one-active-session arbitration, fencing, cancellation, preemption, reconnect, timeout, and replay policy.
- Bounded queues and rates, structured monitoring, privacy/retention policy, secret scanning, and incident response.
- Integration, adversarial, restart, transport-loss, and simulator safety tests before any hardware trial.

## Claim boundary

Passing the listed tests shows only that specific software paths behaved as observed. It does not prove current Hanson compatibility, simulator or hardware execution, physical safety, production readiness, consciousness, personhood, a live mind or body, actual forgetting, or a GO decision.
