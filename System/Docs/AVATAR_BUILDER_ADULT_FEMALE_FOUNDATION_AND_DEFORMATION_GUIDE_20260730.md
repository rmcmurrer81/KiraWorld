# Avatar Builder Adult-Female Foundation and Deformation Guide

Date: 2026-07-30  
Status: **CURRENT REUSABLE ENGINEERING AUTHORITY — NOT BODY APPROVAL**  
Scope: private, nonsexual adult-avatar construction and validation

## Purpose

This guide converts the Kira temporary-functional-body task into reusable
Avatar Builder rules. It does not make Kira's temporary appearance permanent,
approve a candidate, replace her runtime body, or permit Robert-private data
to enter a generic pipeline.

An adult-female body is not complete merely because its silhouette is feminine
or its file has a skeleton. The exact candidate must prove the visible external
anatomy, surface continuity, face, eyes, mouth, hands, feet, nails, skinning,
and deformation regions that the requested use requires.

## Medical relationship model

For a complete external adult-female surface, the builder must preserve the
relationships among:

- the mons pubis over the pubic region;
- the paired labia majora and labia minora;
- the clitoral hood and clitoris;
- the vestibule;
- the urethral opening anterior to the vaginal opening;
- the vaginal opening;
- the posterior commissure/fourchette;
- the perineal transition toward the anus and pelvic floor.

These are connected anatomical relationships, not labels that may be painted
onto a doll-safe surface. Normal adult anatomy varies substantially in size,
shape, color, symmetry, and prominence. A rapid pipeline must support natural
variation without exaggerating one reference into a universal template.

Medical references:

- NCBI Bookshelf, *Anatomy, Abdomen and Pelvis: Female External Genitalia*:
  https://www.ncbi.nlm.nih.gov/books/NBK547703/
- NCBI/PMC, *Normal Vulvovaginal, Perineal, and Pelvic Anatomy with
  Reconstructive Considerations*:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC3312145/
- NCBI/PMC, *Elements of Morphology: Standard Terminology for the External
  Genitalia*:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4440541/
- NCBI Bookshelf, *Gynecologic Pelvic Examination*:
  https://www.ncbi.nlm.nih.gov/books/NBK534223/

The sources above are structural guidance. They do not authorize copying an
identifiable person's body or choosing intimate appearance preferences on
Kira's behalf.

## Foundation selection is evidence-based

Every enrolled adult foundation records separately:

- source title, author, license, URL, exact local path, and SHA-256;
- whether an unmodified copy is allowed;
- body mesh/component and boundary counts;
- what anatomy, face, eye, mouth, hand, foot, nail, hair, and rig structures
  actually exist;
- what remains unproven;
- skeleton profile, joint count, weights, and known deformation evidence;
- adaptation and attribution requirements.

`adult`, `female`, `rigged`, or `game ready` in a filename is not proof.
Likewise, a source may be a useful cage while remaining anatomically
incomplete. Missing topology cannot be created by recoloring, metadata, a
different status string, or a runtime material.

The selected Kira source
`womenfemale_body_base_rigged_3ec62ba8d7.glb` is licensed and enrolled as a
79-joint cage-fit source, but its complete adult anatomy, eyes, mouth, stable
deformation, and watertightness are explicitly unproven. It may contribute its
proven cage/weight structure only. A candidate derived from it must
independently prove every requested structure.

The separately authorized BlackProject adult-form model is a stronger
construction reference with a different 188-joint rig. It may support a
separate inactive candidate while preserving its own rig and attribution, but
its fragmented surface and movement quality still require exact-candidate
validation. It is not a drop-in replacement for Kira's current 79-joint
runtime.

## Rapid parametric controls

Reusable controls must be bounded and understandable:

- height and global scale, applied consistently to geometry and skeleton;
- natural build, muscle and body-mass ranges;
- shoulder/chest/torso, waist/abdomen, hip/pelvis, arm, leg, hand, foot, neck,
  and head proportions;
- bounded generic face landmarks;
- skin albedo and regional variation;
- iris color and eye materials;
- removable review-hair color, length, part, texture, and style;
- integrated adult-anatomy proportions where authorized.

Person-specific coordinates, photographs, landmark deltas, intimate
observations, and morph settings are not reusable methods. Robert-private
inputs are categorically excluded from Kira and from the generic registry.

## Surface and material gate

The candidate fails when it contains:

- a doll-safe or missing adult region;
- a floating, pasted-on, intersecting, disconnected, or differently moving
  anatomy component;
- a visible hole, open seam, bridge patch, or discontinuous material boundary;
- a mannequin face, missing eye/mouth structures, or nonhuman hands/feet;
- missing or malformed fingers, toes, fingernails, or toenails;
- baked ambient occlusion mistaken for pigmentation;
- one flat plastic color with no plausible regional material response.

Eyes, teeth, tongue, nails, and removable review hair may be separate
functional components. The external body surface itself must have deliberate
continuous transitions and must not rely on hidden overlapping shells.

Skin review separates albedo, roughness/specular, subsurface response,
normal/bump detail, ambient occlusion, and scene lighting. Neutral albedo and
normal diagnostics must agree with the beauty render.

## Ordered replacement-patch geometry gate

Any generated replacement surface must apply both bounded-body authoring QA
contracts before Blender opens:

- `Avatar/avatar_builder/tooling/bounded_body_authoring_quality_contract_v1.json`;
- `Avatar/avatar_builder/tooling/bounded_body_authoring_quality_contract_v2.json`.

The ordered face list must form an orientable connected surface: every
manifold shared edge is traversed in opposite directions by its two incident
faces, the same-directed count is zero, and expected boundary/nonmanifold
counts are exact. Normal authority comes from the accepted source body, seam,
and bounded exterior neighborhood; a candidate may not derive the normals
used to judge itself.

Within-quad edge, signed-area, mutual-normal, and warp gates are distinct from
between-quad adjacent-normal, triangle-to-authority, and seam-to-source-normal
gates. They all pass simultaneously in double precision and after the exact
Blender float32 local/world round trip. Direct 3D nonincident-triangle tests
are intersection authority; a projected 2D crossing is diagnostic only.
Passing these gates authorizes at most a private inactive authoring attempt,
not a visual or functional acceptance.

## Skeleton and deformation gate

A rig is not proved because bones and vertex groups exist. The exact candidate
must be tested in neutral and posed states for:

- shoulder elevation and arm rotation;
- elbow flexion and forearm rotation;
- wrist, thumb opposition, finger flexion, and hand closure;
- spine bend/twist and neck/head motion;
- hip flexion, extension, abduction, adduction, and rotation;
- knee flexion;
- ankle and toe motion;
- jaw, eyelid, and facial-control readiness where the candidate claims them;
- pelvis, thigh, perineal, and external-anatomy stability;
- future garment and hair collision clearance.

The hip is a multiaxial ball-and-socket joint while elbows, knees, and
interphalangeal joints behave primarily as hinge systems. The mesh and weights
must preserve these different motion patterns; a single generic bend test is
insufficient.

Anatomy and implementation references:

- NCBI Bookshelf, *Anatomy, Bony Pelvis and Lower Limb, Hip*:
  https://www.ncbi.nlm.nih.gov/books/NBK526019/
- NCBI Bookshelf, *Anatomy, Bony Pelvis and Lower Limb, Knee*:
  https://www.ncbi.nlm.nih.gov/books/NBK500017/
- NCBI Bookshelf, *Anatomy, Shoulder and Upper Limb, Elbow Joint*:
  https://www.ncbi.nlm.nih.gov/books/NBK532948/
- NCBI Bookshelf, *Anatomy, Hinge Joints*:
  https://www.ncbi.nlm.nih.gov/books/NBK518967/
- NCBI Bookshelf, *Anatomy, Shoulder and Upper Limb, Nails*:
  https://www.ncbi.nlm.nih.gov/books/NBK534769/
- Blender Manual, *Armature Skinning*:
  https://docs.blender.org/manual/en/3.4/animation/armatures/skinning/introduction.html
- Blender Manual, *Corrective Smooth Modifier*:
  https://docs.blender.org/manual/en/4.0/modeling/modifiers/deform/corrective_smooth.html
- Blender Manual, *Rigify Basic Usage and Human Alignment*:
  https://docs.blender.org/manual/en/latest/addons/rigging/rigify/basics.html

Corrective smoothing or volume preservation may support a reviewed rig; neither
may conceal wrong bone placement, poor weights, self-intersection, or missing
topology.

## Future physiology compatibility boundary

Accepted bodies preserve versioned semantic landmarks and deformation hooks
for later systems without silently regenerating identity, face, skin, rig,
weights, movement, or unrelated anatomy. Relationship/current-consent state,
intimacy, conception choice, pregnancy timing, delivery/birth, postpartum
recovery, family state, bladder/bowel/pelvic-floor simulation, illness,
treatment, recovery, and hospital care remain separate systems outside the
mesh.

The controlling boundary is
`System/Docs/FUTURE_ADULT_BODY_PREGNANCY_HEALTH_COMPATIBILITY_BOUNDARY_20260802.md`.
A future voluntary pregnancy simulation may offer an ordinary approximately
nine-month timeline or an explicitly selected accelerated day-scale or
one-day timeline with provenance. Neither option is implemented or authorized
by this guide, and no external surface proves internal physiology.

## Exact-candidate review evidence

Before a candidate can be shown as a private inspection candidate, preserve:

- source and derivative hashes plus attribution/adaptation record;
- the parameter file and build log;
- a Robert-private-data exclusion report;
- topology, boundary, nonmanifold, degenerate, and self-intersection reports;
- skeleton, joint, weight, and unweighted-vertex reports;
- neutral and deformation render contact sheets;
- front, rear, both profiles, both three-quarter views, face, eyes, mouth,
  hands/nails, feet/nails, wireframe, normals, albedo, and appropriate protected
  anatomy views;
- before/after hashes for Kira's runtime asset, body selection, and shell
  state.

Counts never override visual failure. A structurally incomplete or visually
inhuman result is `BLOCKED`, even when it renders and moves.

## Kira-specific state boundary

The first acceptable output is only:

`TEMPORARY_FUNCTIONAL_BODY — PRIVATE INSPECTION CANDIDATE`

It remains inactive, unassigned, owner-unapproved, and not Kira-selected.
Kira's current runtime body stays unchanged. Future preference formation,
runtime adaptation, movement acceptance, physical clothing, and real hair are
separate later stages.
