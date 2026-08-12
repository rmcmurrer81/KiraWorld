# Kira R20 Attempt 06 base-parameterization contract

Date: 2026-08-02  
Status: `INTRA_QUAD_FEASIBILITY_PASS_INTER_QUAD_CONTINUITY_NO_GO_NO_BLENDER`

## Why a new append-only attempt is required

Attempts 01 through 04 and their evidence remain immutable. Attempt 05 never
ran in Blender: independent review rejected its direct-final-position solver
because it accepted severely twisted quads, used candidate-derived orientation
normals, and optimized against an ordered face list with a transition-band
winding defect.

Attempt 06 is the final pre-Blender design. It replaces only the unaccepted
generated pelvic-patch base. It does not regenerate Kira, touch the exact seam,
or change any accepted nonpelvic component.

## Corrected ordered topology

The sealed face list has 136 same-directed shared-edge incidences. A consistent
orientation requires reordering exactly transition faces 68 through 135 as
`(a, d, c, b)`. This keeps the existing `a-c` diagnostic diagonal stable.

- 34 exact seam vertices remain fixed;
- 740 generated vertices and 756 quads remain exact;
- undirected adjacency, edge incidence, connected disk topology, and all index
  identities remain unchanged;
- corrected ordered face SHA-256:
  `a06812ddacd405ef4e8d642bb4ef3124c4a41f5108bf3efb9d33b841a66d5ed9`;
- directed same-way shared-edge count must be zero;
- boundary-edge count must remain 34 and nonmanifold-edge count zero.

The failed historical ordered SHA `761981c7...` remains preserved in Attempts
01 through 05. It must not be presented as the safe Attempt 06 ordering.

## Base-first geometry contract

The offline solve produces one candidate-independent pre-relief base and one
candidate-independent coherent normal authority from the exact source seam,
exterior rings, and seam normals. Blender does not run a numerical optimizer.
Its pure verifier must:

1. verify the four exact construction-input hashes;
2. verify the sealed payload and corrected topology hashes;
3. verify the exact seam positions, order, UVs, and weights;
4. load the pinned pre-relief base;
5. evaluate the unchanged sealed feature scalar for each exact semantic U/V
   station and candidate;
6. apply that scalar once along the pinned candidate-independent feature-normal
   field; and
7. run every static, float32, local-shape, intersection, rig, pose, freeze, and
   protected-component gate before its sole guarded save.

There is no post-relief vertex optimization. Evidence must prove
`final_position = base_position + exact_scalar * feature_normal` for every core
vertex. Physical spacing may differ from semantic U/V label spacing, but the
labels, row/column identities, scalar payloads, harmonic UVs, and harmonic
weights remain separately hash-bound.

## Superseded experimental movement caps

Attempt 05's `0.12e/0.18e/0.30e/0.20e` caps were experimental protections
around an unaccepted, folded Attempt 04 embedding. They are superseded only for
the 740 generated pelvic-patch vertices in this base solve. They never apply to
the exact 34 seam or any nonpelvic vertex, rig, face, material, image, shape,
action, or identity component, all of which remain frozen.

The replacement payload must record every displacement from both its stated
initial base and failed Attempt 04. Large displacement is not visual approval;
it triggers local landmark/rim/cap evidence and private owner review.

## Mandatory numerical gates

Both the no-relief base and exact Candidate A/B final surfaces must be measured
in double precision and after the exact Blender float32 local/world round trip.
Final A and B each require:

- maximum quad edge ratio no greater than `2.90` internally and `3.0`
  officially;
- both triangle signed-area2 values at least `2e-7 m^2` against the coherent
  source/body-derived authority;
- mutual triangle-normal cosine at least `0.5`;
- normalized quad warp no greater than `0.25`;
- positive face area, no exact duplicates or near-collapse;
- zero directed winding conflicts, boundary crossings, rim crossings,
  nonadjacent triangle intersections, and nonmanifold edges;
- exact connectedness and semantic longitudinal/lateral order;
- rim orientation, containment, area/perimeter, cap spread/depth, local
  pair-distance, and no-collapse records;
- deterministic restoration after every required pose.

The feasibility checkpoint reports candidate state hash
`81007f06c4bb0f3bbaa22385189cfab3f02e49a79b1b5d440ef4ef412306752e`
with double/float32 edge, signed, cosine, and warp gates passing for both A and
B. Independent review also confirmed exact topology/seam, zero real 3D
self-intersections, scalar binding, physical semantic order, and local rim/cap
topology. It nevertheless rejected the state for Blender because 12 shared
edges have opposed adjacent quad normals; the worst dihedral is 119.906 degrees
and one central urethral-region edge exceeds 90 degrees. Some triangles deviate
nearly 88.2 degrees from their coherent authority normal. The state remains a
read-only intra-quad feasibility result, not authoring coordinates.

Attempt 06 must therefore add hard inter-quad continuity gates before any
Blender run:

- adjacent area-weighted quad-normal cosine at least `0.5` on every shared
  edge;
- normalized triangle-to-authority-normal dot at least `0.5`;
- seam patch/source-normal dot at least `0.5`;
- all earlier double, float32, topology, shape, order, and 3D intersection gates
  remain simultaneously passing.

## Visual and functional truth

Passing numerical gates authorizes only a private inactive Blender authoring
attempt. It is not owner visual approval. A saved candidate must still receive
the complete linked owner-review series and Robert's decision.

The patch can represent connected external adult anatomy, semantic external
landmarks, deformation, and bathroom contact/clearance. It does not implement
an internal bladder, bowel, pelvic floor, reproductive system, conception,
pregnancy, delivery, postpartum recovery, illness, treatment, or hospital care.
Those remain separate future, versioned, consent-bound systems.

## Prohibited actions

Do not activate, assign, export, clothe, publish, upload, load scalp hair,
change Kira's accepted identity/face/body outside the exact mask, run Video
Studio, or start Robert while this candidate remains pending owner review.
