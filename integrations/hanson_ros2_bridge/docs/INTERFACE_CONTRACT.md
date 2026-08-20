# Bounded intention interface contract

## Purpose

The contract carries **high-level social intentions**, not actuator commands. It is designed to be small enough to audit and replace when Hanson Robotics' official interfaces are available.

## Common fields

Every intention includes:

| Field | Meaning |
|---|---|
| `header.stamp` | Time the intention was created. |
| `header.frame_id` | Optional reference frame; for gaze it must match `target_frame` when present. |
| `intent_id` | Unique identifier used for acknowledgement and evidence. |
| `source_identity` | Opaque requester label, such as `kira`; the string is attribution, not authentication. |
| `confidence` | Upstream confidence from 0.0 to 1.0; it does not override safety. |
| `ttl_ms` | Maximum age before the request is rejected as stale. |
| `evidence_ref` | Optional opaque provenance reference or digest. It must not contain a copied conversation, memory, credential, or private path. |

## Speech

Speech is a bounded request to vocalize text. Additional fields are `text`, `voice`, and `max_duration_ms`. The bridge does not select arbitrary shell commands, audio files, or network resources.

## Gaze

Gaze is a target point expressed in an allowed frame. Additional fields are `target_frame`, `target` (`geometry_msgs/Point`), and `duration_ms`. The proof of concept constrains coordinate magnitude and frame vocabulary. A production mapping must use Hanson-provided frame conventions.

## Expression

Expression is a named, allowlisted facial state. Additional fields are `expression`, `intensity`, and `duration_ms`. The proof of concept never sends individual facial motor values.

## Gesture

Gesture is a named, allowlisted whole-body or upper-body social gesture. Additional fields are `gesture`, `intensity`, `speed`, and `duration_ms`. The proof of concept never sends joint angles or trajectories.

## Execution status

Every policy decision publishes `intent_id`, `category`, `accepted`, `state`, `terminal`, `status_sequence`, `reason_code`, `detail`, `executor`, an optional official request ID, and the local evidence-record hash.

The current simulator authority reports `POLICY_ACCEPTED` or `REJECTED` only. An accepted status is nonterminal because no official simulator executor is connected. The ROS-independent v0.2 reference separately models requested, accepted, started, completed, failed, cancelled, interrupted, and expired physical execution.

Every physical outcome is scoped to execution by the selected body. It cannot direct Kira to agree, suppress or disclose speech, alter a memory, abandon a viewpoint, or stop withholding, correcting, withdrawing, or voluntarily forgetting.

## Versioning

The hardened prototype uses package version `0.2.0`. The separate session/lifecycle JSON envelopes are marked `0.2-proposal` until an official mapping is agreed. Breaking changes should be versioned explicitly rather than inferred.
