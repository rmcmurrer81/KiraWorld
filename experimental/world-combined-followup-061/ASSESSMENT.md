# World059 meal station and World060 door hardware: integration assessment

Read-only assessment, 26 September 2026. Status: feasible isolated combination; not assembled, installed, or visually approved.

The two proposals can be combined on installed World056 without rewriting owner worlds. A fresh comparison found all 42 installed source files still match World060's recorded World056 preimages. The proposals change nine distinct files, with two shared pin files requiring a deliberate merge. Copying either candidate wholesale would discard part of the other change.

This assessment uses checkpoint045 (handoff receipt `history/20260926T213435280413Z/RECEIPT.json`), World059's frozen source and later `ACTUAL-DELIVERY.json`, and World060's frozen source, tests, and root public-backup review. The checkpoint identifies both proposals as uninstalled. Backup review is not permission to install or evidence of native visual quality.

All paths below are relative to `tools/world_builder_engine/`.

| Scope | Files | Required treatment |
| --- | --- | --- |
| World059 only | `viewer.mjs`; `layout_package_assets/authored_scene.mjs`; `layout_package_assets/source/room_dressing_plan.mjs`; `layout_package_assets/source/room_dressing_render.mjs` | Preserve exact reviewed meal-station geometry, placement, and shared preview/export implementation. |
| World060 only | `walk_controller.mjs`; `layout_package_assets/source/walk_controller.mjs`; `layout_package_assets/source/scene_metadata.mjs` | Preserve exact reviewed rotating handle colliders, sweep calculations, metadata, and bounded collision batching. |
| Both | `layout_package_export.py`; `layout_package_assets/PRODUCER-PINS.json` | Merge both renderer pins in the exporter and all changed producer hashes. Neither existing whole-file version is sufficient. |

The exporter must bind World059's viewer and World060's preview walker simultaneously. Producer pins must cover the resulting authored-scene, dressing plan/render, metadata, and packaged-walker bytes while preserving every unrelated pin. There is no identified need to change the layout backend, research provenance, Node/Three versions, room geometry, resource caps, or saved project selection.

World059 already passed a bounded CPU export and real GLB import: 20 added meal-station meshes, one assembly, and one conservative static collider; prior geometry, materials, routes, and door poses were preserved. Its earlier README's pending-export statement is superseded by the closed actual-delivery receipt. Native appearance, access, and scale remain unreviewed. Seating and food interaction are not implemented.

World060 fixes visible handle penetration through four attached hardware boxes per door rather than broadening the entire leaf collider. Its existing CPU evidence covers both walkers, five layouts, 540 door poses, and a 24-door capacity case within the unchanged collision-batch limit. It also compares World059 meal placement under old/new door assemblies and finds it unchanged. That is useful compatibility evidence, but it does not establish that a merged preview/export is correct or comfortable to navigate.

The next concrete checks are:

1. Prepare an isolated combination with nine exact World056 preimages and a complete 42-file source closure. Independently inspect the two merged pin files. Keep geometry/research/Node integrity checks and saved-preview compatibility rules intact.
2. Run the inherited meal-placement, omission, route, bounds, and shared-geometry checks against the actual combined modules; likewise run both hardware walkers, near-handle collision, fully open passage, metadata ownership, airlock behavior, and maximum-door batching checks. Do not merely replay stored receipts.
3. Create a fresh immutable preview from the already authorized selected geometry through the existing API, then perform one bounded CPU export/import. Preserve all older previews/exports and the selected-job pointer. Verify all 116 protected originals before and after. Confirm the meal addition and four hardware colliders per door survive export, with no unrelated geometry or presentation changes. Old previews must keep their original renderer; they must not be relabelled as combined output.
4. Retain the native visual gate once computer-use authorization permits it: inspect meal-station scale and access, navigate both sides of door handles and the paired airlock, and check that World056's stable observation-window trim remains intact. No finished VR physics or seated-avatar approval follows from CPU results.

Only after those results and root review should a guarded nine-file installation with rollback be considered. This assessment created no source build, preview, export, model job, or installation, and changed no owner world files.
