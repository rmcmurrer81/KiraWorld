# Avatar Component Production Queue v1

## Purpose

The component production queue closes the handoff between an authoring backend and Avatar Builder review. It packages an already-authored exact-hash body, hair, eyes, and clothes set as four real, separate GLB artifacts and extracts a fifth exact-body-bound rig skeleton descriptor.

It does not reconstruct a likeness from pictures. A photo-only candidate without authored components remains `blocked_general_photo_fit_authoring_missing`; the queue will not rename a generic base mesh as that person.

## Files and storage

```text
Core/avatar_component_production.py
tools/avatar_component_production_queue.py
Avatar/avatar_builder/component_production_requests/
Avatar/avatar_builder/component_production/queued/
Avatar/avatar_builder/component_production/results/
Avatar/avatar_builder/component_production/artifacts/<candidate>/<job-id>/
Avatar/avatar_builder/component_production/plans/
```

The job ID is the canonical SHA-256 of the validated job payload. Job and result files are exclusive-create. Repeating the same request is idempotent. Existing package contents are rehashed before an existing result is accepted. A changed request, orchestration contract, authority artifact, source component, queue payload, symlink, path escape, duplicate artifact, invalid GLB envelope, activation request, or public-export request fails closed.

Processing is bounded to 1–16 jobs per invocation and defaults to four. Nothing is removed from the queue, overwritten, rendered, registered, or activated.

## Supported maturity and source lanes

Both `confirmed_adult_topology` and `non_adult_doll_safe_topology` are supported. The non-adult request must explicitly reject adult anatomy and must already have a valid doll-safe orchestration route. Packaging preserves a topology lane; it does not prove the topology review.

Before file-based planning or component adoption, the queue also runs the
canonical profile preflight described in
`System/Docs/AVATAR_CANONICAL_PROFILE_PREFLIGHT_v1.md`. Exact registered aliases
are allowed, but blank fictional versions, unresolved maturity, profile/request
mismatches, and in-place adult conversion fail before component authoring. An
unresolved candidate's doll-safe safety fallback is not permission to author a
body. The preflight is read-only and records exact registry/profile hashes.

Source lanes are:

- `licensed_shape_preserving_derivative`
- `photo_only_reconstruction`
- `photo_primary_with_reference_model_measurement`

The third lane formalizes the requested model-bonus workflow. Accepted multiview pictures are identity authority. A model is an exact-hash, authorized measurement/topology guide only. The candidate must be a newly authored surface, and the model surface, textures, materials, and identity cannot be copied.

## Body versus garment readiness

`body_private_review_ready` now evaluates component separation, topology, rig binding, stable visual deformation, face/lip-sync, locomotion/contact, clothed-only privacy, and owner review of the exact clothed assembly.

`advanced_garment_capability_ready` evaluates the physical wearable lifecycle independently. A missing robe evidence pack no longer blocks body review. It still blocks use of that robe. This allows the intended order: make and review the person first, then build realistic dressing and undressing.

## Commands

```powershell
py tools\avatar_component_production_queue.py plan --orchestration-request Avatar\avatar_builder\orchestration_requests\robert_user_avatar_20260716.json
py tools\avatar_component_production_queue.py queue --production-request Avatar\avatar_builder\component_production_requests\beth_smith_ordinary_temp_20260716.json
py tools\avatar_component_production_queue.py process --max-jobs 4
```

Planning is read-only. Queueing validates and freezes exact bindings. Processing copies only the four authorized component files into an immutable candidate package and derives the rig descriptor. Runtime activation remains false in every output.

Photo-lane planning can now accept `--multiview-manifest`. The plan records a
path-free exact-hash readiness summary: enrolled/exact/reviewed source counts,
front/depth/full-body coverage, one-frame calibration, landmark regions, scale,
base review, integrity failures, and review gaps. The plan states distinguish:

```text
blocked_multiview_evidence_manifest_missing
blocked_multiview_evidence_invalid
blocked_multiview_evidence_review_incomplete
blocked_multiview_likeness_author_backend_missing
```

Even the last state has no authored components. It means the input contract is
ready but the new-surface likeness worker is still absent.

## Current candidates

- Beth has a real separated component set and has been packaged immutably. This resolves the missing production handoff, not her topology, visual deformation, face/lip-sync, locomotion, likeness, or owner-review blockers.
- Gwen and Robert have no subject-specific photo-fitted component set. Their plans stop at the missing general photo-fit authoring backend. Their existing pictures/models can feed the new picture-primary/model-measurement contract once exact evidence and a new-surface author are available.
- No current non-adult person was built in this pass. Tests exercise a real separated GLB package through the doll-safe route and verify that an adult-anatomy flag is rejected.
