# Authored habitat equipment025

The latest review build is `revision-002/candidate`, composed from a copy of024
and the two authored modules in this directory. The original025 candidate and
its first pinned preview are preserved as historical snapshots. Neither build
is installed or visually approved.

The existing `functional_program` selects the equipment. Unknown unrelated room
functions acquire no habitat dressing. The current seven-room layout receives
six distinct equipment programs and a circulation treatment:

- Equipment vestibule: suit locker bays with helmets, torso/leg shapes, a gear
  bench and hose/connector station.
- Airlock: mounted control cabinet and filter cylinders; a grating texture gives
  the floor a different finish. No pressure or life-support behavior is claimed.
- Operations: two monitor/workstation assemblies with task chairs and a server
  rack, with clearance to walk around them.
- Habitat: two-level bunk, ladder, mattress/pillow forms, galley and storage.
- Laboratory: framed transparent glovebox with glove ports, science worktop,
  microscope, sample bins and storage.
- Observation: upholstered seating and a three-tier growing rack with plants
  and shelf lights.

These are original procedural meshes and textures, not copied set photographs
or a measured reconstruction. Root maintains research and attribution separately
in `research/` and `RESEARCH.md`.

The plan reserves compiled routes, entry space and door swing volumes before
placing equipment. Rendered groups use the same assembly bounds as their
conservative AABB colliders. Ribs, luminaires and small mounted plaques have
physical bounds too. Wall panel finishes replace the old floor grid and giant
floating room labels. Material roughness/metalness, tinted room accents, monitor
emission and bounded per-room task lights distinguish the spaces.

Both the portable synthetic fixture and a read-only evaluation of the actual
preserved Mars geometry pass six validation groups. All16 equipment assemblies
fit their bounds, all six portal routes remain clear when opened, and entry and
door swing spaces remain available. The plan contains51 extra colliders and406
authored meshes, with no equipment omitted. This does not certify visual quality.

Revision002 increases interaction reach from1.8m to2.25m. The previous0.55m click
step could skip the narrow safe interaction band outside the door swing. Four
callback checks reproduce that problem and show that one step can now reach the
door, open it, cross into the airlock and close it. Swing/collision safeguards
are unchanged. The original024 files are preserved.

The latest preview plan is `revision-002/PREVIEW-PLAN.json`. Its exact server
serves loopback only and stops after300 seconds. Root coordinates any browser
graphics before launch.121 source/owner files remain protected; no saved job
pointer, owner geometry, canonical source, model or GPU process was changed by
this preparation.

Installation still requires integrated review with026 immutable-preview
compatibility. Renderer replacement must not break existing saved previews.
The old Mars appearance remains owner-rejected; this new furnished presentation
awaits visual review. The result remains a procedural prototype with static
equipment and session-local doors, not a finished world.
