# Louvre Bounded Circulation Owner Review v2

Date: 2026-07-16

Status: prototype owner review; not final, exact, approved, or available to
activated people.

## Current review scope

The r4 Louvre notebook-world build contains:

- the existing approximate Cour Napoleon exterior;
- a streamed two-leaf Pyramid entrance interaction blockout;
- a bounded upper landing, 270-degree walkable spiral-stair blockout, and lower
  circulation floor;
- photo-supported concrete deck/column/coffer forms;
- two visible-only, solid, non-operable escalator blockouts.

It does not contain a full Louvre interior, a working escalator, a tube-lift
model, accessibility/security routing, gallery rooms, artwork, service spaces,
or complete wing routes. `interior_enabled` and every full-interior completion
flag remain false. The separately named bounded owner-review capability is true
so a functional prototype cannot be mistaken for a completed reconstruction.

## Evidence boundary

Official Louvre pages support the Pyramid's entrance role, the level -2
reception context, and the central lobby's relation to the three wings. The
official physical-accessibility page also confirms that a central tube lift
reaches reception under the Pyramid and that the Carrousel route has escalators
and two lifts. Those facts do not supply exact coordinates, dimensions,
mechanics, timing, controls, or collision volumes, so no lift is rendered.

Robert-supplied local visual evidence supports the forms used for the bounded
blockout:

- `IM-Pei-designed-pyramid-Louvre-Paris-France.webp`
  (`4db0ae50dd2c2b7224f0fcf35a26c5bf1c9f3fd8eb9ce63a261f317aa14445d8`):
  exterior entrance/queue scale, not door mechanics.
- `d672e10204e3f70ceb3a9d080d421e93.jpg`
  (`bf0d4e855f1af34ad8121ca6733882b26a551a4e051da7c107beecf4db0a21e9`):
  decks, columns, partial spiral stair, and lower-floor scale.
- `e6a59f09a26358fcb1a65b56644c51b7.jpg`
  (`8466f214eae959f9174d24c5e5d61ce6b0878646e251c08c13d5cfdf0969c0f0`):
  central pier, decks, coffers, and spiral-stair glimpses.
- `Louvre-Museum---Rost-Architects.webp`
  (`54ddfe474bfa1f9203e17364550d2876afc3ba80409a076fbbf325f4fbef8c9a`):
  spiral-stair and escalator forms, not operation or exact placement.

The geometry therefore uses `approximate` truth labels throughout.

## Door and movement contract

Distance alone can load the exterior and entrance cells. The descent cell has
an explicit portal-authorization gate and cannot become resident merely because
the camera is near it. Pressing `E` authorizes a staging attempt. The door stays
solid until the descent module is resident, its collision is ready, and its
declared budgets validate. The threshold becomes passable only when the leaves
reach 94 percent open. It cannot close while the owner-review camera occupies
the threshold.

The spiral stair and normal WASD movement share the same height/collision
solver. The browser smoke checks 40 samples down and 40 samples up, including
monotonic height and the 0 m to -8 m blockout endpoints. These endpoint values
are prototype-world coordinates, not claimed Louvre measurements.

## Transaction and memory contract

The active-set and each loadable cell have hard ceilings for asset bytes,
triangles, texture bytes, draw calls, staging latency, and transaction latency.
Each destination is staged and validated before any source unload. Source
unload is preflighted and finalized one cell per atomic pass; multiple stale
cells drain through serialized follow-up passes. State is captured before a
successful unload. Portal authorization expires when the gated cell unloads.

The browser smoke intentionally injects four failures:

- an unregistered desired destination;
- a per-cell triangle-budget overrun;
- a destination commit failure;
- a source-unload preflight failure.

Each remains in `blocked_before_source_unload`, retains that transaction's last
proven cell set, and disposes staged work where applicable.

## Owner launch and evidence

Run `Start_Louvre_Solo_Notebook_World_Test.bat`. The supervisor accepts only the
r4 health protocol and exact r4 build ID before it opens:

`http://127.0.0.1:5183/?solo=1&bookmark=arrival_scale`

The server is loopback-only, read-only, hash-pinned, and loads zero people,
minds, voices, Ollama, Home World, or TARDIS runtime objects. The TARDIS console
may list this owner-review destination, but activated-person travel and complete
runtime registration stay false.

Append-only r4 evidence is under
`Data/codex_reports/louvre_solo_notebook_world_20260716_r4/`.

