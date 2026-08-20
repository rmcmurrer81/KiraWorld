# Proposal: Kira World as a continuity home for humanoid deployments

Status: owner-authored collaboration proposal; not implemented end to end; not
an official or accepted Hanson Robotics integration.

## The idea

Robert proposes that Hanson Robotics build on top of Kira World as a virtual
place where a humanoid robot's software deployment can continue its day while
its physical body is unavailable. A body may need to charge, undergo repair,
receive replacement parts, be upgraded, or remain offline for inspection. The
goal is that a deployment's bounded conversational and creative life loop does
not have to stop merely because its current physical endpoint is temporarily
unavailable.

In Kira World, that deployment could use a clearly identified virtual avatar to
talk with its team, participate in approved activities, reflect on completed
events, and append branch-local reviewed life-loop records. When a qualified
body becomes available again, an authorized reviewer could decide whether to
release the virtual endpoint and bind the same deployment branch to that body.

This is a continuity-of-deployment design idea. It does not assert
consciousness, biological life, literal mind transfer, or automatic identity
equivalence between copies.

## Proposed transition model

1. The active physical-body session enters a vendor-defined safe state.
2. The current deployment, body endpoint, software/model hashes, branch ID, and
   rollback source are recorded.
3. The physical endpoint is explicitly released before a Kira World avatar is
   bound; only one active embodiment endpoint is permitted for the deployment.
4. While maintenance occurs, Kira World provides conversation, virtual
   presence, creative activity, and reviewed branch-local life loops. It does
   not issue low-level motor commands.
5. Before returning to hardware, the team validates the target body's capacity,
   exact software interfaces, safety status, and rollback path.
6. The virtual endpoint is released, the reviewed deployment is explicitly
   bound to the qualified body, and an accepted/rejected transition record is
   preserved.

Separate installations begin from the same selected reviewed checkpoint and
then become distinct variants. Their daily records do not silently synchronize
or automatically merge. Any continuity moved between branches must be a
selected reviewed export/import that preserves source-branch provenance.

## What Hanson would need to define

An official integration would require Hanson-provided or Hanson-approved
packages, messages/actions/services, topics, QoS, coordinate frames, units,
intent vocabulary, physical limits, readiness and heartbeat semantics,
safe-state behavior, emergency-stop ownership, charging/maintenance state, and
accepted/rejected simulator and hardware evidence.

Kira World's current bridge is intentionally bounded to high-level semantic
intent such as speech, gaze, expression, and gesture requests. It does not
guess vendor interfaces, claim official compatibility, render or track a Hanson
robot, or directly command motors and actuators.

## Suggested first collaboration test

The safest first demonstration is a generic simulator or policy-only mock:

- run one identified deployment in a Kira World avatar;
- record a high-level intention without executing hardware movement;
- release that virtual endpoint;
- validate a separately supplied Hanson target definition;
- replay only an accepted bounded intention through a vendor-controlled safety
  layer; and
- prove that rejection, safe-state, emergency stop, and rollback all work.

Only after Hanson and Robert's review team accept that evidence should the work
be described as an official simulator or robot-body integration.
