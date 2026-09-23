# Faithful authored-scene export: proposed CPU prototype

Build an isolated GLB from the existing authored scene builders, with034 metadata
beside it. Do not replace recognizable equipment with its metadata bounding boxes.
No installed source, saved world or immutable preview is changed.

The025 renderer contains actual box, cylinder, sphere and torus geometry, normals,
UVs, multipart groups, PBR materials and procedural Canvas2D maps. Its injectable
`canvasFactory` is the useful entry point. Installed Three and the local official
GLTFExporter both use version0.180.0; their core/module bytes match. The bundled
`@napi-rs/canvas`0.1.100 supplies CPU Canvas2D and PNG encoding, avoiding a browser
or WebGL renderer. Dependencies will be pinned; no downloads are required.

## Preserve these properties

| Content | Proposed treatment |
| --- | --- |
| Structure and equipment | Execute the exact authored builder code in a separate scene. Retain every primitive/group transform, geometry attributes/index data and material assignment. Give exported objects stable IDs linked to034 metadata. |
| Floors, panels, screens and signs | Inject a CPU canvas into the existing drawing code. Embed PNGs, sRGB assignments, UVs, wrapping and repeats. Require maps on every authored textured surface and all mounted sign faces. Record the resolved font availability; missing fonts/maps stop the faithful export. Browser/Skia rasterization is not assumed pixel-identical. |
| PBR and transparency | Preserve colors, roughness, metalness, emissive values/intensity and alpha. Verify corresponding glTF material data and supported extensions. `depthWrite:false` and polygon offset are renderer-state limitations, not silently promised portable behavior. |
| Doors | Export a pivot at each exact hinge, with the complete moving leaf/panels/handles/mounts beneath it. Frames and the status indicator stay fixed. Verify closed/intermediate/open world transforms against the existing controller. A motion clip does not implement collision, reach or swing occupancy rules. |
| Collision and interaction | Carry034's corrected collider owners/bounds and the existing conservative door policy as bound sidecar metadata. Cross-reference node IDs in the GLB. No Unity/Unreal/VR adapter or engine-native physics is claimed. |
| Lighting and appearance | Point/directional lights can use the exporter's punctual-light extension; verify directions. Hemisphere fill, scene background, ACES tone mapping/exposure and runtime indicator colors require disclosure in sidecar rendering notes. No identical final lighting claim. |

## First bounded implementation

Use only the existing saved Mars bindings. Verify the same geometry, blueprint,
research/cache and producer hashes before writing a new output folder. Reuse the
pure025 equipment builder and extract the static structural/door assembly from
the pinned installed viewer into a separately reviewed builder, leaving the
canonical viewer untouched. Use the official exporter with a small isolated
Canvas/FileReader compatibility adapter; never instantiate `WebGLRenderer`.

Output should contain `scene.glb`, corrected `scene.json`, a source/producer/file
manifest, and concise fidelity notes. It includes authored mesh/texture assets,
not the original source documents or local paths. Windows font files are local
inputs for rasterized signs; do not redistribute them in the package.

Checks before root review: deterministic scene dimensions and object counts;
all expected maps/signs present; material/texture repeat/color-space data retained;
correct034 node/collider ownership; door hinge world transforms at closed, halfway
and open; importer roundtrip geometry bounds/transforms/texture presence; exact
source preservation. Asset roundtrip is an engineering check, not visual realism.
Actual engine compatibility and owner visual acceptance remain future work.
