# Isolated053 — an actual observation viewport

The saved original habitat calls its observation room “Viewport Deck”, but the
installed051 mesh encloses every exterior wall in solid opaque boxes and panel
planes. It has no viewport or exterior terrain. This candidate replaces one
eligible exterior wall's drawn box with a four-piece surround, retaining its
original full solid safety collider. This is an architectural opening with
glazing, not an image or dark rectangle attached to an opaque wall.

The saved Mars room's east wall has an existing central rib. The selected bay is
beside that rib; no equipment, structural rib, route, door, door interlock or
collider is moved. The opening measures 1.5 by 1.2 metres, with its bottom .95 m
above the floor. Original metal liners, a pale frame, gasket and recessed glazing
occupy the original 15 cm wall depth. The glazing remains nontraversable, without
any pressure-seal or engineering certification claim.

The same authored functions build both the immutable preview and exported GLB.
Original procedural terrain outside the window supplies a muted rusty ground
and distant relief. It is decorative fictional terrain, not a measured location,
walkable exterior or photorealistic Mars reconstruction. The existing viewer
background stays unchanged; background and renderer-specific lighting remain
declared glTF limitations. All saved source geometry and semantic wall/collider
ownership remain intact. The GLB structural group records the viewport contract;
the sidecar still accurately describes the solid, nontraversable wall collider.

Eligibility comes from the authored observation role, an intact full-width wall,
its matching solid collider, absence of an adjacent room/portal, and a bay clear
of existing rib/equipment bounds. Unsupported rooms keep the old solid geometry.
There is no arbitrary inference from a room label. The same earthy scenery is a
fictional authored style when this recipe is used in other compatible layouts;
it is not a claim about their real environment.

CPU geometry tests independently raycast the old and candidate scene, check
transparent aperture sightlines and terrain visibility at 1.56 m eye height,
recess depth, matching wall bounds/ownership, blocked walking, unchanged doors and
equipment, rejected unsupported walls and finite mesh attributes. Twelve cases
passed on the actual saved geometry. The appearance gate admits the exact new
viewer and rejects old or changed appearances for this new exporter. Old previews
and the installed exporter are untouched.

The actual isolated immutable preview was created and reused, then exported and
imported through the real package API: 643 meshes, 102 materials, 70 embedded
textures, all 141 semantic nodes, 134 collider links and six door hinges passed
the roundtrip checks. The CPU export took 2.56 seconds at a sampled family peak
of 670 MiB. All 116 protected original files and 42 installed engine files remain
unchanged.

Two CPU Blender PNGs were generated from the exact same 1.30 MB GLB. The first
retained the earlier galley inspection lighting and showed a clear frame/recess
but a faint gray exterior. The second is explicitly a diagnostic lighting/view
change: a wider inside angle at the same 1.56 m eye height, lower interior review
fill, higher neutral world fill and a supplemental daylight source. The original
GLB, geometry and materials were not altered. The second image shows the existing
rib beside the framed aperture and a muted brown ground/horizon beyond it; it
still looks simplified/procedural. These images are file-rendered evidence of
construction and sightlines, not proof of how the native preview currently lights
the room. The second render took 6.48 seconds and peaked at 690 MiB sampled RSS.
Both owned processes closed cleanly; the sole existing Studio GPU job progressed
from denoising16/30 to17/30. No model or GPU render was launched here.

Root requires an actual native viewer inspection after the existing Studio GPU
job finishes before visual acceptance or installation. Keep both PNGs and their
lighting records; do not present diagnostic relighting as an installed result.

`history/` retains two early CPU harness mistakes: incomplete required metadata
bindings and an assertion that guessed which of two near-equal rib bays would be
selected. Both failed before a successful result was written; neither changed
the product candidate to satisfy an incorrect expectation.

This is not installed. Visual approval, owner approval, game-engine/VR behavior,
pressure simulation and a finished realistic habitat are not established.
