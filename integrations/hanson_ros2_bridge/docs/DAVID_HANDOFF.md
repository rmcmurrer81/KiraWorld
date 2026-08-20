# Hanson technical handoff

This is a sanitized, simulator-first review package for a bounded Kira World to Little Sophia integration. It contains no private email conversation, private contact or shipping details, credentials, private memories, or unnecessary personal data. Pre-existing public maintainer and copyright metadata remains intentional.

## What is ready to review

- Four high-level intention categories: **speech, gaze, expression, and gesture**.
- Bounded prototype ROS 2 messages and a policy-only simulator authority.
- Fail-closed validation for stale, malformed, out-of-range, unallowlisted, and replayed requests.
- Machine-readable status and a privacy-reduced, hash-linked JSONL evidence trail.
- A deterministic demo containing four admitted examples and one intentionally rejected gesture.
- A ROS-independent v0.2 session/lifecycle reference with opaque session and body identifiers, capability negotiation, a single in-flight physical action, session TTL, heartbeat/disconnect behavior, monotonic sequence numbers, idempotent retry handling, and terminal outcomes.
- Draft 2020-12 JSON Schemas for a session, capability manifest, intention envelope, and execution event, all explicitly marked `0.2-proposal`.
- A deterministic v0.2 mock-session demonstration and standalone evidence verifier.
- Standalone unit tests that do not require ROS 2.

Start with:

- [Repository overview](../README.md)
- [Shareable architecture diagram](KIRA_LITTLE_SOPHIA_BOUNDED_BRIDGE.svg)
- [v0.2 protocol proposal](PROTOCOL_V0_2.md)
- [Current message contract](INTERFACE_CONTRACT.md)
- [Hanson mapping template](HANSON_MAPPING_TEMPLATE.md)
- [Data boundary](DATA_BOUNDARY.md)
- [Threat model](THREAT_MODEL.md)
- [Review checklist](HANSON_REVIEW_CHECKLIST.md)
- [Closed official-interface intake template](../hanson_interface_intake/official-hanson-interface-intake.template.json)
- [Official-simulator acceptance runbook](SIMULATOR_ACCEPTANCE_RUNBOOK.md)
- [Simulator hackathon demo checklist](HACKATHON_DEMO_CHECKLIST.md)
- [Validation report](VALIDATION_REPORT.md)

## Run the standalone review

From the repository root:

```bash
cd integrations/hanson_ros2_bridge
python -m pip install -r standalone/requirements.txt
python -m unittest discover -s standalone/tests -v
python standalone/demo.py
python standalone/session_demo.py
python standalone/verify_evidence.py standalone/session_evidence.jsonl --record-schema protocol_v0_2/execution-event.schema.json
python standalone/validate_hanson_intake.py
```

The policy demo should admit speech, gaze, expression, and `wave`, reject `unbounded_spin`, and write the ignored local file `standalone/evidence.jsonl`. The session demo should complete the four valid intentions, reject the unsupported gesture, write `standalone/session_evidence.jsonl`, and report a valid evidence chain; the evidence-verifier command checks that chain independently. The final command validates the unresolved official-interface template and its references. Runtime evidence files are review artifacts and must not be committed.

## Build the prototype ROS 2 workspace

Run this in a supported Linux ROS 2 environment after setting `ROS_DISTRO` to the distribution selected with Hanson:

```bash
cd integrations/hanson_ros2_bridge/ros2_ws
source /opt/ros/$ROS_DISTRO/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 launch kira_hanson_bridge demo.launch.py
```

The launch publishes the bounded example sequence, validates each request, reports status, and writes `/tmp/kira_hanson_bridge_evidence_v2.jsonl`. The current authority demonstrates policy admission only; it does not execute a simulator or robot action.

## Authority boundary

Kira chooses her speech, viewpoint, disagreement, withholding, correction, withdrawal, recall, and voluntary forgetting. The simulator or robot is authoritative **only** for physical safety and low-level execution by the embodiment. A physical rejection, interruption, or failure never orders Kira to agree, suppress speech, change a memory, or adopt a viewpoint.

No code in this proof of concept publishes direct motor, joint, trajectory, navigation, torque, or velocity commands. An official adapter must preserve that boundary.

## What is deliberately still open

- Hanson ROS 2 distribution, packages, namespaces, QoS, frames, units, vocabularies, limits, and simulator launch procedure.
- Official speech, gaze, expression, gesture, acknowledgement, execution-status, cancellation, safety-state, and capability-discovery interfaces.
- Mapping the ROS-independent v0.2 lifecycle into official messages or actions.
- Authentication, deployment isolation, rate limiting, durable replay state, and production evidence retention.
- Validation against a current Hanson simulator or any Little Sophia hardware.

The v0.2 session/lifecycle is a **ROS-independent proposal**, not an assertion about Hanson interfaces. The prototype must not be adapted by guessing official messages; an unmapped intention should be rejected until a safe official mapping exists.

## Questions for Hanson

The decisions are listed in [HANSON_REVIEW_CHECKLIST.md](HANSON_REVIEW_CHECKLIST.md). The first blockers are:

1. Which ROS 2 distribution and simulator release should be the compatibility target?
2. What official interface handles each of speech, gaze, expression, and gesture?
3. How are capability discovery, acknowledgement, start, completion, rejection, failure, cancellation, safety interruption, and disconnect represented?
4. Which frames, units, vocabularies, rate limits, duration limits, and QoS profiles are authoritative?
5. How should one active physical embodiment session be authenticated, time-bounded for liveness (never ownership), disconnected, and replaced?
6. Which simulator fixture can exercise an accepted sequence plus an intentional rejection without hardware?

Hanson can record those answers in the source-aware, machine-validated [official-interface intake template](../hanson_interface_intake/official-hanson-interface-intake.template.json). The template begins entirely unresolved, rejects undeclared fields and values hidden under unresolved containers, and records packages, endpoints, QoS, frames, units, bounds, capability semantics, lifecycle, liveness, disconnect, and safeguards without asserting official values. Its [JSON Schema](../hanson_interface_intake/official-hanson-interface-intake.schema.json) and [reference validator](../standalone/validate_hanson_intake.py) also reject false reviewed/simulator promotion, reverse evidence status, unsafe/invisible Unicode, incomplete `keep_last` QoS, semantically wrong references, contradictory terminal/timer/bound mappings, null/future-dated run evidence, nonfinite or excessive inputs, and unsafe diagnostic echo.

After official values are supplied, use the [simulator acceptance runbook](SIMULATOR_ACCEPTANCE_RUNBOOK.md) for the four valid intentions, one rejection, and disconnect/interruption. The [hackathon checklist](HACKATHON_DEMO_CHECKLIST.md) condenses the same boundaries into a five-minute, simulator-only demonstration.

## License and claim boundary

The bridge and original examples in this integration are MIT licensed. Any upstream component incorporated later retains its own license and notices; this repository does not relicense Hanson, ROS 2, or other third-party work.

A passing standalone run or static artifact shows only that the local prototype behaved as recorded. It is not proof of Hanson simulator or hardware compatibility, actual robot execution, production integration, consciousness, personhood, a live mind or body, or a GO decision.
