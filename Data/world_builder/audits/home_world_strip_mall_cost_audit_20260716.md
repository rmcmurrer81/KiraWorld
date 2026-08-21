# Home World Legacy Strip-Mall Cost Audit

Status: static source audit complete; controlled live RAM/VRAM/draw-call A/B not run.

## Outcome

Home World now leaves the former strip-mall site visually empty by default. The legacy procedural implementation was not deleted and can be restored explicitly with `?stripMall=1`. The Legal Day Spa was not placed on the site and remains a separate notebook world.

The change should save a modest amount of memory and can avoid meaningful render submissions when the old building would be visible. It is not honest to assign a live RAM or VRAM number yet: the old site has no imported GLB payload, and no controlled two-run browser/GPU measurement was started during this safe, non-visual pass.

## Static Expansion Estimate

Calling the preserved `addStripMall()` implementation expands to:

- 128 procedural mesh objects: 122 boxes, 5 canvas-sign planes, and 1 cylinder.
- 37 static colliders, including 5 door colliders.
- 6 interaction zones.
- 5 generated 768 x 192 canvas sign textures.
- 2,949,120 base RGBA texture bytes (2.8125 MiB), or roughly 3,932,160 bytes (3.75 MiB) with a full mip chain.
- No imported GLB requests.

Each visible mesh can require at least one main render submission; shadows, transparent double-sided sign materials, camera frustum, and renderer batching can change the real count. These are source-expansion counts, not a claim that all 128 meshes appear in every frame.

## Reversible Runtime Policy

- Default: skip the legacy construction function and report the coordinates as `empty former strip-mall lot`.
- Default affordance truth: outside, no nearby door, cannot enter.
- Restore: add `?stripMall=1` to the Home World preview URL.
- Preservation: source stays in `main.js`; no destructive deletion.
- Spa: not placed here.

The runtime debug API now exposes `window.kiraHomeWorldDebug.resourceSnapshot()`. It can report Three.js calls, triangles, geometry/texture counts, scene mesh/collider counts, and the current legacy-site state. Those counters still cannot measure total process RAM or complete GPU VRAM.

## Future Controlled Measurement

If Robert wants an exact comparison later, run two otherwise identical isolated Home World sessions—one default and one with `?stripMall=1`—using the same camera route, Kira model, renderer settings, warm-up time, and sampling window. Record process working set, GPU dedicated-memory use, frame time, renderer calls, triangles, geometries, and textures. Do not combine that experiment with the spa, a second person, voice, or another notebook world.
