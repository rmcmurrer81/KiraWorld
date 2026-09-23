# Installed051 navigation audit052

No new traversal defect was found in this bounded CPU audit, and no product fix is proposed.

The actual saved Mars definitions and51 authored furniture colliders were used with both installed051 controller copies. Each normal-height walker completed an87.71-metre route from Equipment Vestibule through Primary Airlock into the corridor, visited Operations, Crew Living, Science Lab and Viewport Deck, then returned to the starting room. Every move used the public look/step/toggle API; no position setter, spawn relocation or saved-geometry edit was introduced. The route mixed straight movement with diagonal forward-plus-strafe input and1/60-second/0.05-second steps. Door states ended closed.

216 centre/shallow-diagonal doorway segments across both controller paths established open passage and closed/reclosed blocking in both directions. Six thin-leaf tests had clear endpoints but an obstructed segment interior.25 additional actual wall/door corners blocked a0.099-metre diagonal segment despite clear endpoints—below the normal0.11-metre maximum step. Seven wall/exterior attempts were held by either solid geometry or missing floor support. Airlock peer opening remained denied at angle-zero reservation, moving, held-open and fully-open stages; closing restored the ability to open the other leaf.

These are mechanical checks of the current conservative square-footprint/AABB model, not a guarantee for arbitrary layouts or body physics. Body height is1.68m and camera eye height1.56m. No jump, vertical connector, head tracking, circular-body sliding, pressure simulation, browser/native UI or visual-realism check was performed. The actual source file was only read;116 protected originals and installed source pins remained unchanged.

Run `audit.mjs` with three explicit arguments: the exact saved geometry file, its SHA256 and an engine-source directory. Baseline source copies under `baseline/tools/world_builder_engine` preserve both controller variants and their imported navigation/dressing dependencies. Historical results remain in `AUDIT-RESULT.json`; use a fresh directory before replay because the script refuses to overwrite its receipt. The geometry itself is not bundled.

## Next useful realism gap

The saved room named **Viewport Deck** describes external visual monitoring, but its compiled room shell still consists of solid opaque walls. Its distinct equipment is a seat and growing rack. The current authored renderer contains equipment glazing but no actual observation viewport through an exterior wall. A label and seating therefore do not fulfill that room's visible function.

A useful bounded successor would add one original framed, recessed, transparent observation window in a verified exterior wall, with a real view beyond it, while keeping the pane nontraversable and preserving routes/door swings. It would need shared preview/export mesh construction, explicit glazing/frame metadata and later artifact inspection. It must preserve old immutable builds and avoid claiming pressure-rated engineering, a source-measured reconstruction or completed realism. This is a proposal only; no window, terrain or geometry changes were made by052.
