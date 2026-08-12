# Kira R25 AFES execution-plan validation V3r24 — author checkpoint

Date: 2026-08-11  
Attempt: `attempt_01`  
Status: `SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT`  
Execution authority: **NONE**  
Candidate executed: **false**

## Outcome

V3r24 is an append-only static diagnostic candidate. It was authored, compiled, analyzed, PE-inspected, hostile-tested, and sealed only in `C:\Users\robmc\Documents\Codex\2026-08-11\c\work\body_v3r24_author`. Nothing in `C:\Users\robmc\Kira` was edited. Neither the V3r24 nor V3r23 executable was invoked. No Python runtime, retained controller, plan callable, bootstrap, broker, process, AFES path, Blender path, body path, save, render, or export path was invoked.

The exact author-side PreSeal and PostSeal tests both returned `V3R24_HOSTILE_STATIC_TESTS_PASS`. Strict MSVC x64 `/W4 /WX /O2 /MT /guard:cf` compile/link returned zero warnings and errors. MSVC `/analyze /W4 /WX` returned an empty `<DEFECTS>` set with no suppression. The rebuilt PE is machine `8664` (x64), optional-header `20B` (PE32+), and has high-entropy VA, dynamic base/ASLR, NX compatibility, and CFG. The exact imported DLL set is `bcrypt.dll` and `KERNEL32.dll`; there is no static Python DLL or process/shell DLL import.

## Corrected failure-cause truth

The V3r22 durable record proves only a failure somewhere inside its former stage-40 validator boundary. The actual V3r22 stage-40 cause remains **UNKNOWN**.

The V3r23 claim that unresolved controller annotation names caused that failure is rejected. The exact installed `C:\Python314\include\cpython\code.h` is 14,708 bytes, SHA-256 `65fe295bd90aab0a5380c4b3c400713917af7f904fbb0ac86e76ffff2de1ab18`, and defines `CO_FUTURE_ANNOTATIONS` as `0x1000000`. The exact retained standard-library zip's `__future__.py` defines that flag as annotations-become-strings behavior. Both V3r22 and V3r23 compile the retained controller with `flags=0x1000000`, `dont_inherit=True`, and `optimize=0`.

V3r24 statically asserts `CO_FUTURE_ANNOTATIONS == 0x1000000`, requires that bit on the compiled module and every retained controller function code object, requires every annotated controller function's generated `__annotate__` stringizer, and fingerprints each stringizer's code/globals/defaults/keyword defaults/closure/metadata. It never reads `function.__annotations__` and never calls `function.__annotate__`. Therefore unresolved annotation-name evaluation is an excluded cause and cannot silently return as a diagnosis.

## Predecessor closures

- V3r23 rejected closure: exactly 15 rows (10 author artifacts plus 5 independent rejection artifacts), 2,728 canonical bytes, SHA-256 `0b09c1f71154b4d56559f043f08076940bcc60e7919d6bcd8e9c3cde3b2a4ea0`, authority `REJECTED_NO_EXECUTION_AUTHORITY`, candidate executed false.
- V3r22 consumed failure closure: exactly 20 rows, 3,779 canonical bytes, SHA-256 `7057deb657f5e235892180e5d694f139450d44897f9353ac3bdb1f15d730aec0`, authority `CONSUMED_FAILURE_DO_NOT_RERUN`.
- Retained manifest: exactly 24,975 bytes, SHA-256 `6df14df08a3f4c5a68c22b3eb3ccd8d8ce46209a156784a7582357071fc78d96`, 139 exact CRLF-terminated lines, 137 data rows. All rows were rehashed during both author test phases.

The runtime fixed array contains exactly 136 unique subjects: the three current self-binding subjects, the exact CPython header, all 15 V3r23 rejected artifacts, all 20 V3r22 consumed-failure artifacts, and the inherited transitive closure. The seal is the exact unique union of 8 current artifacts, 136 fixed bindings, and 137 retained rows: 273 unique subjects.

## Bounded localization telemetry

The prior coarse stage 40 is replaced inside the validator by setup checkpoints `100`, `110`, `120`, and `130`; 21 fallible operations bracketed by entered/returned checkpoint pairs; and success checkpoint `230`. The pairs are `140/141`, `150/151`, `160/161`, `170/171`, `180/181`, `190/191`, `200/201`, `202/203`, `204/205`, `206/207`, `208/209`, `210/211`, `212/213`, `214/215`, `216/217`, `218/219`, `220/221`, `222/223`, `224/225`, `226/227`, and `228/229`.

`operation_enters` increments immediately before each named operation and `operation_returns` immediately after it. Success requires both to equal 21. The sole `_build_execution_plan` expression has its own attempt immediately before and return immediately after; success requires both to equal one. Any exception retains the last checkpoint and counters, captures only a sanitized ASCII exception type up to 63 bytes and message up to 191 bytes, then follows bounded finalization/unload/recheck/terminal cleanup. Traceback and private exception state are not captured. No retry exists.

## Different-audit grammar

Any future acceptance file must be authored by a different reviewer after rehashing these exact bytes. The TSV is exactly 29 LF-only lines: magic `KIRA_R25_AFES_EXECUTION_PLAN_VALIDATION_AUDIT_V3R24\t1` plus 28 ordered fields. It rejects NUL, CR, missing final LF, duplicates, reordering, malformed lower-hex digests, the author as auditor, mismatched current hashes, either predecessor root, the retained root, compile flag/name, excluded cause, count bounds, stop-before boundary, and both predecessor authority states. Its sidecar is exactly 64 lower-hex characters plus LF. No future audit root exists in this author tree.

The required decision is `ACCEPTED_FOR_ONE_BOUNDED_DIAGNOSTIC_PURE_BUILD_EXECUTION_PLAN_VALIDATION_V3R24_ONLY`; this checkpoint does not issue that decision. A different reviewer may reject the candidate. Execution authority remains **NONE** unless and until an exact-byte different review explicitly accepts it.

## Frozen author artifacts

The checkpoint itself is frozen after this table and its identity is reported externally with the completed bundle.

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_execution_plan_validation_v3r24.json` | 17141 | `282b458123f1b48989e1315d90f11663443f84637671e2d0a18bb6af8f22aa3c` |
| `tools/native/kira_r25_afes_execution_plan_validation_v3r24.c` | 148570 | `8bb0974a531bf40c28c9e9400f0b6dec22d87ea57296b2aae7de06322c408ad5` |
| `tools/native/kira_r25_afes_execution_plan_validation_v3r24_identity_anchor.h` | 7447 | `625df0dc5ebd817cdcca767a018cdace631b966c8b57d9dae46ac3ba5af546e9` |
| `tools/native/kira_r25_afes_execution_plan_validation_v3r24.obj` | 234278 | `cd66e41fce8ede60f34bf8590a88c9f8ddc08571d612e4417235f26d1aeae287` |
| `tools/native/kira_r25_afes_execution_plan_validation_v3r24.exe` | 264704 | `281d427482657a73096fa6b44e2092e6e54b760e59c73c37f562e24ad6b03bb9` |
| `Testing/test_kira_r25_foundation_afes_execution_plan_validation_v3r24_static.ps1` | 25519 | `1010f4b122aab45bdaaabd4363d0e33fb93c620d44dc7f342c66e7045c858036` |
| `RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md` | 6780 | `c954a4a3c77e5ed4307837842a964b560e3ad83d6635e2a3e8de46c5ef828658` |
| `RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt` | 6244 | `0473c193b4093358efb04522d5c56dc4de312cc85066dfc55f9f80092d738a20` |
| `RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r24_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json` | 144602 | `fc63c0ada6db0737988724c78acc08907fa319f6badb9de81a930554f6a1e640` |

Disposable analyzer evidence (not seal subjects): `build_cache/v3r24_analyze.obj`, 159,946 bytes, SHA-256 `5194794cf1be264057d04721267846e037db91d12ccee54afd87c7ee303d7777`; `build_cache/v3r24_analyze.xml`, 59 bytes, SHA-256 `ba052e3b011b8f8a3e59a7b5c3120d3c9496a6c3e2fd73c55013bde5e2642bc5`.

## Downstream owner routing

Only a later independently accepted body-engineering result supported by actual Blender, save, and render evidence may feed the Avatar Builder reusable method/template layer. Rejected results may feed only `DO_NOT_REPEAT` tests. V3r24 is pending static review, has no Blender/save/render evidence, integrates no body, and makes no body claim.

## Stop-before handoff

The next action is a different, independent, read-only static review in a separate scratch path. That reviewer must rehash all 273 sealed subjects, run the authored test only in `PostSeal`, rebuild/analyze the exact source separately, inspect the rebuilt PE/imports, audit the annotation exclusion and 21-pair telemetry, and either stage the exact 29-line acceptance grammar or a rejection bundle. The reviewer must not invoke the sealed executable, Python controller, plan callable, Blender, AFES, body, save, render, or export.
