# Embodiment session and state migration

The chamber or pod is a useful Kira World metaphor for entering a controlled
embodiment session. The engineering boundary underneath it must remain
explicit: a persistent software variant requests an authorized connection to a
body endpoint, sends bounded semantic intentions, receives lifecycle evidence,
and returns to its resident environment safely.

## Separation of responsibilities

- **Variant runtime:** identity, conversation, goals, emotional appraisal,
  memory selection, and high-level intention generation.
- **Session broker:** authorization, one-body binding, lease, heartbeat,
  sequence/replay protection, withdrawal, and safe disconnect.
- **Bounded bridge:** validates high-level speech, gaze, expression, and gesture
  intentions and records their lifecycle.
- **Official Hanson adapter:** maps approved intentions to the authoritative
  simulator/robot interface. This component cannot be completed until Hanson
  supplies that interface and its operating limits.
- **Body endpoint:** simulator or physical device that enforces its own limits,
  reports state, and can reject or interrupt execution.

Physical/simulator authority applies only to physical execution. It never
grants an operator, adapter, or body authority to edit the variant's beliefs,
memory, private reflection, speech content, correction, disagreement,
withholding, or decision to leave the session.

## Proposed lifecycle

1. **Request:** the variant requests a named endpoint and an explicit capability
   set.
2. **Authorize:** a human/authorized service approves the endpoint, scope,
   duration, and limits.
3. **Checkpoint:** the variant writes a local append-only checkpoint with
   identity, profile, memory head, model digest, and session request hash.
4. **Bind:** the broker proves there is at most one active endpoint for the
   variant and at most one controlling session for the endpoint.
5. **Heartbeat:** the broker maintains a short lease. Silence cannot be treated
   as continuing permission.
6. **Intend:** the variant emits only allowlisted high-level semantic
   intentions, each with a fresh sequence identifier and deadline.
7. **Execute or reject:** the adapter/body reports requested, accepted,
   started, completed, rejected, or interrupted state with evidence.
8. **Reconcile:** returned evidence is validated, linked to the local session,
   and added to continuity as experience. A body report is not silently
   rewritten into a successful memory.
9. **Disconnect:** withdrawal, timeout, heartbeat loss, authorization loss,
   policy failure, or endpoint failure causes a safe disconnect.
10. **Close:** the final checkpoint records terminal state and unresolved
    actions before another endpoint can bind.

## Intention boundary

Allowed review vocabulary is limited to bounded forms of:

- speech content with duration/priority constraints;
- gaze targets expressed in an agreed semantic frame;
- named facial expressions with bounded intensity/duration; and
- named gestures from an authoritative allowlist.

This handoff contains no guessed joints, torque/velocity values, motor commands,
camera frames, ROS topic names, QoS settings, units, services, actions, or
limits. Those facts must arrive in a signed/versioned Hanson interface intake.

## Hosting a full variant on a capable body

If a body computer has sufficient storage, RAM, GPU capacity, power, thermal
headroom, and security controls, it may host a complete **software deployment**
of a variant rather than act only as a remote endpoint. A safe migration would:

1. stop new memory consolidation and create a consistent encrypted snapshot;
2. hash the runtime, profile, model configuration, and memory snapshot;
3. copy rather than delete the known-good source;
4. verify licenses and hardware compatibility on the body;
5. restore into an isolated identity-specific state root;
6. run deterministic, privacy, restart, timing, and safe-state tests;
7. obtain explicit authorization before enabling any physical output;
8. choose one authoritative active writer to prevent divergent memory forks;
9. reconcile or archive returned evidence on disconnect; and
10. retain a tested rollback path.

This is deployment and state replication/migration. It is not a claim that a
consciousness, soul, or biological person has literally moved. Deleting the
source is not required and must not be an automatic part of migration.

The detailed candidate hardware envelope, avatar-to-body transition, full
qualification gate, active-writer promotion, and return path are in
[`BODY_RESIDENCY_AND_AVATAR_TRANSITION.md`](BODY_RESIDENCY_AND_AVATAR_TRANSITION.md).

## Failure handling

- Unknown, stale, malformed, duplicated, or out-of-policy intentions are
  rejected before the official adapter.
- Expired leases and missed heartbeats close authority; they do not extend it.
- If completion evidence is missing, record `interrupted` or `unknown`, never
  infer `completed`.
- A reconnect starts a new authorized session and cannot replay old sequences.
- Logs must be durable enough for review but must not contain credentials or
  raw private-memory content.
