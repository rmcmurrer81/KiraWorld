# Avatar Builder Static Adult Anatomy and Skin Guide

Status: CURRENT STAGE-A IMPLEMENTATION AUTHORITY  
Scope: private, nonsexual adult static likeness review only

## Why this exists

Avatar Builder must not treat an adult body as a generic mannequin or attach a
separate anatomy object and call it complete. Static review is a distinct gate
before rigging or runtime movement.

## V23 engineering lesson - rendered form controls

The V23 R18-R24 trials establish a reusable Avatar Builder rule: topology
numbers, metadata, and coordinate movement do not prove an effective repair.
Every one of those trials is rejected engineering evidence.

In the V1 baseline, the external form appears partway down the upper legs and
background is visible as a dark hole above it. R19/R20 showed that retaining
the real lateral body surface avoids the broad U/leaf panel created by R18.
R22 then showed that filling a detected internal edge loop can leave the
visible hole unchanged. R24 showed that raising an entire branch can still
leave a missing superior transition and an attached-looking side silhouette.

Avatar Builder must therefore distinguish:

- an open mesh boundary;
- an internal tunnel or cavity;
- visible background caused by missing spatial coverage;
- shadow or ambient occlusion;
- an overlay, replacement panel, or separately attached branch.

Component-ID, flat-material, wireframe, profile, and three-quarter renders are
required together. If a visible hole, panel, pasted-on transition, or
implausible placement remains, the result is rejected even when hashes change
or topology reports improve.

For this repair class, author a compact superior pubic/root bridge from the
retained lower-abdomen and pubic surface. Use actual mesh positions and surface
tangents; preserve lateral body form; weld only true medial counterparts; and
evaluate compact shaft and scrotal branches only after the continuous bridge
exists. Do not collapse lateral pairs to the centerline, invent ellipse
coordinates as if they were source topology, rely on coordinate shifts, add a
floating overlay, use Boolean-only union, or transfer another person's
identity/body surface.

This lesson does not approve V23. Status remains
`V23 IN PROGRESS - NOT OWNER APPROVED`, and Stage A remains static-only.

## Protected owner-reference intake and authority separation

Additional owner references must be registered without expanding their
exposure. The 2026-07-29 Robert batch uses an opaque, hash-only manifest and
keeps the raw files in the owner's source location. Intake must not copy raw
images, emit thumbnails/contact sheets, disclose filenames or paths, train a
general model, or authorize public export.

For a consented self-avatar, owner references control identity and likeness
and may support bounded decisions about proportions, placement, and natural
coloring. General anatomy sources and authorized adult reference models guide
structure, topology, and later functional design only. They do not supply a
donor identity, skin, full-body proportions, or a whole surface to transfer.
When those authorities differ, preserve the owner's identity and proportions
while using anatomy evidence only to repair structurally unsupported areas.

Reference retention is also an explicit state. A future deletion request must
remain `DEFERRED_UNTIL_OWNER_APPROVAL` until its stated body-completion and
owner-approval condition is met. Intake must record that no deletion occurred;
it must not interpret the request as permission to remove evidence during an
unapproved repair phase.

## Structural model

The external male anatomy must be evaluated as connected regions: pubic
transition, root connection, shaft, glans, scrotal transition, and perineal
transition. The root is supported at the pubic region and includes deeper
attachments; therefore a visible surface that hangs from an arbitrary low point
is structurally wrong. The scrotum is inferior to the penis, is thin and
flexible, and is not a rigid sphere or an interchangeable body patch.

Authorized adult anatomy references guide placement and topology only. They do
not supply Robert's identity, proportions, face, skin, or muscular build.
Unclear details inferred from those references remain labeled:

`ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE`

References:

- NCBI, *Anatomy, Abdomen and Pelvis, Penis*
  https://www.ncbi.nlm.nih.gov/sites/books/NBK482236/
- NCBI, *Anatomy, Abdomen and Pelvis: Scrotum*
  https://ncbi.nlm.nih.gov/books/NBK549893/
- Springer/PMC, *Male genital morphology standard*
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4440541/
- NCBI, *Microstructure of the Male Genital Skin*
  https://ncbi.nlm.nih.gov/books/NBK586059/

## Static geometry gate

The primary skin must be one connected component through the anatomy region.
The primary component must have zero open boundary edges and zero nonmanifold
edges. Separate eyes, teeth, nails, and removable hair may remain separate
components. A separate, floating, intersecting, differently colored, or
independently moving anatomy object fails.

Required protected views are front, rear, both profiles, both three-quarter
views, face close-up, side anatomy placement, front anatomy close-up, and
three-quarter anatomy close-up.

## Skin and light separation

Skin color is not shadow. Avatar Builder records these channels separately:

- base albedo and regional color;
- roughness/specular response;
- subsurface scattering;
- normal or bump detail;
- lighting and cast shadow.

Ambient occlusion or cavity darkening must not be baked into the albedo as
dirty-looking pigmentation. Diagnostic review uses neutral fill lighting and a
shader-channel report. Lips, nipples, and other normal regional areas may have
subtle albedo variation without using a single flat body color.

The Blender Principled shader's subsurface method is appropriate for skin, but
its result depends on a closed mesh and must remain distinct from roughness and
base color:
https://docs.blender.org/manual/nb/5.0/render/shader_nodes/shader/principled.html

## Hair in Stage A

The current review hairstyle is removable and must match the protected
reference color and silhouette. For Robert, the accepted color class is
blonde/light-blonde/dark-blonde, not brown. A removable static hairstyle does
not prove the future groom, growth, wetness, grooming, or motion system.

## Stage boundary

Stage A proves only static technical readiness for Robert's visual review.
It never grants owner likeness approval automatically.

Stage B remains blocked until Robert accepts Stage A. Stage B will separately
test unified rig deformation, pelvis/thigh interaction, soft-tissue response,
collision/contact, and standing, walking, sitting, and lying poses. No claim
that anatomy “moves realistically” is permitted during Stage A.
