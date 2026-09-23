# Pure scene metadata prototype030

This isolated candidate implements the first bounded part of029: a pure JavaScript
metadata projection over compiled geometry, an authored dressing plan and door
definitions. It does not install into World Builder, add an export button, create
a mesh file, reconstruct equipment from boxes or run an engine/VR application.

`candidate/tools/world_builder_engine/scene_metadata.mjs` exports
`exportSceneMetadata(geometry, dressing, doorDefinitions, { sceneId, sourceDigests })`
and `canonicalSceneMetadata(scene)`. It has no imports, file/network operations,
renderer calls or model calls. It explicitly copies supported fields and drops
unknown source fields. The three caller-supplied source digests are labelled as
bindings supplied by the caller, not independently verified provenance.

The copied walker has one additive, read-only `definitions()` method. It describes
the actual controller's hinges, leaf/frame dimensions, room/portal IDs, motion
rate, reach and sweep policy directly from controller authoring state. It is
independent of live session angles. Existing movement methods are unchanged.
This avoids inferring hinge behaviour from a screenshot, current pose or mesh.

The synthetic export contains7 rooms,141 nodes,134 collider records and6 doors.
Structural box parameters already present in the source are preserved. The16
equipment assemblies export semantic type, room membership, actual renderer
base-centre transform, dimensions and conservative bounds. Their multipart meshes,
materials and generated textures are explicitly absent. Architecture transforms
match the renderer's world-aligned boxes; an authoring wall-yaw value is not applied
a second time. Equipment is static and has no invented interactions.

Doors declare a toggle intent and the existing conservative collision/swing rules;
they do not become engine-native physics objects. Metadata does not simulate
pressure, science or life support. No session state, VR input, navmesh, network
authority, persistence, Unity/Unreal adapter or glTF/GLB export is implemented.
Rendering quality remains independent of export success.

Run `node test_metadata.mjs -003` for a fresh receipt and synthetic JSON output.
Eleven test groups cover deterministic round trips, immutable inputs, source
coverage, render transforms/bounds, door authoring metadata, byte-equivalent
existing controller behaviour across open/walk/close, truthful capability flags,
unknown-field omission, path/provenance guards, ownership, finite bounds and
invalid navigation. Tests require only Node and the included synthetic/source
closure; no graphics or owner data are loaded. The latest receipt is
`TEST-RESULT-002.json`; the initial receipt is retained as history before correcting
architecture metadata to match the renderer's unrotated world-axis boxes.

Canonical source and owner worlds remain unchanged. A future production exporter
still needs an explicit owner action, verified input digest computation, a package
writer and an independent consumer before an engine or game workflow is claimed.
