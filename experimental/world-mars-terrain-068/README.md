# Original Mars exterior candidate068

Isolated proposal on the final reviewed067 display source. Not installed or visually approved. No source image, downloaded asset, shader-only background, model call, renderer, server or saved-world mutation is included.

The original viewport is a real opening in a wall whose original full safety collider remains intact. Its dimensions, frame, glass, interior equipment, signs, displays, doors and collision rules are unchanged. The source-bound Mars presentation gate is unchanged. Other settings do not acquire a Mars landscape.

The new shared recipe replaces the prior single brown grid and sinusoidal ridge with denser nearby ground, centimeter-scale regolith variation, two irregular ridge bands,18 separately shaped rocks and a curved warm dusty sky beyond the terrain. All distances are authored meters. Heights and color variations are original deterministic design choices, not measured Martian topography, a named real site, live weather or a physically simulated atmosphere. The existing research065 motivates a visible, coherent exterior and explicitly distinguishes the fictional habitat from real mission measurements.

The synthetic fixture has20 meshes,8,601 vertices and15,264 triangles, beneath the proposed24-mesh/12,000-vertex/20,000-triangle limits. Its rocks have different anisotropic shapes; exact geometric dimensions stay below1.8m horizontal and0.85m high. The terrain is more finely sampled close to the window and extends roughly114m outward. The sky is a curved180m shell in the exterior half-space, within the existing250m camera far plane. The global background, camera, hemisphere/directional/room lights, tone mapping and exposure are untouched; no global fog is added.

Standard materials, vertex colors, geometry, transforms and source provenance use the same code in the browser viewer and GLB producer. The sky has a modest common emissive term; its appearance still depends on the existing renderer and lighting. The established export limitation remains: hemisphere fill, ACES exposure and background are not guaranteed to match across arbitrary GLB viewers. Exporting shared geometry does not establish pixel-identical appearance.

## Validation and limits

Ten CPU tests cover exact preserved functions and viewer startup, deterministic viewer/export geometry, invalid source gates, four outward directions and translated floors, mesh budgets and scale, room clearance, actual rays through the aperture to ground/rocks/sky, differentiated terrain bands, unchanged complete authored habitat geometry and collider/door links, and a real texture-free exterior-only GLB export/import. The whole habitat is constructed and compared in memory; this is not a new selected-project portable package export or a browser rendering test.

The bounded runner uses a new output directory, at least5GiB free RAM,1GiB family RSS cap,3GiB reserve and90-second deadline. It rejects an already active exporter/test and checks source bytes before/after. It does not launch a browser or model. Previous CPU failures are preserved: an overly tall initial rock was reduced; unused sphere pole normals were supplied explicitly; test comparisons were corrected for the loader's documented name bookkeeping, tiny transform roundoff and automatically numbered otherwise-unnamed export objects. The final attribute/index comparisons remain exact.

This candidate aims for more natural relative scale and depth. CPU tests do not demonstrate realistic appearance. Native review must look through the existing window near/far and obliquely: ground detail, readable distinct rocks, ridge silhouettes, warm horizon brightness, no sky edge, flicker, interior occlusion or distracting repetition. If that view is not convincing, hold it instead of calling it finished or photorealistic.

## Recovery and next integration

Two source overlays are supplied: viewer.mjs and layout_package_assets/source/room_dressing_render.mjs, each with its exact final067 beforeimage. mars_exterior.mjs is the authored review source copied identically into both; it adds no runtime import or preview asset allowlist entry. authored_scene.mjs stays byte-identical to final067 and already calls the shared exterior function. Synthetic layout input comes from the already published066 synthetic fixture; no raw owner brief or saved world is included.

DEPENDENCIES.json pins the exact067 parent modules, unchanged062 tests/export library dependencies, synthetic source fixture and research. Recovery must resolve those exact files. Do not substitute current canonical source for the historical parent.

Before any installation: root source/independent review, a new immutable preview using the exact two overlays and unchanged authorized source chain, native window inspection, selected-project package API export/import and producer/source closure updates. The producer manifest's shared render hash must change, and its authored_scene entry must remain the reviewed067 hash when composing onto062. Viewer source pins also change. No existing provider/producer pin was rewritten here. Hatch changes are independent and are excluded from068. Installed056 and all067 artifacts remain untouched.

Run the CPU checks only in a new output directory:

`C:/Python314/python.exe -X utf8 -B work/world-mars-terrain-068/run_tests.py cpu-next`

No install or native-preview command is included. Root owns that next approval.
