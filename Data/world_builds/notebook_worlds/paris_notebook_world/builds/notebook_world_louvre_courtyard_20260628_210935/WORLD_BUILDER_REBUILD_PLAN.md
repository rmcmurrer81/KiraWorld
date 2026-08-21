# World Builder Rebuild Plan

Source scaffold: `Data/world_builder/projects/louvre_realism_rebuild_20260704/world_builder_request.json`

This Louvre build is now treated as a World Builder test project instead of a one-off preview.

## 2026-07-16 Evidence Baseline

The first isolated exterior evidence pass is available through
`Start_Louvre_Solo_Notebook_World_Test.bat`. It is hash-pinned, read-only,
loopback-only, and loads no TemporaryAI/person/mind/voice/Ollama/Home World or
TARDIS. It establishes the official 21 m by 35 m main-Pyramid scale, exactly two
smaller Cour Napoleon pyramids, 12 review colliders, five clear static routes,
six landmarks, truth labels, and local/exportable feedback.

This baseline is still an unapproved approximation. Facades, pools, smaller
Pyramid placement, queue geometry, entrance details, paving, materials, and
lighting remain reconstruction work. The under-Pyramid transition and every
interior stay locked.

Owner-review r2 adds five color-coded in-world truth markers, five URL-pinned
camera bookmarks with associated routes, live route/collision/walked-distance
measurements, metric-bound local feedback, and a client-only review package
with an embedded PNG and SHA-256. These tools improve inspection; they do not
upgrade any approximate exterior geometry to sourced or approved status.

## Current Rule Changes

- The TARDIS should not render in the Louvre courtyard by default.
- Pressing C can call it into the active world when available.
- A TARDIS arrival URL may render it for that arrival.

## Next Build Target

Reconcile Cour Napoleon and the Pyramid exterior approximations against stronger
source evidence before adding new interiors.

Required:

- More believable palace facade depth and material layering.
- Realistic courtyard paving and reflecting-pool layout.
- Explicit Pyramid entrance threshold.
- No pass-through glass.
- Review screenshots from front, side, under-entry, and human-scale close views.

## Interior Gate

The under-pyramid lobby remains locked until the entry route is source-reviewed. Any guessed interior should be kept disabled or labeled `style_fill` / `unknown`.
