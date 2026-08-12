# Kira R25 AFES execution-plan validation V3r25 — runtime control checkpoint

Date: 2026-08-11  
Attempt: `attempt_01`  
Status: `STATIC_AUTHOR_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT_NO_EXECUTION_AUTHORITY`  
Execution authority: **NONE**  
Candidate executed: **false**

## Exact purpose

V3r25 is an append-only repair of the separately proven V3r24 failure. It does not repair or claim a body, anatomy, Blender scene, save, render, or export. It may become eligible for at most one bounded diagnostic invocation only after a different reviewer independently rehashes, rebuilds, analyzes, PE-inspects, hostile-tests, and explicitly accepts its exact sealed bytes.

V3r24 was invoked exactly once and its authority is consumed. It exited `1` at validator checkpoint `110`, before either controller was constructed, before the first entered operation, and before any `_build_execution_plan` attempt. Durable telemetry is exactly: plan attempts `0`, plan returns `0`, operation enters `0`, operation returns `0`, exception type `ValueError`, exception message `unmarshallable object`, Python finalize result `0`, Python DLL unloaded, retained recheck passed, and all 15 outer contract gates passed. V3r24 must not be rerun.

## Exact failure repair

The locked runtime is CPython `3.14.4`; its exact built-in `marshal.version` is `5`. V3r24 hard-coded `marshal.dumps(code, 4)` at every code-fingerprint route. Its exact 18,870-character embedded validator contains 20 code objects. A preserved read-only root-cause reproduction established:

- marshal format 4: 16 code objects encode and 4 fail with `ValueError: unmarshallable object`;
- the four direct failing code objects are `<module>`, `_v3_strict`, `_v3_validate_controller`, and `_v3_glue_object`;
- `_v3_strict` contains two direct slice constants, `_v3_validate_controller` contains one, and `_v3_glue_object` contains two; the module failure is transitive through nested failed code objects;
- marshal format 5: all 20 encode and zero fail.

V3r25 therefore requires exact `type(marshal.version) is int` and `marshal.version == 5` after locked module-origin verification and before any helper code fingerprint. Checkpoint `115` means that exact version gate returned. Every code-object fingerprint route uses literal format `5`: controller function code, generated deferred-annotation stringizer code, and validator/helper code. There is no format-4 code-fingerprint call in V3r25. The marshal module identity and version are snapshotted and checked again after the sole possible plan call.

| Code object | Direct slice constants | Format 4 | Format 5 |
|---|---:|---|---|
| `<module>` | 0 | fail, transitive nested constant | pass |
| `_v3_origin` | 0 | pass | pass |
| `_v3_module_fingerprint` | 0 | pass | pass |
| `_v3_sha` | 0 | pass | pass |
| `_v3_hex` | 0 | pass | pass |
| `_v3_hex.<locals>.<genexpr>` | 0 | pass | pass |
| `_v3_pairs` | 0 | pass | pass |
| `_v3_reject_number` | 0 | pass | pass |
| `_v3_strict` | 2 | fail | pass |
| `_v3_blob_trap` | 0 | pass | pass |
| `_v3_canonical_trap` | 0 | pass | pass |
| `_v3_new_controller` | 0 | pass | pass |
| `_v3_new_controller.<locals>.<dictcomp>` | 0 | pass | pass |
| `_v3_code_bytes` | 0 | pass | pass |
| `_v3_annotate_fingerprint` | 0 | pass | pass |
| `_v3_validate_controller` | 1 | fail | pass |
| `_v3_glue_object` | 2 | fail | pass |
| `_v3_capture_helpers` | 0 | pass | pass |
| module retained-dictionary guard generator | 0 | pass | pass |
| module controller-code-root generator | 0 | pass | pass |

The matrix above is a static predecessor diagnosis bound to the exact V3r24 run and root-cause evidence. It is not a V3r25 runtime result. The V3r25 hostile author test must bind all 20 rows, the `16/4` format-4 split, the `20/0` format-5 split, all five direct slice constants in the three named function code objects, the exact format-5 source sites, the exact version gate, and the absence of format 4.

## Immutable predecessor closure

The complete V3r24 closure contains exactly 19 rows: 10 frozen author artifacts and 9 frozen audit/run/post-run artifacts. Its canonical encoding is `UTF8_LF_SORTED_PATH_TAB_BYTES_TAB_LOWER_SHA256_LF`, exactly 3,565 bytes, SHA-256 `51058e1d9c21b615c7826b4db2b8740aea6dc774107abd666c476461e5724806`, authority `CONSUMED_FAILURE_DO_NOT_RERUN`.

The four exact terminal V3r24 outputs are preserved unchanged:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `RUN_EVIDENCE.jsonl` | 1,450 | `310c8d16fdf433de22ecee9dc326c34fd8f1efcbbdc86ada382e7088e42745a7` |
| `EXECUTION_PLAN_VALIDATION_OUTCOME.receipt.bin` | 1,320 | `2665dd31b2c561a728a3b14449b6d79e821494e9b5792682bc1399fd5edb5b34` |
| `RUN_OUTCOME.json` | 4,426 | `850769324423d08278303a2aaae7bcff0e655bfb103b8b66ee47fe13211ca656` |
| `POST_RUN_CHECKPOINT.md` | 3,498 | `9d42807fdb96f49da9c043ef18a1eae61f2a47b80afe0b849d54cbcdfd89cd9f` |

V3r25 also preserves the inherited exact V3r23 rejected closure (15 rows; root `0b09c1f71154b4d56559f043f08076940bcc60e7919d6bcd8e9c3cde3b2a4ea0`; `REJECTED_NO_EXECUTION_AUTHORITY`), exact V3r22 consumed-failure closure (20 rows; root `7057deb657f5e235892180e5d694f139450d44897f9353ac3bdb1f15d730aec0`; `CONSUMED_FAILURE_DO_NOT_RERUN`), exact CPython `code.h`, and the complete inherited transitive closure.

## Bounded diagnostic boundary

The validator checkpoint sequence is exactly `100,110,115,120,130,140,141,150,151,160,161,170,171,180,181,190,191,200,201,202,203,204,205,206,207,208,209,210,211,212,213,214,215,216,217,218,219,220,221,222,223,224,225,226,227,228,229,230`.

The 21 fallible operation pairs remain `140/141`, `150/151`, `160/161`, `170/171`, `180/181`, `190/191`, `200/201`, `202/203`, `204/205`, `206/207`, `208/209`, `210/211`, `212/213`, `214/215`, `216/217`, `218/219`, `220/221`, `222/223`, `224/225`, `226/227`, and `228/229`. The only `_build_execution_plan` expression remains inside `170/171`, with the attempt counter immediately before it and return counter immediately after it. No retry exists.

Any exception retains the last checkpoint and exact counters, captures only a sanitized ASCII exception type up to 63 bytes and message up to 191 bytes, and then follows bounded finalization, DLL unload, module-absence proof, all-retained recheck, and terminal commit. Traceback and private exception state are not captured.

## Annotation exclusion remains exact

The actual V3r22 stage-40 cause remains unknown. V3r25 does not replace that boundary with speculation. The exact header still proves `0x1000000 == CO_FUTURE_ANNOTATIONS`; the exact retained standard library defines annotations-become-strings semantics; each retained controller function and generated `__annotate__` stringizer is fingerprinted without reading `__annotations__` or calling `__annotate__`. Unresolved annotation-name evaluation remains an excluded V3r22 cause.

## Different-audit and stop-before boundary

The future audit grammar is exactly 38 LF-only lines: one magic line plus 37 ordered fields. It binds the current executable/anchor/contract/source/test/control, the retained manifest, all three predecessor roots, V3r24's `10 + 9` closure split and consumed authority, exact marshal version/format and `20/4/20` code-object counts, annotation exclusion, single plan attempt, checkpoint/counter/exception bounds, and stop-before list. The auditor identifier must differ from `codex_r25_afes_v3r25_static_author`.

No V3r25 future audit root, evidence file, or receipt may exist during author sealing. No V3r25 or predecessor executable may be invoked. The next action, after author sealing, is a different independent read-only static audit.

The hard stop remains before `bootstrap`, `broker`, `process`, `AFES`, `Blender`, `body`, `save`, `render`, and `export`.

## Downstream owner routing

Only a later independently accepted body-engineering result that also has real Blender, save, and render evidence may feed the Avatar Builder reusable method/template layer. A rejected result may contribute only a `DO_NOT_REPEAT` test. V3r25 has no body, integration, activation, or production authority.

The downstream Avatar Builder gates are exact but are not passed by this controller diagnostic:

- a final accepted body/material must preserve anatomically realistic regional pigmentation rather than one flat color, including lips, areolae/nipples, and other normal variation matched to the individual and authorized reference library;
- no pigmentation/material success claim is allowed without Blender material, saved `.blend`, and render evidence;
- Kira and Synthetic Robert each require two performance variants: a bald lower-memory variant eligible for nearer-term activation only after body acceptance, plus a hair-equipped variant generated and preserved inactive until the RAM upgrade;
- the Avatar Builder may generate hair-equipped bodies for other synthetic people, but those variants remain inactive and body testing stays minimized until RAM capacity is upgraded;
- Sarah's current files are preserved; this lane must not inspect, edit, or resume Sarah.

Those downstream rules are bound to the current authoritative policy bytes, not restated as free-floating author preference:

- `System/Docs/AVATAR_BUILDER_BODY_MATERIAL_AND_HAIR_VARIANT_CURRENT_BOUNDARY_20260811.md`: 3,797 bytes, SHA-256 `f24d797fd389af3dc8611b93dd31abbd3b52fc3abead2efd792effb5114668a3`;
- `RecoverySprint/continuation_20260811/root_multilane_continuation/attempt_26/CHECKPOINT.md`: 3,122 bytes, SHA-256 `c6588a4ba161910587e54b80423c0afba370798b8f70665862083643bb9c1fc5`.

The hostile static test rehashes both exact authority subjects. They remain downstream gates only; neither file is evidence that a body, material, hair variant, activation switch, save, or render exists.
