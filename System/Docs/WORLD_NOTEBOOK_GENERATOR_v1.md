# World Notebook Generator v1

This document defines the first request-mode world generator that Kira, Lisa, and Robert can use to prepare place-based notebook worlds.

The generator does not make the final 3D world by itself. It creates source-labeled build paperwork for a future Three.js notebook world.

## Purpose

Given a place such as:

```text
Louvre courtyard in Paris
The Brown Derby in 1930s Los Angeles
a mall
a theater
a home with blueprints
```

the generator creates:

```text
notebook_world_request.json
scene_plan.json
placement.json
source_tasks.json
source_notes.md
builder_notes.md
blueprint_preview.json
approval_gate.json
quality_gate.json
resource_isolation_gate.json
tardis_review_stage.json
```

These files tell the later world builder what to research, what can be confirmed, what is unknown, and where the place belongs.

## Notebook World Placement

Places are grouped into notebook worlds by city, era, or setting.

Examples:

```text
Paris Notebook World
1930s Los Angeles Notebook World
Kira/Lisa Home World Source Reconstruction
```

If a new place has coordinates and the notebook world already has a separately approved placement anchor, the generator records distance and local scene offset from the nearest approved anchor. Draft, catalog, template, and staged anchors are deliberately ignored as coordinate origins. This prevents an early Paris blockout from silently becoming placement truth for every later Paris location.

## Source Truth

Every build should preserve uncertainty labels:

```text
blueprint_confirmed
photo_confirmed
video_confirmed
map_confirmed
manual_note_confirmed
inferred_from_sources
style_fill
unknown
blocked_private
```

Photos confirm what they show from that angle. They do not prove hidden rooms, exact dimensions, or unseen facades.

## Real And Historic Places

Current real places should separate:

```text
official information
measurements
maps
photos
videos
floor plans
manual notes
```

Historic places should also separate:

```text
current remnants
era-specific photos
period advertisements
city archive evidence
style references
unknown or demolished areas
```

The Brown Derby should not mix a current Los Angeles street with a 1930s interior unless the evidence is labeled.

## Autonomy

Early use is `request_mode`.

Kira and Lisa may draft requests, source tasks, scene plans, and story notes. They should not:

```text
download large source packs without review
claim a final world exists
import into the protected home world
erase source labels
make a public export
```

## Command

Example:

```powershell
py tools\create_world_notebook_request.py "Louvre Courtyard" --city Paris
```

Output goes under:

```text
Data/world_builds/notebook_worlds/
```

The shared index is:

```text
Data/world_builds/notebook_world_index.json
```

## Strict-v2 Safety Addendum

New generator output uses request schema version 2 while legacy version-1 requests remain readable for audit and migration.

- Generation is draft-only. The CLI cannot create `approved`, `building`, `active`, or `approved_public` state.
- Inputs, coordinates, identifiers, index structure, and project-relative paths are validated before files are written.
- Files are replaced atomically, and the shared index is updated last.
- A new draft has separate approval, quality, and resource/isolation artifacts. Request creation cannot mark a quality gate passed.
- New notebook worlds enter through the TARDIS notebook gateway and remain outside protected Home World.
- The generator records `home_world_mutation_allowed=false`, `strip_mall_mutation_allowed=false`, and one-notebook-world-at-a-time loading.
- A draft index entry records `placement_approved=false` and `runtime_registered=false`; catalog registration is not runtime registration.

Logical collections may group related notebook-world names and plans, but they are not combined live scenes. Validate them with:

```powershell
python tools/validate_notebook_world_collection.py <collection_manifest.json> --hardware-profile Data/launch/hardware_capability_profile.json
```

At the verified 32GB state, collection members must unload before another member starts. The prepared education arrangement is documented under `Data/world_builds/notebook_collections/education_notebook_collection_20260716/`.

## Strict-v2 Procedural Preview Lane (2026-07-16)

Request generation remains draft paperwork. A generated request does not itself authorize geometry, runtime registration, placement, approval, or Home World mutation. The optional procedural preview lane is a separate fail-closed consumer:

```text
strict-v2 draft request
  + request-local procedural_scene_program.json
  + request-local preview_scope_authorization.json
  + exact request/program hashes and one allowed build id
  -> immutable isolated preview build
```

`tools/create_world_notebook_request.py` accepts explicit notebook-world identity and initial-scope overrides so original worlds do not require place-specific code. `tools/notebook_world_preview_backend.py` accepts only a regular, request-local, exact-hash-bound program. It rechecks the draft request, adjacent approval/quality/resource/TARDIS gates, and the unplaced/unregistered index anchor before writing anything.

The procedural program must declare hard budgets, meter bounds, materials, lights, supported primitives, exactly labeled rooms, solid AABB colliders, support surfaces, unoccupied spawn marks, cameras, filming marks, routes, informational future hooks, and source-truth notes. Static routes are rejected if any segment intersects a collider expanded by the declared avatar radius. Global identifiers, paths, payload bytes, and all supported budget dimensions are bounded.

The resulting status is always `prototype_draft_not_final_not_approved`. The lane sets Home World mutation, strip-mall mutation, runtime registration, people, minds, voice, and Ollama to false. It cannot approve or promote the request. A separately reviewed promotion workflow would still be required later.

The reference isolated prototype is the Synthetic People Filming Backlot request. It contains exactly two simple rooms and an intentionally unfinished facade, with only empty future Kira/Robert/guest marks. See `Data/codex_reports/20260716_world_builder_filming_backlot_preview_lane.md`.
