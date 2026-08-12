# Kira R25 AFES execution-plan validation V3r22 different fresh audit

Recorded UTC: `2026-08-11T14:33:06.5285106Z`

Decision:
`ACCEPTED_FOR_ONE_BOUNDED_PURE_BUILD_EXECUTION_PLAN_VALIDATION_V3R22_ONLY`

Reviewer task: `/root/long_v10_author`

Auditor ID: `codex_different_fresh_v3r22_static_reviewer`

Evidence transcription: `/root` must transcribe these exact proposed bytes
because the different reviewer wrote nothing under Kira. The reviewer authored
no sealed V3r22 subject and did not invoke the candidate.

## Independent result

- The exact 56,404-byte seal
  `d0cdd4220881a5dcc4ec8f15321c07d373971e106d3174c23e1bfb8e4e9f8f5a`
  contains 237 unique paths. All 237 rehashed with zero mismatch: 8 current
  artifacts, 100 runtime fixed bindings, and 137 retained-manifest rows with
  the declared 8 overlaps.
- The author checkpoint rehashed exactly: 4,949 bytes,
  `ca15b96dd45068da1d3d3c7c0ce798cbe9a84d4b5452d6fdf50dbf96dc913991`.
- A scratch-only strict x64 rebuild passed `/W4 /WX /O2 /MT /guard:cf
  /std:c17`, with linker `/guard:cf /WX bcrypt.lib`. The isolated rebuild was
  never invoked and did not overwrite the sealed OBJ or EXE.
- Independent MSVC `/analyze /c /W4 /WX /std:c17` completed with zero
  diagnostics and no suppression.
- Both sealed and rebuilt PE images are x64 PE32+, high-entropy VA, ASLR, NX,
  CFG/CF instrumented with an FID table and 34 Guard CF functions. Their exact
  imported DLL set is `bcrypt.dll` and `KERNEL32.dll`; no process/shell import
  and no static Python DLL import exists.
- V3r20's two real C6385 negative controls reproduced independently: 34 bytes
  from a 32-byte reservation object and 31 bytes from a 29-byte terminal
  object. V3r22's `sizeof(magic)-1` copies and fit assertions analyze cleanly.
- The 19-row consumed V3r21 closure independently reconstructs to 3,622 bytes,
  `e7fb0f85513a0cfd068a9cf79fd5ab9f1070842ac78fbef250b082684e82a898`.
- The 27-row V3r9/V3r10/V3r11 history independently reconstructs to 4,593
  bytes,
  `ac609d3149b18546431377a8ec846d4cd3af098663649c03f41e4d83a0a9ff82`.
- The author's PostSeal suite was rerun read-only and returned
  `V3R22_HOSTILE_STATIC_TESTS_PASS`.
- A separate different-reviewer suite passed 78/78 static and mocked hostile
  probes covering all-row manifest parsing/locking/recheck, exact closures,
  twin controller and transitive helper bindings, module/spec/loader/origin
  fingerprints, native SHA counts, audit and sidecar grammar including NUL and
  length attacks, exact one plan call, finalize/unload/old-base/path absence,
  `CREATE_NEW` output exclusivity, forbidden process injection, and the stop
  boundary.
- The V3r22 evidence and receipt paths remained absent throughout review.

## Exact proposed audit artifacts

| File | Bytes | SHA-256 |
|---|---:|---|
| `INDEPENDENT_AUDIT.tsv` | 1,265 | `b29812ed25f40f83671b532ba46e1d09266844abe02a7dae3b07994f2cba9138` |
| `INDEPENDENT_AUDIT.sha256` | 65 | `10c0602b6be576debd34080480568fb595b99771133488ca252d8ddea5637ccf` |
| `AUDIT_DECISION.json` | 4,528 | `672d88ebeba374d3d92faac7b5904afc33fcf7171f695e799f79c3ce5cba4962` |
| `HOSTILE_STATIC_PROBES.txt` | 4,030 | `2f018f3171f194524794859805581e642e14076ba2fbe1a35e1a046750343a3d` |

The TSV is exactly 18 LF-terminated lines, 1,265 bytes, with no CR or NUL.
Its 65-byte sidecar is the exact lowercase SHA-256 plus LF. The auditor differs
from the author and satisfies the sealed grammar.

## Exact one-shot boundary

After `/root` transcribes and rehashes the exact audit artifacts, at most one
no-argument invocation of the exact sealed V3r22 executable from
`C:/Users/robmc/Kira` is authorized. Success or failure consumes that
authority. The only permitted semantic operation is exactly one retained
`_build_execution_plan` call followed by data-only validation, destruction,
Python finalization, DLL release/absence proof, retained-subject rechecks, and
terminal evidence.

The invocation must stop before bootstrap, broker, process creation, AFES,
Blender, body access or mutation, save, render, and export. It grants no retry,
body-lane continuation, or production authority.

## Truth boundary

This acceptance proves no body, internal or external anatomy, physiology,
movement, activation, save, render, owner acceptance, or live feature. During
the different audit there were zero candidate, Python/controller, plan,
bootstrap, broker, process, AFES, Blender, body, save, render, or export calls.
