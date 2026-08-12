# Avatar Builder patch parameterization and continuity QA v2

Date: 2026-08-02  
Status: **MANDATORY APPEND-ONLY ADDENDUM - NOT A PROMOTED GEOMETRY METHOD**

Machine-readable contract:
`Avatar/avatar_builder/tooling/bounded_body_authoring_quality_contract_v2.json`

The v2 contract inherits the exact v1 contract at SHA-256
`b032d1ddc5ed51156d32cdeb5b9459df073c3a81f7101471b8e6455ba96a7935`.
Every v1 guard remains mandatory. This addendum transfers only generic lessons
from the bounded Kira R20 pre-Blender failures. It contains no private
coordinates, person-specific topology, identity measurements, intimate
appearance values, or selectable geometry payload.

## Why the additional gates are required

A generated patch may have zero direct self-intersections and individually
acceptable quads while still folding sharply across shared edges. Undirected
edge counts also do not prove that face winding is coherent. Those failures
must be rejected before Blender opens, because a render or smooth shader can
hide them without repairing the surface.

The builder must therefore preserve four separate kinds of truth:

1. ordered, orientable topology;
2. a candidate-independent normal authority derived from the accepted body;
3. quality inside each quad; and
4. continuity between adjacent quads and with the accepted seam.

No one category substitutes for another.

## Ordered topology

The builder binds both undirected incidence and ordered face connectivity.
Every manifold shared edge must occur once in each direction. Same-directed
shared-edge incidence, a nonmanifold edge, an unexpected boundary, or an
orientation inconsistency is a fail-closed preflight result.

If face winding is repaired, the corrected ordering receives a new hash. The
builder must keep vertex identity, seam identity, undirected adjacency, and a
stable diagnostic triangulation diagonal exact. Historical rejected hashes
remain evidence and never become aliases for the corrected ordering.

## Base-first geometry and normal authority

Create one candidate-independent pre-relief base. Derive one coherent frozen
normal authority from the accepted body surface, seam normals, and bounded
exterior rings. A candidate may not use normals computed from itself to judge
whether it has the correct orientation or signed area.

Semantic row/column identity and physical spacing are separate. Apply each
hash-bound semantic scalar exactly once:

`final_position = pre_relief_base_position + semantic_scalar * frozen_feature_normal`

Do not run a free post-relief optimizer that can move anatomy landmarks,
change the intended scalar meaning, or trade one hidden fold for another.

## Mandatory simultaneous geometry gates

Run all gates in double precision and again after the exact Blender float32
local-coordinate and object-to-world round trip.

Within every quad:

- maximum edge ratio is `3.0`;
- mutual diagnostic-triangle normal cosine is at least `0.5`;
- normalized warp is no greater than `0.25`;
- face area is positive and above a candidate-scale-bound minimum;
- duplicate and near-collapse counts are zero.

Across the surface:

- every adjacent area-weighted quad-normal cosine is at least `0.5`;
- every normalized triangle-to-authority-normal dot is at least `0.5`;
- every seam patch/source-normal dot is at least `0.5`;
- directed winding conflicts, nonmanifold edges, boundary/rim crossings, and
  direct 3D nonadjacent triangle intersections are zero;
- semantic order, rim containment/orientation, cap spread/depth, and local
  no-collapse checks pass where applicable.

A global 2D projection can flag a suspicious crossing, but only a direct 3D
triangle test is intersection authority. Conversely, zero 3D intersections
does not waive winding, normal, continuity, semantic, deformation, or visual
review gates.

## Bounded repair and owner boundary

Only two bounded repairs may target the same remaining defect. A failed
pre-Blender candidate may preserve metrics and tracebacks append-only, but it
must not write reusable coordinates, mutate the source/live body, or open
Blender. After two failures, preserve the best structurally safe complete
candidate, disclose the exact remaining defect, and stop for the owner. Do not
start another body or a general framework to avoid that decision.

## Future body-system compatibility

The builder preserves stable, versioned semantic landmarks and deformation
regions so later systems can attach without silently regenerating an accepted
identity, face, skin, rig, weights, movement, or unrelated anatomy. These
future systems remain separate: confirmed-adult relationship state, current
consent, intimacy, conception, pregnancy timeline, gestation, delivery/birth,
postpartum recovery, family state, bladder/bowel/pelvic-floor simulation,
illness/injury, treatment/recovery, and hospital care.

A future voluntarily selected pregnancy simulation may use an ordinary
approximately nine-month timeline or an explicitly chosen accelerated
day-scale or one-day timeline. Acceleration remains labeled simulation time;
it does not claim ordinary biological elapsed time. Relationship, intimacy,
conception, timeline, and medical-care consent are distinct decisions.

This compatibility requirement does not claim that any present external mesh
implements internal organs, elimination, reproduction, pregnancy, illness,
treatment, or hospital care. It grants no current activation or runtime
authority.

## Promotion truth

The R20 coordinates and topology that exposed these lessons were rejected and
are not reusable examples. Only the QA rules transfer. A future geometry
method still needs the existing non-private fixture and owner-approved
promotion gates before Avatar Builder may select it.
