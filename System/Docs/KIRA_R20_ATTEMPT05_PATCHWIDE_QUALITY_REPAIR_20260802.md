# Kira R20 Attempt 05 patch-wide quality repair

Status: `INDEPENDENT_GEOMETRY_REVIEW_NO_GO_NEVER_RUN_IN_BLENDER`

## Superseding review result

The original focused suite passed, but a separate geometry review found that
the predicate did not enforce its declared `2e-7 m^2` signed-triangle margin
and accepted nearly right-angle quad twists. Candidate A measured minimum
mutual triangle cosine `0.00048494` and normalized warp `0.914`; candidate B
measured cosine `0.00081694` and warp `0.814`. The solver also judged outward
orientation against normals derived from the already folded candidate. It is
therefore rejected and must never start Blender.

Independent edge-incidence review then found that the sealed ordered face list
has 136 same-directed shared-edge incidences. Correct orientability requires
reordering exactly transition faces 68 through 135. The undirected adjacency,
counts, and disk topology remain unchanged, but the ordered face SHA-256 must
change from the failed historical `761981c7...` value to
`a06812ddacd405ef4e8d642bb4ef3124c4a41f5108bf3efb9d33b841a66d5ed9`.
Attempt 05 cannot be repaired by reversing those tuples afterward because it
optimized against the wrong ordered contract; a new base-first attempt must use
the corrected ordering from its first calculation.

The exact reviewed module remains preserved at SHA-256
`5ccb335719cabd1a0bb3f24e56835790c6754ad70b9f8179fa7e4f5cb9ea4dd6`.
Complete rejection evidence is
`../../RecoverySprint/continuation_20260802/kira_r20_attempt05_patchwide_quality_repair_prepared/INDEPENDENT_GEOMETRY_REVIEW_NO_GO.md`.
No `attempt_05` output directory, R20 Blend, mesh mutation, pose, render, or
owner candidate was created.

## Why this repair is patch-wide

The exact Attempt 04 read-only diagnostic found 84 union violations, 81 shared
by both candidates, and 46 deep-core offenders. A narrow seam-band selector is
therefore invalid. Central external-anatomy relief is not the root cause:
setting feature scale to zero leaves 82 failures per candidate.

The current generated collar/core boundary collapses some perimeter segments
and expands others. With that generated boundary frozen, the 3.0 ratio gate is
mathematically impossible. The exact 34 seam and 740/756 topology are feasible
and remain unchanged.

## Smallest implementation boundary

Attempt 05 adds:

1. a pure no-Blender position-repair module that captures the sealed Attempt
   04 constructor and tangentially reparameterizes only its 740 generated final
   surface positions; and
2. a small bootstrap that reuses the unchanged sealed worker/config and routes
   its already validated append-only output to `attempt_05`.

The bootstrap does not clone or edit the 202,035-byte Blender worker. All mesh
replacement, UV/weight propagation, attributes, rig/pose tests, intersection
gates, guarded save, and fresh-process verification remain sealed Attempt 04
behavior.

## Geometry bounds

The 34 seam positions are exact and immovable. All generated movement is
projected into frozen reference tangent planes. Caps are based on exact median
seam edge `e = 0.017658196540973933 m`:

- collar 1 `0.12e`;
- collar 2 `0.18e`;
- core perimeter `0.30e`;
- every core-interior clinical vertex `0.20e`.

The optimizer uses a 2.70 quality barrier and must reach an internal maximum
2.90 while the official unchanged gate remains 3.0. It also requires positive
signed triangles, nonopposed triangle pairs, positive area, no duplicates,
exact seam/topology, frozen-normal drift at most 1e-12 m, and accepted-landmark
centroid drift at most `0.10e`.

Both candidates passed the original incomplete pure tests and simulated Blender
float32 coordinate round-trip. They did **not** pass the later complete geometry
review. This is not a Blender authoring, body, pose, intersection, render,
visual, or owner acceptance.

## Anatomy and future systems

The semantic external-feature formulas, U/V stations, asymmetry, candidate
parameters, and longitudinal landmark order are unchanged. The repair is a
surface sampling correction. It does not implement internal urinary,
digestive, reproductive, pregnancy, illness, or hospital physiology. Those
future adult systems remain separate, consent-bound, versioned upgrades under
`FUTURE_ADULT_BODY_PREGNANCY_HEALTH_COMPATIBILITY_BOUNDARY_20260802.md`.
