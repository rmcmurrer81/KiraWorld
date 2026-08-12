# World Builder Reference Evidence Gate v1

The World Builder now has a reusable, fail-closed rule for real locations:
build only source-supported areas and keep every unsupported destination behind
a closed, locked, collision-solid portal.

`Core/world_reference_evidence.py` validates an area-level evidence contract.
By default an area needs three distinct photo viewpoints, one distinct video
viewpoint, a reviewed plan/map for layout, and a reviewed measurement, section,
or elevation for scale. A project may require more evidence, but it may not
silently count repeated copies of one camera angle as several views.

Passing this gate permits only a draft-authoring attempt. It does not prove
realism, working navigation, a working door, runtime readiness, owner approval,
or a complete location.

## Source and rights rules

- Owner-supplied and public reference images can document visible features,
  but their pixels are not imported as textures unless explicit reuse terms
  allow that use.
- Watermarked stock images are reference-only and are never runtime assets.
- Unknown-rights sources remain context-only and cannot support geometry.
- Google Maps, Street View, and Photorealistic 3D Tiles are treated as
  restricted visualization services. Their imagery/tiles are not cached,
  extracted, traced, machine-interpreted, or converted into Kira World models.
  A future live API visualization must separately meet the service's billing,
  terms, cache, privacy, and on-screen attribution requirements.
- Every source records provenance, rights mode, intended truth use, and—when it
  is a photo or video—a viewpoint identifier.

## Unknown rooms and doors

An area below its evidence threshold must declare
`evidence_sufficient_for_draft=false`. Every portal into it must be
`closed_locked_solid`, must not open, and must keep collision enabled. Finding
new references does not unlock the door automatically: the contract must be
reviewed again, then the area still needs geometry, collision, route, resource,
realism, and owner-review gates.

Validate a contract with:

```powershell
python tools/validate_world_reference_evidence.py <contract.json>
```

