# Shared Person Growth V3 integration candidate — different fresh static audit

Date: 2026-08-11  
Decision: `REJECT_STATIC_INTEGRATION_CANDIDATE_NO_PROMOTION`

## Outcome

The accepted-static Shared Person Growth V3 core remains intact and accepted at its existing static-only boundary. The separate shared integration/promotion candidate is rejected. It must not be promoted to Kira, Lisa, the other existing people, or the Temporary Creator.

All three candidate subjects, the author evidence, the six protected V3 subjects, and the two protected current-runtime subjects matched the sealed byte identities before and after the independent probes: 12/12 checked, zero mismatches. The preserved author/regression suite passed 70 tests and 13 subtests. Those tests were insufficient because two independent hostile probes reproduced promotion-blocking behavior.

## Blocker 1 — same-process capability exposure

`SharedGrowthV3IntegrationAdapter.identity` publicly returns the exact identity object. Python name-mangled fields on the same adapter object expose the 32-byte integration secret, the protected controller, and its authority identity through ordinary `getattr` introspection.

The probe began with an already-valid, controller-issued Kira V3 profile, retained only the adapter object as the proposed integration boundary, recovered those fields, issued a `permanent:kira` receipt, and staged `growth_profile:hostile_introspection.shared_growth_integration_v1.json`. That acceptance is deterministic.

Name mangling is a naming convention, not a protected capability boundary. This does not invalidate the isolated V3 core. It invalidates the claim that this shared-process adapter can securely authorize production migration against other in-process code.

## Blocker 2 — route-source time-of-check/time-of-use gap

The adapter verifies inventory and route-source hashes only during construction. The independent probe copied the exact inventory closure to an isolated temporary project root, successfully constructed the adapter, then changed the cloned `tools/kira_world_shell_server.py` bytes. The source changed from the sealed digest `72e4fc403e00a2c4e7ac84e7a87a3c925fc9ce475a8afc90e17ac9e0b6b19fb4` to `bed97c3bb5cb7ce790d5d0c7ef8cb6954d7c5e1e74a3d77d88bb21bf5edfc85b`.

The already-constructed adapter still issued and staged a Kira migration while the attachment claimed the stale sealed source digest. No issue-time or stage-time exact source rehash closes that interval.

## Evidence

- Author seal: `RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_static_preparation/attempt_01/SEALED_MANIFEST.json` — 3,406 bytes — SHA-256 `1103ed9c29be3c27a6089ea4682dde93c2db248b4bbf2fa7f5637db60f1d337f`.
- Independent probe: `INDEPENDENT_HOSTILE_PROBES.py` — 7,871 bytes — SHA-256 `74ac91571bb0f0c6055f1f4172b69b18e3a5174c4daa8de1c15d06ca1ad4bb38`.
- Probe result: `HOSTILE_PROBE_RESULT.json` — 1,314 bytes — SHA-256 `e6fab7694aa51cacfb709d2b6539f268968a005c9f29e6a2a0593e2860d80f18`.
- Preserved suite: `70 passed, 13 subtests passed`.
- Machine-readable audit: `STATIC_AUDIT_RESULT.json`.
- Decision: `AUDIT_DECISION.json`.

## Required append-only successor

The smallest truthful successor must:

1. keep production adoption disconnected unless issuance is moved outside the inspectable shared Python object boundary;
2. rehash and bind the exact route source at issue time and stage time, with a final readback or generation check before commit;
3. include same-process attribute-introspection and post-construction source-mutation regressions;
4. preserve all V1–V3 core/audit and current-route bytes; and
5. receive another different fresh exact-byte hostile audit before any promotion.

## Side-effect truth

This audit did not change the sealed integration candidate, accepted V3 core, current shell, person profiles, Temporary Creator, registry, or production pointers. Temporary probe files existed only in automatically cleaned temporary directories. No live model, person, memory, emotion, initiative, body, media, voice, GPU, or Blender operation ran.
