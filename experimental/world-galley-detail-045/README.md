# Galley detail045 — isolated, awaiting installation decision

The saved Mars habitat has a bunk, personal storage and a small galley in Crew
Living Quarters. Its old galley used a dark rectangle over a solid countertop
for a sink and generic upper/lower cabinets. It has no dining table or chairs.
This candidate improves that existing galley only; it does not pretend that the
crew room is now a complete mess room.

The assembly remains **1.42 m wide × 0.68 m deep × 1.74 m high**. It now has:

- A countertop built around an open sink mouth, four enclosing basin walls,
  basin bottom and drain. Clear opening is 436 × 396 mm; depth from the 890 mm
  counter to the basin floor is 201 mm.
- A continuous curved faucet mesh and separate valve/lever. The countertop to
  the right provides roughly 823 × 680 mm of clear modeled preparation surface.
- A utility cupboard, three narrow drawers, and a distinct closed cold-food
  compartment with perimeter gasket, handle and toe grille.
- An upper pantry and a closed warming appliance with a recessed interior,
  tray, transparent window, handle, dials and vent details. A modeled task-light
  strip sits beneath the upper cabinet.

These are original authored meshes with the existing materials. No reference
image, brand, text label, random prop or downloaded asset supplies their shape.
Research040 informed the aim of recognizable crew-space equipment; the exact
dimensions come from the existing procedural galley envelope, not measurements
of a real spacecraft or film set. No life-support, food-safety, comfort or
engineering certification is implied. All appliance components are static:
there is no water flow, heating, refrigeration or cupboard-opening interaction.

## Validation completed

`test_galley.mjs` checks four synthetic layouts and the explicit saved Mars
geometry. Rays pass through the sink mouth to the real basin floor and hit its
four side walls. The corresponding old rays hit the flat surface at 866.5 mm;
the candidate rays reach 689 mm. Other checks cover the appliance's recessed
interior, finite geometry/normals, preparation surface, unchanged bounds and
floor support, all six walking routes in both directions, and all six door
sweeps. The other 15 equipment assemblies remain numerically identical.

The galley has 73 meshes and 1,560 triangles. The conservative assembly collider,
placement plan, structural geometry, navigation code, door controller and paired
airlock rules are unchanged. The module embedded in the viewer is identical to
the exporter module after removal of `export` keywords. The authored exporter
assembly produces the same galley geometry as the viewer.

One real CPU API export/import at `actual-001/package` passed in 2.12 seconds,
with a sampled process-family peak of 645.4 MiB. It produced a 1,194,636-byte GLB:
623 meshes, 97 materials, 67 embedded texture maps, seven rooms, six doors and
134 metadata colliders. The importer verifies exact geometry attributes/index
arrays, transforms, material parameters, texture pixels/color space/repeat,
door hinge movement, fixed frames and pairing policy. Texture/material counts
did not increase. See `ACTUAL-EXPORT-RESULT.json` and package `ROUNDTRIP.json`.

One supervised headless Blender CPU render produced
`cpu-review-001/galley-review.png` in 7.19 seconds with a sampled family peak of
680.7 MiB, within the 30-second/2-GiB cap. The source GLB was unchanged; Blender
exited cleanly. The artifact uses explicit review lighting and a raised camera,
so it does not establish the installed preview's lighting or avatar view.
Agent inspection found the full cabinet, visible sink recess and recognizable
appliance forms. The pantry partly obscures the faucet from this camera angle.
Materials still look procedural. Root artifact review and owner review remain
separate; no overall habitat realism approval is claimed.

The first bounds test caught a pull 6 mm beyond the existing collision envelope.
Moving the lower front plane inward 10 mm corrected it. The first candidate and
receipt remain under `history/rev1` and `TEST-INITIAL-FAILED.json`; all later
bounds tests pass. The failed version was never installed or exported.

## Preservation and integration

All 116 protected original files, saved-job pointer, installed source bytes and
previous immutable previews remain unchanged. The candidate preview was created
only under this experiment's `runtime_context` for actual export validation.
No browser, native UI, model, GPU job, server or canonical installation ran.

Five files must change together if root approves the exact `INSTALL-PLAN.json`:
the viewer, shared renderer, exporter appearance digest, producer pins and the
authored-scene provenance comment. Old immutable previews retain their previous
appearance; an approved installation would require a fresh/reused current build
through the existing preview refresh API. Exporting an old preview using the new
appearance is intentionally held by the tested pin contract.

The original compact GLB, metadata, PNG and technical receipts are suitable for
portable backup. Do not include raw owner research, the locally bound preview
tree, installed fonts or native dependency binaries. Local receipts contain
machine paths and need the same path redaction as previous public experiments.
No game-engine runtime, VR support or new appliance interaction is delivered.
