# Shared Growth integration candidate V3 — different quality review

Recorded UTC: `2026-08-11T16:42:32.6015647Z`

Decision: `REJECT`

## Outcome

The sealed closure is intact (11/11 exact), all eight named files compile in
memory (8/8), the focused V3 suite passes (20/20), and the preserved V3 core
plus V1/V2/V3 integration suite passes (103/103). The no-authority/no-commit
boundary is genuine: the candidate has no verifier, key, callback,
controller, staging, write, commit, rollback, cleanup, person/profile/memory
writer, production consumer, or Temporary Creator surface. Canonical envelope
bytes, exact proposal digest binding, ordinary cross-binding refusals, drift
refusals, the hard production refusal, and Temporary Creator refusal all
reproduced independently.

The candidate is nevertheless rejected for two contract-quality failures.

1. An exhaustive matrix compiled only 31 of 35 routes that the fixed inventory
   marks `applicable`. Both profile and state routes for Peter Parker and
   Spider-Gwen fail because their exact `confirmed_adult` status uses the
   `subject_specific` maturity source, while V3 lines 397-400 allow
   `subject_specific` only for `non_adult`. The named tests omit this exact
   lane.
2. `REQUESTED_SCOPE` is an exported mutable list. Appending a second scope and
   submitting that exported value succeeds, contradicting the exact single
   public-scope/no-mutable-catalog contract. The emitted bytes remain inert and
   unconsumed, so this does not create authority or commit capability.

## Preserved boundary

The isolated Shared Growth V3 core remains `ACCEPT_STATIC_ONLY`; V1 and V2
remain rejected. V3 is not accepted, integrated, promoted, or connected.
Kira, Lisa, Synthetic Robert, every other person, variant, or expert, and the
Temporary Creator receive no upgrade. Biological Robert remains distinct from
Synthetic Robert. No person, profile, memory, route, model, body, media, voice,
network/device, production pointer, or Sarah operation changed.

Maturity and opt-in receipt strings are shape-checked assertions, not
authenticated receipts: the absence of any verifier makes that truthful only
for inert proposal bytes that no current route consumes.

## Required next boundary

Preserve sealed V3. Repair append-only so `subject_specific` accepts the exact
inventory-bound `confirmed_adult` or `non_adult` status, add a 35-route
exhaustive regression test, and make the one allowed scope immutable or
function-local. A different fresh review is required before static acceptance;
static review alone can never authorize a commit or person upgrade.

Detailed evidence is in `AUDIT_DECISION.json` and `REVIEW_PROBES.md` beside
this checkpoint.
