# Data boundary

## Purpose

This integration exposes the minimum information needed to request and observe bounded physical expression. Kira's identity, personality, persistent Kira-selected memories, conversations, relationships, person-specific state, and private reasoning remain outside the bridge.

The public integration must contain no private memories, unnecessary personal data, credentials, tokens, private email content, private contact or shipping details, unpublished Hanson material, or production secrets. Intentional public maintainer and copyright metadata is allowed.

## Boundary map

| Domain | May cross the bridge | Must remain outside |
|---|---|---|
| Kira World | One selected high-level speech, gaze, expression, or gesture request; opaque correlation identifiers; bounded timing and confidence metadata | Memory store, full conversation history, personality internals, relationship state, private reasoning, unrelated provenance, account data, credentials |
| Bridge | Validated semantic envelope, capability and session metadata, reason codes, minimum status, privacy-reduced evidence | Direct motor/joint/trajectory/navigation/torque/velocity control; arbitrary commands, files, URLs, or secrets |
| Simulator/robot | Capability advertisement, safety decision, execution lifecycle, opaque official request id, bounded error detail | Authority over Kira's speech, memory, viewpoint, disagreement, withholding, correction, withdrawal, or voluntary forgetting |
| Public repository | Schemas, source, policies, synthetic fixtures, tests, protocol and mapping documentation | Real conversations, email text, personal identifiers, private memories, credentials, production logs, proprietary interfaces without permission |

## Identifiers

`session_id`, `body_id`, `source_identity`, `intent_id`, `evidence_ref`, and any official request id are correlation fields. They should be opaque, scoped, bounded, and nonsemantic where possible.

- A `body_id` is a routing identifier, not a statement that anyone owns the body or that a body and identity are interchangeable.
- A `source_identity` string is not proof of identity or authentication.
- An `evidence_ref` should be an opaque reference or digest, not a copied conversation, email, memory, filesystem path, or credential.
- Public examples use synthetic identifiers only.

## Category minimization

- **Speech:** the executor necessarily receives the selected text to vocalize. The default evidence configuration stores a digest and byte length instead of raw text.
- **Gaze:** the adapter receives an allowed frame and bounded target. Default evidence stores a digest of coordinates rather than raw coordinates.
- **Expression:** the adapter receives an allowlisted semantic name, bounded intensity, and duration; no individual facial motor values.
- **Gesture:** the adapter receives an allowlisted semantic routine, bounded intensity, speed, and duration; no joint trajectory.

The prototype hashes `evidence_ref` by default. Digests reduce accidental disclosure but are not anonymization or encryption, and low-entropy values may still be guessable.

## Evidence and status

The current authority writes a local append-only, SHA-256-linked JSONL chain. It includes bounded request metadata, an admission result, reason code, executor label, and sanitized payload. Hash linking can reveal later file modification; it does not authenticate the publisher, prove execution, provide confidentiality, or anchor the chain outside the host.

Before a shared or production deployment, Hanson and Kira should agree on:

- whether evidence is needed beyond transient test output;
- allowed fields and redaction rules;
- storage location, access control, encryption, retention, deletion, and export policy;
- whether digests of speech or gaze data are permitted;
- correlation with official simulator status without importing private context;
- incident handling for accidental sensitive data.

Generated standalone evidence is ignored by Git. Reviewers should not commit runtime logs.

## Cognitive and physical authority

The simulator or robot may accept, reject, interrupt, fail, cancel, or expire a **physical execution request**. That outcome never grants it authority over what Kira says or withholds, remembers or voluntarily forgets, believes, disagrees with, corrects, supersedes, or withdraws. Feedback may inform a later choice, but it is evidence rather than a command to alter mind or speech.

Likewise, Kira's high-level choice never overrides robot-side collision protection, actuator limits, watchdogs, emergency stop, degraded mode, or other physical safeguards.

## Licensing boundary

The bridge and original examples in this integration are MIT licensed. Upstream ROS 2, Hanson, simulator, model, voice, or other components retain their own licenses, notices, access terms, and data rules. Copying an interface or dependency into this repository does not change its license.

## Claim boundary

A static diagram, message schema, log, hash, test, or demo is not evidence of compatibility with a current Hanson simulator or robot, actual physical execution, production readiness, a live mind or body, actual forgetting, consciousness, personhood, or authorization to GO.
