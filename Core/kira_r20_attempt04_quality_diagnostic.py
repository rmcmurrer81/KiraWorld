"""Pure, read-only face diagnostics for the sealed Kira R20 Attempt04 geometry.

This module is append-only diagnostic support.  It does not change the sealed
R20 construction contract, acceptance thresholds, candidates, or topology and
has no Blender, filesystem, render, runtime, or GPU dependency.
"""

from __future__ import annotations

from collections import defaultdict
import math
from typing import Mapping, Sequence

from . import kira_r20_curvilinear_pelvic_patch as patch


Vec3 = tuple[float, float, float]
Quad = tuple[int, int, int, int]


def _vertex_location(index: int) -> dict[str, object]:
    value = int(index)
    if not 0 <= value < patch.TOTAL_PATCH_INCIDENT_VERTICES:
        raise IndexError(value)
    if value < patch.SEAM_COUNT:
        return {
            "local_patch_vertex_index": value,
            "region": "seam",
            "seam_station": value,
            "reused_source_vertex": True,
        }
    if value < patch.COLLAR_2_OFFSET:
        return {
            "local_patch_vertex_index": value,
            "region": "collar_1",
            "seam_station": value - patch.COLLAR_1_OFFSET,
            "reused_source_vertex": False,
        }
    if value < patch.CORE_OFFSET:
        return {
            "local_patch_vertex_index": value,
            "region": "collar_2",
            "seam_station": value - patch.COLLAR_2_OFFSET,
            "reused_source_vertex": False,
        }
    local = value - patch.CORE_OFFSET
    row, column = divmod(local, patch.CORE_COLUMNS)
    perimeter_lookup = {
        vertex: ordinal for ordinal, vertex in enumerate(patch.core_perimeter_indices())
    }
    record: dict[str, object] = {
        "local_patch_vertex_index": value,
        "region": "core",
        "core_row": row,
        "core_column": column,
        "core_perimeter": value in perimeter_lookup,
        "reused_source_vertex": False,
    }
    if value in perimeter_lookup:
        ordinal = perimeter_lookup[value]
        record.update(
            {
                "core_perimeter_ordinal": ordinal,
                "transition_segment": ordinal // 3,
                "transition_subedge_station": ordinal % 3,
            }
        )
    return record


def vertex_record(
    index: int,
    coordinate: Sequence[float],
    seam_source_vertex_ids: Sequence[int],
) -> dict[str, object]:
    location = _vertex_location(index)
    if len(seam_source_vertex_ids) != patch.SEAM_COUNT:
        raise ValueError("diagnostic requires exactly 34 canonical seam source IDs")
    if location["region"] == "seam":
        location["source_r19_vertex_id"] = int(
            seam_source_vertex_ids[int(location["seam_station"])]
        )
    else:
        location["source_r19_vertex_id"] = None
    location["coordinate_project_m"] = list(patch._v3(coordinate, "diagnostic coordinate"))
    return location


def face_topology_record(face_index: int, face: Sequence[int]) -> dict[str, object]:
    index = int(face_index)
    if not 0 <= index < patch.REPLACEMENT_FACE_COUNT:
        raise IndexError(index)
    actual = tuple(int(value) for value in face)
    if len(actual) != 4 or len(set(actual)) != 4:
        raise ValueError("diagnostic face is not one four-distinct-vertex quad")
    expected = patch.build_quad_topology()[index]
    if actual == expected:
        winding = "forward"
    elif actual == tuple(reversed(expected)):
        winding = "reverse"
    else:
        winding = "topology_or_order_mismatch"

    if index < 2 * patch.SEAM_COUNT:
        segment = index // 2
        category = "seam_to_collar_1" if index % 2 == 0 else "collar_1_to_collar_2"
        location: dict[str, object] = {"seam_segment": segment}
    elif index < 4 * patch.SEAM_COUNT:
        transition = index - 2 * patch.SEAM_COUNT
        segment = transition // 2
        half = "leading" if transition % 2 == 0 else "trailing"
        category = f"collar_2_to_core_3_to_1_{half}"
        location = {
            "transition_segment": segment,
            "transition_half": half,
            "core_perimeter_ordinal_start": 3 * segment,
        }
    else:
        core_face = index - 4 * patch.SEAM_COUNT
        row, column = divmod(core_face, patch.CORE_COLUMNS - 1)
        category = "core_grid"
        location = {"core_face_row": row, "core_face_column": column}
    return {
        "face_topology_index": index,
        "category": category,
        **location,
        "canonical_vertex_indices": list(expected),
        "wound_vertex_indices": list(actual),
        "winding": winding,
        "matches_fixed_topology_and_order": winding != "topology_or_order_mismatch",
    }


def _edge_role(first: Mapping[str, object], second: Mapping[str, object]) -> str:
    first_region = str(first["region"])
    second_region = str(second["region"])
    regions = {first_region, second_region}
    if first_region == second_region:
        if first_region == "core":
            return "core_perimeter_or_grid_edge"
        return f"{first_region}_circumferential"
    if regions == {"seam", "collar_1"}:
        return "seam_to_collar_1_radial"
    if regions == {"collar_1", "collar_2"}:
        return "collar_1_to_collar_2_radial"
    if regions == {"collar_2", "core"}:
        return "collar_2_to_core_transition_radial"
    return "unexpected_region_transition"


def _face_neighbors(faces: Sequence[Quad]) -> dict[int, list[int]]:
    edge_faces: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(faces):
        for first, second in zip(face, face[1:] + face[:1]):
            edge_faces[tuple(sorted((int(first), int(second))))].append(face_index)
    neighbors: defaultdict[int, set[int]] = defaultdict(set)
    for incident in edge_faces.values():
        for first in incident:
            neighbors[first].update(second for second in incident if second != first)
    return {index: sorted(neighbors[index]) for index in range(len(faces))}


def _normalized_dot(first: Vec3, second: Vec3) -> float | None:
    first_length = patch._length(first)
    second_length = patch._length(second)
    if first_length <= 0.0 or second_length <= 0.0:
        return None
    return patch._dot(first, second) / (first_length * second_length)


def _face_metric(
    positions: Sequence[Vec3],
    face_index: int,
    face: Quad,
    neighbors: Mapping[int, Sequence[int]],
    seam_source_vertex_ids: Sequence[int],
    coincidence_tolerance_m: float,
) -> dict[str, object]:
    topology = face_topology_record(face_index, face)
    indices = tuple(int(value) for value in face)
    points = tuple(positions[index] for index in indices)
    first, second, third, fourth = points
    triangle_first_cross = patch._cross(patch._sub(second, first), patch._sub(third, first))
    triangle_second_cross = patch._cross(patch._sub(third, first), patch._sub(fourth, first))
    triangle_areas = [
        0.5 * patch._length(triangle_first_cross),
        0.5 * patch._length(triangle_second_cross),
    ]
    area = sum(triangle_areas)
    edge_records = []
    for slot, (first_index, second_index) in enumerate(
        zip(indices, indices[1:] + indices[:1])
    ):
        first_location = _vertex_location(first_index)
        second_location = _vertex_location(second_index)
        edge_records.append(
            {
                "slot": slot,
                "vertex_pair": [first_index, second_index],
                "role": _edge_role(first_location, second_location),
                "length_m": patch._length(
                    patch._sub(positions[second_index], positions[first_index])
                ),
            }
        )
    edge_lengths = [float(record["length_m"]) for record in edge_records]
    minimum_edge = min(edge_lengths)
    maximum_edge = max(edge_lengths)
    pairwise = []
    for first_slot in range(4):
        for second_slot in range(first_slot + 1, 4):
            pairwise.append(
                (
                    patch._length(patch._sub(points[second_slot], points[first_slot])),
                    indices[first_slot],
                    indices[second_slot],
                )
            )
    minimum_pairwise = min(pairwise)
    diagonals = [
        patch._length(patch._sub(third, first)),
        patch._length(patch._sub(fourth, second)),
    ]
    centroid = tuple(sum(point[axis] for point in points) / 4.0 for axis in range(3))
    ratio = maximum_edge / minimum_edge if minimum_edge > 0.0 else math.inf
    return {
        **topology,
        "neighbor_face_topology_indices": list(neighbors[face_index]),
        "vertices": [
            vertex_record(index, positions[index], seam_source_vertex_ids) for index in indices
        ],
        "edges": edge_records,
        "minimum_edge_length_m": minimum_edge,
        "maximum_edge_length_m": maximum_edge,
        "shortest_edge_slot": edge_lengths.index(minimum_edge),
        "longest_edge_slot": edge_lengths.index(maximum_edge),
        "quad_edge_ratio": ratio,
        "ratio_limit": 3.0,
        "ratio_excess_factor": ratio / 3.0,
        "face_area_m2": area,
        "triangle_areas_m2": triangle_areas,
        "diagonal_lengths_m": diagonals,
        "triangle_normal_dot": _normalized_dot(triangle_first_cross, triangle_second_cross),
        "centroid_project_m": list(centroid),
        "minimum_pairwise_vertex_distance_m": minimum_pairwise[0],
        "minimum_pairwise_vertex_indices": [minimum_pairwise[1], minimum_pairwise[2]],
        "near_coordinate_coincidence_at_tolerance": minimum_pairwise[0]
        <= coincidence_tolerance_m,
    }


def detailed_geometry_quality(
    positions: Sequence[Sequence[float]],
    faces: Sequence[Quad],
    seam_source_vertex_ids: Sequence[int],
    *,
    worst_n: int,
    maximum_quad_edge_ratio: float,
    coincidence_tolerance_m: float,
) -> dict[str, object]:
    values = tuple(patch._v3(value, "diagnostic position") for value in positions)
    face_values = tuple(tuple(int(index) for index in face) for face in faces)
    if len(values) != patch.TOTAL_PATCH_INCIDENT_VERTICES:
        raise ValueError("diagnostic requires all 774 positions")
    if len(face_values) != patch.REPLACEMENT_FACE_COUNT:
        raise ValueError("diagnostic requires all 756 faces")
    if len(seam_source_vertex_ids) != patch.SEAM_COUNT:
        raise ValueError("diagnostic requires all 34 seam source IDs")
    count = int(worst_n)
    threshold = float(maximum_quad_edge_ratio)
    tolerance = float(coincidence_tolerance_m)
    if not 1 <= count <= len(face_values):
        raise ValueError("worst_n is outside the exact face count")
    if not math.isfinite(threshold) or threshold != 3.0:
        raise ValueError("diagnostic ratio threshold must remain exactly 3.0")
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("coincidence tolerance must be finite and nonnegative")

    neighbors = _face_neighbors(face_values)
    records = [
        _face_metric(
            values,
            face_index,
            face,
            neighbors,
            seam_source_vertex_ids,
            tolerance,
        )
        for face_index, face in enumerate(face_values)
    ]
    ranked = sorted(
        records,
        key=lambda record: (
            -float(record["quad_edge_ratio"]),
            int(record["face_topology_index"]),
        ),
    )
    for rank, record in enumerate(ranked[:count], start=1):
        record["rank"] = rank
    failed = [record for record in records if float(record["quad_edge_ratio"]) > threshold]
    minimum_area = min(
        records,
        key=lambda record: (
            float(record["face_area_m2"]),
            int(record["face_topology_index"]),
        ),
    )

    categories: dict[str, dict[str, object]] = {}
    for category in sorted({str(record["category"]) for record in records}):
        members = [record for record in records if record["category"] == category]
        category_failed = [
            record for record in members if float(record["quad_edge_ratio"]) > threshold
        ]
        worst = max(
            members,
            key=lambda record: (
                float(record["quad_edge_ratio"]),
                -int(record["face_topology_index"]),
            ),
        )
        categories[category] = {
            "face_count": len(members),
            "maximum_quad_edge_ratio": worst["quad_edge_ratio"],
            "worst_face_topology_index": worst["face_topology_index"],
            "minimum_face_area_m2": min(float(record["face_area_m2"]) for record in members),
            "faces_exceeding_ratio_threshold": len(category_failed),
            "exceeding_face_topology_indices": [
                int(record["face_topology_index"]) for record in category_failed
            ],
        }

    perimeter = patch.core_perimeter_indices()
    collar_core_pairs = [
        (
            patch._length(patch._sub(values[core_index], values[collar_index])),
            collar_index,
            core_index,
        )
        for collar_index in range(patch.COLLAR_2_OFFSET, patch.CORE_OFFSET)
        for core_index in perimeter
    ]
    closest_collar_core = min(collar_core_pairs)
    coordinate_groups: defaultdict[Vec3, list[int]] = defaultdict(list)
    for index, value in enumerate(values):
        coordinate_groups[value].append(index)
    exact_duplicates = [indices for indices in coordinate_groups.values() if len(indices) > 1]
    topology_matches = all(bool(record["matches_fixed_topology_and_order"]) for record in records)
    failed_categories = {str(record["category"]) for record in failed}
    transition_categories = {
        "collar_2_to_core_3_to_1_leading",
        "collar_2_to_core_3_to_1_trailing",
    }
    failed_near = any(
        bool(record["near_coordinate_coincidence_at_tolerance"]) for record in failed
    )
    collar_core_near = closest_collar_core[0] <= tolerance
    only_transition = bool(failed) and failed_categories.issubset(transition_categories)
    if not failed:
        classification = "NO_EDGE_RATIO_FAILURE"
    elif not topology_matches:
        classification = "TOPOLOGY_OR_VERTEX_ORDER_DRIFT"
    elif exact_duplicates or failed_near or collar_core_near:
        classification = "COORDINATE_COINCIDENCE_OR_NEAR_COLLAPSE"
    elif only_transition:
        classification = "FIXED_TRANSITION_FACE_METRIC_PLACEMENT_IMBALANCE"
    else:
        classification = "GEOMETRIC_PLACEMENT_IMBALANCE_OUTSIDE_OR_ACROSS_TRANSITION"

    compact_metrics = [
        {
            "face_topology_index": record["face_topology_index"],
            "category": record["category"],
            "face_area_m2": record["face_area_m2"],
            "quad_edge_ratio": record["quad_edge_ratio"],
            "minimum_edge_length_m": record["minimum_edge_length_m"],
            "maximum_edge_length_m": record["maximum_edge_length_m"],
            "shortest_edge_role": record["edges"][int(record["shortest_edge_slot"])]["role"],
            "longest_edge_role": record["edges"][int(record["longest_edge_slot"])]["role"],
        }
        for record in records
    ]
    return {
        "coordinate_space": "project_world_meters",
        "face_count": len(records),
        "worst_n": count,
        "maximum_quad_edge_ratio_threshold_unchanged": threshold,
        "minimum_face_area_threshold_m2_unchanged": 1.0e-10,
        "coincidence_tolerance_m": tolerance,
        "minimum_face_area_m2": minimum_area["face_area_m2"],
        "minimum_area_face_topology_index": minimum_area["face_topology_index"],
        "degenerate_face_count_at_1e_10_m2": sum(
            float(record["face_area_m2"]) <= 1.0e-10 for record in records
        ),
        "maximum_quad_edge_ratio": ranked[0]["quad_edge_ratio"],
        "maximum_ratio_face_topology_index": ranked[0]["face_topology_index"],
        "faces_exceeding_ratio_threshold": len(failed),
        "exceeding_face_topology_indices": [
            int(record["face_topology_index"]) for record in failed
        ],
        "category_summary": categories,
        "all_faces_match_fixed_topology_and_order": topology_matches,
        "fixed_topology_connectivity_sha256": patch.topology_contract(face_values)[
            "connectivity_sha256"
        ],
        "exact_duplicate_coordinate_groups": exact_duplicates,
        "closest_collar_2_to_core_perimeter": {
            "distance_m": closest_collar_core[0],
            "collar_2_vertex": _vertex_location(closest_collar_core[1]),
            "core_perimeter_vertex": _vertex_location(closest_collar_core[2]),
            "near_coincidence_at_tolerance": collar_core_near,
        },
        "failure_localization": {
            "failure_occurs_only_on_fixed_34_to_102_transition_faces": only_transition,
            "topology_or_vertex_order_drift_detected": not topology_matches,
            "exact_coordinate_duplicate_detected": bool(exact_duplicates),
            "failed_face_coordinate_coincidence_detected": failed_near,
            "collar_2_core_perimeter_coincidence_detected": collar_core_near,
            "metric_placement_imbalance_detected": bool(failed)
            and topology_matches
            and not exact_duplicates
            and not failed_near
            and not collar_core_near,
            "classification": classification,
        },
        "all_face_metrics": compact_metrics,
        "all_violating_face_metrics": [
            compact_metrics[int(record["face_topology_index"])] for record in failed
        ],
        "worst_faces": ranked[:count],
    }


def compare_candidate_quality(
    first_positions: Sequence[Sequence[float]],
    first: Mapping[str, object],
    second_positions: Sequence[Sequence[float]],
    second: Mapping[str, object],
    *,
    difference_count: int,
) -> dict[str, object]:
    first_values = tuple(patch._v3(value, "first position") for value in first_positions)
    second_values = tuple(patch._v3(value, "second position") for value in second_positions)
    if len(first_values) != patch.TOTAL_PATCH_INCIDENT_VERTICES or len(second_values) != len(
        first_values
    ):
        raise ValueError("comparison requires two complete 774-position fields")
    first_metrics = {
        int(record["face_topology_index"]): record
        for record in first["all_face_metrics"]  # type: ignore[index]
    }
    second_metrics = {
        int(record["face_topology_index"]): record
        for record in second["all_face_metrics"]  # type: ignore[index]
    }
    if set(first_metrics) != set(range(patch.REPLACEMENT_FACE_COUNT)) or set(
        second_metrics
    ) != set(first_metrics):
        raise ValueError("candidate reports do not cover the exact common topology")
    ratio_deltas = [
        {
            "face_topology_index": index,
            "category": first_metrics[index]["category"],
            "first_quad_edge_ratio": first_metrics[index]["quad_edge_ratio"],
            "second_quad_edge_ratio": second_metrics[index]["quad_edge_ratio"],
            "second_minus_first_quad_edge_ratio": float(
                second_metrics[index]["quad_edge_ratio"]
            )
            - float(first_metrics[index]["quad_edge_ratio"]),
        }
        for index in range(patch.REPLACEMENT_FACE_COUNT)
    ]
    ratio_deltas.sort(
        key=lambda record: (
            -abs(float(record["second_minus_first_quad_edge_ratio"])),
            int(record["face_topology_index"]),
        )
    )
    displacement_by_region: defaultdict[str, list[float]] = defaultdict(list)
    all_displacements = []
    for index, (first_position, second_position) in enumerate(
        zip(first_values, second_values)
    ):
        displacement = patch._length(patch._sub(second_position, first_position))
        all_displacements.append(displacement)
        displacement_by_region[str(_vertex_location(index)["region"])].append(displacement)
    first_failed = {
        int(value) for value in first["exceeding_face_topology_indices"]  # type: ignore[index]
    }
    second_failed = {
        int(value) for value in second["exceeding_face_topology_indices"]  # type: ignore[index]
    }
    first_worst = [
        int(record["face_topology_index"]) for record in first["worst_faces"]  # type: ignore[index]
    ]
    second_worst = [
        int(record["face_topology_index"]) for record in second["worst_faces"]  # type: ignore[index]
    ]
    first_maximum = float(first["maximum_quad_edge_ratio"])
    second_maximum = float(second["maximum_quad_edge_ratio"])
    return {
        "same_fixed_topology_connectivity": first["fixed_topology_connectivity_sha256"]
        == second["fixed_topology_connectivity_sha256"],
        "first_maximum_quad_edge_ratio": first_maximum,
        "second_maximum_quad_edge_ratio": second_maximum,
        "second_minus_first_maximum_quad_edge_ratio": second_maximum - first_maximum,
        "lower_maximum_ratio": "first"
        if first_maximum < second_maximum
        else "second"
        if second_maximum < first_maximum
        else "equal",
        "common_exceeding_face_topology_indices": sorted(first_failed & second_failed),
        "first_only_exceeding_face_topology_indices": sorted(first_failed - second_failed),
        "second_only_exceeding_face_topology_indices": sorted(second_failed - first_failed),
        "common_worst_n_face_topology_indices": sorted(set(first_worst) & set(second_worst)),
        "maximum_candidate_position_delta_m": max(all_displacements),
        "maximum_candidate_position_delta_by_region_m": {
            region: max(values) for region, values in sorted(displacement_by_region.items())
        },
        "largest_absolute_face_ratio_differences": ratio_deltas[: int(difference_count)],
    }
