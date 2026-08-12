# Resident Media Voluntary Gate V11 - Fresh Static Review

Date: 2026-08-11

Verdict: `STATIC_REJECT`

Live authorization: `NONE`

## Outcome first

The sealed V11 package is rejected as a static security boundary. All four
sealed V11 subjects match their author checkpoint, the referenced V10 fresh
rejection checkpoint matches, and the authored V11 suite passes. Fresh
ordinary tests also confirm the requested fail-closed refusal text, exact
video/audio/caption role coverage, duplicate receipt rejection, empty-field
rejection, fixed-seal catalog-change rejection, and journal restore
consistency.

Two deterministic caller-authority failures remain:

1. The capability constructor is described as controller-reserved, but the
   reserved issuer token is a module attribute. Passing
   `v11._CONTROLLER_ISSUER_TOKEN` to
   `ControllerProtectedAuthorityCapabilityV11` constructs a capability that
   `ProtectedMonotonicBackendV11` accepts. No refusal is raised.
2. The owner-selected catalog digest and selection receipt are runtime module
   globals annotated `Final`, not immutable authority. A caller can make a
   valid catalog with an altered derivative path, byte count, and digest,
   rebind `OWNER_SELECTED_CATALOG_SHA256_V11` and
   `OWNER_SELECTION_RECEIPT_SHA256_V11` consistently, and then obtain a V11
   capability for that changed catalog. No refusal is raised.

The second failure restores the decisive V10 owner-unselected derivative
problem at the V11 process boundary. The checkpoint's process-local/no-OS-
trust-root caveat correctly limits its scope, but it does not make the claimed
static exact catalog or constructor reservation true against an ordinary
caller in that same Python process.

## Evidence

- `HASH_VERIFICATION.md` records byte counts and SHA-256 values.
- `TEST_RESULTS.md` records the exact static commands and counts.
- `REVIEW_RESULT.json` contains the structured verdict.
- `test_resident_media_voluntary_v11_review.py` is the append-only,
  review-owned ordinary unit-test module.

The full fresh review module reports `2 failed, 7 passed, 16 subtests passed`.
The seven requested-area tests report `7 passed, 16 subtests passed` when the
two independent boundary probes are deselected. The sealed authored suite
reports `17 passed, 11 subtests passed`.

## Required repair boundary

A successor must place the owner-selected catalog identity and issuance secret
outside caller-mutable Python module state, or narrow its claims so the module
is not treated as a caller-resistant static authority. It must prove that a
caller cannot construct an accepted capability and cannot change the catalog
authority by rebinding runtime globals. Preserve V11 and this rejection
evidence unchanged; use an append-only V12 with a new seal and different fresh
review.

## Truth and safety boundary

This was local static source inspection and ordinary in-memory unit testing
only. No media was opened or played. No model, network, page renderer, media
decoder, audio output, camera, microphone, device, person state, body, Blender,
production pointer, or production route was used or changed. This rejection
never enables live use.
