# Root multilane continuation checkpoint — Body V3r29 Audit-A rejection

Recorded UTC: `2026-08-12T01:33:33.291Z`

## Verdict

`REJECT_AUDIT_A_NO_STAGE2_MATERIALIZATION_OR_BUILD_AUTHORITY`

The different reviewer preserved the positive V3r29 compiler, analyzer,
exact-type, seal, final-handle, and predecessor-closure evidence, but found
three blocking defects:

1. the installed PostSeal fixture is location-dependent and attempts a Kira
   ledger write before refusing `materialization_ledger_root_scope`;
2. seven Blender-worker staging objects are not pre-reserved or held before
   Blender exits, leaving substitution, hard-link, and replacement races; and
3. the one-use materialization ledger is pathname-only, leaving directory or
   junction swap/reset gaps.

The exact seven-file rejection bundle is installed append-only under
`RecoverySprint/continuation_20260811/kira_r25_medical_reference_proxy_v3r29_fresh_static_audit/attempt_01/`.
Its evidence manifest is 586 bytes, SHA-256
`26443bd9855aa312000725449067f7609577101d1991b078698f6e575013e2e8`;
decision is 6768 bytes,
`f2de5822e705213abcf8a46c0b6fef8c3cd7dbac25d9cc8b886f6615394185d0`;
audit checkpoint is 3626 bytes,
`aaf680746bdd2179fcaf3de8d0235b26089e6582e2691c56d57e0f2a42cff0ad`.
All seven copied files rehash exactly; their canonical evidence root is
`882955c42d7d4ade325c1eca7db0e6400e2defe21218e8aba7ff82ab208cfbc3`.

## Boundary and successor

V3r29 must not materialize or build Stage 2 and must not run Blender. It is not
Kira's body, anatomy, physiology, material, bald activation body, hair body, or
an Avatar Builder template. Append-only V3r30 authoring is active in scratch
to close all three defects, after which another different Audit A is required.
