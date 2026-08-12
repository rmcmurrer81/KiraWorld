# Louvre corrected R7 owner review

## Outcome

R7 is a separate zero-person correction after Robert rejected the R5/R6
photogrammetry combination. It removes the broken wide scan from the review
path and returns to a coherent, bounded procedural layout. It is deliberately
labelled `corrected_spatial_blockout_not_realism_not_approved`.

R7 does not overwrite R4, R5, or R6 and does not mutate Home World, TARDIS,
World Shell state, a person, a mind, or voice state.

## Owner verdict — 2026-07-17

Robert judged R7 "a little better" than the rejected mashup but still visibly
too fake. R7 therefore remains **rejected for realism and promotion**. Do not
replace the normal Louvre destination with it, open its locked continuations,
or use it as positive proof for unattended World Builder expansion. Its useful
result is limited to the corrected pyramid count/layout and a coherent low-cost
blockout. The next Louvre pass must be evidence-driven architectural authoring,
materials, lighting, and bounded navigable interiors—not additional procedural
detail presented as realism.

## What the owner can review

- A walkable, west-open Cour Napoleon blockout.
- One main Pyramid at the Louvre's published 35 m base and 21 m height.
- Three smaller pyramidions placed north, east, and south from the main
  Pyramid using the licensed Cour Napoleon plan. Their 9.2 m base and 5.3 m
  height are plan-derived approximations, not published measurements.
- Procedural Richelieu/north, Denon/south, and Sully/east massing without the
  rejected scan or distant Paris clutter.
- A separate fixed-camera Hall Napoleon visual study showing a helical stair,
  glass guards, steel stringer, central lift form, coffered deck context,
  columns, and locked wing boundaries.

This is a spatial correction and visual study, not a realistic or complete
Louvre reconstruction.

## Evidence decision

The shared fail-closed evidence validator requires at least three distinct
photo viewpoints, one video viewpoint, a reviewed layout source, and a scale
source before an area may enter draft authoring.

| Area | Draft evidence | Runtime approval | Result |
| --- | --- | --- | --- |
| Cour Napoleon bounded exterior | Pass | No | Walkable owner-review blockout |
| Hall Napoleon stair study | Pass | No | Fixed-camera visual draft only |
| Richelieu galleries | Fail | No | Closed, locked, collision-solid |
| Sully galleries | Fail | No | Closed, locked, collision-solid |
| Denon galleries | Fail | No | Closed, locked, collision-solid |

The Hall study uses the Louvre's published 2,500 m2 hall area only as an
overall envelope scale anchor. The stair, lift, escalator, door mechanism, and
connected walking route still lack reviewed component dimensions. Passing the
minimum evidence gate therefore does not open a door or establish realism.

## Pyramid-count source conflict

The Louvre's French Pyramid page says the main Pyramid has *three* smaller
sisters and that the inverted Pyramid brings the total to five. The English
page's wording says two smaller pyramids while also stating a total of five,
which is internally inconsistent. R7 follows the French original and the
licensed Cour Napoleon plan: one main exterior Pyramid, three smaller exterior
pyramidions, and no claim that the inverted Pyramid exists in the exterior.

## Locked physical boundaries

The evidence contract contains four physical destination portals:

1. Main Pyramid exterior to Hall Napoleon.
2. Hall Napoleon to Richelieu.
3. Hall Napoleon to Sully.
4. Hall Napoleon to Denon.

Every portal is `closed_locked_solid`, has collision enabled, and reports
`opens: false`. The central lift and escalator forms are non-operable studies,
not extra portals. No galleries, rooms, artworks, working doors, working lift,
or working escalators are loaded.

## Source and rights handling

- [Louvre French Pyramid page](https://www.louvre.fr/decouvrir/le-palais/une-pyramide-pour-symbole)
- [Louvre English Pyramid page](https://www.louvre.fr/en/explore/the-palace/a-pyramid-for-a-symbol)
- [Louvre May 2026 English map](https://api-www.louvre.fr/sites/default/files/2026-05/2026-05_Plan_Louvre_EN.pdf)
- [Louvre map and entrances](https://www.louvre.fr/en/visit/map-entrances-directions)
- [Louvre Pyramid Project press page](https://presse.louvre.fr/the-pyramid-project/?lang=en)
- [Louvre Hall Napoleon venue facts](https://mini-site.louvre.fr/trimestriel/2024/evenements_prives_2024/10/)
- [NCK helical stair engineering description](https://nck.ca/en/projects/pyramid-of-the-grand-louvre-and-monumental-spiral-staircase-of-the-louvre-museum/)
- [Cour Napoleon plan by Paris 16, CC BY-SA 4.0](https://commons.wikimedia.org/wiki/File:Plan_of_the_Cour_Napol%C3%A9on%2C_Louvre.svg)

Owner-supplied photos are private reference inputs and are hash-pinned. Stock
or watermarked imagery and video are reference-only. No photo, map tile,
watermark, video frame, GLB, GLTF, FBX, or R5/R6 scan is served by R7.

## Launch and World Shell/TARDIS routing

Launch the isolated review with:

`C:\Users\robmc\Kira\Start_Louvre_Corrected_R7_Owner_Review.bat`

The launcher verifies the pinned build and opens:

`http://127.0.0.1:5197/?solo=1&bookmark=west_arrival`

The World Shell destination row now includes an explicit **Louvre Corrected R7
Review** button beside the normal world/TARDIS controls. Clicking it opens the
shell's same-origin `/review/louvre-r7` gateway in a separate window. The
gateway validates the exact R7 protocol, build ID, pinned runtime-isolation
contract, and zero-person routing. If the service is absent, it starts the
pinned port-5197 server on demand, waits for that same health contract, and
only then redirects to the stable review URL. It does not call `/api/location`
or `/api/activate`; it does not transport a person, activate a person, mutate
the active shell location, or replace the older Louvre audit route.

If the gateway cannot validate or start the exact pinned service, it refuses
the redirect and displays the standalone launcher path instead of opening an
unknown process on port 5197.

The gateway was tested from a cold state by stopping the verified R7 listener,
letting the helper restart the pinned server, validating the returned protocol,
build ID, zero-person isolation, and safe-route flags, and then exercising the
HTTP handler. The handler returned a no-store 302 redirect to the stable R7
URL. No person or mind system was started by that test.

The normal Louvre location continues to use the older R4 service on port 5183.
That coexistence is intentional: R7 is available from the destination controls
for owner review but remains not approved and is not promoted as the completed
or production Louvre.

## Verification

- Production build: passed; 9 modules transformed; 3 served files.
- Pinned package: passed; 12 source/reference inputs; 3 served files.
- Server verification: passed; main + 3 smaller pyramids, Hall study, 4 locked
  portals, zero people/minds.
- R7 Python unit suite: 8 tests passed in 0.105 seconds.
- Shared evidence plus R7 suite: 17 tests passed.
- Browser smoke: passed with 6 screenshots, no page errors, no console errors,
  no request failures, no HTTP errors, and no model/scan resource requests.
- Browser renderer sample: 14,614 triangles, 725 draw calls, 10.1 ms frame p95.
- Grounding: feet delta 0.000 m on accepted courtyard paving.
- Collision probes: main Pyramid, north smaller pyramidion, and Sully boundary
  all rejected crossing; ordinary paving accepted movement.

The final browser report is
`Data/codex_reports/20260716_louvre_corrected_r7_browser_smoke_final.json`.

## Owner-review checklist

Use the seven fixed bookmarks and answer only these bounded questions:

- Is the west-open courtyard orientation coherent?
- Is one main plus three smaller pyramidions the right count and rough layout?
- Is the procedural palace massing a better base than the rejected scan?
- Does the Hall study capture the stair's overall helical relationship well
  enough to justify gathering exact measurements next?
- Should R7 eventually replace the normal Louvre port-5183 audit route, or
  should it remain a separate owner-review button for another correction?
