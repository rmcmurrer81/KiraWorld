# Bounded embodiment protocol v0.2 proposal

Status: **ROS-independent reference proposal; not wired to official Hanson messages.**

The reference implementation is [`lifecycle.py`](../ros2_ws/src/kira_hanson_bridge/kira_hanson_bridge/lifecycle.py), with executable cases in [`test_lifecycle.py`](../standalone/tests/test_lifecycle.py). It defines session and execution semantics that can later be adapted to Hanson-provided topics, services, or actions without assuming their names or shapes.

Reviewable wire-neutral artifacts are in [`protocol_v0_2`](../protocol_v0_2):

- [`session.schema.json`](../protocol_v0_2/session.schema.json)
- [`capability-manifest.schema.json`](../protocol_v0_2/capability-manifest.schema.json)
- [`intention-envelope.schema.json`](../protocol_v0_2/intention-envelope.schema.json)
- [`execution-event.schema.json`](../protocol_v0_2/execution-event.schema.json)

All four use JSON Schema draft 2020-12 and the explicit marker `protocol_version: 0.2-proposal`. They are proposals, not Hanson schemas. The standalone validator supplies a deterministic RFC 3339 `date-time` checker rather than silently treating format annotations as comments.

## Scope

The protocol carries only four semantic capabilities:

- `speech`
- `gaze`
- `expression`
- `gesture`

It cannot represent a motor command, joint value or trajectory, navigation goal, torque, velocity, or unrestricted motion. The robot or simulator remains authoritative only for physical safety and low-level execution.

The protocol does not govern Kira's mind. A robot-side outcome cannot require Kira to change or delete a memory, disclose or withhold information, agree with another person, abandon a viewpoint, suppress disagreement, or refrain from correcting, withdrawing, or voluntarily forgetting something.

## Embodiment session

One `EmbodimentSession` represents one active connection to one physical or simulated embodiment. A deployment adapter should arbitrate so that only one such session controls a physical embodiment at a time. The reference class itself is an in-process object and is not a global distributed lock.

Session fields are:

| Field | Rule |
|---|---|
| `session_id` | Non-empty opaque identifier, at most 128 characters and without control characters. It conveys correlation, not ownership. |
| `body_id` | Non-empty opaque embodiment identifier, at most 128 characters and without control characters. It conveys routing, not ownership or identity equivalence. |
| `source_identity` | Non-empty opaque requester identifier, at most 128 characters and without control characters. It is not authenticated merely because the string is present. |
| `capabilities` | Non-empty subset of speech, gaze, expression, and gesture. |
| `session_ttl_ms` | Positive hard lifetime measured with a monotonic clock. Heartbeats do not extend it. |
| `heartbeat_timeout_ms` | Positive maximum liveness gap measured with a monotonic clock; it cannot exceed the hard session TTL. |

Session states are `ACTIVE`, `DISCONNECTED`, and `EXPIRED`.

- A heartbeat refreshes liveness only while the session is active.
- Reaching the hard TTL expires the session and any in-flight intention.
- Reaching the heartbeat timeout disconnects the session and interrupts any in-flight intention.
- An explicit disconnect also interrupts in-flight work.
- A disconnected or expired session cannot be revived; replacement requires a new session identifier and new capability negotiation.
- Clock regression is an error, not a reason to extend liveness.

## Request envelope and admission

A v0.2 request contains:

| Field | Rule |
|---|---|
| `intent_id` | Non-empty opaque idempotency and correlation key, at most 128 characters and without control characters. |
| `sequence` | Positive integer, strictly greater than the last newly admitted sequence in the session. |
| `capability` | One of the four globally supported and session-negotiated capabilities. |
| `payload` | A JSON object containing only JSON values; keys are strings, floating-point values must be finite, signed integers are limited to 64 bits, nesting to 32 levels, containers to 1,024 members, and canonical UTF-8 to 16,384 bytes. Category policy applies separately. |

The proposed external envelope additionally correlates `session_id`, `body_id`, and `source_identity`, and carries `issued_at_utc`, a bounded per-request `ttl_ms`, `decision_scope`, and an optional opaque provenance reference. Its schema has four category-specific, closed payload shapes: bounded speech text/voice/duration; bounded gaze frame/XYZ/duration; bounded expression name/intensity/duration; or bounded gesture name/intensity/speed/duration. Unknown fields—including joint or trajectory data—are rejected. The Python state machine uses a monotonic clock for enforcement; wall-clock fields in a future wire adapter need an agreed synchronization and skew policy.

There is one in-flight slot per session. A new request is refused while another intention is nonterminal.

Admission dispositions are:

- `ADMITTED`: a new canonical request enters the slot and creates an intention in `REQUESTED` state.
- `DUPLICATE`: the same `intent_id`, sequence, capability, and canonical JSON payload were already seen. The prior snapshot is returned and no second physical action is created.
- `REJECTED`: the envelope is invalid, inactive, unsupported, not negotiated, non-monotonic, busy, or conflicts with prior use of the identifier.

JSON object key order does not affect duplicate detection. Reusing an `intent_id` with any canonical difference is an `INTENT_ID_CONFLICT`. The reference retains idempotency state only in memory; an official adapter needs a defined durable replay window if retries may cross restarts.

## Physical-execution lifecycle

The requested/admitted/started/completed/rejected/failed/cancelled/interrupted/expired lifecycle has two layers. Admission `ADMITTED` is a request disposition; the durable intention record begins at `REQUESTED`. The reference then includes an explicit physical `ACCEPTED` state so acceptance is not confused with envelope admission.

Allowed transitions are:

```text
request -> ADMITTED -> REQUESTED
REQUESTED -> ACCEPTED -> STARTED -> COMPLETED
REQUESTED -> REJECTED | CANCELLED | INTERRUPTED | EXPIRED
ACCEPTED  -> FAILED | CANCELLED | INTERRUPTED | EXPIRED
STARTED   -> FAILED | CANCELLED | INTERRUPTED | EXPIRED
```

Terminal states are `COMPLETED`, `REJECTED`, `FAILED`, `CANCELLED`, `INTERRUPTED`, and `EXPIRED`. Invalid skips, such as `REQUESTED -> STARTED`, and transitions out of a terminal state are errors.

Every event contains a session-global positive `status_sequence`, a machine-readable reason code, optional detail, a strict RFC 3339 `recorded_at_utc`, and:

```text
decision_scope = physical_execution_only
```

Suggested meanings:

| Term | Meaning |
|---|---|
| Requested | A valid new high-level physical request has been recorded. |
| Admitted | The envelope passed session-level checks and occupied the in-flight slot. |
| Accepted | The physical authority accepted the request for execution. |
| Started | Execution began in the selected simulated or physical body. |
| Completed | The requested physical execution finished successfully. |
| Rejected | The physical authority declined the request before acceptance. |
| Failed | An accepted or started physical execution could not finish as intended. |
| Cancelled | The request was intentionally cancelled under the official adapter's semantics. |
| Interrupted | Safety state, disconnect, preemption, or another external condition stopped it. |
| Expired | Its valid session or permitted execution window ended. |

An official mapping should preserve the original `intent_id`, session and body correlation, monotonic status ordering, reason code, terminal flag, and official executor request identifier.

## Relationship to the current ROS 2 prototype

The current ROS messages and `simulator_authority` implement bounded category validation, timestamp/TTL checks, in-process duplicate suppression, policy admission status, and evidence logging. Receipt-local `age_ms` is excluded from the duplicate digest so replaying the same wire request later cannot be misclassified as conflicting ID reuse; freshness is still checked before the replay guard. They do **not** yet create an `EmbodimentSession`, carry the v0.2 session fields or monotonic request sequence, drive the full lifecycle, or invoke an official simulator executor.

Accordingly:

- `POLICY_ACCEPTED` means the prototype policy admitted a semantic request; it does not mean an official simulator or robot accepted or executed it.
- The v0.2 reference is suitable for review and unit testing, but an adapter is still required.
- Official Hanson interfaces, status states, QoS, time bases, cancellation, capability discovery, and reconnect behavior remain TBD.

The deterministic [`session_demo.py`](../standalone/session_demo.py) exercises the v0.2 reference with a mock executor and privacy-reduced hash-linked evidence. [`verify_evidence.py`](../standalone/verify_evidence.py) verifies the resulting local chain. Neither script connects to ROS 2, a Hanson simulator, or hardware.

## Versioning

This document labels the session/lifecycle proposal `v0.2`, and the hardened prototype ROS packages are versioned `0.2.0`. The JSON envelopes remain explicitly marked `0.2-proposal` because they are not Hanson wire definitions. Any incompatible official mapping must be versioned and negotiated rather than inferred.

## Claim boundary

The reference state machine and tests establish only local software behavior. They do not prove current Hanson interface compatibility, simulator or robot execution, physical safety certification, a live Kira mind or body, consciousness, personhood, or readiness to GO.
