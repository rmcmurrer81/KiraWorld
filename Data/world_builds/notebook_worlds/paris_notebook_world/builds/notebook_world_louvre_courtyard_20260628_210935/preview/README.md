# Louvre Courtyard Preview

## 2026-07-16 Bounded Pyramid Circulation Owner Review r4

The same project-root launcher now verifies and opens the hash-pinned r4 build:

```text
Start_Louvre_Solo_Notebook_World_Test.bat
http://127.0.0.1:5183/?solo=1&bookmark=arrival_scale
```

This remains a Robert-only, zero-person, zero-mind, zero-voice notebook-world
review. It adds one deliberately bounded interior interaction slice without
claiming a complete or exact Louvre interior:

- Distance-only arrival loads the Cour Napoleon exterior. Approaching the
  entrance loads the approximate door cell, but the descent cell is protected
  by explicit portal authorization.
- Press `E` at the threshold. The descent module must stage, pass collision and
  byte/triangle/texture/draw-call/latency budgets, and commit before the two
  approximate sliding leaves can become collision-passable.
- The 270-degree spiral stair blockout is walkable in both directions between
  the exterior level and the bounded lower circulation floor. Its form is
  guided by Robert-supplied photos; its dimensions and placement are not a
  surveyed reconstruction.
- Two escalator forms are visible for scale/composition review only. They are
  solid and non-operable. The official Louvre accessibility page also confirms
  a central tube lift reaches reception, but this build does not infer or render
  its geometry, controls, mechanics, timing, or collision.
- Full lobby geometry, accessibility/security flow, working escalators, the
  central tube lift, gallery rooms, artwork, service spaces, and every other
  unknown interior cell remain locked and unloaded.
- Streaming transitions are serialized and transactional. Destination cells
  stage before source unload; unload is preflighted and limited to one source
  per atomic pass. Missing registration, resource overrun, commit failure, or
  unload-preflight failure retains that pass's last proven cell set. Door and
  circulation state persist across unload/reload, while the threshold remains
  solid until the destination is reauthorized and resident.

The r4 browser evidence remains local and is not included in this portable
source subset. The r3 section below is retained as history and no longer
describes the current pinned build.

## 2026-07-16 Solo Exterior Review Build r3

Use the project-root launcher:

```text
Start_Louvre_Solo_Notebook_World_Test.bat
```

It starts a detached read-only server on `127.0.0.1:5183`, polls `/healthz`
until that exact pinned build reports `people=0` and `minds=0`, and only then
opens:

```text
http://127.0.0.1:5183/?solo=1&bookmark=arrival_scale
```

This is an exterior-only, inactive-person notebook-world test. It does not load
or activate a TemporaryAI, person, mind, voice, Ollama, Home World, TARDIS,
museum interior, or gallery. It is not registered as a runtime destination and
does not mutate Home World or the strip mall. The launcher accepts only
`solo=1` plus one of five pinned bookmark IDs. Actor, TARDIS, alternate-area,
unknown-bookmark, and legacy query modes redirect to the arrival bookmark.
Clicking the URL alone cannot start a local server; use the launcher. If startup
or hash verification fails, the launcher leaves the browser closed and shows
the two log paths under `Logs/louvre_solo_review/`.

The TARDIS console also lists `Louvre solo exterior review (draft)` for Robert's
owner-only review. That listing forces `solo=1&bookmark=arrival_scale`; it is
not a completed-world registration and cannot promote the locked entrance,
below-Pyramid circulation, galleries, or artwork.

`louvre_cell_streaming_contract.json` and `src/louvre_cell_streaming.js` add the
first fail-closed proximity-cell scaffold for the larger Paris world. Only the
current Cour Napoleon exterior is runtime-loadable. Entrance, level -2
circulation, and the Richelieu/Sully/Denon gallery zones have no geometry bounds
or runtime bindings yet, so the loader cannot invent or load them. The current
exterior still needs extraction from the legacy eager entry file into its own
on-demand module before this counts as a memory/performance result.

Current evidence:

- Official-source scale: main Pyramid 21 m high, 35 m base width, and about
  1,000 m2 base area.
- Official-source count: exactly two smaller Cour Napoleon pyramids.
- Approximate review geometry: palace facades, pools and small-Pyramid
  placement, queue layout, entrance doors, paving, materials, and lighting.
- Locked: the exterior-to-level-minus-2 transition, lobby, galleries, artwork,
  service areas, and any claim that this is a finished reconstruction.
- Navigation review: 12 solid collision regions, five static clearance-checked
  routes, six proximity landmarks, a 1.68 m review eye height, and fail-closed
  movement into blocked regions.
- Owner review: five color-coded, vertically anchored in-world truth markers
  distinguish mixed official/approximate geometry, approximation, and locked
  work. Press `L` or use `Markers on/off` to toggle them.
- Reproducible views: press `B` to cycle five fixed camera bookmarks. Each view
  has a copyable URL and selects its associated measured route.
- Live measurements: active-route progress, remaining distance, cross-track
  distance, walked distance, collision count, and last declared collider.
- Feedback: press `F`; each browser-local note retains bookmark, route, and
  measurement context. `Export full review package + PNG` creates one
  self-contained JSON file with the source/isolation contract, measurements,
  feedback, and an embedded PNG plus SHA-256. The server receives nothing and
  has no write endpoint.
- Verification: `py -m unittest Testing.test_louvre_solo_notebook_world` and
  `node tools/louvre_solo_browser_smoke.mjs ...` both passed on 2026-07-16.

Source-of-truth and build-isolation files:

- `louvre_exterior_contract.json`
- `louvre_solo_pinned_build_manifest.json`
- `tools/serve_louvre_solo_notebook_world_test.py`
- Local r2 owner-review notes, browser-smoke evidence, and the review package
  are intentionally not included in this portable source subset.

The material below records the older multi-area Vite development preview. It
is retained for reconstruction history; it is not the isolated launcher
contract and should not be used as proof that actors, TARDIS travel, interiors,
or legacy Paris modules are ready.

This is a first walkable Three.js notebook-world prototype for Robert review.

Run URL while the local Vite server is active:

```text
http://127.0.0.1:5183/
```

Photo/visitor URL:

```text
http://127.0.0.1:5183/?photo=1
```

Show notebook source labels:

```text
http://127.0.0.1:5183/?labels=1
```

Show actor name labels:

```text
http://127.0.0.1:5183/?names=1
```

Show visitor placeholders:

```text
http://127.0.0.1:5183/?actors=1
```

Review the current Pyramid entrance pass:

```text
http://127.0.0.1:5183/?view=entrance
```

Review the current palace facade pass:

```text
http://127.0.0.1:5183/?view=facade
```

Review the first TARDIS gateway prototype:

```text
http://127.0.0.1:5183/?area=tardis
http://127.0.0.1:5183/?area=tardis&view=exterior
http://127.0.0.1:5183/?area=tardis&view=interior
```

Review the first Place des Vosges world-generator seed:

```text
http://127.0.0.1:5183/?area=vosges
http://127.0.0.1:5183/?area=vosges&view=overview
```

Controls:

```text
Click to enter walking mode
WASD to move
Mouse to look
Shift to move faster
P to save a browser PNG snapshot
Esc to release pointer
Louvre / Place des Vosges: C calls the TARDIS, E enters at the police-box doors
TARDIS interior: E exits, T cycles console destinations, Enter travels to the selected ready destination
```

Current build truth:

- Pyramid scale is seeded from the official Louvre Pyramid key figures and modeled at 21 m high with a 35 m square base.
- Camera eye height is 1.68 m and normal movement is 1.65 m/s for a VR/Katwalk-style scale feel.
- Robert-supplied local images are indexed under `sources/robert_supplied_images/` and currently guide exterior/interior reference, but not public export.
- Robert-supplied bakery images are still indexed under `sources/robert_supplied_bakery_images/`. They were not deleted. The failed live bakery model was removed and the future rebuild must start from a blueprint.
- Robert-supplied Marinette bedroom images are indexed under `sources/robert_supplied_marinette_bedroom_images/` for the later upstairs-bedroom pass.
- Robert-supplied Paris route maps are preserved under `sources/robert_supplied_paris_route_maps/` for the future Louvre-to-bakery notebook world route. They are fan planning references only until reconciled with official/open map data and a written blueprint.
- Robert, Kira, Lisa, and Marinette/Ladybug can appear as visitor placeholders through `actor_manifest.json` when `?actors=1` is set. Placeholders are hidden by default for cleaner architecture review.
- Generic symbolic visitors are also hidden by default; do not use them in normal realism review because they make the scene read as fake. Use `?actors=1` only when testing avatar/AI placement.
- `?photo=1` hides the HUD/crosshair/status so saved visit images are clean; use `?labels=1` and `?names=1` only when debugging notebook provenance or actor placement.
- `?area=interior` is disabled for now and falls back to the Louvre courtyard. The interior must be rebuilt from blueprint before it is walkable again.
- `?area=bakery` no longer starts a bakery model; it falls back to the Louvre because the bakery geometry was removed from the live preview.
- Robert's accurate avatar is not built yet; the current body is a clothed placeholder for framing screenshots.
- Palace facades now have extra placeholder rhythm, arcade shadows, dormers, cornices, and roof/statue silhouettes, but detailed ornament, exact elevations, paving, reflecting pools, and courtyard limits are still approximations.
- 2026-06-29 bakery removal: the failed bakery geometry was deleted from the live `src/main.js` scene after Robert said to stop iterating on it. Reference images and source folders remain for a future blueprint-first rebuild.
- 2026-06-29 blueprint gate added: see `../BLUEPRINT_RULES.md`. No new location geometry should be built without a blueprint/reconstruction note first.
- 2026-06-29 Louvre world-generator blueprint added: see `../LOUVRE_WORLD_GENERATOR_BLUEPRINT.md`. The exterior Pyramid/courtyard section is the active section; the interior is paused until the entrance is researched and approved.
- 2026-06-29 Louvre under-pyramid note corrected: see `../LOUVRE_UNDER_PYRAMID_BLUEPRINT.md`. The guessed under-pyramid blockout is disabled from live rendering.
- Current navigation: Louvre courtyard only. The main Pyramid footprint blocks walking through the glass except for the visible south entrance vestibule, which is locked until the sourced lobby blueprint is built. `M` displays a blueprint-lock reminder instead of teleporting inside. Bakery travel is disabled until a bakery blueprint exists.
- The fake procedural sky dome is hidden. Realistic sky/cloud lighting is a future pass, not part of the current review.
- 2026-06-29 entrance correction: the visible Pyramid entrance was reduced from a bulky blockout to a thinner transparent door wall with slim mullions, a `MUSEE DU LOUVRE` sign rail, vertical pull handles, sagging queue ropes, and front-apron collision that lets Robert approach/back away without passing through the glass.
- Community/public-photo intake is queued in `source_tasks.json`.
- Museum interiors are intentionally unknown until floor plans, photos, videos, or manual notes are reviewed.
- 2026-06-29 TARDIS gateway prototype added under `?area=tardis`. This is blueprint-first and structurally focused: police-box exterior, larger independent control room, central world console, persistent-object shelf placeholders, Robert check-in screen, and manual `E`/`C`/`T` controls. It is not final photoreal art.
- TARDIS reference images were copied without deleting originals into `Data/world_reconstruction/sources/tardis/doctor_who_reference/`.
- TARDIS blueprint/policy file: `Data/world_access/TARDIS_GATEWAY_BLUEPRINT.md`.
- TARDIS verification screenshots saved:
  - `preview/tardis_exterior_gateway_20260629.png`
  - `preview/tardis_interior_console_20260629.png`
- 2026-06-29 ground flicker correction: the thin paving seam meshes were removed because they caused z-fighting/flickering brown lines while moving. Paving seams are texture-only until the sourced stone-paving pass.
- 2026-06-29 Place des Vosges seed added from blueprint: see `../PLACE_DES_VOSGES_WORLD_GENERATOR_BLUEPRINT.md`. This is a world-generator/TARDIS travel test only, not final photoreal art.
- 2026-06-29 TARDIS call/travel wiring: `C` calls the exterior in the Louvre and Place des Vosges, `E` enters at the police-box doors, `T` cycles destinations inside, and `Enter` travels to a ready destination.
- 2026-06-29 TARDIS exterior proportion correction: the exterior was slimmed/tallened using Robert's supplied prop dimension sheet as a first proportion guide.
- 2026-06-29 TemporaryAI console generator is now a TARDIS blueprint requirement, but it is not implemented in the playable preview yet.

Next build pass:

- Improve the Louvre exterior/Pyramid entrance from `../LOUVRE_WORLD_GENERATOR_BLUEPRINT.md`: official map anchors, courtyard layout, walk-blocking glass, real entrance route, denser Pyramid grid, pools/fountains, queue stanchions, palace facade references, and source-based screenshots.
- Before any bakery rebuild, create a dedicated bakery blueprint document using the supplied bakery and bedroom pictures. No blueprint, no build.
- Add reviewed public-photo reference board and measured Louvre courtyard/facade plan.
- Add Lisa/Kira/TemporaryAI avatar spawn points after movement permissions are reviewed.
