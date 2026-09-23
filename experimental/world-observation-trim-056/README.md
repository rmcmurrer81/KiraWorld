# Observation trim 056 — isolated, not installed

The 055 ivory window frame and metal reveal have overlapping, equally oriented room-facing surfaces at the same depth. This reproduces a concrete cause of the striped trim seen during the parent task's browser review. For the standard 1.5 × 1.2 m opening, the overlapping front faces cover about 0.18432 m².

056 shortens the metal reveal by the frame's 26 mm depth and shifts its center 13 mm outward. The reveal's inner face now meets the frame's back. The ivory frame, aperture, glazing, gasket, wall surroundings, terrain, ribs and full solid safety collider are unchanged. The complete assembly retains the original wall bounds. No polygon offset, opacity or depth-test workaround is added. The same shared source is inlined into the preview and used by the existing GLB producer; its one producer hash/size entry is refreshed.

`FROM055.diff` is the complete three-file change. `CANDIDATE-CLOSURE.json` records the 22-file candidate, which reuses the frozen 055 source except for these three files. The renderer only admits wall thicknesses from 0.12 to 0.30 m, so the shortened reveal remains positive throughout its supported range.

`GEOMETRY-TESTS.json` records 14 CPU cases and 630 actual Three.js ray intersections. Tests reproduce the old equally oriented coplanar faces, require their absence in 056, check oblique rays at 0.5/2/10 m, verify transparent aperture rays, unchanged bounds and collider blocking, exact non-reveal mesh/scenery signatures, all four wall orientations, three supported thicknesses and an offset floor. `INTEGRITY.json` separately verifies the 116 protected originals, canonical source pins, frozen 055 files and producer bindings. These are geometry and integrity results, not a browser rendering or owner-quality approval.

No browser, server, model, GPU inference, GLB export, installation or Git push was performed for 056. The selected World job and original source files were preserved. Native visual confirmation remains pending, and the scene retains its simple procedural appearance.

To rerun the geometry test in a disposable copy, retain the sibling frozen `world-observation-exclusion-055` dependency, copy this directory, remove only that disposable copy's `GEOMETRY-TESTS.json`, then run the pinned Node executable against `test_trim.mjs`. The test refuses to overwrite an existing receipt. Do not run `stage.py` inside the frozen delivery. `verify.py` performs read-only delivery and source checks.
