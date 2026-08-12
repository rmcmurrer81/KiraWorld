# Kira R25 AFES V3r17 static preparation checkpoint

Recorded UTC: `2026-08-11T06:18:12.5005517Z`

Author: `codex_r25_afes_v3r17_static_author_agent`

Status: `SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT`

Execution authority: **none**

Freeze rule: **this checkpoint and its referenced manifest are the single V3r17
outer closure; no sealed V3r17 subject may be edited after this point.**

## Outcome

V3r16 remains rejected and has no execution authority. Its original outer
checkpoint, its deterministically recorded post-seal/current bytes, and every
file in its rejection evidence bundle are preserved exactly. V3r17 repairs
only the two controlling defects identified by that rejection:

1. V3r17 has one coherent outer checkpoint/manifest closure, created only
   after source, anchor, object, executable, test, contract, runtime-control,
   and build-result bytes reached their final values.
2. The exact future different-auditor directory is bound consistently as
   `RecoverySprint/continuation_20260811/kira_r25_afes_contract_lock_diagnostic_v3r17_fresh_static_audit/attempt_01`.

The diagnostic mechanics remain reservation-first and read-only: two fixed
outputs are reserved with `CREATE_NEW` and write-through before the exact V3r15
contract is opened; two complete snapshots are taken from one handle with
granular size/path/file-ID rechecks; a terminal JSONL record and second packed
receipt record are flushed and read back; then execution stops.

This preparation did not run V3r17 or V3r16, retry V3r15, open the target
contract through either candidate, load Python, read a controller or execution
contract, enter AFES or Blender, open a Blend, or touch a body.

## Exact sealed V3r17 subjects

| Subject | Bytes | SHA-256 |
|---|---:|---|
| `Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_contract_lock_diagnostic_v3r17.json` | 6,437 | `36bec41ecd003c821fd275af0a1c7dc6b2ee6d95584c28eabc7a1da4909d6403` |
| `tools/native/kira_r25_afes_contract_lock_diagnostic_v3r17.c` | 38,490 | `a88eddeab401b0679ec6cebda9d27fbe7b0c14394f5920b13a8cc07f9d8cc2a3` |
| `tools/native/kira_r25_afes_contract_lock_diagnostic_v3r17_identity_anchor.h` | 1,325 | `93b741594f244a17064ddb2630932f5ac1750509f2deba57bdac2e6ff56ad803` |
| `tools/native/kira_r25_afes_contract_lock_diagnostic_v3r17.obj` | 48,816 | `b2ad82fdc5e7c27923adb25a5cc8a26ca2f95413d6a0665a10d3a7c4ce0326c6` |
| `tools/native/kira_r25_afes_contract_lock_diagnostic_v3r17.exe` | 164,864 | `39820aec1e0835b241975b0ac291e798c4767361d97c51cd7d328da0858fcf9c` |
| `Testing/test_kira_r25_foundation_afes_contract_lock_diagnostic_v3r17_static.ps1` | 23,228 | `7d35c70b87cfbe55f42e2044efbf80f79d539c7e72631b4673ac567ae58e710a` |
| `RUNTIME_CONTROL_CHECKPOINT.md` | 2,714 | `e85e4367e09ce2616ec0fcc7d6006c6b25f250f8041a9ba9d026408ce2dee54c` |
| `BUILD_AND_STATIC_TEST_RESULTS.txt` | 1,921 | `a082745ae4b3c873374f25823fae30ac1b1c52f6aaff3d52696c9938dfa2853c` |
| `STATIC_SEAL_MANIFEST.json` | 9,009 | `17c13017c4de4af447e77abecca02d851e999cd1b098c78e32ea07b4768fbfc2` |

`STATIC_SEAL_MANIFEST.json` additionally binds 20 exact V3r16 current and
rejection-evidence subjects. It preserves rather than hides the V3r16 outer
seal mismatch: the outer checkpoint recorded manifest SHA-256
`434a2e11bb574e299136188556fafab8e5f709b05025d0a15cba1c25b3820234`,
while the preserved current V3r16 manifest is SHA-256
`ae32d720ebdc3cf69f2895be47c26c5040afde9e248488c193c270645c08b4a8`.
V3r16 remains `REJECT`.

## Static verification before freeze

- MSVC x64 strict compilation passed with `/W4 /WX /O2 /MT /guard:cf
  /std:c17`; no warning was emitted.
- Hostile static suite passed `179/179`.
- The suite checked all 20 preserved V3r16 subjects and rejected narrowed
  sharing, removed snapshot two, weakened `CREATE_NEW`, inserted Python,
  inserted process creation, target drift, and diagnosis before reservation.
- Read-only PE inspection found x64 PE32+, CFG, high-entropy VA, ASLR, NX, no
  delay imports, and exactly `bcrypt.dll` plus `KERNEL32.dll` import DLLs.
- No Python, Blender, `CreateProcess`, or `ShellExecute` image/import is present.

The candidate executable was **not run**. Both fixed runtime outputs and both
future-audit files were absent at freeze.

## Exact future different-auditor binding

The different fresh auditor may create evidence only under:

`RecoverySprint/continuation_20260811/kira_r25_afes_contract_lock_diagnostic_v3r17_fresh_static_audit/attempt_01`

The candidate binds exactly:

- `INDEPENDENT_AUDIT.tsv`
- `INDEPENDENT_AUDIT.sha256`

Only that different auditor may issue
`ACCEPTED_FOR_ONE_BOUNDED_CONTRACT_LOCK_DIAGNOSTIC_ONLY`. This checkpoint does
not issue it and grants no runtime authority.

## Absolute stop boundary

V3r17 must stop before Python, controller, execution contract, plan builder,
broker, child, shell, process creation, AFES, Blender, Blend, body, mesh,
armature, anatomy, material, pose, movement, save, render, or export. It is not
a body result and cannot be promoted to production. No main registry or handoff
file was edited by this lane.

## Required next step

`DIFFERENT_FRESH_EXACT_BYTE_HOSTILE_STATIC_AUDIT_REQUIRED`

The different auditor must rehash this exact outer closure and all 20 preserved
V3r16/rejection subjects, independently compile and inspect without running the
candidate, rerun hostile static tests, verify the exact audit path, and either
reject V3r17 or issue the one bounded diagnostic-only decision. Any drift of a
sealed V3r17 subject after this freeze is an automatic rejection.
