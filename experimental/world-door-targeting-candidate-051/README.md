# Facing-aware door selection051

This isolated five-file upgrade carries frozen050's door-targeting correction into both the preview and its authored export controller. It is ready for root review, **not installed**.

In the actual saved Mars airlock, the old F action reopened the nearer entry behind the user while the camera faced the corridor exit. The same problem selected Crew Living when looking west toward Operations. Selection now filters nearby doors by the walking camera's horizontal facing direction before using the existing distance order. If no nearby door is faced, F makes no change and explains why.

## Exact scope

- Preview controller and two help strings come byte-for-byte from frozen050.
- The portable authored controller receives the same three changed regions. Its six door definitions, dimensions, hinge transforms, frames, collision rules and paired-airlock policy are unchanged.
- The exporter pins the new preview/controller hashes; the producer manifest pins the new portable controller.
- No geometry, furnishings, source worlds, saved pointers, research or dependencies are modified.

`SOURCE.diff` contains the complete five-file delta. `INSTALL-PLAN.json` has exact preimages, destinations and116 protected-input hashes. Plan SHA256: `acc62a7e35915eaf62ce3914b04f0cc14f144285f00c701fa1f7a11edc2d435c`.

## Validation

Both controller paths passed seven tests against the same actual saved Mars geometry, including furnished walking, opposite corridor targets, airlock denial, sideways no-op and all six doors' closed/open/reclosed routes. Four additional checks preserve portable definitions/policy and compare200 deterministic frontend/portable input ticks. Viewer callback checks cover four label states and the blocked-message callback without a browser.

Seven export-contract checks exercise current/old/changed preview pins, actual producer/dependency hashes and missing/modified portable source. Eight temporary installer tests include rollback and concurrent-file preservation.

`ACTUAL-EXPORT-RESULT.json` records one real CPU-only export/import:2.33 seconds,813,416,448 bytes sampled family peak RSS. The new immutable candidate preview reuses its exact build on repeat. The GLB is byte-identical to installed045 (`0b6ee808519f83e73a3ff5b9df336d456e76f7fce91fe493e797702ba226531b`), with623 meshes,97 materials,67 textures,7 rooms,134 colliders and6 doors. `COMPATIBILITY-RESULT.json` separately verifies earlier saved previews, the owner pointer and protected originals.

## Review and installation

Run `C:/Python314/python.exe install_exact.py` from this directory for a read-only preflight. Root must review and explicitly authorize the exact plan before invoking `--apply acc62a7e35915eaf62ce3914b04f0cc14f144285f00c701fa1f7a11edc2d435c`. Default execution does not install. `--rollback` with the same hash restores only the five exact after-images; it refuses concurrent changes. The installer retains preimages and writes a distinct execution receipt.

After an approved installation, **Refresh/Open current preview** creates or reuses a new immutable build for the selected saved world. Previously saved previews remain valid and keep their old controls. The new exporter deliberately holds old appearance/controller versions with an instruction to open the current preview. It never rewrites old packages. No native UI has been opened for051.

## Limits

This is horizontal facing selection with a60-degree half-angle, not pixel picking or occlusion raycasts. Explicit low-level door IDs retain the existing proximity, swing-occupancy and interlock rules. Door states remain session-local; pressure, exterior EVA, appliance operation and real habitat engineering are not simulated. The independent experimental consumer043/044 is unchanged. A GLB/metadata package does not itself execute this JavaScript or provide game-engine/VR controls. This correction establishes neither visual realism nor owner approval.
