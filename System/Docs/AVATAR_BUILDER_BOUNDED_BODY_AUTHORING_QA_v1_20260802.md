# Avatar Builder bounded body-authoring QA v1

Status: **MANDATORY GENERIC QA CONTRACT — NOT A PROMOTED GEOMETRY METHOD**

Contract:
`Avatar/avatar_builder/tooling/bounded_body_authoring_quality_contract_v1.json`

Mandatory append-only replacement-surface addendum:
`Avatar/avatar_builder/tooling/bounded_body_authoring_quality_contract_v2.json`
and
`System/Docs/AVATAR_BUILDER_PATCH_PARAMETERIZATION_AND_CONTINUITY_QA_v2_20260802.md`.
The v1 contract remains exact; v2 adds the ordered-surface, coherent-normal,
inter-quad continuity, precision-roundtrip, direct-3D-intersection, bounded
geometry-repair, and future-system compatibility gates learned after v1.

This record transfers only general engineering lessons into Avatar Builder.
It contains no private geometry, identity values, textures, protected images,
person-specific indices, coordinates, deltas, morphs, or measurements. It does
not approve a body, promote a reusable geometry method, open Blender, assign a
resident, or authorize runtime export.

## Required authoring sequence

1. Bind the exact source asset, complete source-package inventory, worker,
   plan, QA contract, and protected live-state baseline by project-relative
   path and SHA-256.
2. Refuse absolute paths, traversal, symlinks, source overwrite, and any output
   directory that existed when the process began.
3. In a read-only preflight, exercise every immutable digest and candidate mask
   before creating an attempt directory.
4. Record every semantic correction as its own stage. Bind its candidate-
   supplied mask by count and index-set hash, pin its boundary, and record the
   exact changed-index set.
5. Recompute canonical nonadjacent face-pair sets after every stage. The gate
   is `after_pairs - permitted_before_pairs == empty`; counts alone do not
   identify which operation introduced a defect.
6. Render explicit neutral, component, pose, and contact evidence only after
   the structural gates pass. Restore and digest neutral after every pose.
7. Preserve a complete inactive candidate for owner review after the bounded
   attempt limit. Never convert technical success into owner approval.

## Blender 5.1 digest compatibility

Mesh attributes can expose either scalars or RNA array values. A deterministic
digest must tag and encode booleans, integers, floats, strings, and recursively
encoded arrays. Unknown value or data-item types fail closed.

Actions can use legacy `action.fcurves` or layered storage. Layered traversal
must include action slots, layers, strips, channel bags, and their F-curves.
Curve paths, indices, key coordinates, handles, interpolation, and easing are
part of the digest. An API change never justifies deleting the action guard.

There is not yet a promoted reusable Blender digest implementation. A future
generic helper must pass the existing reusable-method promotion gate and
non-private fixture proof before it can become selectable.

## Collision-aware local backoff

When one authorized stage introduces a new pair:

- attribute the pair to the exact stage and mask;
- keep both the pre-stage safe coordinates and proposed coordinates;
- derive a protected core only from moved vertices on offending faces;
- expand only bounded edge rings inside the same authorized mask;
- blend those rings toward their safe coordinates while leaving unaffected
  proposed coordinates intact;
- keep pinned boundaries byte-exact;
- recompute exact pairs after every bounded pass;
- discard the staged result if any new pair remains.

Lowering a global strength may reduce collision counts but does not prove zero
collisions. Conversely, zero intersections and a closed manifold do not prove
that the shape looks natural.

## Pose and contact evidence

Knees require side- and degree-labeled evidence at 30, 55, and 80 degrees for
left, right, and bilateral bends. Each state records requested and measured
angle, direction/frame, exact intersection delta, support/contact residual,
foot support, render hash, and neutral-restoration digest.

Seated, lying, and activity-ready contact states remain separate. Capsule
clearance and a pose name do not prove skinned-mesh quality. A static lying
render is not accepted natural motion, and seat contact does not pass when the
feet float or limbs overlap rigidly.

## Visual stop and rejection rules

Only two completed visual repairs may target the same defect. A mechanical
pre-authoring failure does not consume a visual attempt when it created no mesh
mutation, render, or candidate save, but its append-only traceback and hashes
remain preserved.

After the second visual repair, do not start another body or general framework.
Preserve the best structurally safe complete candidate, disclose every defect,
and stop for the owner. If no structurally safe candidate exists, stop as
blocked rather than exporting or activating one.

The following can never be labeled a visual pass merely because topology or
hash gates passed:

- a plate-like or layered surface;
- dark, pinched, or rounded knee collapse at 55 or 80 degrees;
- new posed self-intersections;
- unsupported or floating feet;
- rigid or overlapping contact limbs;
- a generic or mannequin-like face or eyes;
- simplified flat nail plates;
- a review camera that does not actually show the claimed component.

These conditions remain explicit rejection or owner-decision findings. They
do not authorize activation, assignment, publication, upload, or an inferred
approval.

## 2026-08-02 R19 transferable component lessons

The following additional rules are generic method lessons only. They do not
promote the in-progress Kira R19 candidate or transfer her private geometry.

- Preserve a qualified foundation's regional albedo, roughness, normal, and
  micro-surface graph unless a hash-bound replacement proves equal or better
  in matched renders. Replacing textured skin with one flat color is a
  mannequin-regression failure even when the RGB direction is warmer.
- A color correction must use derived material copies, retain every source
  image/normal/roughness connection, record the inserted node and parameters,
  and render the same face/body under fixed color management before selection.
- Eyebrow alternatives are detachable components. Render one option at a time
  with identical camera/light settings; never stack variants or regenerate an
  accepted face to correct brows.
- An aperture replacement has two topology ledgers: the exact affected seam
  and the inherited foundation boundary multiset outside it. Require all
  intended seam vertices to merge, one connected target component, zero new
  patch/seam boundaries, and a byte-stable inherited outside-boundary set.
  Do not falsely claim a globally closed body when a foundation deliberately
  retains eye, mouth, or digit openings for attached components.
- A zero-intersection patch can still fail visually. Boundary-to-centroid
  spokes, broad triangular panels, and smooth-shaded aprons are rejected when
  their construction remains visible. Use surrounding curvature and
  anatomically grouped boundary arcs rather than a single center fan.
- Contact acceptance measures the visible skinned surface, not only bones or
  collision capsules. A reusable seated action must record seat and both-foot
  residuals, support penetration, and exact posed intersection deltas, then be
  rerun on the final repaired surface before promotion.
- Nail projection requires digit-local dorsal/tangent frames. Rolled thumbs
  and compact toes may not share a global ray direction or MakeHuman-specific
  length bounds. Every generated shell still needs positive bounded clearance,
  exact narrow-phase intersection checks, attached silhouette review, and an
  explicit bone binding.

## Additional measured-method lessons

These are generic authoring rules only. Candidate-specific measurements,
identity values, paths, hashes, and review findings remain in their private
append-only handoffs.

- A Blender 5.1 read-only armature signature stays out of edit mode and hashes
  the full `bone.matrix_local` rows together with `head_local`, `tail_local`,
  parent name, and `use_deform`; it never assumes that `Bone.roll` is exposed.
  Syntax compilation and a normalized worker diff are mandatory before a
  Blender launch.
- Material graph presence is not a visual color gate. Iris hue must be reviewed
  through the final cornea under fixed lighting and color management. Albedo,
  roughness, and specular response remain separate gates.
- Deterministic action ranking keeps a visual veto. Numeric seat or foot
  contact cannot replace side, three-quarter, and contact close renders.
- A supported face-up pose still requires visual review of spine silhouette,
  head/neck and shoulder support, limbs, hands, and soft-tissue response.
- Activity evidence is labeled literally. A reach is not eating, drinking,
  swallowing, or grasping without the corresponding measured contact and
  object evidence.
- Zero body-to-nail crossings does not prove nail appearance. Preserve exact
  body self-intersection counts beside every action render.
