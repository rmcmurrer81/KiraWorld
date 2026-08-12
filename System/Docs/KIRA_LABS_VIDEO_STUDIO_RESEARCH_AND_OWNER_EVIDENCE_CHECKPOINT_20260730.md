# Kira Labs Video Studio 2.0 alpha.1 research and owner-evidence checkpoint

Date: 2026-07-30  
Scope: isolated `2.0.0-alpha.1` staging only  
Status: `RESEARCH PATH REPAIRED; OWNER EVIDENCE INTEGRATED; PRIVATE ONLY`

## Controlling boundaries

- Active Video Studio v1.9 was not modified.
- No replacement launcher, BAT file, duplicate interface, upload, or
  publication path was created.
- Research may start only from the existing visible **Run Research** action.
  Opening a project or calling an implicit backend path does not start network
  research.
- Research success does not imply fact-sheet, script, voice, render, owner
  approval, or publication success.

## Exact research-stage root cause

The existing workflow button reached `project_service._run_stage`, but the
non-Kira research branch called only `_snapshot_existing_research`. That path
required pre-imported source records and never invoked the already present
online-research service. Therefore a new project with no imported sources
truthfully became blocked with:

`no researched source records exist; network research is never started implicitly`

The UI then displayed only the generic word `blocked`, hiding that useful
reason.

## Implemented repair

The existing alpha now:

1. persists `RUNNING` before the provider call;
2. paints the running state in the existing UI;
3. invokes the configured no-key research ensemble only for the explicit
   visible Run Research action;
4. gathers real source metadata from Google News RSS, Bing Web RSS, and the
   Wikipedia Search API;
5. records provider errors, exact query provenance, semantic relevance,
   publisher diversity, trusted-source count, and query coverage;
6. saves `research/research_manifest.json` and
   `research/RESEARCH_AUDIT_VALIDATION.json`;
7. reports the precise blocking reason when providers fail, no relevant
   records return, project state is invalid, or audit validation fails;
8. enables Fact Sheet only after Research passes.

Search-result metadata is not treated as a verified factual claim. Rumor or
speculation records remain `UNVERIFIED_PUBLIC_RUMOR` and are ineligible for
fact claims even when a reputable publisher carried the item. Relevant,
trusted, non-rumor sources are marked only as eligible for later fact
verification.

## Genuine normal-UI proof

Final authoritative smoke project:

`C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests\20260730_012956_who_is_jean_grey_v2_who_is_jean_grey`

Observed through the actual Tk `StudioApp` and the actual Run Research button:

- initial Research: `pending`;
- Fact Sheet button before research: disabled;
- UI state immediately before provider call: `running`;
- persisted project state immediately before provider call: `running`;
- explicit-user-action flag: true;
- final Research: `passed`;
- selected relevant records: 8;
- distinct publishers: Deadline, Variety, Wikipedia;
- all four generated query IDs covered;
- trusted-source count: 8;
- Fact Sheet button after research: enabled;
- publication enabled: false.

The owner-created project that originally exposed the bug was also repaired
through the same existing UI path:

`C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests\20260730_003117_who_is_jean_grey_v2_who_is_jean_grey`

Its current authoritative research artifact is:

`C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests\20260730_003117_who_is_jean_grey_v2_who_is_jean_grey\research\research_manifest.json`

Its audit file is:

`C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests\20260730_003117_who_is_jean_grey_v2_who_is_jean_grey\research\RESEARCH_AUDIT_VALIDATION.json`

That project records the original blocked attempts, the later real `running`
transition, and the audited `passed` result. It contains eight selected
records from three publishers. Fact Sheet remains pending but is now
available. Publication remains disabled.

Earlier smoke projects `20260730_005926...`, `20260730_012044...`, and
`20260730_012339...` are preserved as superseded or rejected engineering
evidence. They are not the authoritative proof because they exposed,
respectively, a weak relevance gate, a correctly blocked insufficient source
set, and a rumor-heavy source-selection weakness.

## New-release owner evidence

The normal alpha project service and UI now distinguish:

- `PUBLIC_VERIFIED_SOURCE`;
- `OWNER_FIRSTHAND_SCREENING_NOTE`;
- `OWNER_CONFIRMED_SCREENING_FACT`;
- `OWNER_INTERPRETATION`;
- `UNVERIFIED_PUBLIC_RUMOR`.

Owner evidence preserves the exact note, a SHA-256 of that note, record time,
optional screening time, evidence class, confirmation history, and later
corroboration without rewriting the original observation.

Rules:

- An unconfirmed firsthand note is valid private production evidence but does
  not silently become a direct script fact.
- A fact Robert explicitly confirms was clearly shown, stated, named in
  dialogue, or identified in credits may be promoted internally to
  `OWNER_CONFIRMED_SCREENING_FACT`.
- Internal provenance does not force narration such as "According to Robert."
  A confirmed screening fact may be narrated directly.
- The script may not call a claim officially confirmed by Marvel, Sony,
  Disney, an actor, or a publication unless a corresponding official public
  source is linked.
- `OWNER_INTERPRETATION` requires interpretation language such as "appears,"
  "suggests," or "I believe."
- Lack of immediate online corroboration does not block a private owner review.
- No actual Spider-Man spoiler or owner observation was invented or inserted.
- Nothing publishes automatically.

## Files changed in isolated alpha

- `kira_video_studio/settings.py`
  - SHA-256:
    `79aa1111ff67176eb1ba6a2fdddca11c66f2991c64667919c1b571ff38ed0577`
- `kira_video_studio/project_service.py`
  - SHA-256:
    `b6289f6b646802a1b31e5ab17dd1f9056f63acfcabaf7efcebbcffaa4e1f0d20`
- `kira_video_studio/ui.py`
  - SHA-256:
    `b36959f7c10ac7011fb13c7812cfa58abe870e1edbab050ac67d1bf6af19dce5`
- `kira_video_studio/online_research.py`
  - SHA-256:
    `ddcfa037b0c9b319c9d4e7968441c21ff0f0a91b36b7ec38b140fa5f333daa32`
- `kira_video_studio/owner_evidence.py`
  - SHA-256:
    `c01ec31c2f00aec6695ac5177b11a18da71dc349d80e5e17c5fcb5caa0911202`
- focused tests in `tests/test_project_service.py`,
  `tests/test_ui_launcher.py`, `tests/test_online_acquisition.py`, and
  `tests/test_owner_evidence.py`.

## Validation

- Focused alpha regression suite: 60 tests, all passed.
- Complete isolated alpha test discovery: 225 tests, all passed.
- Hidden GUI construction/destruction: two clean cycles, six tabs, no startup
  exception, no project opened, publication disabled.
- `py app.py --self-test`: passed.
- Existing launcher probe:
  `START_KIRA_LABS_VIDEO_STUDIO.bat --probe-only`: passed.
- The test suite caught an initially misplaced owner-evidence function during
  implementation; it was corrected before deployment and all 60 focused tests
  then passed.

## Active v1.9 preservation

The apparent 96-file diagnostic count came from an authored-file inventory
that intentionally excludes 22 Python bytecode files. The original full-tree
seal method was then rerun read-only and matched exactly:

- root: `C:\KiraVideos\VideoStudio`;
- file count: 118;
- byte count: 21,953,950;
- Windows tree SHA-256:
  `7e36756a953a266d0adf52343b7271c0306bcdd3908508c1567615ffc58a5460`;
- canonical POSIX tree SHA-256:
  `7bcfc1bcc58cf3c93658a4dbcd9e3bcc38c8f908cda3ab7fe0c88417879ea891`.

Active v1.9 is unchanged.

## Honest remaining boundary

This checkpoint proves the normal Research action and the owner-evidence
provenance path. It does not prove that every later production stage is
complete. The repaired Jean Grey project has Research passed and Fact Sheet
available, but Fact Sheet has not yet been generated or passed.

## Spider-Man review intake migration

The existing private intake at:

`C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests\20260730_002332_spider_man_brand_new_day_robert_s_spoiler_review_v2_spider_man_brand`

now carries the same owner-evidence classes and internal-provenance rules. Its
owner-evidence list remains empty; no spoiler or Robert opinion was invented.
Its status remains `AWAITING_ROBERT_OWNER_NOTES`, publication remains disabled,
and its intake manifest was recomputed.

- `project.v2.json` SHA-256:
  `3c5cea76885fafef80e2f06a51c09526ceb7761ff23a450edf48c300d5f49280`
- `manifests/INTAKE_PACKAGE_MANIFEST.json` SHA-256:
  `84426ff847ec1a12ec66403d4c51b6ca4d16bfbf78ce518b587184ec7853c67c`
