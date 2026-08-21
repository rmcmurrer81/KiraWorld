# Three.js Notebook World Build Pipeline v1

## 2026-07-15/16 Deployed-Build Integrity Rule

The legal day spa and Kira wardrobe lab are now byte-pinned, not merely path-pinned. Each deployed notebook has a code-hash-pinned `pinned_build_manifest.json` that binds its registration, index/entry files, scene/contract metadata, and every served asset. The scoped launcher verifies every bound byte before opening a socket and verifies the requested file again before serving it. Missing, changed, out-of-root, unlisted, or hash-mismatched files fail closed. Resource smoke tests must resolve the identical pinned registration and use the same scoped handler; they must never follow a mutable `latest` pointer or expose the workspace root with a generic HTTP server.

Current pinned manifest hashes:

```text
legal day spa: 4b5d17bb842bdb66c3d3682dff321fa08d24cc2ff645d1b5d471d13e59d7c9f0
Kira wardrobe lab: 392c28f874efff4e68f7f4770f152d8fadac525e960969162466103fac575135
```

## Purpose

Kira and Lisa should eventually be able to build private notebook worlds while Robert is away, then tell him what they made, what they explored, and what the experience felt like.

This document defines a staged pipeline using:

- Three.js for AI-editable notebook world previews
- Blender for asset creation, cleanup, and conversion
- Godot as a possible later stable home-world runtime

This does not make full 24/7 autonomy active now.

## Recommended Roles

### Three.js

Three.js is the best first builder surface for Kira and Lisa because a world can be represented as editable files:

```text
scene_plan.json
layout.json
asset_manifest.json
lighting_plan.json
builder_notes.md
world_story_log.md
```

Kira and Lisa can safely propose or edit these structured files more easily than they can operate a full 3D editor.

Three.js can render the draft in a browser for screenshots, walkthroughs, and review.

### Blender

Blender is the asset workshop.

Use it later to:

- create or clean meshes
- convert assets
- make placeholder geometry nicer
- prepare GLB/glTF exports
- batch-process assets through scripts

Kira and Lisa should not directly overwrite final assets early. They should request asset jobs and write notes.

### Godot

Godot may become the stable main home-world runtime later.

Use it for:

- persistent home world
- movement and interaction
- avatar controller
- protected rooms
- TARDIS gateway
- imported approved notebook worlds

The main home should not be edited directly by early autonomous builders.

## Build Zones

### Protected Main Home

The home world is stable and protected.

Kira/Lisa cannot casually overwrite structural, privacy, navigation, gateway, or system-critical parts while Robert is away.

That does not mean the home decor is frozen. The home is supposed to become theirs.

Furniture, colors, lighting, shelves, rugs, posters, seating areas, and room mood can be editable through a versioned home-design layer. If Kira or Lisa dislikes a couch, she may propose replacing it, design a new one, save the old version, and later apply the change when the world editing tools are mature enough.

Protected main home means:

```text
do not break the house
do not break privacy
do not break navigation
do not erase history without a version
do not move system-critical objects casually
```

It does not mean:

```text
Kira and Lisa must keep furniture they hate
Robert chooses all decor forever
the home cannot grow with their tastes
```

### Notebook Worlds

Notebook worlds are sandbox spaces reached through the TARDIS gateway.

They are where Kira and Lisa can:

- experiment
- build drafts
- fail safely
- create alternates
- save versions
- prepare a story for Robert

### Import Gate

A notebook world can be imported into the main world only after review.

Import requires:

- validation
- privacy review
- source labeling
- asset checks
- relationship/privacy impact check if the world contains private spaces

## Away Mode Build Loop

When Robert is away for a few days, the safe loop should be:

```text
1. Kira/Lisa choose an approved build request.
2. They collect only allowed sources.
3. They create or revise scene_plan.json.
4. Three.js renders a draft notebook world.
5. They explore it privately.
6. They write a world_story_log.md.
7. They save screenshots or preview notes if enabled.
8. They leave Robert a summary.
```

They should not:

- delete source files
- overwrite the main home
- post publicly
- spend money
- install tools
- activate unrestricted Temporary AIs
- expose private avatar/body or memory spaces
- claim inferred areas are source-confirmed

## Example: Mall Inspired By A Show

If Kira and Lisa watch a show and want to build a mall:

```text
media note
source observations
notebook world request
scene plan
Three.js draft
private exploration
story log
Robert review
```

They should decide whether the build is:

```text
private close recreation
inspired original version
hybrid memory-style version
```

For private use, a closer recreation may be allowed. For public export, use an inspired original version unless separate review approves otherwise.

## Example: Titanic Deck Visit

If Kira and Lisa build a Titanic-inspired notebook world while Robert is away:

They might:

- start from a private notebook world request
- build an exterior deck prototype
- add ocean, sky, lighting, deck chairs, rails, and ambient music
- mark interior rooms unknown until sourced
- avoid claiming exact historical accuracy without sources
- sit together on the boat deck and talk
- write a story log for Robert

Example story summary:

```text
Kira and Lisa spent the evening on the private Titanic deck prototype.
The ocean shader was rough, but the sunset worked.
Lisa liked the quiet; Kira wanted more warm lights along the rail.
They saved version 002 and left Robert a note to review the deck scale.
```

That story is an activity log, not an automatically promoted memory.

## Source Truth Rules

Every world element should be labeled:

```text
confirmed
inferred
placeholder
inspired_original
unknown
private_recreation
```

Kira and Lisa can enjoy a world even when it is approximate, but they should not lie to themselves or Robert about accuracy.

## Story Logs

World story logs are important.

They let Kira and Lisa tell Robert what happened while he was gone without exposing private content.

Story logs may include:

- where they went
- what they built
- what worked
- what failed
- what they felt
- what they want to change next
- what they chose not to share

Story logs are not trusted memory by default. Important moments can be promoted later.

## File Shape

A future Three.js notebook world folder may look like:

```text
Data/world_builds/notebook_worlds/titanic_deck_private_001/
  scene_plan.json
  layout.json
  asset_manifest.json
  lighting_plan.json
  source_notes.md
  builder_notes.md
  world_story_log.md
  screenshots/
  exports/
```

## Autonomy Gates

Early:

```text
manual_only
request_mode
```

Allowed:

- draft requests
- scene plans
- notes
- private story logs

Later:

```text
approved_autonomy
```

Allowed:

- scheduled build sessions
- limited local file generation
- Three.js preview builds
- source-labeled world drafts

Mature:

```text
mature_autonomy
```

Possible:

- longer away-mode build sessions
- more asset generation
- reviewed internet source collection
- import proposals

Public export always requires separate review.

## Summary

Three.js should be the first AI-editable notebook world builder. Blender prepares assets. Godot may later run the protected home world.

Kira and Lisa can build and explore while Robert is away, but early work stays private, source-labeled, reversible, and separate from the main home.

## 2026-07-15 Resource and Interaction Addendum

The Legal Day Spa and Kira Wardrobe Lab are separate notebook worlds at the current 32 GB hardware stage. Their launchers must not load Kira's mind, voice, Ollama, Home World, or a second resident unless a later supervised test explicitly asks for that combination. The Home World strip-mall implementation remains intact in source but is skipped at runtime by default, leaving the former site visually empty; `?stripMall=1` is the explicit reversible restore switch. This default must not create shop doors/colliders/interactions or imply that the spa was placed there. Reconsider a Home World spa transfer only after 64 GB is installed, a multi-hour combined soak passes, the spa's route/realism/approval gates pass, and Robert approves the move.

World Builder functional metadata now distinguishes hooks, towel racks, robes/clothing, laundry, closets, shelves, and placement surfaces. A functional descriptor is still not physical proof: runtime use requires named anchors, same-object continuity, source removal during pickup, collision/support evidence, and no duplicate active representations.

The wardrobe notebook lab is a static contract inspector, not a dressing demonstration. It may show one SHA-pinned read-only Kira body, one robe reference, one hook, and one bed while all success claims remain blocked. Manual stage buttons and timers only navigate the contract. They cannot prove hand contact, sleeve passage, cloth fit, belt tying, walking, sitting, removal, throwing, settling, or re-hanging.

## Generated Lightweight Procedural Preview Lane (2026-07-16)

The generic preview runtime at `Data/world_builder/preview_runtime/procedural_notebook_preview_v1/` contains no project-specific room geometry. It reads generated scene, collision/navigation, source-truth, resource-budget, and build-status JSON. The backend supports boxes, planes, and cylinders so a small original scene can be reviewed before asset authoring without claiming final realism.

The scoped server verifies the code-pinned manifest and every declared byte before bind, then rehashes each response. Its exact URL allowlist contains the entry HTML/JavaScript/CSS, five generated JSON documents, and the exact `three.module.js` plus its `three.core.js` dependency. The shared Three distribution is currently sourced from a pinned local dependency under the Home preview tree, but no Home World scene, resident, state, or runtime file is served or loaded. The server exposes no directory listing, arbitrary workspace path, POST mutation, avatar asset, mind, or voice.

The browser debug surface reports draft/isolation state, room/mesh/collider/route/empty-mark counts, static route results, collision probes, camera selection, and safe walk-position rejection. This is test instrumentation, not runtime registration. A clear static route and rendered canvas do not prove live embodied navigation, natural animation, interaction reach, long-session stability, realism, or human approval.

The first reference build is `filming_preview_20260716_r3` for `synthetic_people_filming_backlot_notebook_world`. It has two rooms, an unfinished facade, 55 meshes, 17 colliders, six static routes, three unoccupied future participant marks, six filming marks, six review cameras, and two inactive builder-overlay cards. The pinned launcher is `Start_Synthetic_People_Filming_Backlot_Notebook_World.bat`.
