# Shared Growth V3 integration candidate V2 independent hostile findings

Recorded UTC: `2026-08-11T13:53:22.2180209Z`

Decision: `REJECT_STATIC_INTEGRATION_CANDIDATE_NO_PROMOTION`

## Exact preservation

- All 14 sealed V2 rows matched exact byte counts and SHA-256 hashes.
- V2 seal: 4,146 bytes, SHA-256
  `0ec609dc63b6d440f35c9ec3969b15972c5032bd71c7b89e0595f57b54df6820`.
- Exact V2 source and test compiled in memory: 2/2.
- The isolated Shared Growth V3 core remains unchanged at
  `ACCEPT_STATIC_ONLY`.
- No integration, promotion, person upgrade, Temporary Creator upgrade,
  production route, live model, memory, profile, body, media, voice, GPU,
  Blender, or Sarah operation ran or changed.

The different read-only reviewer did not invoke sealed author suites that
create temporary roots, cloned sources, or staging files. Their historical
author results remain preserved but are not reclassified as independent audit
evidence.

## Blocking finding 1 — mutable verifier substitution

`SharedGrowthV3ExternalAuthorityAdapterV2.__slots__` exposes mutable
`_authority_public_key` and `_authority_verification_key_sha256` fields.
`__slots__` prevents an instance dictionary; it does not make slot values
immutable. Same-process code can assign a rogue public verifier and its digest,
then provide a matching callback. Response and binding checks consult those
same mutable fields, so the rogue verifier can mint an accepted protocol flow.

## Blocking finding 2 — non-production staging is not enforced

The constructor accepts any caller-provided `Path`, resolves it, may create it,
and rejects only a symlink. There is no protected-root exclusion, allowlist,
separation from project/person/profile/Creator/current paths, or authority
binding. Writing below a root that the caller merely calls non-production does
not enforce the sealed contract's non-production claim.

## Blocking finding 3 — durable post-commit recovery gap

The external `COMMIT_STATIC_STAGE` action may complete durably. If its signed
outer response then fails cross-binding or receipt/ticket validation before
`commit_receipt` is assigned, the outer failure path removes local output but
attempts external rollback only when `commit_receipt` is non-null. A durable
remote commit can therefore survive without query, rollback, or recovery.

## Blocking finding 4 — cleanup lacks stable file identity

The exclusive output descriptor is closed before external callbacks. Later
failure cleanup checks only the path and symlink state and then unlinks the
current regular object. A callback or concurrent actor can rename the created
file, replace its pathname with another regular object or hardlink, and cause a
later validation failure. Cleanup can then delete the replacement while the
candidate output survives elsewhere.

## Required append-only repair

Integration candidate V3 must bind an immutable externally anchored verifier,
enforce the staging root as a real protected boundary, recover after every
possibly durable commit outcome including signed-but-invalid responses, and
retain/compare stable handle and file identity through cleanup. It remains
disconnected/default-off and requires a different fresh audit. Nobody receives
Shared Growth through V2.
