# Official-simulator acceptance runbook

This runbook turns a Hanson-supplied interface mapping into repeatable simulator evidence. It is deliberately **not executable as written until every required official value is sourced and validated**. It does not authorize hardware use, production deployment, or a GO decision.

## Scope

The acceptance target is one named commit, one named ROS 2 environment, and one named official Hanson simulator release. It exercises only four bounded high-level intention categories:

- speech;
- gaze;
- expression; and
- gesture.

The generic bridge must not publish motor, joint, trajectory, navigation, torque, velocity, or arbitrary command payloads. The simulator remains authoritative for physical safety, low-level execution, rejection, and interruption. Physical status never governs Kira's speech, memory, viewpoint, disagreement, withholding, correction, withdrawal, or voluntary forgetting.

## Hard prerequisites

Stop before launching the official simulator unless all of these are true:

- [ ] The test is confined to an isolated simulator fixture; no physical robot or actuator endpoint is reachable.
- [ ] The exact repository commit SHA and clean/dirty worktree state are recorded.
- [ ] A working copy of [`official-hanson-interface-intake.template.json`](../hanson_interface_intake/official-hanson-interface-intake.template.json) has been completed from public or explicitly authorized official sources.
- [ ] The intake names the exact ROS 2 distribution and patch, simulator/version, operating system, architecture, RMW, packages, endpoints, message/action/service types, QoS, frames, units, limits, vocabularies, lifecycle, liveness, disconnect, and safety semantics.
- [ ] Every `confirmed_official` or `not_applicable_confirmed` value cites an `official_sources` entry cleared for repository publication.
- [ ] Private email content, credentials, private memory, unnecessary personal data, production configuration, and unreleased material remain outside the intake and evidence.
- [ ] The official adapter maps only semantic intentions to official interfaces and does not add a direct low-level command path.
- [ ] The official simulator supplies a safe link-loss or heartbeat-loss test fixture and an authoritative readiness signal.
- [ ] Evidence retention and access are agreed before the run.

Validate the completed intake from `integrations/hanson_ros2_bridge`:

```bash
python standalone/validate_hanson_intake.py path/to/completed-intake.json --require-official
```

`valid=true` is a structural and reference-integrity result. It does not prove that supplied values are truthful, current, safe, or compatible; a Hanson reviewer must still confirm them.

The strict gate requires named, sourced environment/simulator values; nonempty official package, interface, frame, unit, limit, capability, lifecycle, session/liveness, and safeguard mappings; semantically correct interface roles and QoS channels; consistent terminal states and bounds; and `0 < heartbeat period <= heartbeat timeout <= session TTL`. A final reviewed status activates this gate automatically. `simulator_validated_for_named_versions` additionally requires pass evidence, and pass evidence cannot appear under any other intake status.

## Freeze the run identity

Create an acceptance record before execution and fill these values without abbreviating versions:

| Field | Recorded value |
|---|---|
| UTC start |  |
| Repository commit SHA |  |
| Worktree clean/dirty plus diff reference |  |
| Completed intake SHA-256 |  |
| ROS 2 distribution and patch |  |
| RMW implementation |  |
| Simulator product/version |  |
| Fixture/world |  |
| Official package versions/commits |  |
| Adapter version/commit |  |
| Policy/configuration SHA-256 |  |
| Evidence destination and retention rule |  |
| Hanson simulator reviewer |  |

Do not reuse results after any recorded component, interface definition, policy, mapping, or fixture changes.

## Preflight

1. Run the local review suite:

   ```bash
   python -m unittest discover -s standalone/tests -v
   python standalone/demo.py
   python standalone/session_demo.py
   python standalone/verify_evidence.py standalone/session_evidence.jsonl --record-schema protocol_v0_2/execution-event.schema.json
   ```

2. Build the two prototype packages in the exact ROS 2 environment named by the intake. Record the complete build command and result. Do not substitute a different distribution to make the build pass.
3. Start only the official simulator and fixture named by the intake, using its structured package/file/arguments. Do not invent a launch command.
4. Wait for the official readiness signal and capability discovery result. Treat absence, disagreement, degraded status, or incomplete discovery as a stop condition.
5. Confirm endpoint graph, type hashes/definitions, directions, QoS, frames, units, and namespaces against the completed intake.
6. Confirm the adapter cannot resolve or publish to physical hardware endpoints.
7. Start privacy-reduced evidence capture and official simulator status capture. Record clocks and the agreed correlation fields.
8. Select one valid, visibly distinguishable input for each capability from the **confirmed official** vocabulary and bounds. Do not invent or approximate a gesture, expression, frame, unit, or physical limit.
9. Select one rejection input that is definitely outside a confirmed vocabulary or bound and is safe to submit to the bounded policy. Record why it is invalid before running it.

## Acceptance sequence

Use fresh opaque session and intention identifiers. Run one intention at a time unless the official intake explicitly confirms safe concurrency.

| Case | Input selection | Required observation |
|---|---|---|
| `SPEECH_VALID` | Confirmed safe speech input within text, voice, locale, duration, and queue bounds | Correlated admission, official acceptance, start if represented, terminal completion, and no unrelated capability activation |
| `GAZE_VALID` | Confirmed reachable target in a confirmed frame and unit | Correct frame/unit interpretation, correlated lifecycle, terminal completion, and simulator-enforced workspace limits |
| `EXPRESSION_VALID` | Confirmed expression name, intensity scale, and duration | Exact semantic mapping, correlated lifecycle, terminal completion, and confirmed reset/blend behavior |
| `GESTURE_VALID` | Confirmed gesture name, scale, and duration | Exact semantic mapping, correlated lifecycle, terminal completion, and no invented joint-level approximation |
| `INTENT_REJECTED` | One pre-recorded unsupported or out-of-bounds semantic request | Terminal rejection with stable reason; no official physical dispatch, start, or completion |
| `DISCONNECT_INTERRUPTED` | A confirmed safe duration-bearing intention, followed only after official start by the simulator's approved link/heartbeat-loss fixture | Authoritative disconnect detection, bounded interruption/safe outcome, terminal status mapped to `INTERRUPTED`, and no silent retry after reconnect |

For every case, capture:

- local `session_id`, `intent_id`, and monotonic request sequence;
- the official request/correlation identifier, when provided;
- request, admission, official acceptance, start, and terminal timestamps;
- every raw official status value plus its reviewed local mapping;
- policy and simulator reason codes;
- whether any official dispatch occurred;
- evidence record hashes and the final chain hash; and
- screenshots or recordings only when their retention and privacy boundary is approved.

If the official simulator has no distinct `INTERRUPTED` state, preserve its exact outcome and mark the proposed mapping unresolved. Do not silently relabel `FAILED`, `CANCELLED`, timeout, or lost status as interruption to obtain a pass.

## Disconnect/interruption procedure

1. Confirm that the selected action is safe in the isolated fixture and long enough to observe `STARTED` before fault injection.
2. Start the intention and wait for the official correlated start signal.
3. Trigger only the simulator's documented link-loss or heartbeat-loss mechanism. Do not terminate unrelated host services or disable robot-side safeguards.
4. Observe the authoritative physical outcome and watchdog/safety-state evidence.
5. Restore connectivity by the documented simulator procedure.
6. Confirm the old request is not retried, resumed, or duplicated automatically.
7. Confirm reconnect or replacement creates the officially defined session/liveness outcome; do not reuse a fenced or expired session unless the official contract explicitly permits it.
8. Record any late status without changing an already terminal local result.

## Pass criteria

The run is accepted as **simulator evidence for only the named versions** when all of these are true:

- [ ] All four valid intentions produce the exact reviewed official mapping and a correlated terminal result.
- [ ] The invalid intention is rejected and produces no physical dispatch.
- [ ] Disconnect is detected through the confirmed mechanism and the in-flight request reaches the reviewed interrupted/safe outcome.
- [ ] Reconnect causes no automatic replay, duplication, or continuation of the interrupted request.
- [ ] Status order, terminality, request correlation, frame/unit use, QoS behavior, and time assumptions match the completed intake.
- [ ] The simulator or its official component remains authoritative for every physical limit and safeguard.
- [ ] The generic bridge emits no direct low-level command and cannot bypass a safeguard.
- [ ] Evidence-chain verification passes and retained evidence contains no prohibited data.
- [ ] Every mismatch is recorded; no limit, validator, mapping, or safety behavior was weakened to make the demonstration pass.

Any failure leaves `review.simulator_evidence.status` as `failed` or `not_run`. A pass may set it to `passed_for_named_versions` with the full nonzero 40-character commit SHA, UTC completion time, and acceptance-record reference. The validator rejects Git's all-zero null object ID and a completion time more than five minutes ahead of the validating host, but source authenticity and clock correctness still require human/external review. A pass is not evidence of hardware compatibility, production readiness, safety certification, a live mind or body, consciousness, personhood, actual forgetting, or authorization to proceed beyond the reviewed simulator scope.

## Teardown

- Stop the bridge and simulator using their documented procedures.
- Verify no process remains connected to a simulator or physical endpoint.
- Verify the final evidence chain before moving or archiving it.
- Remove generated local evidence that is not approved for retention.
- Store approved results with the intake, exact source/configuration hashes, build output, endpoint graph, and deviations.
- Open follow-up issues for every mismatch; do not patch around unknown official semantics during the acceptance run.
