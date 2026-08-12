# Kira R6 private clothed owner review v1

Status of this contact-sheet artifact: private, inactive, unapproved, and fail-closed.

Update on 2026-07-19: after this contact sheet was completed, Robert explicitly
requested that the exact R6 body be added to Kira for ordinary live visual
feedback. R6 is now selected separately as a reversible owner-review trial.
That later selection does not turn this static page into an activation or
approval surface. See KIRA_R6_REVERSIBLE_LIVE_OWNER_REVIEW_TRIAL_v1.md.

## Open the review

Run Open_Kira_R6_Private_Clothed_Owner_Review.bat, or open:

Avatar/avatar_builder/private_owner_reviews/kira/r6_neutral_clothed_20260718/index.html

The page has no activation, approval, export, or live-body replacement control.
It shows the exact current body and exact R6 candidate as read-only render
inputs. Retained full-body pictures use a temporary matte-charcoal inspection
top and shorts. That coverage is not an exported garment and proves nothing
about the wardrobe system.

## Exact identities

- Current live Kira body:
  3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e
- R6 candidate:
  ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77
- Staged brown-eye source:
  fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413

The builder hash-checks those inputs and the live body before rendering, then
checks the live body again after rendering.

## What the review found

R6 can be inspected without the former blue cover. Neutral, three-quarter,
side, back, reach, stride, seated, and face views are retained.

The eye result is a failure, not a pass. The exact staged eye source places
sclera in the socket area, but the iris and pupil are not visibly seated on
R6 in the exact fit diagnostic. The sheet therefore includes two different
pieces of evidence:

1. the actual R6 eye-fit diagnostic, which remains failed/unresolved; and
2. the brown-eye rig's source proof, explicitly labeled as not R6 fit proof.

The renderer applies diagnostic-only colors and hides the imported GLB cornea
because Blender 5.1 renders that cornea opaque. These temporary render settings
do not edit either GLB and do not prove runtime material quality.

## Gates still closed

- adult anatomical completeness;
- natural long-duration rig deformation and movement;
- final skin, hair, face, and Kira-specific likeness;
- correct R6 iris/pupil seating and expression fit;
- owner-visible existing-mouth audio lip sync;
- a separate wearable/shareable garment system;
- Kira's voluntary choice and exact owner acceptance;
- live promotion or activation; and
- avatar autobuild, which still requires two independently approved bodies.

The original live GLB remains unchanged. A separate guarded profile selection
now loads R6 only for the reversible live trial; permanent promotion remains
blocked until the outstanding gates can truthfully be satisfied.

## Rebuild and verify

Rebuild:

py Tools\build_kira_r6_private_owner_review.py

The canonical directory is append-only for a completed review. Preserve or
choose a new run directory before rebuilding.

Verify:

py -m unittest Testing.test_kira_r6_private_owner_review -v
