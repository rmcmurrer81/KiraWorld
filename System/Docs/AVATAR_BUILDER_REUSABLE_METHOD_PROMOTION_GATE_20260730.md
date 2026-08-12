# Avatar Builder Reusable-Method Promotion Gate — 2026-07-30

Status: **IMPLEMENTED — LOCKED WITH ZERO PROMOTED METHODS**

This gate separates reusable Avatar Builder engineering from Robert's private
avatar data. It does not approve a body, start movement, change a runtime body,
activate anyone, modify the user interface, or authorize public export.

## Promotion prerequisites

A method remains blocked and unselectable until:

1. an exact hash-bound Biological Robert static-foundation owner-approval
   record exists;
2. that record contains Robert's explicit decision to approve the exact static
   foundation and does not imply movement or runtime approval;
3. an independent evaluator validates the exact generic method definition;
4. at least two distinct non-private synthetic fixtures pass topology, visual,
   deformation-readiness, private-data-exclusion, and runtime-nonmutation
   checks;
5. the generic implementation lives beneath
   `Avatar/avatar_builder/tooling/reusable_methods/`;
6. the definition, implementation, and generalization proof pass the private
   payload scanner.

The private payload scanner rejects:

- private or protected photo paths;
- identity/body measurements;
- person-specific vertex/face indices;
- person-specific coordinates, morphs, or deltas;
- private anatomy observations;
- Robert-specific identity text.

## Rejected-method archive

Rejected methods remain available as historical engineering evidence but are
not copied into the selectable registry. The safe archive stores only:

- a method fingerprint;
- a safe method identifier when one exists;
- failure codes;
- a statement that the private evidence remains outside the registry.

It does not store the raw submission or private data.

Current registry:

`Avatar/avatar_builder/tooling/reusable_method_registry_v1.json`

Current selectable method count: **0**

Current rejected evidence includes the clean-bridge milestone,
same-surface-relief trial, and symmetric-root-graft trial. None is promoted.

## Normal-path integration

`Core/avatar_builder_orchestration.py` now evaluates
`reusable_method_selection` whenever an authoring request supplies
`reusable_method_id`. An archived, unknown, revoked, or incompletely bound
method blocks the normal authoring route.

Requests that do not select a reusable method continue through their existing
source and maturity lanes. This change adds no new launcher, user interface,
runtime selector, body assignment, or activation behavior.

## Evidence

- gate:
  `Core/avatar_reusable_method_registry.py`
- policy:
  `Avatar/avatar_builder/policies/reusable_method_promotion_gate_v1.json`
- registry:
  `Avatar/avatar_builder/tooling/reusable_method_registry_v1.json`
- tests:
  `tools/test_avatar_reusable_method_promotion_gate.py`
- test report:
  `Avatar/avatar_builder/proofs/reusable_method_promotion_gate_20260730/TEST_REPORT.json`

Test result: **12 passed, 0 failed**

Covered cases include missing owner approval, missing independent proof,
private-photo paths, identity measurements, person-specific coordinates,
private anatomy observations, person identity leakage, safe archive behavior,
normal-orchestration rejection, and the explicit two-step
eligible-then-registered selection path.

