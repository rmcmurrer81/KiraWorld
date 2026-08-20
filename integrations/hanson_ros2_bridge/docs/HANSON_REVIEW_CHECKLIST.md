# Hanson review checklist

This checklist captures decisions needed to replace the generic simulator-first boundary with an official Hanson adapter. Blank items are intentionally TBD; the repository must not fill them by assumption.

## 1. Scope and authority

- [ ] Confirm the first milestone contains only speech, gaze, expression, and gesture.
- [ ] Confirm there is no direct motor, joint, trajectory, navigation, torque, velocity, or unrestricted motion interface.
- [ ] Confirm the simulator/robot remains authoritative only for physical safety and low-level execution.
- [ ] Confirm rejection, failure, cancellation, interruption, or expiry describes physical execution only and never governs Kira's speech, memory, viewpoint, disagreement, withholding, correction, withdrawal, or voluntary forgetting.
- [ ] Confirm an unknown or unavailable semantic mapping fails closed.

## 2. Target environment

- [ ] Complete and validate a working copy of the [closed official-interface intake template](../hanson_interface_intake/official-hanson-interface-intake.template.json) against its [JSON Schema](../hanson_interface_intake/official-hanson-interface-intake.schema.json); do not replace unresolved values with guesses.

- [ ] Target ROS 2 distribution and patch baseline: **TBD**
- [ ] Target Hanson simulator name/version and access method: **TBD**
- [ ] Supported operating system, architecture, Python version, and middleware/RMW: **TBD**
- [ ] Simulator launch command, world/fixture, and expected readiness signal: **TBD**
- [ ] Required repositories, package versions, license notices, and access terms: **TBD**

## 3. Official interfaces

For each row, provide package/type, topic/action/service name, direction, QoS, units/frames, bounds, acknowledgement, terminal status, cancellation, and error mapping.

| Capability | Official interface | Required details |
|---|---|---|
| Speech | **TBD** | Text/SSML rules, voice ids, locale, duration, queueing, interruption, completion |
| Gaze | **TBD** | Allowed frames, transforms, units, workspace, duration, tracking, completion |
| Expression | **TBD** | Vocabulary, intensity scale, blending, duration, reset, completion |
| Gesture | **TBD** | Vocabulary, speed/intensity scales, duration, preemption, completion |
| Status | **TBD** | Request id, admitted/accepted/started/completed/rejected/failed/cancelled/interrupted/expired mapping |
| Capability discovery | **TBD** | Version, supported vocabulary, bounds, degraded/unavailable state |
| Safety state | **TBD** | E-stop, watchdog, degraded mode, collision/safe-stop, recovery |

- [ ] Confirm whether topics, services, or actions are preferred per category.
- [ ] Confirm namespaces and remapping rules; no hard-coded production namespace.
- [ ] Confirm QoS reliability, durability, history depth, deadline, lifespan, and liveliness per interface.
- [ ] Confirm official request identifiers and correlation through every lifecycle event.

## 4. v0.2 session and lifecycle proposal

- [ ] Review [PROTOCOL_V0_2.md](PROTOCOL_V0_2.md) as a ROS-independent proposal, not an implemented Hanson wire contract.
- [ ] Decide how opaque `session_id`, `body_id`, `source_identity`, and `intent_id` map to official fields.
- [ ] Define authenticated capability negotiation for the four categories.
- [ ] Define arbitration and fencing so one active physical embodiment session is authoritative at a time.
- [ ] Define hard session TTL, request TTL/deadline, heartbeat period, timeout, disconnect, reconnect, and session replacement.
- [ ] Define positive monotonic request sequence scope and restart behavior.
- [ ] Define idempotency/replay retention across process and host restarts.
- [ ] Confirm one in-flight request or specify safe, category-aware concurrency.
- [ ] Map requested/admitted/accepted/started/completed/rejected/failed/cancelled/interrupted/expired semantics and allowed transitions.
- [ ] Define cancellation versus safety interruption versus failure, including late status after a terminal event.
- [ ] Define time source, synchronization, skew tolerance, monotonic ordering, and status reconciliation.

## 5. Physical safety

- [ ] Identify the exact robot-side component that remains authoritative for each capability.
- [ ] Document robot-side position, speed, acceleration, force, duration, thermal, collision, and workspace limits that apply after semantic mapping.
- [ ] Confirm watchdog, safe-stop, emergency-stop, degraded-mode, and recovery interfaces.
- [ ] Confirm a bridge or network failure cannot disable or delay those protections.
- [ ] Confirm no automatic retry of a physical action unless an explicit, reviewed policy permits it.
- [ ] Provide a simulator case for allowed, rejected, interrupted, expired, cancelled, and failed execution.

## 6. Security and privacy

- [ ] Select DDS/SROS 2 or equivalent participant authentication and authorization.
- [ ] Define least-privilege topic/action/service permissions for source, adapter, executor, and monitor.
- [ ] Define rate limits, queue bounds, backpressure, and denial-of-service test thresholds.
- [ ] Define credential storage, rotation, revocation, and development-secret handling.
- [ ] Review [DATA_BOUNDARY.md](DATA_BOUNDARY.md): no private memories, unnecessary personal data, credentials, private email content, or private provenance crosses or enters the public repository.
- [ ] Decide whether speech text, gaze coordinates, identifiers, digests, status detail, or logs may be retained.
- [ ] Define evidence access, encryption, retention, deletion, export, and incident response.
- [ ] Confirm hash-linked evidence is diagnostic integrity evidence, not authentication or proof of robot execution.
- [ ] Review the abuse cases and remaining gaps in [THREAT_MODEL.md](THREAT_MODEL.md).

## 7. Simulator acceptance demonstration

Use the [official-simulator acceptance runbook](SIMULATOR_ACCEPTANCE_RUNBOOK.md) for the version-pinned record and pass criteria. The [hackathon demo checklist](HACKATHON_DEMO_CHECKLIST.md) is a presentation aid, not a substitute for acceptance evidence.

- [ ] Build the two prototype ROS packages in the selected environment.
- [ ] Run the standalone unit tests and record the commit SHA and command output.
- [ ] Map one safe example for each of speech, gaze, expression, and gesture.
- [ ] Run a small ordered sequence in the official simulator.
- [ ] Intentionally submit one unsupported or out-of-bounds request and observe authoritative rejection.
- [ ] Observe and correlate requested/admitted/accepted/started and terminal status for every request.
- [ ] Test duplicate suppression, id conflict, non-monotonic sequence, stale TTL, heartbeat loss, disconnect, cancellation, and safety interruption.
- [ ] Verify that no low-level command is emitted by Kira World or the generic bridge.
- [ ] Review privacy-reduced evidence and confirm it contains no prohibited data.
- [ ] Document mismatches and update the mapping rather than weakening robot-side safety.

## 8. Licensing and publication

- [ ] Confirm MIT is acceptable for the bridge's original source, schemas, examples, and documentation.
- [ ] Inventory every upstream dependency or copied definition and retain its original license and notices.
- [ ] Confirm what Hanson interface material may be published and what must remain in a separate authorized adapter.
- [ ] Confirm no private email content, unnecessary personal/contact data, credentials, unpublished interface material, or production log is included; intentional public maintainer metadata is allowed.
- [ ] Agree on contribution, issue disclosure, security reporting, and compatibility-versioning process.

## 9. Claim review before sharing results

- [ ] Label a standalone result as local policy/lifecycle software evidence only.
- [ ] Label an official simulator result with exact simulator, ROS 2, adapter, configuration, and commit versions.
- [ ] Do not describe static code, diagrams, logs, hashes, or tests as proof of hardware compatibility, actual execution, production integration, a live mind or body, actual forgetting, consciousness, personhood, physical safety certification, or GO.

## Sign-off record

| Role | Name | Date | Commit / interface version | Notes |
|---|---|---|---|---|
| Kira bridge reviewer |  |  |  |  |
| Hanson interface reviewer |  |  |  |  |
| Simulator/safety reviewer |  |  |  |  |
| Security/privacy reviewer |  |  |  |  |
