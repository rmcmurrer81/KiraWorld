# Place des Vosges World Generator Blueprint

Status: first seed blueprint before build
Created: 2026-06-29
Location type: real Paris park/square, future bakery-neighborhood anchor

## Build Rule

This file exists because Robert's rule is now explicit: no blueprint, no build. The first model pass may only build the features listed here, and anything uncertain must remain simplified or labeled as inferred.

## Source Seeds

- Robert's Paris/bakery route maps saved under `sources/robert_supplied_paris_route_maps/`
- Place des Vosges source intake saved under `sources/place_des_vosges/`
- Web/source research, 2026-06-29:
  - Place des Vosges is commonly described as a near-perfect square about 140 m by 140 m.
  - It is Paris's oldest planned square / oldest royal square, in the Marais.
  - The central garden is Square Louis XIII, with an equestrian statue marker in the center.
  - The garden has paths, trees, lawns/flowerbeds, and four fountains placed symmetrically around the center.
  - Surrounding buildings are uniform red brick and pale stone, with slate roofs, dormers, and ground-floor arcades containing shops/cafes/galleries.

## Source Links To Use

- Secondary geometry/history seed: https://en.wikipedia.org/wiki/Place_des_Vosges
- Additional dimension/facade seed: https://aviewoncities.com/paris/place-des-vosges
- Fountain reference seed: https://commons.wikimedia.org/wiki/File:Fountain_%40_Square_Louis_XIII_%40_Place_des_Vosges_%40_Marais_%40_Paris_%2830896795463%29.jpg

## First Build Scope

Build one walkable exterior seed area:

- 140 m square overall footprint, scaled 1 unit = 1 meter.
- Perimeter cobbled/stone street and sidewalks.
- Central fenced garden with clipped trees.
- Cross/diagonal garden paths that meet at the central Louis XIII statue placeholder.
- Four fountain basins around the center.
- Simplified red-brick/pale-stone facade ring with arcade openings and roof/dormer rhythm.
- A TARDIS arrival pad near the street edge, outside the garden fence.

## Movement And Travel

- `?area=vosges` loads the Place des Vosges seed.
- The TARDIS can be called with `C` in Louvre or Place des Vosges.
- Pressing `E` near the TARDIS door enters the persistent TARDIS preview.
- Inside the TARDIS, the console can select Louvre Courtyard or Place des Vosges and travel to the selected area.

## Implementation Note 2026-06-29

- A first blueprint-approved seed was added at `?area=vosges`.
- This seed is for travel/world-generator testing only. It is not final photoreal art.
- The current seed includes a 140 m class square, central Square Louis XIII garden, four fountain placeholders, clipped tree placeholders, surrounding arcade/facade placeholders, and a TARDIS arrival point at the street edge.
- A local source manifest and an open Wikimedia fountain reference were saved under `sources/place_des_vosges/`.
- The seed must be replaced section by section after official/open map geometry and street-level references are gathered.

## Known Unknowns

- Exact tree count, bench locations, gate locations, fountain details, statue detail, and facade ornament are not final.
- The bakery placement near Place des Vosges is still fictional/fan reconstruction until the bakery blueprint is rebuilt.
- This first park pass is not photoreal; it is a measured/world-generator seed for travel testing.

## Next Required Source Pass

- Gather official/open map geometry for Place des Vosges and nearby streets.
- Gather street-level and aerial references for the arcades, entrances, garden paths, fences, fountains, and Louis XIII statue.
- Replace seed facades and vegetation with source-matched geometry/materials section by section.
