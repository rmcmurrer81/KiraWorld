# Implementation status

## Prepared in this branch

- Typed ROS 2 intention messages for speech, gaze, expression, and gesture.
- A machine-readable execution-status message.
- A simulator-authority node that validates every request against a YAML safety policy.
- Fail-closed limits for stale requests, duration, confidence, speech size, gaze range, expression vocabulary, and gesture vocabulary.
- JSONL evidence logging for accepted and rejected requests.
- A demo publisher that sends four valid intentions and one intentionally unsupported gesture.
- A status monitor and launch file for the complete demonstration.
- A standalone pure-Python policy demonstration and unit-test suite that can be reviewed without ROS 2.
- Interface, safety, and future Hanson-mapping documentation.
- Required/future/stale timestamp checks, strict field/configuration validation, bounded message strings, source allowlisting, and duplicate/conflicting-ID protection.
- Relative/remappable ROS topic names and configurable launch namespace, topic prefix, policy path, and evidence path.
- Privacy-reduced SHA-256-linked evidence plus an independent verifier.
- A ROS-independent v0.2 session/lifecycle reference with capability negotiation, one in-flight action, monotonic sequence, idempotency, hard TTL, heartbeat/disconnect, and complete terminal states.
- Draft JSON Schemas and a deterministic full-lifecycle mock session demo.
- A closed, source-aware official-Hanson-interface intake schema/template plus bounded structural, Unicode-lexical, semantic-role, lifecycle/timer, QoS/depth, numeric, hierarchy, reference, evidence-time/SHA, promotion, and privacy-safe diagnostic validation; all official template values remain unresolved rather than guessed.
- A version-pinned official-simulator acceptance runbook and a simulator-only hackathon demo checklist covering four valid intentions, one rejection, and disconnect/interruption.

## Deliberately not implemented

- Direct joint, motor, actuator, walking, navigation, or unrestricted motion commands.
- Assumed Hanson Robotics topic names, coordinate frames, expression names, gesture names, or action interfaces.
- Automatic weakening or bypass of robot-side safety controls.
- Claims of compatibility with a production Hanson robot before official mapping and validation.
- A claimed or guessed Hanson message, topic, frame, vocabulary, simulator, or safety interface.
- Authentication, a distributed single-session lock, durable cross-restart replay state, production rate limiting, or an official executor.

## Validation still required

This branch has not yet been run against Hanson Robotics' current simulator, production hardware, or finalized official ROS 2 messages. The standalone tests cover local policy and lifecycle behavior only. The transport and packages must be built in the selected ROS 2 distribution, then the generic intention types must be mapped to official Hanson interfaces with Hanson-provided authentication, capabilities, limits, readiness, heartbeat, cancellation, and lifecycle semantics.

## Proposed first review sequence

1. Review the four high-level intention contracts.
2. Confirm the preferred ROS 2 distribution.
3. Confirm whether each category should use topics, services, or actions.
4. Confirm supported gaze frames, expression vocabulary, and gesture vocabulary.
5. Map the accepted semantic request into the official simulator interface.
6. Add separate accepted, queued, started, completed, failed, cancelled, and safety-interrupted statuses where supported.
7. Review the v0.2 session/lifecycle proposal, data boundary, and threat model.
8. Run the five-step demonstration and independently verify the evidence chain.
9. Map and run the same sequence in the official simulator, including authoritative terminal status.
