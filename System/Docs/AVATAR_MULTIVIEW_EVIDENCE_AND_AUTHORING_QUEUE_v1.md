# Avatar Multiview Evidence and Authoring Queue v1

Date: 2026-07-16

## Purpose

This is the exact-hash review boundary between source pictures and a future
photo-to-new-mesh likeness author. It prevents an image inventory, an automatic
landmark suggestion, a generic base, or a downloaded reference model from being
reported as a reviewed person-specific build input.

Implementation:

```text
Core/avatar_multiview_authoring.py
tools/avatar_multiview_authoring_queue.py
Avatar/avatar_builder/multiview_authoring/manifests/private/
Avatar/avatar_builder/multiview_authoring/queued/
```

The module reads and hashes evidence. It does not decode images into a public
preview, suggest landmarks, fit a mesh, render, copy a reference model, replace
a runtime body, or activate anyone.

## Manifest contract

One private manifest binds exactly one candidate, subject, selected version,
and topology lane. Required top-level values include:

```text
manifest_type: avatar_multiview_likeness_evidence
topology_lane: confirmed_adult_topology | non_adult_doll_safe_topology
output_rule: private_review_only_not_runtime
runtime_activation_requested: false
public_export_allowed: false
```

Each enrolled image has an opaque source ID, a safe project-relative private
path, its SHA-256, and its native encoded dimensions. The evaluator reopens the
file and independently verifies all three. Its returned readiness summary
contains counts and opaque IDs only; it does not return source paths or image
filenames.

An image is not a reviewed source until it has a separately stored, exact-hash
JSON review artifact binding:

- candidate, subject, selected version, source ID, and source SHA-256;
- a human-confirmed same-subject and same-version decision;
- front/profile/three-quarter/full-body view classification;
- native dimensions and an in-bounds reviewed crop;
- a reviewed camera model and shared calibration-frame ID;
- human-confirmed landmark points in source-pixel coordinates;
- reviewer identity and review time.

Automatic landmark suggestions may be stored as suggestions, but they fail
until a reviewer explicitly confirms them. The full reviewed set must cover:

```text
face outline, brow, eye socket rims, nose, lips, chin, ears, neck,
shoulders, chest, waist, hips, elbows, wrists, hands, knees, ankles, feet
```

At least three distinct reviewed images must collectively provide a front
identity view, profile or three-quarter depth view, and full-body view in one
calibration frame.

## Scale, base, and optional model evidence

A separate exact-hash scale review must choose one of:

```text
reviewed_metric
scale_unknown_review_only
```

Unknown scale is an explicit private-review limitation, not an inferred height.

The selected cage/base source and its review artifact are rehashed. They must
match the manifest topology lane, be confirmed rig-compatible, and require a
new candidate surface. `copy_as_candidate_body_allowed` must be false.

Optional models require their own exact review artifacts and may use only:

```text
measurement_and_topology_guidance_only
```

Model surface, materials, textures, and identity copying remain forbidden. A
model never substitutes for picture identity evidence.

## Queue behavior

`evaluate` can report one of:

```text
blocked_manifest_integrity_or_identity
blocked_review_incomplete
ready_for_likeness_authoring_queue
```

`queue` accepts only the last state and writes an immutable content-addressed
job. Today that job says `queued_waiting_for_likeness_author_backend` because
the production-quality cage/sculpt likeness author is not installed. A queued
evidence job is not a mesh or an approval.

Examples:

```powershell
python tools\avatar_multiview_authoring_queue.py evaluate `
  --manifest Avatar\avatar_builder\multiview_authoring\manifests\private\robert_user_avatar_20260716.draft.json `
  --candidate-id robert_user_avatar_20260716 `
  --subject-id robert_mcmurrer `
  --topology-lane confirmed_adult_topology

python tools\avatar_component_production_queue.py plan `
  --orchestration-request Avatar\avatar_builder\orchestration_requests\robert_user_avatar_20260716.json `
  --multiview-manifest Avatar\avatar_builder\multiview_authoring\manifests\private\robert_user_avatar_20260716.draft.json
```

Only after an evaluation passes, bind its exact manifest hash when queueing:

```powershell
python tools\avatar_multiview_authoring_queue.py queue `
  --manifest <reviewed-manifest.json> `
  --candidate-id <candidate-id> `
  --subject-id <subject-id> `
  --topology-lane <exact-topology-lane> `
  --expected-manifest-sha256 <exact-sha256>
```

## Current drafts

| Candidate | Exact files | Reviewed sources | Current result |
|---|---:|---:|---|
| Robert user avatar | 15/15 | 0 | Hashes and dimensions pass. Per-image identity/version, view, crop/calibration, landmark reviews, scale review, and reviewed adult-male base are missing. |
| Existing Earth-65 adult Gwen candidate | 4/4 | 0 | Downloaded references are enrolled under `spider_gwen_spider_gwen_20260606_013325` and the selected age-18-20 current-build version, but are not approved as same-version identity views; view/calibration/landmark, scale, and base reviews are missing. |
| Adult Kira build variant | 0 | 0 | Existing design-ingredient references were not falsely relabeled as Kira identity pictures. A safe exact-identity multiview set or a separately approved non-photo identity strategy is missing. |

The older `spider_gwen_adult_avatar_project_variant_20260716` manifest remains
on disk only as history of the earlier fail-closed workaround. It is marked
`superseded_audit_only`, cannot enter the authoring queue, is hidden from the
normal workspace candidate list, and redirects manual workspace actions to the
existing canonical Earth-65 Gwen candidate. It is not a second Gwen.

After those evidence gaps are resolved, the exact remaining implementation
blocker is still the generalized landmark/calibration-driven cage/sculpt worker
that authors a new surface and exports separately fitted body, eyes, hair,
clothes, and rig artifacts.

## Local owner-review UI

`System/Docs/AVATAR_MULTIVIEW_OWNER_REVIEW_WORKFLOW_v1.md` defines the
loopback-only workflow for authoring the exact review artifacts required above.
It can inspect only manifest-enrolled, rehashed images and requires explicit
owner confirmation for identity/version, view, crop, calibration, every
landmark, scale, and topology base. It has no queue or activation operation.
