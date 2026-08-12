# Avatar Multiview Likeness Author Requirements v1

## Purpose

This is the missing authoring stage between reviewed pictures and
`Core/avatar_component_production.py`. Component production can validate and
immutably package already-authored body, hair, eyes, clothes, and rig files; it
must not pretend that copying or renaming a generic/reference model created a
person-specific likeness.

## Required input contract

Every authoring job must bind the following by exact candidate ID and SHA-256:

- a canonical identity/version/maturity preflight that permits authoring;
- at least one accepted front identity view, one profile or three-quarter
  identity view, and one full-body view of the same subject and version;
- reviewed image dimensions, crop/calibration, view labels, and face/body
  landmarks;
- a reviewed target height or an explicit `scale_unknown_review_only` label;
- the selected adult or non-adult doll-safe base and its exact hash;
- any reference model as measurement/topology guidance only, with its exact
  hash and allowed-use record;
- an output rule of `private_review_only_not_runtime`.

Landmarks must cover face outline, brow, eye socket rims, nose, lips, chin,
ears, neck, shoulders, chest, waist, hips, elbows, wrists, hands, knees,
ankles, and feet. Automatic landmark suggestions remain unapproved until a
reviewer confirms the target, view, and placement.

## Authoring behavior

1. Calibrate front and depth views to one metric coordinate frame.
2. Fit an approved base through cage/lattice and local sculpt deltas. Preserve
   continuous topology and rig compatibility; do not copy a character model's
   surface, materials, textures, or identity.
3. Fit a separate head/face surface, eye sockets, eyelids, nose, lips, jaw,
   ears, and neck against all accepted views.
4. Export eyes and hair as separate fitted systems.
5. Export a separate basic review garment. Advanced robe or other garment
   behavior is a later independent capability.
6. Bind a stable body/finger/face rig to the exact authored body.
7. Render clothed front, profile, back, three-quarter, face, hands, and
   deformation proofs. Retain landmark overlays and delta reports.
8. Fail if the output still reads as the untouched base, the landmarks do not
   reproject within reviewed tolerance, eyes float/protrude, topology breaks,
   or clothing is baked into the body.

## Current local capability audit (2026-07-16)

- Blender `5.1.2` is installed at
  `C:/Program Files/Blender Foundation/Blender 5.1/blender.exe`.
- Main Python `3.14.4` has CUDA-enabled PyTorch, but no `cv2`, MediaPipe,
  `trimesh`, Open3D, SMPL-X, face-alignment, or InsightFace.
- Blender Python has `numpy` and `bpy`, but no Pillow, SciPy, OpenCV,
  MediaPipe, or SMPL-X.
- The existing Gwen real-model script imports the adult female base and
  performs coarse band deltas; it explicitly reports
  `failed_requires_landmark_lattice_sculpt_fit`. That is a useful negative
  test, not a likeness author.
- Robert has 15 private multiview photos, but they do not yet have reviewed
  per-photo view/landmark/calibration records or metric scale measurements.

Therefore a high-quality automatic likeness author is not installed today.

The exact-hash manifest/review gate is now implemented in
`Core/avatar_multiview_authoring.py` and documented in
`System/Docs/AVATAR_MULTIVIEW_EVIDENCE_AND_AUTHORING_QUEUE_v1.md`. It verifies
source image hashes and dimensions plus separately rehashed human view,
crop/calibration, landmark, scale, base, and optional model-review artifacts.
Automatic suggestions remain unapproved until confirmed. Passing evidence can
only enter an inactive content-addressed queue; the queue does not run a mesh
author.

The remaining implementation stages are a private landmark placement/review UI
and the generalized Blender cage/sculpt worker. Until the reviewed evidence and
worker both exist, Gwen and Robert must remain blocked rather than receiving
renamed generic bodies.

## Candidate order

1. Validate Beth's already-authored separated adult artifact.
2. Use Robert's authorized 15-view set to calibrate the general photo-primary
   author after landmarks and scale are reviewed.
3. Use the now-explicit existing Earth-65 adult Gwen candidate and accepted
   same-version views. Keep animated-film and other Gwen variants excluded.
4. Apply the same author to every other candidate only after its version and
   maturity preflight passes.

This document authorizes no rendering of private source images, no activation,
no runtime replacement, and no public export.
