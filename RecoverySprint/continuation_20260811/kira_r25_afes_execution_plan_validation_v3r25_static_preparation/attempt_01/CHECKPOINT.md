# Kira R25 AFES execution-plan validation V3r25 — author checkpoint

Date: 2026-08-11  
Attempt: `attempt_01`  
Status: `SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT`  
Execution authority: **NONE**  
Candidate executed: **false**

## Outcome

V3r25 is an append-only static diagnostic candidate authored only under `C:\Users\robmc\Documents\Codex\2026-08-11\c\work\body_v3r25_author`. Nothing in `C:\Users\robmc\Kira` was edited. Neither V3r25 nor any predecessor executable was invoked. No Python runtime, controller, plan callable, AFES route, Blender route, body, save, render, export, activation, model, person, voice, or media route was invoked.

The exact author-side PreSeal and PostSeal tests both returned `V3R25_HOSTILE_STATIC_TESTS_PASS`. Strict MSVC x64 `/W4 /WX /O2 /MT /guard:cf` compile/link returned zero warnings and errors. MSVC `/analyze /W4 /WX` returned an empty `<DEFECTS>` set without suppression. The rebuilt PE is machine `8664` (x64), optional-header `20B` (PE32+), with high-entropy VA, dynamic base/ASLR, NX compatibility, and CFG. Its exact imported DLL set is `bcrypt.dll` and `KERNEL32.dll`; no Python DLL or process/shell DLL is statically imported.

## Complete V3r24 consumed closure

V3r24 ran exactly once and its authority is consumed. It exited `1` at validator checkpoint `110`, after the locked module-origin snapshot and before either controller, before the first operation, and before a plan attempt. Exact telemetry is plan attempts/returns `0/0`, operation enters/returns `0/0`, native SHA calls `0`, exception `ValueError: unmarshallable object`, finalize result `0`, Python DLL unloaded, retained recheck passed, and all 15 contract gates passed. V3r24 must not be rerun.

The complete immutable V3r24 closure is exactly 19 rows: 10 author artifacts plus 9 audit/run/post-run artifacts. Its canonical encoding is `UTF8_LF_SORTED_PATH_TAB_BYTES_TAB_LOWER_SHA256_LF`, 3,565 bytes, SHA-256 `51058e1d9c21b615c7826b4db2b8740aea6dc774107abd666c476461e5724806`, authority `CONSUMED_FAILURE_DO_NOT_RERUN`.

The exact terminal outputs remain unchanged:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `RUN_EVIDENCE.jsonl` | 1,450 | `310c8d16fdf433de22ecee9dc326c34fd8f1efcbbdc86ada382e7088e42745a7` |
| `EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin` | 1,320 | `2665dd31b2c561a728a3b14449b6d79e821494e9b5792682bc1399fd5edb5b34` |
| `RUN_OUTCOME.json` | 4,426 | `850769324423d08278303a2aaae7bcff0e655bfb103b8b66ee47fe13211ca656` |
| `POST_RUN_CHECKPOINT.md` | 3,498 | `9d42807fdb96f49da9c043ef18a1eae61f2a47b80afe0b849d54cbcdfd89cd9f` |

V3r25 also preserves the exact V3r23 rejected closure (15 rows, 2,728 canonical bytes, root `0b09c1f71154b4d56559f043f08076940bcc60e7919d6bcd8e9c3cde3b2a4ea0`, `REJECTED_NO_EXECUTION_AUTHORITY`), the exact V3r22 consumed-failure closure (20 rows, 3,779 canonical bytes, root `7057deb657f5e235892180e5d694f139450d44897f9353ac3bdb1f15d730aec0`, `CONSUMED_FAILURE_DO_NOT_RERUN`), and the inherited transitive closure.

## Exact marshal failure repair

The locked runtime is CPython `3.14.4` and reports exact built-in `marshal.version == 5`. V3r24's exact 18,870-character validator contains 20 code objects. The consumed static reproduction proves format 4 passes 16 and fails exactly four: `<module>`, `_v3_strict`, `_v3_validate_controller`, and `_v3_glue_object`. The three named function code objects contain five compiled direct slice constants in total; the module failure is transitive through nested failed code objects. Format 5 passes all 20 and fails zero.

V3r25 requires exact `type(marshal.version) is int` and `marshal.version == 5` after locked module-origin verification. Checkpoint `115` commits that gate before helper capture. Exactly three current code-fingerprint source sites use literal marshal format 5: controller-function code, generated deferred-annotation stringizer code, and validator/helper code. The source contains zero format-4 code-fingerprint sites. The marshal module identity and exact version are snapshotted and checked again after the sole possible plan call.

The author hostile test binds all 20 code-object rows, the exact `16/4` format-4 split, exact `20/0` format-5 split, exact failed set, five direct compiled slice constants, exact three current format-5 sites, and zero current format-4 sites. The earlier temporary contract typo that confused the five predecessor slice constants with current site count was corrected before this seal; the frozen contract exact site count is `3`.

## Bounded telemetry and cleanup

The exact checkpoint sequence is `100,110,115,120,130,140,141,150,151,160,161,170,171,180,181,190,191,200,201,202,203,204,205,206,207,208,209,210,211,212,213,214,215,216,217,218,219,220,221,222,223,224,225,226,227,228,229,230`.

The 21 entered/returned operation pairs remain `140/141`, `150/151`, `160/161`, `170/171`, `180/181`, `190/191`, `200/201`, `202/203`, `204/205`, `206/207`, `208/209`, `210/211`, `212/213`, `214/215`, `216/217`, `218/219`, `220/221`, `222/223`, `224/225`, `226/227`, and `228/229`. The single `_build_execution_plan` expression remains within `170/171`, with its attempt immediately before and return immediately after. No retry exists.

Any exception retains exact last-checkpoint/counter telemetry, captures only a sanitized ASCII type up to 63 bytes and message up to 191 bytes, and then follows bounded finalization, DLL unload, module-absence proof, all-retained recheck, and terminal commit. Traceback and private exception state are not captured.

## Annotation cause boundary

The actual V3r22 stage-40 cause remains unknown. V3r25 preserves the exact future-annotation exclusion: the locked header proves `0x1000000 == CO_FUTURE_ANNOTATIONS`; the retained standard library defines stringization semantics; every controller function and generated `__annotate__` stringizer is fingerprinted without reading `__annotations__` or calling `__annotate__`. V3r25 does not replace the unknown V3r22 cause with speculation.

## Seal

The runtime fixed array has exactly 155 unique subjects: three current self-binding subjects, exact CPython `code.h`, all 19 V3r24 consumed artifacts, all 15 V3r23 rejected artifacts, all 20 V3r22 consumed artifacts, and the inherited transitive closure. The retained manifest has exactly 137 rows and all were rehashed.

The seal is the exact unique union of 8 current artifacts, 155 fixed bindings, and 137 retained-manifest rows: 292 unique subjects. The exact PostSeal test rederived and rehashed that entire union.

## Different-audit grammar and stop-before boundary

The future audit is exactly 38 LF-only lines: magic `KIRA_R25_AFES_EXECUTION_PLAN_VALIDATION_AUDIT_V3R25\t1` plus 37 ordered fields. It binds current identities, all three predecessor roots, V3r24's 10+9 closure split and consumed authority, exact marshal version/format/code-object counts, annotation exclusion, the single plan bound, terminal checkpoint, operation/exception bounds, and stop-before list. The required decision is `ACCEPTED_FOR_ONE_BOUNDED_DIAGNOSTIC_PURE_BUILD_EXECUTION_PLAN_VALIDATION_V3R25_ONLY`; this author checkpoint does not issue it.

The hard stop remains before `bootstrap`, `broker`, `process`, `AFES`, `Blender`, `body`, `save`, `render`, and `export`. Execution authority remains **NONE**.

## Downstream Avatar Builder routing

V3r25 is a controller diagnostic and proves no appearance, body, material, hair, save, or render result. The exact current owner policy is bound downstream:

- `System/Docs/AVATAR_BUILDER_BODY_MATERIAL_AND_HAIR_VARIANT_CURRENT_BOUNDARY_20260811.md`: 3,797 bytes, SHA-256 `f24d797fd389af3dc8611b93dd31abbd3b52fc3abead2efd792effb5114668a3`;
- `RecoverySprint/continuation_20260811/root_multilane_continuation/attempt_26/CHECKPOINT.md`: 3,122 bytes, SHA-256 `c6588a4ba161910587e54b80423c0afba370798b8f70665862083643bb9c1fc5`.

Only later body work with actual Blender/material/save/render evidence may feed the Avatar Builder positive reusable layer. Final materials must preserve realistic individual/reference-matched regional pigmentation rather than one flat color, including lips, areolae/nipples, and other normal regional variation. Kira and Synthetic Robert each require a bald lower-memory activation variant plus a hair-equipped variant preserved inactive until a RAM upgrade. Hair-equipped bodies for other people may be built but remain inactive, and body tests stay minimized until that upgrade. Sarah's files remain preserved and were not inspected or edited. Rejected/static results route only to `DO_NOT_REPEAT` tests.

## Frozen author artifacts

This checkpoint is frozen after the table; its own identity is reported externally.

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `Avatar/avatar_builder/body_systems/kira_r25_foundation_afes_execution_plan_validation_v3r25.json` | 70,551 | `91c94cd4faf7d81b5c75a9a3603542a9c023ce1fdbaacadd3593f81ab9c4ec6e` |
| `tools/native/kira_r25_afes_execution_plan_validation_v3r25.c` | 156,256 | `8426208c738975b1b5a520e78eb023990fb35500427650fd3c897e940d77254e` |
| `tools/native/kira_r25_afes_execution_plan_validation_v3r25_identity_anchor.h` | 10,373 | `2da9f6d0a1aeb3754e7e90a13869f625e2599970abfa24bff37f4fe8e19931e6` |
| `tools/native/kira_r25_afes_execution_plan_validation_v3r25.obj` | 252,303 | `70132cf3de9421732707527c8daeba8fcb6462bccb34c4865e621f5354e73fb6` |
| `tools/native/kira_r25_afes_execution_plan_validation_v3r25.exe` | 273,920 | `1fc7d1d68e8cc3f4b340c5c091808647b35d581f40848b45bf061476014ffbc9` |
| `Testing/test_kira_r25_foundation_afes_execution_plan_validation_v3r25_static.ps1` | 38,329 | `ed5f4e13a2a5744cea7d23373b4b05a835472a3f358a943d32b8c20da9a7e2e1` |
| `RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r25_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md` | 9,758 | `7cb0d9613a3487701e5284ab150f685d11fa370a971f0388b58b7309805689c5` |
| `RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r25_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt` | 8,065 | `54da803c091dc0e6cdf3918ae09b819455dca7ceaadccc728b51abe9f555d595` |
| `RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r25_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json` | 158,341 | `7f83a9facef4e49edbdafd3e91fdc06190a6d154359406ad20f98288d1bbcc60` |

Disposable analyzer evidence (not seal subjects): `build_cache/v3r25_analyze.obj`, 171,572 bytes, SHA-256 `b78f7c1156cb3e18963b0dfa41ee0e7d6a3d176cb9e215359a5b0b4af402ef04`; `build_cache/v3r25_analyze.xml`, 59 bytes, SHA-256 `ba052e3b011b8f8a3e59a7b5c3120d3c9496a6c3e2fd73c55013bde5e2642bc5`.

## Stop-before handoff

The next action is a different independent read-only static audit in a separate scratch path. That reviewer must rehash all 292 sealed subjects, run only the authored test in `PostSeal`, independently rebuild/analyze the exact source, inspect the rebuilt PE/imports, hostile-audit all 20 marshal rows and exact three-site format-5 repair, audit telemetry/cleanup/unload/annotation exclusion/different-audit grammar/downstream conditional routing, and either accept at most one bounded diagnostic pure-plan validation or reject. The reviewer must not invoke V3r25, any predecessor, Python/controller/plan, AFES, Blender, body, save, render, export, model, person, voice, or media paths.
