# Avatar Likeness Author Backend v1

## Outcome

`Core/avatar_likeness_author_backend.py` now implements the fail-closed bridge
between the reviewed multiview queue and the separated-component production
pipeline. It is preparation and proof plumbing, not an automatic likeness
solver.

The backend accepts the immutable job shape produced by
`Core/avatar_multiview_authoring.queue_multiview_authoring_manifest`. It
recomputes that job's content hash, reopens the bound manifest, rehashes every
image and review artifact, reruns view/calibration/landmark/scale/base checks,
and requires canonical identity/version/maturity preflight. If the identity
registry is absent or invalid, this stage fails closed. A raw manifest, draft
manifest, changed source, malformed queue record, or now-blocked identity
cannot enter this stage.

The queue filename/content digest is an integrity and idempotency binding, not
an authenticated signature. Software or a person with local write access could
reproduce a syntactically valid queue record, but that record still cannot
bypass full manifest, review-artifact, canonical identity, version, or maturity
revalidation. The backend does not claim stronger queue provenance.

## Installed stages

The new CLI is `tools/avatar_likeness_author_backend.py`.

1. `inspect --queued-job <path>` verifies the reviewed queue job and reports
   whether an exact operator-approved author capability exists.
2. `prepare --queued-job <path>` creates an immutable content-addressed work
   order only when the Blender executable, worker script, capability flags,
   and operator review record all match their SHA-256 bindings.
3. `finalize --work-order <path>` revalidates the queue, canonical profile,
   work order, tool capability, worker result, every component, every
   declaration, and every review render before staging a private review
   package.

Preparation does not invoke Blender. It creates deterministic input and output
contracts for a future exact worker. The work order seed and ID derive from the
reviewed evidence job, manifest, canonical preflight, Blender, worker,
algorithm, candidate, version, and topology hashes.

Work-order and backend-proof writes recheck project confinement and reject
symlinks both before and after parent creation. They cannot follow a preexisting
`work_orders` or candidate-output link outside the allowed root.

For profiles whose canonical version is required, the queue version must match
the exact canonical profile version. For profiles that intentionally have no
canonical version field, such as an owner reference-set build, the exact
reviewed-manifest version remains the authority and is explicitly labeled
`reviewed_manifest_exact_optional_canonical_version`; it is not misreported as
a canonical profile match.

## Required worker output

The work order requires distinct private GLB files for:

- body;
- hair;
- eyes;
- basic clothes;
- clothed review assembly.

It separately requires:

- a new-surface worker declaration bound to the reviewed base and exact body;
- per-reviewed-source landmark reprojection metrics;
- a finite/bounded rig mechanical-smoke declaration;
- clothed front, profile, back, three-quarter, face, and hand review PNGs;
- backend-generated component-integrity proof;
- backend-generated exact-body rig-structure proof;
- an inactive component-authority artifact for the later immutable adoption
  queue;
- a private owner-review candidate manifest.

Every component GLB must be self-contained: exactly one JSON chunk and one
embedded BIN chunk, no external buffer/image URI, and all declared meshes must
be reachable from the active scene. Every primitive needs finite, bounded,
nondegenerate float `POSITION` geometry within the vertex/file limits. The body
additionally requires an active-scene skin, reachable joints, exact inverse-bind
matrices, per-vertex `JOINTS_0`, and finite normalized `WEIGHTS_0`. An empty
mesh object is not an owner-reviewable body.

Reprojection output must cover exactly the human-reviewed landmark count for
each bound source-review artifact. Counts cannot be shortened, values must be
finite and nonnegative, and mean error cannot exceed maximum error. These
metrics still require owner review and have no automatic acceptance threshold.

Candidate output is staged under
`Avatar/avatar_builder/candidate_sources/<candidate>/likeness_authoring/<job>`
so the existing component-production validator can later consume its exact
hashes after the orchestration request is explicitly updated. Finalization
does not mutate that request or silently adopt components.

## Truth boundaries

The finalizer can prove exact hashes, distinct files/bytes, self-contained
active-scene bounded POSITION geometry, a structurally bound skin/joint export,
reviewed-input binding, exact per-source metric-record coverage, and valid
private review-image envelopes. It deliberately keeps all of these false until
later independent review:

- identity likeness proven;
- new-surface authorship independently proven;
- anatomical completeness proven;
- stable working rig proven;
- visual deformation quality proven;
- face, gaze, blink, expression, and lip-sync controls proven;
- clothing fit or wearable behavior proven;
- owner visual approval proven;
- runtime activation allowed;
- public export allowed.

A worker is not allowed to self-approve likeness or anatomy. Its declaration
must explicitly leave those claims false, and backend status continues to say
unproven.

## Current local blocker order

The immediate end-to-end blocker for the current real candidates is still the
absence of a fully owner-reviewed, queue-ready multiview job. There is currently
no real queued evidence job or work order, so the CLI cannot yet reach author
tool preparation for Robert or Gwen.

The next backend blocker is also real: the generalized Blender cage/lattice/
sculpt worker is not installed. The exact expected worker is
`tools/blender_fit_reviewed_multiview_surface.py`; no operator-approved active
capability descriptor exists at
`Avatar/avatar_builder/likeness_authoring/tooling/active_capability.json`.
Direct tooling inspection therefore returns
`blocked_required_author_tooling_missing` and creates no work order or body.
Installed Blender alone does not satisfy this gate.

No placeholder capability descriptor was created because that would falsely
claim a generalized worker exists.

## Candidate readiness on 2026-07-16

| Candidate | Reviewed-input state | What remains before an owner-reviewable body exists |
|---|---|---|
| Existing Earth-65 adult Gwen | 4/4 files hash/dimension verified; 0 owner-reviewed; not queue-ready | Same-version front, profile/three-quarter, and full-body approval; all required face/body landmarks; one calibration frame; scale review; reviewed adult cage base; then a real approved worker run and all required component/rig/review outputs |
| Robert owner avatar | 15/15 files hash/dimension verified; 0 owner-reviewed; not queue-ready | Owner classification of usable front/profile/full-body views; landmark/crop/calibration records; metric or explicit unknown scale; reviewed adult cage base; then the same worker/output/review sequence |
| Kathryn adult continuation | No multiview manifest; 0 enrolled/reviewed views | Create an exact adult-present 2016-pilot/accepted-picture manifest, keep Amy Adams' *Cruel Intentions 2* performance excluded from Sarah Michelle Gellar likeness evidence, review views/landmarks/scale/base and any measurement-only model, then queue and run the worker |

Even after an owner-review package exists, component adoption, topology audit,
stable walk/turn/stop/sit/rise/lie/deformation tests, face/lip-sync proof,
wearable proof, owner approval, and a separate activation decision remain.

## Verification

`Testing/test_avatar_likeness_author_backend.py` covers:

- missing canonical registry fails closed;
- required canonical versions must match, while optional profile versions are
  explicitly bound to the reviewed manifest;
- missing tooling blocks without creating a work order;
- work orders are deterministic, content-addressed, idempotent, and inactive;
- symlinked work-order ancestry is rejected before writing;
- changed source evidence is rejected after queueing;
- canonical identity preflight cannot be bypassed;
- changed approved worker bytes invalidate the work order;
- reviewed evidence summaries cannot be rewritten after preparation;
- incomplete worker output cannot finalize;
- external GLB dependencies, missing/unbounded POSITION geometry, inactive
  meshes, and missing body skin bindings cannot finalize;
- reprojection counts must match every reviewed landmark and mean error cannot
  exceed maximum error;
- valid fixture output produces separate component and rig proof records while
  leaving all quality and activation claims false;
- a worker cannot self-approve likeness; and
- profile/GLB dependency exceptions return structured CLI `blocked` status.

This stage does not authorize private-source rendering, avatar activation,
runtime replacement, or public distribution.

The hardened pass completed with 16 focused backend tests, 89 related
owner-review/multiview/component/preflight/orchestration integration tests, and
200 broader avatar/body/garment/workspace tests passing. Python compilation
also passed.
