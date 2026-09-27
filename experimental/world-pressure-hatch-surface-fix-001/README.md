# Hatch surface correction — isolated successor

This candidate corrects geometry defects seen during the parent's actual browser review of frozen066. It is not installed, exported, enabled in the World controller, or visually approved. The existing review server and frozen066/visual001 files remain unchanged.

## Confirmed causes

The old structural surround and shallow seat both had a front plane at local z = 0.080 m. They covered the same ring area, so the graphics depth buffer could not consistently select one material. Their identical aperture contours also duplicated vertical and curved reveal surfaces over z = 0.060–0.080 m. CPU ray intersections reproduce coincident nearest faces at the vertical band, top band, curved crown, reveal, and sill.

The old gasket occupied z = 0.0735–0.0875 m, overlapping the seat's flush upward-facing y = 0 sill surface. Two separate inspection-context defects compounded this: the uncut floor also had its top at y = 0, and the rectangular wall opening placed its reveal on the hatch's aperture reveal.

The rear trim penetrated the surround over z = -0.095–-0.086 m. This was not another equal front-plane witness, but it was unnecessary intersecting geometry and is now a butt joint.

## Geometry correction

| Part | Old local depth interval | Corrected interval / profile |
|---|---|---|
| Structural surround | -0.095 to 0.080 | Same depth; its inner contour now matches the seat's outer contour |
| Seat insert | 0.060 to 0.080 | -0.095 to 0.080; fills the frame opening up to the aperture, without overlapping the surround ring |
| Gasket | 0.0735 to 0.0875 | 0.080 to 0.0875; starts at the seat face, preserving the closed-leaf contact plane |
| Rear trim | -0.104 to -0.086 | -0.113 to -0.095; meets the frame rear face |

There are internal contacting boundaries between adjoining materials. There are no duplicate exposed front/reveal/sill faces at the tested witnesses. The aperture, moving leaf, bilateral controls, hinge, moving colliders, and analytic swing envelope are unchanged. Materials, builder, lighting and shadow bias are unchanged; this is not a bias workaround.

The recipe now declares `limits.requiresFlushSillFloorCutout` and `limits.flushSillFloorCutoutLocal`. That rectangle assigns the tiny y=0 sill footprint to the hatch mesh. The decorative floor must be cut there while keeping the walking support surface continuous. The disposable viewer's wall now follows the outer frame profile instead of duplicating the smaller aperture reveal. These are also requirements before integrating the hatch into a real World preview/export; this candidate does not modify that production architecture.

## Scope and evidence

- Three candidate source changes relative to frozen066: the two identical recipe copies and their producer pin. All other candidate files are preserved exactly.
- The separate `preview/` bundle contains the corrected recipe plus a new pure `inspection_context.mjs`; it has eight exact allowed assets. Host, Origin, path and hash guards are unchanged except for allowing that one additional module.
- Twenty CPU geometry tests pass, including reproducing the previous duplicate faces, corrected surface ownership, actual context-wall/floor intersections, all mesh vertices within their owned colliders, navigation, and four axis/direction modes.
- Four socket-free server admission/tamper tests pass; syntax checks and static bundle verification pass. No socket, browser, rendering process, model, export or installation was started here.
- See `TEST-RESULT.json`, `SOURCE-CHANGES.json`, `PRESERVATION-RESULT.json`, `SOURCE.diff`, and `FROZEN-MANIFEST.json` for actual bindings and results.

## Prepared visual review

The parent may explicitly start `preview/preview_server.py serve --manifest-sha256 <hash from TEST-RESULT.json> --port 0` using bundled Python. The process prints its loopback URL; the parent owns shutdown. Repeat closed/35°/90° from both sides and inspect the gasket, crown, seat, sill and hinge closely. Visual success is not inferred from the CPU checks.

There is still no pressure simulation, seal certification, working dog train, latch state, or permission to activate this in a saved World. Conservative collider overlap around rounded geometry remains a known limitation of the original candidate; these checks are not complete rigid-body self-collision proof.
