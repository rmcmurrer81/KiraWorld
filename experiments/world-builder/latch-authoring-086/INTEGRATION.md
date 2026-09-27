#086 shared latch authoring core: not a new installed world

Existing v1 authoring source and consumer083 remain unchanged.086 introduces `authored_pressure_hatch_latch_geometry_v2` in `src/pressure_hatch_latched.mjs`; it deliberately is not accepted by the old hatch geometry, architectural cutout or consumer contracts. Exact084 `latch_visual.mjs` is preserved byte for byte.085's native review supports the component's visible keeper/bolt motion only; it did not approve a complete base or establish pressure containment.

## Implemented source seam

`planLatchedPressureHatch(geometry, portalId)` accepts the same compiled meter-based geometry and produces a new frozen plan for either member of an authored airlock pair. Ordinary doors return null. It preserves the original leaf, hinge, structural surround, bevelled seat, reinforcement, latch rails, through shafts, grab bars, hinge hardware, architectural aperture and floor limits.

It removes exactly21 old parts: three dogs, three housings, three solid keepers, three supports, both wheels, six spokes and the old gasket. It supplies28 replacement meshes: three translating bolts, three housings, three shortened supports, twelve keeper bars with real openings, two wheel rims, four rotating crossbars and one continuous variable-depth gasket. Nothing is added over an unchanged old latch. Every mesh has a unique part owner and collider links.

`latchHatchCollidersAt(plan, angle)` transforms conservative local bounds for every visual pose to a requested valid hinge angle. Bolt bounds are the union of translation endpoints; smoothstep is monotone and stays within that interval. Wheel rims use the torus radial envelope; crossbars use their corner radius over the full rotation, rather than just endpoint widths. Gasket bounds cover its entire proposed depth variation. Four separate keeper bars retain the opening instead of replacing it with a solid box. The analytic hinge sweep includes all visual-pose bounds, conservatively exceeding the release-only operating envelope.

`describeLatchedHatchAuthoring(plan)` provides frozen export-ready per-part representations, initial released state, complete collider ownership and all-pose bounds under `latched_hatch_authoring_metadata_v2`. This is a core input for an exporter, not an already admitted `scene.json`. `validateLatchedHatchPlan(serialized, geometry, portalId)` recomputes exact authoring parameters and returns a locally bound plan; the builder rejects an unvalidated JSON clone.

`buildLatchedPressureHatch({THREE, plan, doorId, runtimeIdentity, readDoor, isCurrent})` builds retained073 artwork plus exact084 replacement geometry. It exposes root, meshes, snapshot, syncDoor, request, advance, pause, resume, reset and dispose. It has no separate animation loop, no door command and no pressure action. On invalid/stale observations the full assembly hides; disposed observers do not call the host. A moving door with nonreleased latch artwork faults rather than granting permission. Root/consumer must separately enforce release before opening and keep existing reach, floor, collision and interlock guards.

## Exact remaining producer and consumer changes

The following existing source seams require a separately reviewed successor. None was changed by this public addition:

| Current seam | Required new reviewed successor |
| --- | --- |
|073 `pressure_hatch.mjs` and its export/source mirror | Select086 only for paired pressure hatches; preserve ordinary doors and v1 packages. Bind086 plus exact084 and the retained source helper. |
|073 `walk_controller.mjs` and export/source mirror | Admitv2 definitions, use all-pose part colliders/sweep, and coordinate release-before-hinge without relaxing reach, occupied-swing or pair checks. |
|073 `pressure_hatch_architecture.mjs` and mirror | Recompute the exact unchanged leaf/aperture/cutout geometry forv2 explicitly. Do not change the existingv1 allowlist to accept arbitrary contracts. |
|073 `viewer.mjs` and hatch preflight | Use one current runtime/door identity for the086 assembly, sync after door states, aggregate pause reasons and dispose on world replacement. Add actual paired-placement sweep/obstruction checks. |
|073 `layout_package_assets/source/pressure_hatch_metadata.mjs` and scene metadata | Define a distinctv2 representation with all-pose colliders, visual articulation and explicit hierarchy. Keep pressure/fictional seal state separate. |
|073 `layout_package_assets/authored_scene.mjs` and `build_glb.mjs` | Build the initial released pose from086. Current083 requires each moving mesh to be a direct child of one hinge with identity local transforms;084 uses a separate matrix-bound moving group and wheel subgroups. The new exporter must deliberately bake or describe that new hierarchy and round-trip it, not pretend it meets the old hierarchy. |
|073 `world_layout_preview.py`, `layout_package_export.py` and source receipts | Copy and hash the complete new module closure, update exact renderer bindings, and produce a fresh immutable preview/package. No reuse of old manifest or GLB hashes. |
|083 `door_metadata.mjs`, `package_loader.mjs`, runtime and `airlock_host.mjs` | Keep both old exact package admissions intact. Add only a newly reviewed exact package/source closure, validate thev2 hierarchy/part parameters/bounds, and order fictional latch release and door movement with cancellation tests. Do not turn visual engagement into a seal acknowledgement or pressure proof. |

A new whole-base integration therefore needs more than this bounded core. No exporter, importer, controller, installed source, saved geometry, selected-world pointer or existing preview has been changed. A separate source merge/review should precede one fresh visual/export/import attempt.

## Verification and remaining review

Eight focused Node/Three.js CPU tests cover exact part replacement, all four portal orientations,17 closed visual samples, released hinge poses through90degrees, analytic sweep bounds, keeper channel and central passage, metadata ownership, recomputed plan tampering, old-contract rejection, pause/fault/disposal and independent opposite hatches. These tests do not load a GLB or browser and use original artificial dimensions. The portable tests use only artificial inputs and existing public dependencies; no private package or saved-world data is required.

Actual base placement, occupied-swing admission with the new conservative bounds, final wall/floor visual parity, moving wheel/gasket close-up, GLB export/import and headset use remain untested for086. No pressure or physical seal simulation is provided. Normal release/engagement artwork remains separate from the existing fictional seal acknowledgement and six-second symbolic cycle.
