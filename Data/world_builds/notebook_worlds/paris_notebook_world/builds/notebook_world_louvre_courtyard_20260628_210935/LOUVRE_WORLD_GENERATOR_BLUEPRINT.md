# Louvre World Generator Blueprint

## Rule For This Location

The Louvre is a real historical place. The world generator must not build a new Louvre section from imagination.

Build order:

1. Source maps, plans, dimensions, and entrance information.
2. Create or update this blueprint.
3. Build one section only.
4. Compare from multiple viewpoints against source photos.
5. Add collision/walk limits for glass, walls, water, doors, and railings.
6. Do not move to the next section until the current section is believable enough to inspect at human scale.

## Primary Sources

- Official Louvre map/entrances/directions page: `https://www.louvre.fr/en/visit/map-entrances-directions`
- Current official Louvre museum map PDF reviewed for this pass: `https://api-www.louvre.fr/sites/default/files/2026-05/2026-05_Plan_Louvre_EN.pdf`
- Official Louvre Pyramid page: `https://www.louvre.fr/en/explore/the-palace/a-pyramid-for-a-symbol`
- Official Louvre visit page: `https://www.louvre.fr/en/visit`

## Confirmed Anchors

From the official Louvre sources:

- The Pyramid is the Louvre's main entrance.
- Metro access includes Palais-Royal / Musee du Louvre on lines 1 and 7, and Pyramides on line 14.
- The official museum map is the required source for level, wing, entrance, and route layout before any interior rebuild.
- The official entrance page lists the Pyramid as the main entrance for individual visitors and divides it into three queues: ticket/Paris Museum Pass, no-ticket, and priority access. It is not a pass-through glass wall.
- Official Pyramid key figures: height 21 m, base width 35 m, base area about 1,000 m2, 675 diamond-shaped glass panes, 118 triangular glass panes, 6,000 bars/girders, and 2,150 nodes.
- The Louvre official Pyramid page states that there are exactly two smaller pyramids in Cour Napoleon. Their exact placement and dimensions remain approximate in this build. The inverted Pyramid at the Carrousel is a separate feature and is outside this exterior test.

## First Build Section: Cour Napoleon / Pyramid Exterior

Do not work on the interior again until the exterior entrance section is corrected.

Required exterior elements:

- Main glass Pyramid with correct walk-blocking glass footprint.
- Visible south/Tuileries-side entrance door/vestibule area at the Pyramid, not a pass-through glass wall.
- Smaller Cour Napoleon pyramids reconciled to the official Louvre page before final count/placement.
- Reflecting pools and fountain areas placed around the pyramids.
- Queue stanchions around the entrance.
- Palace facades as surrounding context, but marked as approximations until facade references are sourced.
- Courtyard paving scale and seams.
- Visitor-scale figures only as scale references, not decoration.

Required exterior collision:

- Player cannot walk through main Pyramid glass.
- Player cannot walk through small pyramids.
- Player cannot walk through reflecting pools/fountains.
- Player cannot walk through palace walls.
- Doors or entrance points must be explicit route transitions, not accidental holes.

## Second Build Section: Pyramid Entrance

Only after exterior review:

- Research the exact entrance/vestibule layout from official maps and public photos.
- Build the entry route as a controlled transition from courtyard to below-ground lobby.
- Add door/queue/security context only where supported by references.

## Third Build Section: Under-Pyramid Lobby

Only after entrance review:

- Use the official museum map for the below-ground orientation.
- Use Robert-supplied under-pyramid photos for visual features: glass lattice overhead, concrete deck, coffered underside, columns, polished floor, stairs/escalators, curved stair/ramp, signage, and queues.
- If room dimensions are unknown, estimate from known objects such as people, stanchions, stair tread scale, door heights, and displayed art/signage sizes. Record the estimate in this blueprint.
- Build one visible lobby subsection at a time.

## Current Live State

The failed bakery geometry is removed from the live preview. The failed under-pyramid blockout is also disabled from live rendering.

The current live scene is a rough Cour Napoleon/Pyramid exterior placeholder with a walk-blocking main Pyramid footprint. It is not final or photoreal. No new Louvre section is allowed to be modeled until this blueprint records the source, expected geometry, and review checklist for that section.

2026-07-16 solo exterior evidence pass:

- Added `preview/louvre_exterior_contract.json` as the machine-readable source, scale, collision, route, landmark, approximation, locked-unknown, feedback, and isolation contract.
- Main Pyramid dimensions are bound to the official 21 m height and 35 m base width. One world unit is one meter for this test.
- Corrected the Cour Napoleon small-Pyramid count from the older three-placeholder interpretation to exactly two. Placement and size remain labeled approximate.
- Replaced the visually heavy extra front X layer with a calmer 14-division lattice approximation. It is not a pane-by-pane model of 675 diamonds and 118 triangles.
- Added shallow pool basins and curbs, three source-category queue lanes, 12 declared collision boxes, five static clearance-checked review routes, six landmarks, and a fail-closed movement probe.
- Added a visible measured/approximate/locked panel and browser-local feedback with JSON export.
- Added a hash-pinned, loopback-only, read-only launcher. It serves only three built files and forces `?solo=1`; actor, alternate-area, and legacy-TARDIS queries cannot be selected through it.
- Kept the exterior-to-level-minus-2 transition, under-Pyramid lobby, galleries, artwork, and service areas locked. No guessed interior was enabled.
- Browser smoke at 1440 x 900 passed with no page, console, request, or HTTP errors. This proves only the isolated preview functions; it does not prove a synthetic person's embodied navigation or reconstruction accuracy.
- No TemporaryAI, person, mind, voice, Ollama process, Home World, or TARDIS was loaded or activated for this pass.

2026-07-16 owner-review pass r2:

- Added five default-visible in-world truth markers. Blue markers identify mixed
  official facts and approximate geometry, amber identifies approximation, and
  red identifies locked work. Each marker has a vertical anchor to its subject
  and can be hidden without changing the world.
- Added five contract-pinned camera bookmarks: arrival scale, human-height
  entrance, two-small-Pyramid overview, west-pool approximation, and palace
  massing. Each has a deterministic URL and an associated review route.
- Added route-polyline measurements for total length, along-route distance,
  remaining distance, percent complete, nearest route point, and cross-track
  distance. Added session walked distance and debounced declared-collision
  counts. These are review metrics, not autonomous navigation evidence.
- Feedback entries now retain bookmark, reproducible URL, active route, viewer
  position, and measurement snapshot.
- Added a client-only owner-review package export containing the entire
  source/isolation contract, fixed-view URL, route checks, metrics, feedback,
  and an embedded PNG with SHA-256. The server remains read-only and receives
  no feedback or capture data.
- Did not add or promote new Louvre geometry or materials in this pass. The
  available evidence did not justify turning any existing exterior
  approximation into an accuracy claim.

2026-06-29 reference correction pass:

- The fake procedural sky dome has been hidden. Sky/cloud work is deferred until it can be sourced or made realistic enough for VR review.
- The main Pyramid glass is less opaque so the palace facade can be seen through it, matching the user-supplied front entrance photos more closely.
- The entrance was reduced from a bulky black/glass block to a thinner transparent door wall with slim dark mullions, a black sign rail, visible `MUSEE DU LOUVRE` sign text, and a low threshold/mat.
- The cross-like door handles were removed and replaced with vertical pull handles.
- The front-facing Pyramid lattice has an additional dense diamond/X emphasis layer. This is still approximate; it must be refined against real photos and official Pyramid pane counts.
- Queue stanchions now use sagging rope curves instead of only straight rails.
- The entrance collision was changed from a clamp/trap volume to a front apron: the player can approach and back away, but cannot pass through the locked door until the lobby blueprint exists.

## Known Problems To Fix Next

- The solo review now blocks 12 declared exterior regions, but collision remains axis-aligned review geometry rather than mesh-precise palace, rope, curb, and door collision.
- The palace facades are blocky placeholders and do not match historical facade detail.
- The Pyramid grid is still a restrained procedural approximation and needs sourced pane/rib engineering geometry before any accuracy claim.
- The entrance vestibule and doors are closer than the previous blockout, but still not accurate enough.
- The pools and queue areas are approximate.
- The isolated launcher hard-disables actors and redirects actor/legacy-area query strings. Actor tests belong in a separate, explicitly authorized build.
- The world needs real source boards and saved blueprint-to-model review screenshots for each section.
