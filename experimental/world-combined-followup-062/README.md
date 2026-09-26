# World062: isolated meal station and door hardware combination

This candidate combines the exact reviewed World059 meal-station source with World060 door-hardware collision source on the current installed World056 closure. It is **not installed, rendered, exported, or visually approved**. Realistic finished appearance is still required; functional geometry and CPU assertions do not establish that quality.

Nine source files differ from installed056. Four retain exact059 bytes: viewer, authored scene, dressing plan, and dressing renderer. Three retain exact060 bytes: both walking controllers and scene metadata. Only the two shared binding files are deliberately merged: the exporter now pins both the059 viewer and060 preview walker, and PRODUCER-PINS binds all five changed producer modules. Every other source and external dependency pin remains unchanged. `SOURCE.diff`, `MERGE-PROVENANCE.json`, `SOURCE-PINS.json`, and `CANDIDATE-CLOSURE.json` record the exact transition.

Fresh CPU checks ran against the combined modules:

- The inherited meal suite passed all four synthetic layouts and the actual saved Mars geometry: placement, omission when crowded, bounds, unchanged prior furniture, routes, shared preview/export geometry, metadata ownership, and unsupported role handling.
- The inherited hardware suite passed both controllers across five layouts, 540 door poses and 321,108 assertions. It covers mesh-vertex containment, reserved sweep bounds, fully open passages, prior handle penetration, airlock exclusion, unchanged furnishing placement, and all24 doors within the existing128-collider batching limit.
- Read-only exporter admission verified both merged renderer pins together. Only the combined viewer/walker pair passes the mocked appearance boundary; all eight old/tampered combinations are held. All17 producer-file hashes and sizes match. The installed056 saved preview remains eligible in the installed exporter, while the combined exporter holds it rather than silently adding newer furniture/collision behavior. The separate059 preview is outside the canonical verifier's permitted root and is held by that scope guard.
- All42 installed source files, the combined42-file closure, and all116 protected owner originals were verified before and after; the selected-job pointer remains unchanged.

The first contract-test attempt assumed the separate059 preview would reach the renderer-version check. Its earlier path-scope guard correctly held the foreign preview. The test now asserts that existing boundary explicitly; no implementation guard was weakened.

No preview creation, actual GLB export/import, renderer, model, GPU, UI, installation, or Git publication ran for062. Geometry tests assemble Three objects with an inert canvas solely to test physical meshes; they do not render images or establish texture transport. The previous059 GLB result is separate evidence and is not claimed as a combined062 export.

The next authorized validation stage is an independent review of the two merged pin files, followed by a new immutable combined preview and one supervised CPU export/import using the existing API. Preserve old previews, selected pointers and owner files. Native inspection remains necessary for scale, meal access, both sides of handles, paired airlock traversal and observation-window trim before guarded installation. No seating interaction, food simulation or finished VR physics is added here.

`OWNER-PRESERVATION.local.json` is local recovery metadata and should not be included in a public backup. The frozen manifest binds its digest separately. No root handoff or canonical source was changed.
