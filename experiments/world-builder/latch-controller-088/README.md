# 088: isolated latch authority and real controller gates

This is an **uninstalled source candidate**, not an integrated visible hatch or newly admitted world package. It implements the first reviewed portion of plan087 against exact producer073 / consumer083 / authoring086. Installed World remains056. No model, browser, service, native renderer, full-world export or Git operation was run.

Five source files are new or changed: one shared pure latch authority, one strict v2 metadata projector/validator, the actual producer walking/door controller, the portable door/runtime controller and its door-metadata dispatcher. Six exact inherited modules complete the11-file candidate. All copied dependencies have exact beforeimages.084 and086 original bytes are unchanged.

## Implemented behavior

`createDoorSystem` and `createWalkController` default to the unchanged legacy path. Explicit `hatchVariant: 'latched_v2'` selects086 only for the nominated paired hatches. Ordinary doors retain the old definitions, colliders and motion. The portable runtime selects the new path only for `authored_pressure_hatch_latch_geometry_v2`; old descriptors still use their existing validator.

Each v2 door has one session-local pure latch authority. It holds the fraction, target, fault, pause reasons and pending opening intent. It starts released, takes0.8seconds of active time to travel, and accepts steps of at most0.05seconds. No renderer or second fraction clock was added. Engagement requires an exactly closed, stopped leaf with no pending hinge target or motion hold. The actual low-level `toggle` methods reject an engaged, releasing, paused or faulted latch, so directly calling a runtime API cannot bypass the visual gate.

`releaseAndOpen` is one explicit pending command. On completed release it is consumed once and rechecks reach, adjacent room, peer-door reservation and occupied swing through the existing toggle method. A failed recheck is retained as `lastOpenResult` and never retried automatically. Pause revokes that opening intent. Clearing a pause can resume the visual fraction, but does not recreate the opening request. Any observed stale runtime permanently retires this controller, even if its callback later returns true. Dispose is terminal and prevents new latch or door commands.

The original peer interlock and pressure-free door policies remain unchanged. Latch completion neither acknowledges a seal nor starts the separate symbolic pressure cycle. No pressure or physical latch simulation is claimed.

## Strict metadata boundary

`describeLatchedDoor` builds exact v2 semantic nodes, conservative all-pose colliders, leaf/hinge metadata and the authored latch contract from086. It carries only bounded numeric room/portal recipe inputs and authored functional roles; no research text, private source path, memory or source-file lookup is involved. It requires explicit compiled meter-based input.

`validateLatchedDoor` independently recomputes the descriptor, compares exact parts/parameters/bounds/collider ownership, and cross-binds the recipe to the actual portable scene rooms, portal associations and both paired hatch descriptors. Extra or unclaimed v2 parts reject. The old validator rejects this new variant. No GLB loader, package allowlist, exporter, preview backend, application UI or installed source was changed, and no arbitrary/new package hash is admitted by this candidate.

The bounded source option and descriptors are not yet wired into the full scene exporter. Existing legacy metadata/export entry points still reject the new hatch plan. Do not call this a ready portable package or copy these files directly over canonical World.

## Evidence

The final `cpu-003` run passed13 focused Node tests in0.785seconds, using173,084,672bytes peak family RSS, with no remaining owned processes. Unchanged limits:5GiB available RAM before starting,0.8GiB family RSS,3GiB reserve and45seconds. The source/helper imports are inert and do not load providers or weights.

Tests exercise both actual low-level controllers, including direct-call bypass attempts, pending-target engagement rejection, release continuation, peer reservation during release, occupied-swing and moved-away completion rejection, pause/no-replay, stale false→true retirement, disposal, four orientations, metadata tampering and invalid units. Default v1 producer output/state matches the original and both exact previously admitted package metadata fixtures still validate. Their original package/scene hashes are checked; no new GLB is imported.

A read-only check uses the exact073 preview manifest/geometry binding and checks both real hatch placements with086 conservative collision bounds and existing room dressing. It constructs the walking controller, validates a memory-only v2 projection of the same portable scene, and verifies source bytes remain identical. This is CPU placement/metadata evidence, not an actual new preview, source-chain publication or export.578 protected files—including parent frozen sources, canonical World dependencies and116 owner originals—were hashed before and after the final run and preserved.

Earlier `cpu-001`/`002` evidence is retained. Only `cpu-003` describes the final source. `prepare.py` and `integrate.py` preserve initial construction history; do not rerun them into this directory. Final candidate bytes, exact beforeimages, `SOURCE.diff` and manifests are authoritative recovery artifacts.

## Deferred mesh and application integration

No normalized mesh-binding implementation was added in this stage. Inspection confirmed that084 has a matrix-bound second moving group, reflected local bases and nested wheel groups, whereas the old importer requires direct hinge children with identity transforms. Baking geometry and correct reflection/winding, then driving imported mesh transforms from the one authority needs a separately reviewed adapter and round-trip tests. Adding it here would widen a controller gate change into unreviewed geometry/export work.

The next source stage should implement that adapter against the final authority snapshots, then update explicit v2 architecture/scene projection, source-pin closure and the strict importer branch. The UI must pass a captured current-session predicate, aggregate pause reasons, call these control methods rather than mutable render state, and handle pending release before starting its existing hinge sequence. Existing083 host/app files are untouched; neither the new controls nor their visuals are available through that UI yet. Full preview/export/native inspection and final art/owner/headset approval remain pending.
