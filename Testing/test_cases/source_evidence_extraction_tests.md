# Source Evidence Extraction Test Cases v1

## Test 1 — Index Must Exist

Before running:

```bash
python Kira/Core/source_evidence_extractor.py --project-root .
```

this file should exist:

```text
Kira/Data/indexes/character_source_index.json
```

Expected:
- If missing, extractor reports a clear error.
- User should run `source_indexer.py` first.

## Test 2 — Canon Script Evidence

Input:

```text
Kira/Data/library/scripts/Miraculous_Ladybug/
```

Expected:
- Evidence output appears under `Kira/Data/processed/source_evidence/`.
- Canon sources are marked `source_authority: canon`.
- Dialogue/action/location/trait clues are saved where found.

## Test 3 — Fanfic Evidence

Input:

```text
Kira/Data/library/stories/fanfic/Miraculous_Ladybug/
```

Expected:
- Evidence is marked `source_authority: fanfic_variant`.
- Evidence has `requires_review: true`.
- Canon evidence is not overwritten.

## Test 4 — Reading Is Not Memory

Expected:
- Evidence files are not written to Kira or Lisa personal memory.
- Source evidence stays under `Kira/Data/processed/source_evidence/`.

## Test 5 — Weak Evidence Should Require Review

Expected:
- Action, relationship, and trait evidence should usually have `requires_review: true`.
- The system should not treat keyword matches as final truth.

## Test 6 — Copyright Safety

Expected:
- Evidence stores short excerpts or summaries.
- Evidence should not copy entire scripts, stories, chapters, or books.
