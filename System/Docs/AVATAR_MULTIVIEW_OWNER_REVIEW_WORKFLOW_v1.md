# Avatar Multiview Owner Review Workflow v1

Date: 2026-07-16

## Purpose

This is the private human-review step between exact-hash enrolled images and
the existing multiview evidence evaluator. It gives Robert a local browser UI
for inspecting the exact source bytes and explicitly authoring the review
artifacts required by `Core/avatar_multiview_authoring.py`.

It does not contain an avatar queue endpoint, likeness author, mesh operation,
render/export operation, or runtime activation endpoint.

## Robert launcher

Run:

```text
Start_Robert_Avatar_Multiview_Owner_Review.bat
```

The launcher binds the service to `127.0.0.1:8876` and opens the browser. The
command underneath is:

```powershell
python tools\avatar_multiview_owner_review_server.py serve `
  --manifest Avatar\avatar_builder\multiview_authoring\manifests\private\robert_user_avatar_20260716.draft.json `
  --reviewer-id robert_owner `
  --open-browser
```

Stop it with Ctrl+C in the launcher window.

## What Robert must review

For each chosen exact image:

1. Inspect the displayed image and exact SHA-256/native dimensions.
2. Explicitly confirm that it depicts the locked subject and selected version.
3. Choose its view label.
4. Enter and confirm an in-bounds crop.
5. Choose the camera model and one shared coordinate-frame ID for the reviewed
   multiview set.
6. Click or enter every landmark manually, assign its required region, and
   explicitly confirm each point.
7. Check the final confirmations and save the immutable source-review artifact.

The complete evidence set needs at least three distinct reviewed images that
collectively contain a front view, a profile/three-quarter depth view, a
full-body view, and all required landmark regions shown in the UI. The workflow
does not suggest or infer landmarks.

Robert must also make two separate decisions:

- Scale: approve a reviewed metric height, or explicitly choose
  `scale_unknown_review_only` and forbid height inference.
- Topology base: select one exact entry from the audited base-authority catalog,
  confirm the manifest's locked adult or non-adult topology lane, confirm the
  inspected cage source, and confirm that a new subject surface is required and
  surface copying is forbidden. Free-form base paths are not accepted.

The workflow never changes the manifest's candidate, subject, selected version,
or topology lane.

## Exact-hash behavior

Each save requires the manifest SHA-256 that the page originally loaded. The
service reopens and rehashes the manifest and source/base file before writing.
A sibling OS file lock serializes cooperative writers across server processes;
the manifest hash is checked again while that lock is held before atomic
replacement. If another review changed the manifest, or a source file changed,
the save is blocked and the page must refresh.

Approved review JSON is immutable and content-addressed under:

```text
Avatar/avatar_builder/multiview_authoring/private_reviews/<candidate_id>/
```

The manifest receives only an artifact path plus its exact SHA-256 binding. The
existing evaluator independently rehashes those artifacts.

## Local privacy and request boundaries

- The server binds only to IPv4 loopback `127.0.0.1`.
- Peer address and `Host` are checked; DNS-rebinding-style hostnames are denied.
- Write requests require an in-memory CSRF token and a loopback `Origin`.
- Private images have no general file route. Each image URL contains an opaque
  HMAC token plus current manifest/source hash bindings.
- Image URLs are revalidated against the manifest immediately before bytes are
  served.
- Responses use no-store caching, no CORS permission, frame denial, a restrictive
  content-security policy, and disabled camera/microphone/geolocation access.
- Source filesystem paths and image bytes are omitted from API summaries and
  Markdown reports.

This protects the material from network exposure. It is not a separate Windows
account security boundary against other software already running as Robert on
the same computer.

## Canonical Gwen and topology routing

The former `spider_gwen_adult_avatar_project_variant_20260716` manifest is
rejected as superseded audit material. The only reviewable Gwen target is the
existing canonical Earth-65 adult 18-20 profile:

```text
spider_gwen_spider_gwen_20260606_013325
```

`confirmed_adult_topology` and `non_adult_doll_safe_topology` remain distinct.
A base review must exactly confirm the lane already locked in the manifest; the
UI cannot switch lanes.

Every session load and every save also runs the read-only canonical identity
preflight. Candidate aliases must resolve through the candidate identity
registry; subject, required fictional version, maturity lane, and topology lane
must match the canonical profile. Review artifacts bind the exact registry and
profile SHA-256 values. A missing, changed, or contradictory registry/profile
route blocks the save.

Only regular JSON manifests below this exact root are reviewable:

```text
Avatar/avatar_builder/multiview_authoring/manifests/private/
```

Manifests copied elsewhere in the project, absolute/out-of-project paths, and
paths containing symlink components are rejected even if their JSON claims
private visibility.

## Audited topology-base authority

The base picker reads only
`Avatar/avatar_builder/multiview_authoring/base_catalog/authority.json`. Each
entry is exact-hash bound to one `base_body_reference` record in the asset
library manifest. The service independently rehashes the catalog, asset-library
manifest, and GLB, reruns a non-rendering GLB structure inspection, compares the
audited metrics, and enforces adult versus non-adult use flags. If any binding
or metric changed, or no entry is authorized for the manifest's topology lane,
the base stays not ready.

The current structural gate proves only a nonempty, weighted, skinned cage with
a bounded joint set and no detected accessor/joint/layout errors. It does not
prove stable deformation, motion quality, likeness, or anatomical completeness,
and it never permits copying the reference mesh as the candidate body.

## Path-free report

The browser includes a live path-free report. It can also be printed without
starting the server:

```powershell
python tools\avatar_multiview_owner_review_server.py report `
  --manifest Avatar\avatar_builder\multiview_authoring\manifests\private\robert_user_avatar_20260716.draft.json `
  --reviewer-id robert_owner
```

An optional `--output Data/codex_reports/<name>.md` is restricted to that report
directory.

## Current limit after review

Completing these reviews can make the evidence contract pass, but the next
state remains an input-readiness result. A non-rendering preparation/proof
backend now exists for canonical routing, source evidence, and structural
checks. The generalized Blender worker that fits and authors a new likeness
surface from the reviewed cage still does not exist. This owner-review server
never calls `queue_multiview_authoring_manifest` and cannot create or activate a
body.

## Verification

The 2026-07-16 implementation pass completed with:

- Python compilation for the review core, server, and tests;
- browser JavaScript syntax verification with Node's parser;
- 17 focused owner-review tests: 16 passed and the file-symlink case skipped
  because this Windows account does not hold symlink privilege;
- 79 owner-review/multiview/component/preflight/workspace/likeness integration
  tests: 78 passed with that same platform skip; and
- 192 broader avatar tests: 191 passed with that same platform skip and no
  failures. The former Beth clothed-diagnostic hash mismatch was resolved by
  retaining the exact reviewed model snapshot beside the current R5 proof.
