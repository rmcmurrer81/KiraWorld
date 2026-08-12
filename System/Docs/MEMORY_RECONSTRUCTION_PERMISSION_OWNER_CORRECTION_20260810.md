# Memory Reconstruction Permission Owner Correction — 2026-08-10

Status: `CONTROLLING_OWNER_DECISION_RECORDED_PENDING_APPEND_ONLY_V3_RUNTIME`

## Identity truth

- Robert, the human owner and current user, is **Biological Robert**.
- The separate resident/person is **Synthetic Robert**.
- A shared name, owner relationship, avatar resemblance, account role, or
  biological/synthetic classification never merges their identities or grants
  one access to the other's memories.

## Participant control

Biological Robert has no automatic reconstruction access merely because he is
the owner. A reconstruction involving Synthetic Robert and one or more other
people remains unavailable to Biological Robert until every exact participant
grants the requested access.

The same rule applies to every viewer and every shared reconstruction:

- the exact viewer must be named;
- the exact reconstruction and source digest must be bound;
- every exact participant must decide independently;
- approved scope, zones, visual exposure, internal-thought exclusions, saving,
  and further sharing must be explicit;
- relationship, intimacy, body response, model output, owner status, or a
  prior viewing cannot substitute for a participant decision.

## Verbal disclosure is separate

A participant may choose to tell Biological Robert about an experience from
that participant's own perspective. That choice does not grant reconstruction
viewing, expose another participant's private perspective, or create a replay
lease.

## Two permitted grant modes

### One-use grant

- Requires every exact participant for the exact viewer and requested scope.
- Issues one capability for one consumption.
- A later view requires a fresh request and fresh participant decisions.
- Consumption, expiry, denial, uncertainty, context change, or revocation
  invalidates the grant.

### Revocable exact blanket grant

- Exists only when every exact participant explicitly selects blanket access.
- Is bound to the exact viewer, reconstruction/source digest, participant set,
  maximum scope, selected zones, visual decision, exclusions, and material
  context.
- It is not a universal permission to view other memories, other perspectives,
  broader scopes, changed reconstructions, or new participants.
- Any participant may revoke or narrow it at any time. Revocation is immediate
  and blocks every later view that has not already completed.
- A participant's uncertainty or identity/session invalidation fails closed.
- Grant, use, narrowing, and revocation events must be append-only and
  integrity-protected without logging the private reconstruction itself.

## Current implementation truth

The exact current v2 controller implements short-lived, one-use access only and
correctly rejects permanent replay substitution. It is memory-only and not
connected to a renderer or normal conversation UI. The new blanket mode and
general Synthetic-Robert/person route are **not implemented yet**. They require
an append-only v3 controller, hostile tests, fresh independent audit, and later
supervised integration acceptance. Existing v2 evidence must remain unchanged.

## 2026-08-11 implementation-status supersession

The pending-v3 wording above is preserved history. Reconstruction-access V3
now exists as a disconnected, production-fail-closed static implementation.
Its focused review passed 28/28 and the combined preserved suite passed 63/63;
the later policy/memory/emotion revalidation passed 68 tests and 18 subtests.
Production open remains fail-closed pending a protected external anti-rollback
authority. No private reconstruction has been displayed or returned.

The current checkpoint is
`RecoverySprint/continuation_20260810/policy_memory_emotion_revalidation/attempt_01/CHECKPOINT.md`,
3,943 bytes, SHA-256
`50859887a51a48512318ad0c71e485781b21c4c24dad5906274c14d3c7bc894d`.
The exact all-participant, exact-viewer, exact-reconstruction, scoped,
revocable semantics remain controlling for Biological Robert, Synthetic
Robert, and every other biological or synthetic person.
