# Kira R25 AFES Python/controller validation V3r20 static preparation

Recorded UTC: `2026-08-11T10:01:56.0829283Z`

Status: `SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT`

Execution authority: `NONE`

## Outcome

V3r20 is the append-only successor to the consumed V3r19 invocation. V3r19
remains sealed and unchanged; it exited `4` at the first source-subject gate,
created no evidence or receipt, and entered no Python, controller, AFES,
Blender, body, save, render, or export path. Its postmortem and exact recheck
are included in the V3r20 predecessor closure.

V3r20 repairs only the native file-identity control defect. It remains inert
and cannot be invoked unless a different reviewer validates its exact sealed
bytes and issues the exact V3r20 one-shot decision. Even a later static
acceptance would stop before plan building, process/broker launch, AFES,
Blender, body mutation, save, render, and export.

## Identity repair

V3r19 used one ambiguous `verify_handle_exact` interface for both identity
capture and retained-identity verification. A zero-initialized output value was
compared with the real identity before the later capture branch, so the first
unchanged subject always failed.

V3r20 removes that interface:

- `verify_handle_capture` proves regular file, exact bytes, exact final path,
  and exact SHA-256, then returns the observed `FILE_ID_INFO`;
- `verify_handle_bound` captures into a fresh local value and compares it with
  a previously retained identity;
- new opens use capture; all same-handle retained rechecks use bound identity;
- the static suite reproduces the exact V3r19 compare-before-capture ordering
  as a negative control and rejects reintroduction of the ambiguous API.

## Author verification

- strict x64 MSVC build: `/W4 /WX /O2 /MT /guard:cf /std:c17` `PASS`;
- pre-seal hostile/static checks: `V3R20_HOSTILE_STATIC_TESTS_PASS`;
- post-seal exact-set/rehash checks: `V3R20_HOSTILE_STATIC_TESTS_PASS`;
- seal closure: `76/76`, unique, exact bytes and SHA-256;
- closure groups: 8 V3r20 author artifacts, 4 V3r14 runtime-authority
  subjects, 13 V3r15 subjects, 17 V3r17 subjects, 14 V3r18 rejected
  subjects, 15 V3r19 accepted-then-consumed-failure subjects, and 5 retained
  runtime locks;
- PE: x64/PE32+, high-entropy VA, ASLR, NX, CFG;
- imported DLLs: only `bcrypt.dll` and `KERNEL32.dll`;
- runtime evidence, runtime receipt, and future-audit directory: absent;
- candidate/Python/controller/AFES/Blender/body execution: false.

## Exact V3r20 artifacts

| Path | Bytes | SHA-256 |
|---|---:|---|
| `Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_python_controller_validation_v3r20.json` | 5,875 | `4f81b85565e62c6de41e9270e696b6a95c48aca4322b36dfd119cc17ac6fa809` |
| `tools/native/kira_r25_afes_python_controller_validation_v3r20.c` | 77,359 | `d9050f8a407595da2e0c733d4d5946043aeb9ee058b9c25aa8f6c025fc368b69` |
| `tools/native/kira_r25_afes_python_controller_validation_v3r20_identity_anchor.h` | 7,563 | `3705f769367596fbf89cdfff4978662f667b3314c063322613520d802b0f71bb` |
| `tools/native/kira_r25_afes_python_controller_validation_v3r20.obj` | 121,813 | `fbee2be25f57e9116eaf19e0b07449f6421fb85172684f102cd0e14af2ed5865` |
| `tools/native/kira_r25_afes_python_controller_validation_v3r20.exe` | 196,608 | `dc48be07c1f4505751d029df017acb48d91fe673a97e89d308cfcececf8b4213` |
| `Testing/test_kira_r25_foundation_afes_python_controller_validation_v3r20_static.ps1` | 19,733 | `8f892d750d9da3512599961a7ad20c3540c81a7d64467224c8bd944c148f9f2e` |
| `RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r20_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md` | 2,760 | `bfea85067eefd5f1eed9f4aef96a8536b10ab625ba3db07c44c030402f10163c` |
| `RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r20_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt` | 2,548 | `81f98c59a5f3d3a5f41a30614171e223c98540080649806e88b738e597502a1e` |
| `RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r20_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json` | 36,152 | `3dacef076bc0046cd42c1fdbe34f331e391177776125efb146465801fcbf13c2` |

## Preserved predecessor truth

V3r19 is `CONSUMED_FAILURE_NO_RETRY`. Its read-only failure recheck is 2,674
bytes, SHA-256
`edef1373f32149d8ed654bb47632cade404224dbca183c8dcd5501d8b6a8b7b9`;
its postmortem is 2,561 bytes, SHA-256
`e97c6733ef8db99e540e893492b237c3c3938a3dd883f1bb1d6303ec346f40f2`.
No V3r19 body or anatomy operation occurred.

## Required next step

A different fresh reviewer must rehash all 76 subjects, rebuild independently,
attack the identity capture/bound split and all inherited gates, and issue
either rejection or the exact V3r20 one-run static authorization. Do not run
this executable merely because the author build and tests pass. No body or
anatomy completion is claimed.
