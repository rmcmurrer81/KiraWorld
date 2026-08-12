# Library Source Intake Test Cases v1

## Test 1 — Canon Script Detection

Folder:

```text
Kira/Data/library/scripts/Miraculous_Ladybug/
```

Expected:
- Scanner finds PDF/TXT/MD files.
- Scanner detects Ladybug/Marinette if aliases appear.
- Scanner writes canon evidence with `source_authority: canon`.

## Test 2 — Fanfic Folder Exists but Is Empty

Folder:

```text
Kira/Data/library/stories/fanfic/Miraculous_Ladybug/
```

Expected:
- Scanner does not crash.
- Scanner logs no files found or no evidence found.
- Canon processing continues.

## Test 3 — Fanfic Story Added Later

Folder:

```text
Kira/Data/library/stories/fanfic/Miraculous_Ladybug/pending_review/
```

Expected:
- Scanner finds the story.
- Scanner marks evidence as `source_authority: fanfic_variant`.
- Scanner marks evidence as requiring review.
- Scanner does not overwrite canon profile.

## Test 4 — Duplicate Script Removed

Old duplicate folder:

```text
Kira/TemporaryAI/characters/ladybug/sources/scripts/
```

Expected:
- This folder should not be used as the true source location.
- Duplicate source files should be deleted or ignored after backup.
- The true raw-source folder is `Kira/Data/library/scripts/Miraculous_Ladybug/`.

## Test 5 — Reading Does Not Equal Memory

If Kira reads a script or story for fun:

Expected:
- She may create a reading note.
- She may form an interest.
- She may ask questions.
- She must not treat the source as her personal memory.
