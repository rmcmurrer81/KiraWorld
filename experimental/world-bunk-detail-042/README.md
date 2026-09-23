# Static bunk geometry detail042 — isolated

The habitat bunk used box pillows and flat blankets, with no upper front guard.
This candidate authors rounded mattress/pillow meshes, a folded blanket surface
with dropped outer edges, connected upper guard members and a ladder-side access
bay. These are original deterministic meshes; no images or external assets were
copied. Dimensions are grounded in the existing authored assembly, not a claim
about a measured real spacecraft or a certified bunk design.

The assembly remains 2.08 m long, 0.90 m deep and 2.12 m high. Upper mattress top
is 1.42 m; guard top is 1.78 m. The front access bay is 0.523 m wide and contains
the existing ladder alignment. Guard posts reach the upper deck. Soft furnishings
fit the conservative existing bunk collider; mattress/deck and pillow/mattress
vertical support relations are checked. The ladder stiles now reach floor level.

Four synthetic layouts and the explicit saved Mars geometry pass CPU checks:
actual meshes inside the original collider; six routes clear in both directions;
six door sweep bounds clear; bunk footprint inside the room floor support; no
other furnishing overlaps; finite vertices/normals; 6,708 triangles per bunk;
15 other equipment groups unchanged. The module embedded in the native viewer
is byte-identical to the exporter module after removal of export keywords.
Actual authored exporter mesh assembly matches the viewer's bunk meshes.

The exporter-path geometry test uses inert Canvas placeholders only to reach
mesh assembly. That geometry test alone does not verify rasterized textures or a real GLB
roundtrip. Subsequent actual checks are separately recorded in ACTUAL-EXPORT-RESULT.json.
No browser, native UI, model or GPU job was run. Static geometry establishes no
cloth physics, comfort, structural safety, standard compliance or visual approval.
The conservative collision box still prevents walking/climbing/sitting inside the
bunk; this change does not implement avatar resting interaction.

Five files were installed together after root approval: viewer, shared renderer, producer pins,
the export assembly comment, and the API's exact viewer digest. Old immutable
previews remain intact and must not silently acquire the newer appearance.
Open current preview now creates/reuses a newly pinned build; a repeated API
refresh reused the new build while every old preview/pointer stayed unchanged. New exports must match that build, not the old viewer.

Exact installation and a fresh installed API export/import passed. See
INSTALLED.json, ROOT-EXECUTION.json and ROOT-ARTIFACT-REVIEW.json; the original
INSTALL-PLAN.json remains the frozen pre-install proposal. A real GLB export/import and two bounded offline CPU review renders now passed.
See CURRENT-STATUS.json, ACTUAL-EXPORT-RESULT.json and cpu-review-002/bunk-review.png.
Root accepted the limited static geometry improvement and installed it; native UI was
not opened. The first review was noisy/tightly framed; the second is the selected
640x480 artifact. Both use the actual GLB, with a disclosed neutral review light.
Total rendering time was about 14.3 seconds; peak sampled family RSS stayed below
676 MiB. This does not make the whole habitat visually approved.
