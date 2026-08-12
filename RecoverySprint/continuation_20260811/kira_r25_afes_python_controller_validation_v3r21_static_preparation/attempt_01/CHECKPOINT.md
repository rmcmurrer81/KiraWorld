# Kira R25 AFES Python/controller validation V3r21 static preparation

Recorded UTC: `2026-08-11T11:02:41.2474730Z`

Status: `SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT`

Execution authority: `NONE`

## Outcome

V3r21 is the append-only successor to V3r20. V3r20 remains sealed, rejected,
and unexecuted. Its different fresh review found two real C6385 out-of-bounds
reads in durable receipt construction: a 34-byte copy from a 32-byte
reservation string object and a 31-byte copy from a 29-byte terminal string
object. Static executable inspection also proved the reservation read consumed
its terminator plus `KI` from an adjacent literal. V3r20 created no evidence or
receipt and entered no Python, controller, AFES, Blender, body, save, render, or
export path.

V3r21 repairs only that native receipt/analyzer boundary while preserving all
prior gates. It remains inert and cannot be invoked unless a different reviewer
validates its exact sealed bytes and issues the exact V3r21 one-shot decision.
Even a later static acceptance would stop before plan building, process/broker
launch, AFES, Blender, body mutation, save, render, and export.

## Receipt and analyzer repair

- reservation and terminal magic are named byte arrays;
- copy bounds are `sizeof(array) - 1U` after the complete record is zeroed;
- C17 `_Static_assert` checks prove each literal payload fits its destination;
- final-path scratch buffers moved from large stack frames to zeroed heap
  storage, receive explicit terminators, and are wiped/freed;
- the Python module path is bounded by `MAX_PATH`;
- handle cleanup requires a value that is neither `NULL` nor
  `INVALID_HANDLE_VALUE`;
- independent author-side MSVC `/analyze` completed with zero unsuppressed
  warnings and no warning suppression.

The exact V3r20 author artifacts, seal/checkpoint, and five rejection files form
a 15-subject immutable negative-control closure. V3r20 was not retried.

## Author verification

- strict x64 MSVC build: `/W4 /WX /O2 /MT /guard:cf /std:c17` `PASS`;
- MSVC `/analyze /W4 /WX /std:c17`: `PASS_ZERO_UNSUPPRESSED_WARNINGS`;
- pre-seal hostile/static checks: `V3R21_HOSTILE_STATIC_TESTS_PASS`;
- post-seal exact-set/rehash checks: `V3R21_HOSTILE_STATIC_TESTS_PASS`;
- seal closure: `91/91`, unique, exact bytes and SHA-256;
- closure groups: 8 V3r21 author artifacts, 4 V3r14 runtime-authority
  subjects, 13 V3r15 subjects, 17 V3r17 subjects, 14 V3r18 rejected
  subjects, 15 V3r19 accepted-then-consumed-failure subjects, 15 V3r20
  rejected/unexecuted subjects, and 5 retained runtime locks;
- PE: x64/PE32+, high-entropy VA, ASLR, NX, CFG with FID table;
- imported DLLs: only `bcrypt.dll` and `KERNEL32.dll`;
- runtime evidence, runtime receipt, and future-audit directory: absent;
- candidate/Python/controller/AFES/Blender/body execution: false.

## Exact V3r21 artifacts

| Path | Bytes | SHA-256 |
|---|---:|---|
| `Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_python_controller_validation_v3r21.json` | 8,327 | `008ec197cf8f05f1ea26eb42c240d9260e5d03d1a3259b9c27293badc8e7267b` |
| `tools/native/kira_r25_afes_python_controller_validation_v3r21.c` | 84,245 | `7e78c480643fb7735b1d6738e565c06d169cbd50410e040c8f1f8c7416a0f6f6` |
| `tools/native/kira_r25_afes_python_controller_validation_v3r21_identity_anchor.h` | 9,825 | `99c5a828cbe2970191a69d02c4f5492c4214b5a72404e9009a83181c85e521da` |
| `tools/native/kira_r25_afes_python_controller_validation_v3r21.obj` | 137,184 | `b1711756e91f52068abaf43f5d7b0e948f22115e76f333e97fecf2b3f968b4bf` |
| `tools/native/kira_r25_afes_python_controller_validation_v3r21.exe` | 203,776 | `d61bc0db5fa8229dfd5922aa3ecc51116908378bb80bcb443739d8c7d96c83fc` |
| `Testing/test_kira_r25_foundation_afes_python_controller_validation_v3r21_static.ps1` | 24,053 | `2be6643c7fc8a92a328c675cde7fca19d142a26ce17c4735d135d1a1c3e3e9c5` |
| `RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r21_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md` | 3,328 | `875b36cfe5a3d1a648a6b123800ec25711fe6f3e498e6de69817215d801f0486` |
| `RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r21_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt` | 3,144 | `f6e498f23971ff19d2622ab5c0e43b0b1946032cefa746225e1a46740fbfc38a` |
| `RecoverySprint/continuation_20260811/kira_r25_afes_python_controller_validation_v3r21_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json` | 43,485 | `6323c0c8708dd871c411b2f8a8c236d28634cc31c94b749f8a79f8295f719f20` |

## Preserved predecessor truth

V3r20 is `REJECTED_NO_EXECUTION_AUTHORITY`. Its independent rejection audit is
4,841 bytes, SHA-256
`790b122d1eb135754b78673b57fa74e48babf0bec4b5e07498015b95bd7a1273`;
its `/analyze` evidence is 1,878 bytes, SHA-256
`697a9987dbd224478ae4e759bf00ee28b3928b03494ddf8283cf103e78acaa8c`;
and its rejection checkpoint is 2,799 bytes, SHA-256
`16174d65ab9da57c1f9508de2ef71aae07aa5d95fd2c1bed7517a5ba35c40a4c`.
No V3r20 body or anatomy operation occurred.

## Required next step

A different fresh reviewer must rehash all 91 subjects, rebuild independently,
run `/analyze`, attack the safe literal-copy and heap/termination/handle repairs
plus every inherited gate, and issue either rejection or the exact V3r21
one-run static authorization. Do not run this executable merely because the
author build and tests pass. No body or anatomy completion is claimed.
