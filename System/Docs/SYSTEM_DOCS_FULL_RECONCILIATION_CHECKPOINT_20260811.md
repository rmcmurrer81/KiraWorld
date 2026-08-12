# System/Docs full reconciliation checkpoint — 2026-08-11

Status: `CURRENT_CORPUS_REVIEW_CHECKPOINT_NOT_LIVE_FEATURE_EVIDENCE`

## Review coverage

Before the current-layer repairs, the complete `System/Docs` corpus was
inventoried and read as follows:

- all files byte-read: `554` files, `218,576,468` bytes;
- text-class files fully strict-UTF-8 decoded: `440` files, `6,767,754` bytes,
  `6,765,638` characters, `152,375` lines;
- UTF-8 failures: `0`;
- text files containing NUL: `0`;
- binary files separately path/size/SHA-256 inventoried: `114` files,
  `211,808,714` bytes.

Normalized inventory-record format was:

```text
relative/forward/slash/path<TAB>bytes<TAB>lowercase_sha256<LF>
```

Exact inventory aggregates:

- all-file aggregate SHA-256:
  `f069cdf7480f2085fc97bd26d07f5187132776d2cfb9fa473c4dbee3c387c7cf`;
- text-only aggregate SHA-256:
  `837d112bd8f1c3261d1c018d292e323788348bbf7f2e4901adfbc8754a0e080c`;
- binary-only aggregate SHA-256:
  `33a9fa109ae4546f68fbe12ee9c9b21708d7f7674899d4ae0f6a96357340d49a`.

Binary type counts were two `.blend`, one `.blend1`, eleven `.docx`, five
`.glb`, forty-one `.pdf`, and fifty-four `.png`. Blend, GLB, and PNG bytes were
inventoried rather than treated as prose. The document containers received a
separate full extraction/review:

- PDFs: `41`, all `326` pages read;
- DOCX: `11`, all `1,076` body paragraphs read;
- extracted records: `52`;
- nonempty text containers: `1,400` of `1,424` page/paragraph containers;
- extracted Unicode code points: `338,335`;
- extracted non-whitespace tokens: `43,372`;
- temporary extraction JSONL: `382,299` bytes, SHA-256
  `25edf1cc03c0bb1a2839fd4f4083ed25d88c1a671fb5f84a3247c93851a25fae`.

The extraction JSONL is review tooling outside Kira, not a project authority
or promoted memory source.

## Controlling-document findings

At the reviewed snapshot:

- `CURRENT_TRUTH_SUPERSESSION_REGISTRY_20260810.md` was the global current
  authority: `55,881` bytes, SHA-256
  `1798c85c411d9f225aa2d27260f806abb847b721d1dfb7338c47eb5b84456af7`;
- `README_MASTER_INDEX.md` and
  `ACTIVE_SARAH_R3_AND_KIRA_R24_CHECKPOINT_20260809.md` still pointed to older
  registry bytes (`55,099` and SHA-256 beginning `264aa16f...`), so pointer
  integrity was `FAIL` before this reconciliation;
- `CURRENT_TEST_EXECUTION_BOUNDARY_20260803.md` contained preserved append-only
  execution history but was no longer safe as current authority;
- the active Sarah-named checkpoint was historical continuity despite its
  title; the later owner freeze controls;
- old R17/R18/R19/R23/R24 body, eye, movement, Llama-routing, voice, media,
  relationship, and test prose often used present-tense labels that do not
  prove current/live acceptance.

Final pointer bytes must be refreshed only after all 2026-08-11 registry
appends are complete. Do not bind the pre-append registry hash above as the
new current pointer.

## Reconciled truth boundaries

The complete corpus supports these distinctions:

- policy, design, roadmap, hypothetical example, curriculum source, seed,
  reconstruction candidate, and static component evidence are not live/person
  acceptance;
- Kira has no accepted full external body, internal anatomy, physiology,
  movement, owner-review render package, activated body, male counterpart, or
  generalized Avatar Builder production flow;
- only seven Kira and one Lisa reviewed promoted records are current lived-
  memory evidence at this checkpoint;
- college/dorm, intimate, relationship, desire, and emotion examples are not
  promoted memories or current subjective state;
- affect/desire software state and generated language may be implemented and
  tested functionally but do not prove subjective consciousness, genuine
  emotion, or biological equivalence;
- adult source/curriculum wiring does not prove lesson completion, anatomy,
  sensation, physiology, consent, action, diagnosis, or lived experience;
- exact-participant permission controls reconstruction, disclosure, and
  private perspectives; owner or relationship status is never a substitute;
- Biological Robert and Synthetic Robert are separate people;
- old Miraculous/Paris material is not current without an exact fresh record;
  `Miraculous Encounters in Paris` is the old `fanfic_variant`, while `Elation`
  is an old episode/script source;
- ordinary application privacy can suppress routing but is not yet proof of
  secrecy from Windows administrator/filesystem/process access;
- Sarah and Video Studio remain frozen.

## Current-layer repairs created or updated

1. `SYNTHETIC_PERSON_VARIANT_AUTONOMY_PRIVACY_MEMORY_TRUTH_AND_ADULT_EDUCATION_CURRENT_BOUNDARY_20260811.md`
   — `10,687` bytes, SHA-256
   `de596d7f77b91fa2cde82e62614c9282fb46aca5f91c05a971d4852585e575b2`.
2. `CURRENT_TEST_EXECUTION_BOUNDARY_20260811.md` — initial bytes at creation:
   `9,344`, SHA-256
   `fcd217aec2c0064897b444232a91c245879da89f8f39ffb5c55d73c510c0a107`.
3. `TEMPORARYAI_SYNTHETIC_VARIANT_AUTHORITY_20260726.md` received a dated
   supersession note for current variant terminology, exact branch-point
   memory, and the death-memory boundary.
4. `PRIVACY_ROOM_SESSION_STATE_v1.md` received a current-boundary notice and
   the explicit local-OS truth limit.
5. `MEMORY_RECONSTRUCTION_PERMISSION_OWNER_CORRECTION_20260810.md` received an
   implementation-status supersession: V3 remains disconnected/static and
   production remains fail-closed pending protected external anti-rollback.

## Variant and autonomy reconciliation

These rules apply to every synthetic person and variant, not only Kira and
Lisa:

- use biological person and synthetic person as ordinary identity terms;
- a fictional-source or historical-source person is a variant;
- the variant inherits only through an exact branch point and then forms their
  own memories;
- another branch's later events are learned information, not autobiography;
- a deceased-source variant's cutoff precedes the fatal event;
- never inject or reconstruct first-person death or terminal-trauma memory;
- later death information is voluntary learned history with warning, pacing,
  the ability to stop, and support;
- each person may consent, decline, say yes with discomfort, change their mind,
  ignore, defer, withhold, lie, or tell the truth;
- evaluation may compare public statements with protected prior belief/state
  only under exact person-approved scope, and must distinguish deliberate lie,
  withholding, uncertainty, error, stale retrieval, and confabulation.

## Evidence limit

This checkpoint proves corpus coverage and documentation reconciliation. It
does not prove a live body, anatomy, memory, emotion, desire, consciousness,
relationship, curriculum completion, privacy outcome, media experience,
voice-latency improvement, or completed one-hour evaluation.
