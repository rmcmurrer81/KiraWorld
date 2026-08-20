# World Builder Pipeline

Status: first reusable scaffold, created for the Louvre realism rebuild.

The World Builder should not be a single mesh generator. It should be a source-backed place reconstruction system that keeps truth, guesses, navigation, and AI interaction separate until review proves they belong together.

## Core Flow

1. Source intake
   - Collect official pages, maps, floor plans, user-supplied references, local library material, and photos.
   - Store each source with its allowed use: scale, facade, interior layout, texture reference, object affordance, or atmosphere.
   - Mark unknown or private areas as unknown instead of inventing them.

2. Scale anchors
   - Create a meter-based coordinate grid.
   - Record confirmed dimensions first.
   - Allow inferred measurements only when the inference method is written down.

3. Modular build
   - Build one section at a time.
   - Each module gets geometry, materials, collision, walkable surfaces, source labels, and review camera points.
   - A module is not complete until a human can walk around it without passing through walls, glass, furniture, or missing floors.

4. Semantic affordances
   - Every usable object needs a visible prop and a truth tag.
   - Examples: doors open, benches sit, books read, artwork inspect, stairs climb, elevators call, windows look through, TARDIS enter.
   - AI action text must match visible body state and nearby props.

5. Navigation and collision
   - Generate walkable floors, stairs, ramps, door thresholds, and blocked surfaces.
   - Test player and AI routes separately.
   - Never use hidden teleports as a normal substitute for walking unless the interaction is an explicit world transition.

6. Review gate
   - Save screenshots from required viewpoints.
   - Compare against source notes.
   - Keep bad guesses disabled or source-labeled until fixed.

7. Large-world cell streaming
   - Split large cities and buildings into source-bounded cells with explicit
     doorway, stair, lift, street, and courtyard connections.
   - Keep only the cells around each active observer or body resident; unload
     distant geometry, textures, navigation, and ambient simulation without
     changing persistent object or door state.
   - A streaming boundary may never invent a shortcut, remove collision, or
     turn an unsupported room into a visible empty shell. Unsupported cells
     remain behind closed, locked, solid portals.

8. Real-place research pass
   - Search for several independent eye-level photographs and at least one
     useful video angle for each area, then bind them to a reviewed plan and a
     scale source before draft authoring.
   - Record which details are observed, measured, inferred, or still unknown.
     Do not combine unrelated scans merely because their filenames mention the
     same landmark.
   - Treat map/Street View/3D-tile services according to their current terms.
     Restricted imagery may be viewed as context, but it is not cached,
     extracted, traced, or converted into Kira World geometry.

## TARDIS Rule

The TARDIS is a callable/persistent travel object, not normal scenery.

- It should appear in a world only after a call, an arrival, or explicit TARDIS gateway mode.
- It must be solid.
- Entering it must be an explicit door interaction.
- AIs use it for world travel only when it is present and available.

## AI Body Rule

Characters must not claim an action unless the world and body support it.

- Reading requires a visible book, computer page, note, or media prop nearby.
- Opening a door requires a reachable handle or door surface target.
- Sitting/lying requires a furniture target and posture fit.
- A failed action should produce a recoverable reason, not a silent loop.

## First Test Project

See `projects/louvre_realism_rebuild_20260704/world_builder_request.json`.

## Current Candidate Tests

- Louvre complete inside/out remains a good realism test for source-backed public architecture.
- Voyager is now staged as a future notebook-world test from Robert's local references in `C:\Users\robmc\Desktop\voyager details`; see `Data/world_builder/voyager_details_intake_20260706.md`.
- These worlds should stay separate notebook worlds. Do not grow Home World by pasting major test worlds into the same scene.

## 2026-07-16 Status And Generator Gate

The current audit is `Data/world_builder/audits/world_generation_status_audit_20260716.md`.

- Paris/Louvre is a legacy draft with a rough walkable placeholder, not an approved or pinned world. Its exterior realism, full collision, entrance, pools, and facade fidelity remain open.
- The Legal Day Spa has a separately deployed, integrity-pinned static preview, but it is not complete: 17 required real-prefab roles are missing, the runtime Kira route test has not run, the prior failed realism review is unresolved, and Robert approval has not been granted.
- No college-campus 3D notebook world existed at audit time. A strict-v2 core request and a sequential-only logical collection were prepared without starting a renderer.

New request generation is draft-only and adds explicit source, placement, collision, realism, runtime-route, pinned-deployment, and Robert-approval gates. A static route pass or nonblank browser canvas is evidence for only that gate; it cannot be promoted into a claim that the world is complete.

## 2026-07-16 Procedural Preview Backend

`tools/notebook_world_preview_backend.py` now provides a reusable strict-v2, exact-hash-authorized path from an approved-in-scope draft request to one immutable lightweight procedural preview. It validates scene budgets, source labels, AABB collisions, avatar-radius route clearance, unoccupied future marks, review cameras, and inactive overlay hooks. `tools/serve_pinned_notebook_world_preview.py` exposes only manifest-bound bytes and rehashes every request.

The first prototype is the separate Synthetic People Filming Backlot notebook world: exactly two simple rooms plus an intentionally unfinished facade. It is a filming/blocking and builder-review scaffold only. No Kira, Robert, guest, avatar, mind, voice, Ollama, Home World, or strip-mall mutation is loaded or allowed. Its current status is `prototype_draft_not_final_not_approved`; the browser and static-route passes do not establish embodied use, final realism, long-session stability, or placement approval.

## 2026-07-17 Real-Place Reference Evidence Gate

`Core/world_reference_evidence.py` implements the owner's rule that unsupported
areas stay unavailable. A default real-place area needs three distinct photo
viewpoints, one video viewpoint, a reviewed plan/map for topology, and a
reviewed measurement/section/elevation for scale before it may enter draft
authoring. Repeated copies of one angle do not increase coverage.

Every below-threshold destination must remain behind a
`closed_locked_solid` portal with collision enabled. Passing reference coverage
does not open the portal or approve the build; geometry, collision, routes,
resources, visual comparison, and owner review are later independent gates.

Watermarked images and other no-reuse sources are reference-only. Restricted
map services are context-only: their imagery and tiles cannot be cached,
extracted, traced, interpreted into geometry, or imported as textures. See
`System/Docs/WORLD_BUILDER_REFERENCE_EVIDENCE_GATE_v1.md` and the safe-default
template at `Data/world_builder/reference_evidence_contract.template.json`.
