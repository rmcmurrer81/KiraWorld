# Authored Mars GLB prototype036

This isolated CPU export preserves the installed original procedural room meshes,
materials, textures and door geometry. It does not improve their realism and is
not installed as a World Builder control. No browser, GPU, model or download was
used. Original saved worlds and media remain untouched.

The complete local review package is `actual-mars-005/`: `scene.glb`, corrected034
`scene.json`, `ROUNDTRIP.json`, `README.txt`, empty runtime log and sealed manifest.
The metadata sidecar retains its historical metadata-only capability labels; the
package manifest describes the added actual meshes/textures. No engine-native
collision, interaction, pressure simulation, persistence or VR adapter is supplied.

Results: 557 meshes, 95 material instances (70 distinct parameter sets), 67 embedded
PNG textures, 7 rooms, 141 semantic nodes, 134 linked colliders and6 hinged doors.
Two complete exports produce identical GLB bytes and receipts. The actual Three180
importer retains geometry attribute/index bytes, world transforms, material values,
texture effective pixels/repeat/wrap/color-space, room bounds and collider IDs.
All doors match the controller at closed, half-open and open poses; fixed frames
stay fixed. The extracted installed-viewer baseline independently matches all557
mesh records and per-room membership/bounds/material counts. These are engineering
checks, not appearance or owner acceptance.

`TEXTURE-CONTACT-SHEET.png` contains11 labeled CPU cards from embedded PNGs: two
floor surfaces, a screen, wall panel and all7 room signs. Only a vertical flip is
applied for readable Canvas UV orientation. This inspection does not substitute
for a rendered world review.

The original025 dressing renderer is an exact byte copy. Structure and doors are
transcribed from the pinned installed viewer, with explicit hinge parents and
stable IDs added for export. Three180 exporter/loader are unchanged MIT sources.
CPU Canvas0.1.100 and registered Windows font files are external pinned inputs;
their binaries/font files are not redistributed. A native Canvas `data()` method
is hidden on local adapter instances because Three otherwise mistakes it for a
DataTexture and exports transparent PNGs. PNG callbacks are delivered in request
order for deterministic embedded-buffer ordering. These corrections affect only
the isolated CPU adapter.

Missing fonts/maps/owner links fail clearly. External fetches are refused. The
original renderer's hemisphere fill, background, ACES tone mapping/exposure,
polygon offset, depth-write choice and live indicator colors are not guaranteed
portable. Text rasterization is Skia-based and not browser-pixel-identical.

For a public checkout replay, `export_saved_mars.py --help` lists explicit saved
bindings, the verified034 metadata package/writer, Node, CPU Canvas/native and
three font inputs. It is deliberately scoped to the reviewed Mars geometry hash;
it never searches owner folders or overwrites an output. The original saved geometry/research documents remain local. Public backup
includes the original authored GLB, texture contact sheet, code, source pins and
hashed evidence. Font/native binaries and node_modules folders are excluded;
only the minimal unmodified MIT Three JavaScript dependency closure is archived.

Public import paths point to vendor/three instead of node_modules/three. The exact
Three JavaScript bytes and self-referencing package exports are unchanged;
IMPORT-REBASE.json records every import-only change. The package manifest preserves
hashes of the locally tested producer revision. This public import arrangement
has a module-load check only; full public-wrapper replay is pending GPU-slot cleanup.
