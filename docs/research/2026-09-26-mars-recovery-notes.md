# Recovery and current review status for World033 v2

This increment preserves experimental source, not an installed World Builder update. Installed056 remains unchanged. It contains no owner world, raw request, personal media or saved private geometry.

## Hatch066 is visually failed

Root's actual isolated browser inspection found **severe coplanar z-fighting on the seat, surround, reveal and sill**. The thirteen CPU suites remain valid technical evidence, but they do not establish acceptable appearance. Hatch066 is **not visually approved and must not be promoted**. A separate corrected successor is being prepared; its code and any future review are not included here.

The original hatch README and CPU receipts describe the earlier frozen state. The v2 candidates-status JSON and this note supersede their pending-visual-review wording; the historical files are intentionally unchanged. No seal certification, pressure simulation, functioning latch or finished VR claim is made.

## Mars067 is an overlay

The four files under `experimental/world-mars-displays-067/` match the corrected independent CPU review. They are not a self-contained installation. Their unchanged parent062 source is recoverable from the complete source preimages under `experimental/world-pressure-hatch-066/preimages/tools/world_builder_engine/` in the same increment. Work only in a separate reconstruction directory; do not overwrite installed files or owner worlds.

For source reconstruction, copy that parent preimage tree into a disposable `tools/world_builder_engine/` tree, then overlay the three files under067's `candidate/tools/world_builder_engine/`. Keep the standalone067 `mars_displays.mjs` as the original authored helper/reference. The two hatch-specific new module copies are not necessary for this display reconstruction and are not automatically activated.

The following unchanged direct imports were checked byte-for-byte against the parent:

| Relative path in the parent source tree | SHA-256 |
| --- | --- |
| `layout_package_assets/vendor/three/build/three.module.js` | `c8211c69345d2e9949dc7a8ac969380497aa0600a5a8ac6a459c8cd02dd9cb8a` |
| `layout_package_assets/source/room_dressing_plan.mjs` | `f5987f9c1e39b172f7f326e930bbb0b58ebdfc76939ee0cc26272aafc94cfcf3` |
| `layout_package_assets/source/walk_controller.mjs` | `97f651e7699715afb3fc02990beb82fbc39228b0fb668a5fd9e8c79cc078c338` |
| `walk_controller.mjs` | `a54e668e4c77cb1d40d145f7543257f07fb1f257fb108fcf0712727afba90d22` |

The renderer's `viewer.mjs` expects preview-local `three.module.js` and `three.core.js`; the normal preview builder supplies these. Opening the source viewer alone is not a supported preview. Preserve the included Three.js MIT license. The display source changes still require compatible producer/renderer pins and an explicitly reviewed integration before normal preview/export admission. Do not bypass those checks or copy this overlay into an existing immutable preview.

The display helper's nine CPU checks and initial readable-browser observation are limited evidence. Authored telemetry is explicitly fictional, not live Mars data. Full export/import, installation, general appearance and owner approval remain pending. This public source subset deliberately omits actual private063 geometry and parts of the local validation workspace; it does not promise reproduction of an owner's saved world from these files alone.
