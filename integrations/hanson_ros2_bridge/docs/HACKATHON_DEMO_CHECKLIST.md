# Simulator hackathon demo checklist

This is a short event checklist for a truthful, resilient demonstration of the bounded bridge. The demo is simulator-only and vendor-neutral until the official Hanson intake is completed. It is not a hardware demonstration, production integration, safety certification, or GO decision.

## Demo promise

- [ ] Show only speech, gaze, expression, and gesture as bounded high-level intentions.
- [ ] Show one intentional rejection and one controlled disconnect/interruption.
- [ ] Show correlated lifecycle status and privacy-reduced evidence.
- [ ] Keep simulator/robot authority limited to physical safety and execution.
- [ ] State plainly whether the run uses the generic deterministic mock or a named official Hanson simulator.
- [ ] Never imply that physical status controls Kira's speech, memory, viewpoint, disagreement, withholding, correction, withdrawal, or voluntary forgetting.

## Freeze 24 hours before the event

- [ ] Pin one branch and full commit SHA; record whether the worktree is clean.
- [ ] Pin Python, dependency, ROS 2, RMW, simulator, package, adapter, policy, and fixture versions actually used.
- [ ] Run all standalone tests, both demos, the evidence verifier, and the intake validator.
- [ ] Confirm reviewed/simulator status and evidence agree bidirectionally, and that the strict intake gate reports no unresolved, unverified, empty core, semantically mis-typed, or contradictory mapping.
- [ ] If claiming an official-simulator run, complete the [official interface intake](../hanson_interface_intake/official-hanson-interface-intake.template.json) and follow the [acceptance runbook](SIMULATOR_ACCEPTANCE_RUNBOOK.md).
- [ ] Rehearse offline or on an isolated network; cache only redistributable dependencies and assets.
- [ ] Confirm there are no private emails, credentials, private memories, unnecessary personal data, production logs, unpublished definitions, or real-person data in the repository, terminal, slides, recordings, or evidence.
- [ ] Confirm no physical hardware endpoint is reachable.
- [ ] Save a known-good privacy-reduced evidence file and screenshots as a clearly labelled prerecorded fallback.

## Roles

| Role | Responsibility | Assigned |
|---|---|---|
| Narrator | Explain the bounded contract and claim limits |  |
| Demo driver | Run only the rehearsed commands and sequence |  |
| Evidence observer | Watch lifecycle, correlation, simulator safety state, and evidence verification |  |
| Recovery lead | Stop the sequence, switch to fallback, and preserve diagnostics without improvising mappings |  |

One person may cover multiple roles, but the stop authority should be explicit.

## Five-minute demo flow

- [ ] **0:00–0:40 — Boundary:** show the architecture diagram; say “high-level intentions in, authoritative physical status out; no direct low-level command path.”
- [ ] **0:40–1:20 — Inspectability:** show one bounded message/schema and the completed-or-unresolved official intake status.
- [ ] **1:20–2:50 — Four valid intentions:** speech, gaze, expression, then gesture, one at a time, with visible correlated status.
- [ ] **2:50–3:30 — Rejection:** submit the rehearsed unsupported/out-of-bounds semantic request; show rejection and absence of physical dispatch.
- [ ] **3:30–4:15 — Disconnect:** trigger only the approved simulator fixture after a correlated start; show interruption/safe outcome and no automatic retry.
- [ ] **4:15–5:00 — Evidence:** verify the chain, name the exact versions tested, and state the remaining official-simulator or hardware gates.

## On-stage preflight

- [ ] Screen sharing reveals only the intended terminal, simulator, architecture, and evidence views.
- [ ] Notifications, mailbox windows, browser autofill, secrets, and unrelated logs are closed.
- [ ] Terminal history and environment output contain no tokens, private paths, or personal data.
- [ ] Simulator readiness and capability discovery match the frozen intake.
- [ ] Clock, namespace, topics/actions/services, types, QoS, frames, units, and policy hashes match rehearsal.
- [ ] Evidence files start empty or at a deliberately recorded prior hash.
- [ ] The rejection and disconnect fixtures are safe, deterministic, and rehearsed.
- [ ] The recovery lead knows the documented simulator stop procedure.

## Stop conditions

Stop the live sequence and use the labelled fallback if any of these occurs:

- an official field is unresolved, guessed, or differs from the completed intake;
- capability discovery, readiness, safety state, time synchronization, or endpoint type/QoS is unexpected;
- a request cannot be correlated to exactly one lifecycle;
- a terminal request receives further physical status or appears to retry automatically;
- the invalid request dispatches, or the disconnect test does not reach the reviewed safe outcome;
- any low-level, hardware, secret-bearing, private, or unreviewed endpoint appears;
- evidence cannot be verified or contains prohibited data; or
- the team would need to weaken a validator, limit, mapping, or safeguard to continue.

Do not debug by inventing a Hanson interface or widening bounds on stage.

## Evidence to retain

- [ ] Full commit SHA and worktree state.
- [ ] Completed intake plus SHA-256 and official-source references.
- [ ] Named environment, simulator, fixture, package, adapter, policy, and configuration versions.
- [ ] Test/build output and endpoint graph/type/QoS snapshot.
- [ ] Per-intention correlation and terminal outcome for four valid, one rejected, and one interrupted case.
- [ ] Evidence-chain count and final SHA-256.
- [ ] Deviations, failures, fallback use, and open questions.
- [ ] Publication/privacy review for every artifact shared after the event.

## Truthful closing line

“This run demonstrates the bounded software behavior shown here for the exact named environment. It does not by itself prove hardware compatibility, production readiness, physical-safety certification, consciousness, personhood, a live mind or body, actual forgetting, or broader authorization.”
