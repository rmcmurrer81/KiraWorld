# Root multi-lane continuation checkpoint — attempt 04

Date: 2026-08-11

Status: `V3R21_DIFFERENT_ACCEPTANCE_CONSUMED_SUCCESS_NO_BODY`

This append-only checkpoint records the V3r21 different review and the single
bounded run it authorized. It supersedes only attempt 03's V3r21-pending
wording. Every predecessor, rejection, failed audit, and consumed authority
remains preserved.

## Different review

- Reviewer: `/root/body_v3r21_contract_test`.
- The reviewer authored none of the V3r21 sealed candidate bytes.
- Because the reviewer's sandbox could not create the new evidence directory,
  root transcribed the reviewer's exact evidence append-only; the evidence
  identifies both the reviewer and transcriber.
- Decision:
  `ACCEPTED_FOR_ONE_BOUNDED_GRANULAR_CONTRACT_AND_PYTHON_CONTROLLER_VALIDATION_V3R21_ONLY`.
- Seal closure: 91/91 unique exact subjects, zero drift.
- Independent strict x64 `/W4 /WX /O2 /MT /guard:cf /std:c17` rebuild: pass.
- Independent MSVC `/analyze`: exit `0`, zero diagnostics, no suppression.
- Sealed and rebuilt PE: x64 PE32+, high-entropy VA, ASLR, NX, CFG/FID; DLL
  imports limited to `bcrypt.dll` and `KERNEL32.dll`.
- V3r20's two exact literal-overread negative controls were reproduced.
- Hostile/static probes: 37/37 pass; malformed audit variants: 11/11 refused.

Exact review evidence under
`RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r21_fresh_static_audit/attempt_01/`:

- `INDEPENDENT_AUDIT.tsv`: 6,259 bytes, SHA-256
  `235e13793ed4112c9dfaa7173125b31712cb84323d46224932f5fda135f69fd5`.
- `INDEPENDENT_AUDIT.sha256`: 65 bytes, file SHA-256
  `5b12a7534239ac1bba7174cc4f2c44cf3ad63a3a8ba555fffe0d260988d34773`.
- `AUDIT_DECISION.json`: 2,263 bytes, SHA-256
  `e02ad4252df2338b05fdbeec5bf2e7d719b45beb103f5a25d10a81d901380355`.
- `HOSTILE_STATIC_PROBES.txt`: 2,825 bytes, SHA-256
  `95e1bfd37cf036ee552f046d3ad49ebd88b6369aad0d1614d69ea007f3c8de4f`.
- `CHECKPOINT.md`: 2,954 bytes, SHA-256
  `9b81bda48a01652cbe17ad83d4e3a1f9c59642d2d3755684071e6eedfcab9d95`.

## One bounded invocation

Immediately before execution, root rehashed all 91 sealed subjects with zero
drift and confirmed both fixed outputs absent. Root then invoked the exact
sealed V3r21 executable once, with no arguments, from the Kira root. Exit code
was `0`. The authority is permanently consumed: `DO_NOT_RERUN_V3R21`.

Exact run outputs:

- `RUN_EVIDENCE.jsonl`: 1,312 bytes, SHA-256
  `76ce1202eb11b0e5d7a9473800179b9f01665cfd235e89558bcfd55aa723d8e4`.
- `PYTHON_CONTROLLER_VALIDATION_OUTCOME.receipt.bin`: 1,016 bytes, SHA-256
  `7c53fc7beef0a350a2c15f8e0dd6c82730c6dea48f56cf24324a78145ecad31a`.
- `RUN_OUTCOME.json`: 2,142 bytes, SHA-256
  `ce26d16412c8e90d752af9f4182368db45241146dedd26b5cdee9ec55de68f6d`.
- `POST_RUN_CHECKPOINT.md`: 3,530 bytes, SHA-256
  `86dbeb13bdd284bda80cedb4e12200151451df90c99db97d4b4832e9218a237b`.

The different reviewer then performed a read-only post-run review. It proved:

- exactly nine LF-only JSON records in required stage order;
- exact 424-byte reservation plus 592-byte success completion and no trailing
  receipt byte;
- terminal stage `60`, exact reservation digest, and executable/audit/
  manifest/controller/contracts/file-identity cross-bindings;
- contract passed mask `32767`, failure/error `0`, and three exact 6,174-byte
  snapshots, all SHA-256
  `ad33386d767b516425dcbed073e22dfc9747a963a64dc5d205483d210acac79d`;
- Python finalize called/result `1/0`, `FreeLibrary` called/result `1/1`, module
  snapshot success, eight modules checked, and neither old module base nor
  exact Python DLL path present.

## Exact meaning and stop boundary

This pass proves only exact authority-contract controls, isolated Python load,
controller definitions, five exported symbols, strict inert projection,
finalization/unload, and durable evidence/receipt controls.

It did not invoke a controller callable, `_build_execution_plan`, bootstrap,
broker, process, AFES, Blender, mesh, body, internal anatomy, physiology,
movement, save, render, or export. It is not a finished-body claim. Kira still
has no accepted full internal/external body.

Any next progress requires a new append-only candidate, a new static seal, and
a different fresh audit before its first bounded execution. V3r21 must never
be rerun.

## Other lanes unchanged by this checkpoint

- Long V9 remains rejected; V10 authoring is static/mocked only.
- Blackwell voice V13 remains rejected; existing latency remains
  `LATENCY_FAIL`.
- Resident-media V13 remains rejected; V14 authoring is static-only.
- Shared Growth isolated V3 remains `ACCEPT_STATIC_ONLY`; integration V2 is
  rejected and nobody receives it.
- Sarah and Video Studio remain owner-frozen.
- Only seven Kira and one Lisa promoted memories are current evidence.

No Sarah, Video Studio, live model, synthesis, playback, media experience,
private-state inspection, AFES, Blender, body, save, render, or export action
was performed for this checkpoint.
