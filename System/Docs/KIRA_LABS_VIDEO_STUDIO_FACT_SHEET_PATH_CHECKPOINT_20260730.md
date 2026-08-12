# Kira Labs Video Studio V2 Fact Sheet path checkpoint

Date: 2026-07-30  
Status: `VISIBLE FACT SHEET BUTTON REPAIRED; EXACT PROJECT PASSED; CLAIM REVIEW STILL REQUIRED`

## Scope

This checkpoint applies only to the isolated staging installation:

`C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1`

The active Video Studio v1.9 installation was not modified. No media was
uploaded or published.

## Root cause

The existing Tk callback was working correctly. It called `begin_stage`,
persisted `RUNNING`, and then called the project service. The failure was in:

`kira_video_studio/project_service.py::_run_fact_sheet`

That handler only inspected `project["sources"]["fact_sheet"]` for an already
reviewed non-empty sheet. It never read the passed Research artifacts and
never created a reviewable draft. The visible button therefore asked Robert
to supply the artifact it was supposed to prepare.

## Repair

The existing visible button now:

1. requires the normal Research stage to be `passed`;
2. resolves exactly one project-local `research_manifest.json`;
3. resolves exactly one project-local
   `RESEARCH_AUDIT_VALIDATION.json`;
4. validates schema, version, passed status, subject binding, and equality
   between the embedded and standalone research audit;
5. generates source-bound draft proposals;
6. preserves source IDs, publisher, URL, source-record evidence class,
   claim-level evidence class, verification/review status, uncertainty, and
   rumor-exclusion status;
7. excludes `UNVERIFIED_PUBLIC_RUMOR` from factual claims;
8. marks RSS/search excerpts as
   `UNVERIFIED_SOURCE_TEXT_PROPOSAL` and
   `REVIEW_REQUIRED_SEARCH_OR_RSS_EXCERPT`;
9. prevents those excerpts from entering a script;
10. writes and hashes a private draft plus a calculated audit;
11. marks the workflow stage passed only when that structural audit passes;
12. enables Script after the Fact Sheet stage passes.

Fact Sheet `PASSED` means a valid review artifact exists. It does **not** mean
that every proposed claim is approved for narration.

## Files changed in the isolated alpha

- `kira_video_studio/fact_sheet_builder.py`
- `kira_video_studio/project_service.py`
- `kira_video_studio/schema.py`
- `tests/test_fact_sheet_builder.py`
- `tests/test_project_service.py`
- `tools/verify_fact_sheet_visible_button.py`

The matching development mirror is:

`VideoStudioDevelopment/alpha_2_0_0_working_20260730`

## Exact owner project proof

Project:

`C:\Users\robmc\KiraVideos\StudioOutputs\V2_PrivateTests\20260730_012956_who_is_jean_grey_v2_who_is_jean_grey`

The installed `StudioApp` was created through Tk and its real
`workflow_stage_buttons["fact_sheet"].invoke()` control was invoked.

Observed result:

- prior historical state: `blocked` by the old handler;
- real button state before retry: `normal`;
- new persisted transition: `running`;
- final Fact Sheet state: `passed`;
- Script button after completion: `normal`;
- source-bound draft records: 8;
- currently script-eligible records: 0;
- awaiting owner/source-content review: 8;
- RSS/search excerpts promoted as verified facts: false;
- automatic upload: false;
- posting performed: false;
- public release approved: false.

Artifacts:

- `sources/FACT_SHEET_DRAFT.json`
  - SHA-256:
    `1a0ebd8926f7a934b121b2bfe17ade996fe4a41a43dafa3467546c29ae5cc10f`
- `sources/FACT_SHEET_AUDIT.json`
  - SHA-256:
    `5aab5abf9ea0ef71b3171e216fb7b118a31bba90c1997998f695e81629556540`
- `validation/FACT_SHEET_VISIBLE_BUTTON_PROOF.json`

The original failed attempts remain in the project history. They were not
rewritten as though they never occurred.

## Test and seal evidence

Focused Fact Sheet/project-service tests:

- 29 passed;
- 0 failed.

Complete isolated-alpha discovery:

- 230 passed;
- 0 failed.

Read-only active v1.9 seal verification:

- files: 118;
- bytes: 21,953,950;
- Windows tree SHA-256:
  `7e36756a953a266d0adf52343b7271c0306bcdd3908508c1567615ffc58a5460`;
- canonical POSIX tree SHA-256:
  `7bcfc1bcc58cf3c93658a4dbcd9e3bcc38c8f908cda3ab7fe0c88417879ea891`;
- preserved seal match: true.

## Jean Grey visual direction

Robert's current editorial request is a private, video-first Jean Grey
retrospective using deliberately matched, muted moving footage for different
versions of Jean Grey, ending with a rights-reviewed public-event or red-carpet
clip of Sadie Sink. This is an editorial visual request, not evidence that
Sadie Sink portrays Jean Grey. That identity claim must remain governed by
public verification or Robert's explicit owner-screening evidence. Source
audio stays muted unless deliberately selected, and every asset still requires
source and rights records.

## Next safe work

Do not promote the eight source-title/excerpt proposals into narration merely
because the Fact Sheet stage passed. The next normal-path work is to provide
full-source evidence or an explicit review action for individual claims, then
exercise Script and the later production buttons with their real prerequisites.
Do not weaken the fact gate to make later buttons appear successful.
