# Kira R24 nonuniform source-edge feasibility result

Created UTC: `2026-08-09`

Status: `NO_ELIGIBLE_NONUNIFORM_RECORD_FAIL_CLOSED`

This is a read-only premutation geometry result. It is not a body candidate,
an anatomy completion, a render, movement acceptance, or owner approval.

## Exact execution truth

The independently audited wrapper ran once. Blender 5.1.2 opened the sealed
source Blend in background mode and exited `0` after one worker invocation.
The wrapper recorded exact protected pre/post integrity, no worker failure, no
native invocation error, and no finalization error. It did not mutate a mesh or
datablock and did not save, render, export, activate, assign, or publish a body.

- Result:
  `RecoverySprint/continuation_20260808/kira_r24_nonuniform_source_edge_feasibility/nonuniform_feasibility_01/NONUNIFORM_SOURCE_EDGE_FEASIBILITY.json`
- Result SHA-256:
  `1616863af7bcef1f74e120d3a0e5ccef6071c8d90bfa382d261bb542f9c67356`
- Wrapper completion SHA-256:
  `92c21029d702efd3325a97e3ef036df31463eb82273ed535d3934e28882af3cc`
- External integrity SHA-256:
  `61690b791e067cd1ba665cb48a1eb70f716286ffb74a8b5234ba1b8f6b15e4ef`
- Records generated/evaluated: `192/192`
- Eligible records: `0`
- Automatic retry: forbidden

The deterministically selected diagnostic row was
`plane_sample_112_of_190`. It passed every inherited gate except
`boundary_angle_gate`:

- minimum projected angle: `1.4840928997651306 degrees`;
- required minimum: `12.000001 degrees`;
- maximum chart deviation: `0.0010918951425287567 m`;
- required maximum: `0.001099999999 m`;
- chart-margin pass: approximately `8.105 micrometres`.

The row is not a repair candidate. Of its 70 edge parameters, 64 are at the
minimum or maximum open dyadic endpoints and 66 are within one percent of an
endpoint. Together with the consumed uniform family—which passed angle but
failed chart deviation—this is evidence that the fixed 70-edge carrier
topology is the blocker. Neither family may be retried, relaxed, or accepted as
least-bad.

## Smallest next bounded lane

The next static-only lane is:

`LOCAL_TRANSITION_ACTUAL_PLANE_CONTOUR_TOPOLOGY_FEASIBILITY_01`

It must rederive the exact consumed plane
`lower + (upper - lower) * 112/190`, intersect that plane with all 73 exact
E-star collar triangles, and evaluate the resulting actual unclamped
piecewise-linear contour. It may change only the carrier-cycle topology. It
must preserve E-star, D2, all source coordinates, the 73-face collar, the
34-point seam, all exterior-adjacent faces, protected inventories, owner/
opposite provenance, and the unchanged angle/chart gates.

The lane is not permission to reuse or clamp the rejected 70 source edges,
search alternate planes, expand E-star, mutate Blender data, save a body,
render review images, integrate brows/nails, activate Kira, or begin Robert.
It requires a fresh append-only static package, focused no-Blender tests, and
an independent audit before at most one guarded read-only Blender execution.

All output and controlled-cache evidence from `nonuniform_feasibility_01` must
remain byte-for-byte preserved. Never delete it and never rerun that lane.
