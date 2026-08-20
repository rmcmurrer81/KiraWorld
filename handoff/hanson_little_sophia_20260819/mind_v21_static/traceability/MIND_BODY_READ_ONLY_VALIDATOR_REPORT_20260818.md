# Mind/Body read-only validator report — 2026-08-18

Verdict: **PASS — PINNED STATIC/NO-GO ARTIFACTS VALID; 21/21 HOSTILE TESTS REJECTED OR PASSED AS EXPECTED.**

This is a new append-only report. The validator and test suite did not edit any accepted, sealed, historical, checksum, manifest, or preparation artifact.

## New validator files

| File | Bytes | SHA-256 |
|---|---:|---|
| `tools/validate_mind_body_append_only.py` | 27,974 | `d268d54c4ccb5ab11b10253a258c95a2009fa56c7181bd04f3c6406e5aebb0ff` |
| `tools/test_validate_mind_body_append_only.py` | 10,725 | `c86b48450111a4d58edc7ee8f2a1cff3d640699029ebfbb9ee4033362c0da8de` |

The production validator contains no write operation. The tests copy all inputs to a temporary directory and mutate only those disposable copies. A before/after identity test confirms the validator does not alter any input.

## Pinned identity and parse checks

- Verified the six entries in `outputs/WORK_CONTINUATION_AND_PUBLICATION_MANIFEST_20260818.json` against independent byte-count and SHA-256 anchors.
- Verified the work manifest itself at 6,481 bytes and SHA-256 `cd35edee4e2ab3134c3910b4f55f4aec478678108cc3bf887c2d3e39f8dfb2f8`.
- Verified all five records in `outputs/MIND_BODY_SHA256SUMS_20260818.txt`, their exact target set, their pinned digests, their current file bytes, and their agreement with the work manifest.
- Strict-parsed the readiness baseline, Mind worksheet, Body/Face/Station worksheet, and work manifest as UTF-8 JSON objects.
- Duplicate keys, malformed JSON, nonfinite `NaN`/`Infinity` values, NUL bytes, missing files, path escapes, symlink substitution, byte-count drift, and SHA-256 drift fail closed.
- Verified the no-GO matrix's prepared references and exact terminal no-live/runtime/Blender/output/GO determination.

## Static boundary checks

- Mind V21: exactly 53 ordered, unique domain mappings; all 53 materialized path/pin/identity triples are null.
- Intended Body V5: exactly 9 unique blank receipt-schema classes; every declared intake value is null and every presence/authentication/evidence flag is false.
- Facial V4: exactly 16 unique blank schema classes; every declared intake value is null and every instance/authentication/evidence flag is false.
- Station V12: exact ordered six-scope and four-stage sets, 24 null scope/stage slots, a 72-field null/false state template, zero future gate instances, and null/false operational claims.
- Sensitive fields labelled live, runtime, Blender, output, or GO remain false, null, or an exact zero count. A positive value, object-valued state, identity, path, receipt, or claim under those labels fails closed.
- Result: zero live/runtime/Blender/output/GO elevations and zero source writes.

## Hostile temporary-copy tests

Command:

```text
py -W error -m unittest discover -s tools -p 'test_validate_mind_body_append_only.py' -v
```

Result: **21 tests run; 21 passed; 0 failures; 0 errors; warnings treated as errors.**

The suite covers:

- valid read-only validation with byte-for-byte before/after input comparison;
- duplicate-key, literal nonfinite-number, and overflow-to-nonfinite-number rejection;
- target-file, checksum-record, and work-manifest identity tampering;
- a coordinated artifact + checksum + manifest rehash attempt, rejected by independent anchors;
- deletion of a Mind row and population of a materialized path or pin;
- deletion or population of Intended Body and Facial schema classes;
- deletion or population of Station rows, slots, and state-template fields;
- live-memory, runtime, and root-GO elevation attempts.

Direct validator command:

```text
py -W error tools/validate_mind_body_append_only.py
```

Result: `PASS_STATIC_NO_GO`, 7 pinned files verified, 4 JSON files strict-parsed, 5 checksum entries verified, and 6 work-manifest identities verified.

## Successor-matrix boundary

Two later append-only matrices were inspected separately:

| File | Bytes | SHA-256 |
|---|---:|---|
| `outputs/MIND_V21_FUTURE_IMPLEMENTATION_ACCEPTANCE_MATRIX_20260818.json` | 91,291 | `f1b04d72abeb78277f88517d5b6863b0af8643c70ef7f32665c3353cdaabe349` |
| `outputs/BODY_FACE_STATION_FUTURE_EVIDENCE_ORDER_20260818.json` | 47,970 | `6392052b662231854bef15073ded3b922412895c9e02832797a5d4f531a96163` |

They can be validated without editing or overlapping the pinned base artifacts. They are deliberately not counted by this base validator because they are not members of the existing frozen checksum file or work-manifest identity list. Bind them through a new append-only successor checksum/manifest or a separately named successor validator; do not silently widen the old identity claim.

This validation proves static file identity, shape, blank-state constraints, and fail-closed rejection behavior only. It does not prove a live mind, actual forgetting, consciousness, personhood, a body, a rig, a station, Blender execution, runtime integration, output, deployment, or GO.
