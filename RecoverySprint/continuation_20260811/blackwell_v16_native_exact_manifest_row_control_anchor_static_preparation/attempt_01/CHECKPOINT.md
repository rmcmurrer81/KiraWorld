# Blackwell voice V16 exact-manifest-row control anchor checkpoint

Recorded UTC: `2026-08-11T17:53:46.6947903Z`

Status: `SEALED_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT`

Execution authority: `NONE`

V15 rerun: `false`

V16 candidate invoked: `false`

Python candidate invoked: `false`

## Consumed V15 diagnosis

The accepted V15 one-shot invocation returned exit code `4` at coarse stage
`10` and created neither run evidence nor an outcome receipt. Its authority is
permanently consumed: `DO_NOT_RERUN_V15`.

The exact failure is
`V15_STAGE10_WHITESPACE_SENSITIVE_SEAL_ROW_FORMAT_MISMATCH`. V15's native
`seal_contract_exact` and `seal_exact_row` searched for spaced fragments such
as `"path": "..."`, but every one of the 21 seal subject objects used compact
JSON such as `"path":"..."`. The object and build spaced sentinel counts were
both zero; all 21 old spaced subject-path counts were zero. The corresponding
compact sentinels and every full compact row occurred exactly once.

V15 therefore necessarily rejected before stage `20` and output reservation.
Even without the first sentinel, each later old row check would reject. No
Python DLL, candidate, model, GPU, synthesis, audio, playback, or latency path
was reached.

Exact read-only diagnostic artifacts:

- `READ_ONLY_DIAGNOSIS.json`: 3,181 bytes,
  `c7d512f1eb1af0cc8c764fd818405b9526eddf0268a50ff2aba43e9364a44463`.
- consumed-failure `CHECKPOINT.md`: 2,298 bytes,
  `d1a808c3710fbab34e1978c0f9a463189949b6b43c56efa34ded95fb57b0506d`.

## Append-only V16 repair

V16 preserves every sealed V15 byte and its exact accepted-then-consumed audit.
It retains the already accepted V15 Python source, private validator, config,
six V14 native attestations, immutable origin binding, exact loader types,
complete mutable namespace/path graph state, and full V15/V14/V13/V12 slot
checks unchanged.

Only the native seal boundary changes. `seal_exact_row` now constructs one
complete compact row:

`{"path":"<path>","bytes":<bytes>,"sha256":"<digest>"}`

The exact complete row must occur once. The path must be canonical printable
ASCII using forward slashes without JSON escapes, empty segments, or dot
segments; bytes must be positive; the digest must be exactly 64 lowercase hex
characters. The native contract also requires exactly 41 compact row prefixes.
There is no separate path/bytes/digest search and no bounded cross-field
window.

Hostile tests refuse missing rows, duplicate rows, whitespace mutation, wrong
bytes, wrong digest, NULs, path-only/field-only decoys, and fields split across
different rows. They reproduce the exact V15 negative control (`0/21` old
spaced path matches) and the exact compact control (`21/21` full rows).

## Static/build evidence

- PreBuild hostile static suite: `PASS`.
- Strict MSVC x64 `/W4 /WX /O2 /MT /guard:cf /std:c17`: `PASS`, zero diagnostics.
- Strict `/analyze /W4 /WX`: `PASS`, zero diagnostics and an empty 59-byte
  analyzer `DEFECTS` document.
- Object: 115,406 bytes,
  `33203388375639e2fd93af99a69e05e97b25ef5ccb6cecbf6f8e272ce5e486d4`.
- Executable: 182,784 bytes,
  `dc688ea754a9003654f1981f670f20cc3109166326a33233a88a1712a34f80f0`.
- Analyzer object: 69,946 bytes,
  `f0f2a0d9f9efd26efc936d54d2f9ffda4d5186a2f0c1fb5d3668fc2c3d2d1f41`.
- PE: x64 PE32+, High Entropy VA, ASLR, NX, CFG, CF instrumented, FID table,
  0x33 Guard CF functions; imports only `bcrypt.dll` and `KERNEL32.dll`.
- PostBuild hostile static suite: `PASS`.
- Complete 41-row seal and PostSeal hostile static suite: `PASS`.
- Final seal: 9,065 bytes,
  `b02ecdace1727a5ab9e8dba9a580932fe886e9ae05561f5241b1fbbffc21acd4`;
  `41/41` exact rows and `41/41` unique paths.

## Boundary and next step

All V16 work exists only under Documents/Codex staging; Kira was not edited.
No V15 or V16 executable or Python candidate was invoked during diagnosis or
authoring. No model, GPU, synthesis, audio, playback, latency, network, person,
body, Blender, or production work occurred.

Static author completion grants no execution authority. Root must preserve V15
and its consumed audit exactly, transcribe the V16 package append-only, rehash
all 41 rows, and obtain a different fresh V16 audit. At most one later
no-argument disconnected static-control validation may be authorized; success
or failure consumes it, and it grants no voice or other live authority.
