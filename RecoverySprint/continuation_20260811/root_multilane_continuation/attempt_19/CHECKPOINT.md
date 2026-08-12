# Root multilane continuation - attempt 19

Date: 2026-08-11

## Blackwell voice V15 accepted static review and consumed pre-output failure

The different fresh V15 review returned `ACCEPT_STATIC_ONLY`. It rehashed all
21 unique seal subjects before and after with zero drift, passed the authored
PostSeal suite, independently rebuilt/analyzed the native control with zero
diagnostics, and confirmed x64 PE32+, high-entropy VA, ASLR, NX, CFG, and
imports limited to `bcrypt.dll` and `KERNEL32.dll`.

Exact review artifacts in
`RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_fresh_static_audit/attempt_01/`:

- `INDEPENDENT_AUDIT.tsv` - 920 bytes - SHA-256
  `38f1ac1902d7547fe161204d7fd61d3aa493e971108133bbbd9a6b61844af128`;
- `INDEPENDENT_AUDIT.sha256` - 65 bytes - file SHA-256
  `effe3c23d7e2c5b7f65a07fd225ec84b87d01e668728a2f61678a6bc9382ad5f`;
- `AUDIT_DECISION.json` - 6,899 bytes - SHA-256
  `c525ab16cfad6c6c25f2cbbb8d48a02ec57bdef55832821dc761db731ac80ffe`;
- `REVIEW_PROBES.md` - 9,787 bytes - SHA-256
  `082e5fda87136eefd02e5913aca0b89d165eee8da138a1156cf6a49cef5393f8`;
- `CHECKPOINT.md` - 5,280 bytes - SHA-256
  `5e6a0799da297b962e9bb9dc9973bcc14d8cce252a0f4e9ccf438e13084f2822`.

Root then used the one authorized no-argument disconnected static-control
invocation exactly once. It returned exit code `4`; neither fixed evidence nor
receipt path was created. Authority is consumed regardless of result:
`DO_NOT_RERUN_V15`.

The exact failure is now proven statically. V15's verifier searches sealed
subject rows with whitespace-sensitive tokens such as `"path": "..."`, while
all 21 exact manifest rows use compact canonical tokens such as
`"path":"..."`. Every spaced subject-path token has count 0 and every compact
subject-path token has count 1. The object/build sentinels fail the same way.
Stage 10 therefore rejects before output reservation and before Python load.

Exact failure records:

- `blackwell_v15_native_exact_control_anchor_consumed_failure/attempt_01/STATIC_FAILURE_DIAGNOSIS.md`
  - 4,001 bytes - SHA-256
  `2ec653382ba9d915cac53e525419829ac53e314782a91d7de77cdf7e8ab1275f`;
- sibling `CHECKPOINT.md` - 1,618 bytes - SHA-256
  `ce921ae577bcd68d21e3153afa06cdac7aedbe619dc94e6a290ad28e107d9b7b`.

Preserve V15 and continue append-only as V16 with structural/canonical,
duplicate-rejecting manifest validation. V15 proves no synthesis, playback,
audible speech, or latency improvement. The last accepted latency values remain
`LATENCY_FAIL`: 13.947 s cold and 7.576-8.138 s warm text response; 23.460 s
cold and 7.979-11.128 s warm displayed-text-to-audio onset; 5.577-5.908 s
reload/prewarm overhead.

## Reusable-result routing boundary

The owner's new routing direction applies to Kira, Lisa, Synthetic Robert,
all other residents, variants and experts, and the Temporary Creator:

- independently accepted body engineering lessons may be added append-only to
  the Avatar Builder's reusable method/template layer;
- independently accepted mind/person-development lessons may be added
  append-only to the Temporary Creator's reusable template layer;
- rejected results are retained only as explicit negative tests and
  `do-not-repeat` lessons, never as installed capabilities or person state;
- static-only acceptance does not authorize production integration, a body,
  memory promotion, emotion/desire fact, or creation/update of any person;
- each receiving integration needs its own exact binding, tests, evidence, and
  independent review before promotion.

The long one-hour evaluation remains gated. V10 is rejected and must be
repaired append-only as V11, independently reviewed, and authorized for one
bounded run before any one-hour conversation, protected-belief comparison,
audio playback, or new latency measurement. The run must be used to identify
improvements as well as measure behavior.

No model, private-belief evaluation, synthesis, audio/playback, person-state,
body/Blender, media, network/device, or Sarah operation occurred in this
checkpoint.
