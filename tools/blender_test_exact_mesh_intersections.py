"""In-memory regressions for exact nonadjacent mesh intersections."""

from __future__ import annotations

from pathlib import Path
import sys

import bmesh
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.blender_exact_mesh_intersections import (
    classify_triangle_pair,
    exact_nonadjacent_intersection_report,
)


TOLERANCE = 1.0e-9


def mesh_report(
    coordinates: tuple[tuple[float, float, float], ...],
    face_indices: tuple[tuple[int, ...], ...],
) -> dict[str, object]:
    """Build a temporary synthetic BMesh and return its read-only audit."""

    mesh = bmesh.new()
    try:
        vertices = [mesh.verts.new(value) for value in coordinates]
        mesh.verts.ensure_lookup_table()
        for indices in face_indices:
            mesh.faces.new(tuple(vertices[index] for index in indices))
        mesh.faces.ensure_lookup_table()
        mesh.normal_update()
        return exact_nonadjacent_intersection_report(
            mesh,
            include_pair_details=True,
        )
    finally:
        mesh.free()

base = (
    Vector((-1.0, -1.0, 0.0)),
    Vector((1.0, -1.0, 0.0)),
    Vector((0.0, 1.0, 0.0)),
)
crossing = (
    Vector((0.0, -0.5, -1.0)),
    Vector((0.0, -0.5, 1.0)),
    Vector((0.0, 0.75, 0.0)),
)
coplanar_overlap = (
    Vector((-0.5, -0.5, 0.0)),
    Vector((0.5, -0.5, 0.0)),
    Vector((0.0, 0.5, 0.0)),
)
coplanar_touch = (
    Vector((1.0, -1.0, 0.0)),
    Vector((2.0, -1.0, 0.0)),
    Vector((1.5, 0.0, 0.0)),
)
parallel_separate = tuple(point + Vector((0.0, 0.0, 0.25)) for point in base)

crossing_result = classify_triangle_pair(
    base,
    crossing,
    linear_tolerance=TOLERANCE,
)
overlap_result = classify_triangle_pair(
    base,
    coplanar_overlap,
    linear_tolerance=TOLERANCE,
)
touch_result = classify_triangle_pair(
    base,
    coplanar_touch,
    linear_tolerance=TOLERANCE,
)
separate_result = classify_triangle_pair(
    base,
    parallel_separate,
    linear_tolerance=TOLERANCE,
)

assert crossing_result["classification"] == "noncoplanar_crossing_segment"
assert crossing_result["genuine_penetration"] is True
assert crossing_result["intersection_segment_length_m"] > 0.0
assert overlap_result["classification"] == "coplanar_positive_area_overlap"
assert overlap_result["genuine_penetration"] is True
assert overlap_result["coplanar_overlap_area_m2"] > 0.0
assert touch_result["classification"] == "coplanar_touch_or_numerical_contact"
assert touch_result["genuine_penetration"] is False
assert separate_result["classification"] in {
    "bvh_aabb_only",
    "parallel_bvh_aabb_only",
}
assert separate_result["genuine_penetration"] is False

# These two coplanar polygons deliberately overlap while sharing an original
# source edge.  They are topology-adjacent and therefore outside a
# *nonadjacent* self-intersection gate, even when tessellation produces an
# overlapping triangle pair that does not itself contain the shared edge.
shared_edge_report = mesh_report(
    (
        (-1.0, -1.0, 0.0),
        (1.0, -1.0, 0.0),
        (1.0, 1.0, 0.0),
        (-1.0, 1.0, 0.0),
        (0.5, 0.75, 0.0),
        (-0.5, 0.75, 0.0),
    ),
    (
        (0, 1, 2, 3),
        (1, 0, 5, 4),
    ),
)
assert shared_edge_report["bvh_nonadjacent_candidate_pair_count"] == 0
assert shared_edge_report["exact_genuine_penetration_pair_count"] == 0

# These planar polygons share only source vertex 0 while crossing elsewhere.
# A source-vertex adjacency exclusion must still remove the pair even when the
# particular crossing tessellation triangles use disjoint triangle vertices.
shared_vertex_report = mesh_report(
    (
        (0.0, -1.0, 0.0),
        (-1.0, -1.0, 0.0),
        (1.0, -1.0, 0.0),
        (1.0, 1.0, 0.0),
        (-1.0, 1.0, 0.0),
        (0.0, -0.5, -1.0),
        (0.0, 0.75, -1.0),
        (0.0, 0.75, 1.0),
        (0.0, -0.5, 1.0),
    ),
    (
        (1, 0, 2, 3, 4),
        (0, 5, 6, 7, 8),
    ),
)
assert shared_vertex_report["bvh_nonadjacent_candidate_pair_count"] == 0
assert shared_vertex_report["exact_genuine_penetration_pair_count"] == 0

# Two crossing triangles with entirely disjoint source topology must remain a
# genuine nonadjacent penetration.  The adjacency repair must not suppress it.
disjoint_crossing_report = mesh_report(
    (
        (-1.0, -1.0, 0.0),
        (1.0, -1.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, -0.5, -1.0),
        (0.0, -0.5, 1.0),
        (0.0, 0.75, 0.0),
    ),
    (
        (0, 1, 2),
        (3, 4, 5),
    ),
)
assert disjoint_crossing_report["bvh_nonadjacent_candidate_pair_count"] == 1
assert disjoint_crossing_report["exact_genuine_penetration_pair_count"] == 1
assert disjoint_crossing_report["pairs"][0][
    "genuine_positive_area_or_segment_penetration"
] is True

print(
    "EXACT_MESH_INTERSECTION_NARROW_PHASE_PASS "
    f"crossing={crossing_result['classification']} "
    f"coplanar={overlap_result['classification']} "
    f"touch={touch_result['classification']} "
    f"separate={separate_result['classification']} "
    "shared_edge_excluded=true "
    "shared_vertex_excluded=true "
    "disjoint_crossing_detected=true"
)
