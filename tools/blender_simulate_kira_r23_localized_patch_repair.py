#!/usr/bin/env python3
"""Bounded no-save simulation for the final localized Kira R23 patch repair.

The worker reuses the sealed R19 body, exact Attempt05 donor core/topology, and
Attempt04 seam-chord-safe application path.  It searches only Hermite collar
geometry while using exact-loop UV choices and seam-pinned harmonic weights.
It never saves a Blend, renders, exports, or touches runtime/person state.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXECUTION_FLAG = "--execute-readonly-simulation"
BOUND_STATUS = "BOUND_NOT_RUN_EXPLICIT_READONLY_SIMULATION_REQUIRED"


class SimulationError(RuntimeError):
    """Fail-closed simulation error."""


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument(EXECUTION_FLAG, action="store_true")
    return parser.parse_args(raw)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise SimulationError(f"JSON root is not an object: {path}")
    return value


def project_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def require_binding(binding: Mapping[str, Any], label: str) -> Path:
    path = project_path(str(binding["path"]))
    if not path.is_file() or path.is_symlink():
        raise SimulationError(f"{label} is absent or linked: {path}")
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(binding["bytes"]) or digest != str(binding["sha256"]):
        raise SimulationError(
            f"{label} drifted: bytes={size}, sha256={digest}"
        )
    return path


def vector_record(value: Any) -> list[float]:
    return [float(value[index]) for index in range(len(value))]


def face_edges(face: Sequence[int]) -> set[tuple[int, int]]:
    return {
        tuple(sorted((int(face[index]), int(face[(index + 1) % len(face)]))))
        for index in range(len(face))
    }


def weight_distance(first: Mapping[str, float], second: Mapping[str, float]) -> float:
    names = set(first).union(second)
    return max(
        (abs(float(first.get(name, 0.0)) - float(second.get(name, 0.0))) for name in names),
        default=0.0,
    )


def percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    offset = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[offset]


def sample_segment(parameters: Sequence[float], fraction: float) -> int:
    for index, start in enumerate(parameters):
        end = parameters[index + 1] if index + 1 < len(parameters) else 1.0
        if start <= fraction <= end or index + 1 == len(parameters):
            return index
    raise SimulationError("cycle fraction lacks a source segment")


def projected_inward(raw: Any, tangent: Any, label: str) -> Any:
    if tangent.length <= 1.0e-12:
        raise SimulationError(f"{label} has a degenerate boundary tangent")
    direction = raw - tangent.normalized() * raw.dot(tangent.normalized())
    if direction.length <= 1.0e-12:
        raise SimulationError(f"{label} has no non-tangential inward direction")
    return direction


def capture_design(
    author_config: Mapping[str, Any],
    verification_config: Mapping[str, Any],
    repair_overlay: Mapping[str, Any],
    bpy: Any,
    bmesh: Any,
    author: Any,
    attempt04: Any,
    verifier: Any,
    preflight_module: Any,
    actions_module: Any,
    exact_module: Any,
    topology: Any,
) -> dict[str, Any]:
    from mathutils import Vector

    source_path = project_path(
        verification_config["fixed_inputs"]["r19_source_blend"]["path"]
    )
    if bpy.data.filepath:
        raise SimulationError("design capture must begin in factory-empty Blender")
    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    attempt04.bind_attempt04_runtime(repair_overlay)
    preflight, captured, _effective = author.reproduce_passed_preflight(author_config)
    names = verification_config["objects"]
    body = bpy.data.objects.get(names["r19_body"])
    donor = bpy.data.objects.get(author_config["qualified_donor_disk"]["object_name"])
    rig = bpy.data.objects.get(names["rig"])
    if body is None or donor is None or rig is None:
        raise SimulationError("sealed preparation omitted the body, donor, or rig")
    verifier.suspend_rig_action(rig)
    verifier.apply_pose(rig, {})
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()

    selected_faces = {int(value) for value in captured["chosen"]}
    target_cycle = [int(value) for value in captured["chosen_cycle"]]
    donor_disk, donor_vertices, donor_cycle, memberships = author.exact_donor_disk(
        donor, preflight, author_config
    )
    prepared = author.prepare_patch(
        body,
        donor,
        selected_faces,
        target_cycle,
        donor_disk,
        donor_vertices,
        donor_cycle,
        memberships,
        preflight,
        author_config,
    )
    if prepared["topology_sha256"] != (
        "8a30a63adcd431145f25308ea8d87c86782d0e11a3ed307a3ec431085351617c"
    ) or prepared["position_sha256"] != (
        "737a955c0701fa2fe87ff8de7e972716ec7e94731897abadaa107d7d3d2321b6"
    ):
        raise SimulationError("reproduced Attempt05 patch topology/position drifted")

    source = verifier.source_snapshot(
        verification_config,
        bpy,
        bmesh,
        preflight_module,
        actions_module,
        exact_module,
        topology,
    )
    target_world = [body.matrix_world @ body.data.vertices[index].co for index in target_cycle]
    donor_order = [int(value) for value in prepared["donor_vertex_order"]]
    donor_start = int(prepared["donor_start"])
    donor_to_local = {
        donor_index: donor_start + offset
        for offset, donor_index in enumerate(donor_order)
    }
    aligned_cycle = [int(value) for value in prepared["donor_boundary_order"]]
    local_donor_boundary = [donor_to_local[index] for index in aligned_cycle]
    base_world = [Vector(tuple(value)) for value in prepared["positions_world"]]
    donor_boundary_world = [base_world[donor_to_local[index]] for index in aligned_cycle]
    target_parameters = author.cycle_parameters([tuple(value) for value in target_world])
    donor_parameters = author.cycle_parameters(
        [tuple(value) for value in donor_boundary_world]
    )
    sampled_target_world = [
        Vector(author.sample_cycle([tuple(value) for value in target_world], target_parameters, fraction))
        for fraction in donor_parameters
    ]

    source_faces = author.preflight_base.faces_of(body)
    selected_incidence: dict[tuple[int, int], list[int]] = defaultdict(list)
    all_incidence: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(source_faces):
        for edge in face_edges(face):
            all_incidence[edge].append(face_index)
            if face_index in selected_faces:
                selected_incidence[edge].append(face_index)
    source_inward_at_vertex: list[Any] = []
    for offset, vertex_index in enumerate(target_cycle):
        previous = target_cycle[(offset - 1) % len(target_cycle)]
        following = target_cycle[(offset + 1) % len(target_cycle)]
        tangent = (
            body.matrix_world @ body.data.vertices[following].co
            - body.matrix_world @ body.data.vertices[previous].co
        )
        incident = [
            face_index
            for face_index in selected_faces
            if vertex_index in source_faces[face_index]
        ]
        weighted_points = []
        weighted_areas = []
        for face_index in incident:
            face = source_faces[face_index]
            points = [body.matrix_world @ body.data.vertices[index].co for index in face]
            centroid = sum(points, Vector()) / len(points)
            area = 0.0
            for triangle_offset in range(1, len(points) - 1):
                area += 0.5 * (
                    points[triangle_offset] - points[0]
                ).cross(points[triangle_offset + 1] - points[0]).length
            weighted_points.append(centroid)
            weighted_areas.append(max(area, 1.0e-15))
        if not weighted_points:
            raise SimulationError("seam vertex lacks an incident selected face")
        total_area = math.fsum(weighted_areas)
        mean = sum(
            (point * (area / total_area) for point, area in zip(weighted_points, weighted_areas)),
            Vector(),
        )
        origin = body.matrix_world @ body.data.vertices[vertex_index].co
        source_inward_at_vertex.append(
            projected_inward(mean - origin, tangent, f"source seam {vertex_index}")
        )
    sampled_source_inward = [
        Vector(
            author.sample_cycle(
                [tuple(value) for value in source_inward_at_vertex],
                target_parameters,
                fraction,
            )
        )
        for fraction in donor_parameters
    ]

    donor_faces = author.preflight_base.faces_of(donor)
    donor_adjacency: dict[int, set[int]] = {index: set() for index in donor_vertices}
    for face_index in donor_disk:
        face = donor_faces[face_index]
        for index, vertex in enumerate(face):
            neighbor = face[(index + 1) % len(face)]
            if vertex in donor_adjacency and neighbor in donor_adjacency:
                donor_adjacency[vertex].add(neighbor)
                donor_adjacency[neighbor].add(vertex)
    boundary_set = set(aligned_cycle)
    donor_inward = []
    for offset, donor_index in enumerate(aligned_cycle):
        previous = aligned_cycle[(offset - 1) % len(aligned_cycle)]
        following = aligned_cycle[(offset + 1) % len(aligned_cycle)]
        tangent = base_world[donor_to_local[following]] - base_world[donor_to_local[previous]]
        neighbors = sorted(donor_adjacency[donor_index].difference(boundary_set))
        graph_distance = 1
        if not neighbors:
            seen = {donor_index}
            frontier = {donor_index}
            while frontier and not neighbors:
                next_frontier = {
                    neighbor
                    for current in frontier
                    for neighbor in donor_adjacency[current]
                    if neighbor not in seen
                }
                seen.update(next_frontier)
                graph_distance += 1
                neighbors = sorted(next_frontier.difference(boundary_set))
                frontier = next_frontier
        if not neighbors:
            raise SimulationError("donor boundary component lacks an interior vertex")
        mean = sum(
            (base_world[donor_to_local[index]] for index in neighbors), Vector()
        ) / len(neighbors)
        donor_inward.append(
            projected_inward(
                mean - base_world[donor_to_local[donor_index]],
                tangent,
                f"donor boundary {donor_index}",
            )
        )

    retained_directed_edges = []
    source_to_local = {vertex: offset for offset, vertex in enumerate(target_cycle)}
    for offset, first in enumerate(target_cycle):
        second = target_cycle[(offset + 1) % len(target_cycle)]
        edge = tuple(sorted((first, second)))
        retained = [value for value in all_incidence[edge] if value not in selected_faces]
        if len(retained) != 1:
            raise SimulationError("source seam edge lacks one retained face")
        face = source_faces[retained[0]]
        directed = None
        for corner, value in enumerate(face):
            next_value = face[(corner + 1) % len(face)]
            if {value, next_value} == {first, second}:
                directed = (source_to_local[value], source_to_local[next_value])
                break
        if directed is None:
            raise SimulationError("retained seam direction was not found")
        retained_directed_edges.append(directed)

    return {
        "body": body,
        "rig": rig,
        "donor": donor,
        "preflight": preflight,
        "source_snapshot": source,
        "selected_faces": selected_faces,
        "target_cycle": target_cycle,
        "prepared": prepared,
        "base_world": base_world,
        "sampled_target_world": sampled_target_world,
        "sampled_source_inward": sampled_source_inward,
        "donor_inward": donor_inward,
        "donor_boundary_world": donor_boundary_world,
        "local_donor_boundary": local_donor_boundary,
        "donor_memberships": {
            str(name): {int(value) for value in values}
            for name, values in memberships.items()
        },
        "retained_directed_edges": retained_directed_edges,
    }


def build_uv_fields(
    design: Mapping[str, Any], repair_core: Any
) -> tuple[dict[str, list[tuple[float, float]]], dict[str, Any]]:
    prepared = design["prepared"]
    target_cycle = design["target_cycle"]
    target_count = len(target_cycle)
    collar_size = int(prepared["collar_ring_size"])
    donor_start = int(prepared["donor_start"])
    transition_nodes = set(range(target_count, donor_start)).union(
        design["local_donor_boundary"]
    ).union(range(target_count))
    adjacency: dict[int, set[int]] = {index: set() for index in transition_nodes}
    for face in prepared["faces"]:
        for edge in face_edges(face):
            if edge[0] in transition_nodes and edge[1] in transition_nodes:
                adjacency[edge[0]].add(edge[1])
                adjacency[edge[1]].add(edge[0])
    fields: dict[str, list[tuple[float, float]]] = {}
    evidence: dict[str, Any] = {}
    source = design["source_snapshot"]
    for layer_name, base_field in sorted(prepared["uv_fields"].items()):
        candidates = [
            source["seam"][vertex]["uv"][layer_name]
            for vertex in target_cycle
        ]
        chosen = repair_core.minimum_variation_closed_cycle_choices(candidates)
        fixed = {index: chosen[index] for index in range(target_count)}
        for local_index in design["local_donor_boundary"]:
            fixed[int(local_index)] = tuple(map(float, base_field[int(local_index)]))
        solved = repair_core.harmonic_interpolate_boundary_field(
            adjacency, fixed, tolerance=1.0e-12
        )
        field = [tuple(map(float, value)) for value in base_field]
        for local_index, value in solved.items():
            field[int(local_index)] = tuple(map(float, value))
        fields[layer_name] = field
        exact_errors = [
            min(
                math.dist(field[index], tuple(map(float, candidate)))
                for candidate in candidates[index]
            )
            for index in range(target_count)
        ]
        evidence[layer_name] = {
            "chosen_exact_cycle_sha256": canonical_sha256(chosen),
            "maximum_exact_choice_error": max(exact_errors, default=0.0),
            "transition_node_count": len(transition_nodes),
            "outer_boundary_count": target_count,
            "donor_boundary_count": len(design["local_donor_boundary"]),
            "collar_ring_size": collar_size,
        }
    return fields, evidence


def build_weight_field(
    design: Mapping[str, Any], repair_core: Any
) -> tuple[dict[int, dict[str, float]], dict[str, Any]]:
    prepared = design["prepared"]
    target_cycle = design["target_cycle"]
    target_count = len(target_cycle)
    node_count = len(prepared["positions_body_local"])
    adjacency: dict[int, set[int]] = {index: set() for index in range(node_count)}
    patch_edges = set()
    for face in prepared["faces"]:
        for edge in face_edges(face):
            adjacency[edge[0]].add(edge[1])
            adjacency[edge[1]].add(edge[0])
            patch_edges.add(edge)
    source = design["source_snapshot"]
    seam_weights = [source["seam"][vertex]["weights"] for vertex in target_cycle]
    group_names = sorted(set().union(*(weights.keys() for weights in seam_weights)))
    boundary = {
        index: tuple(float(seam_weights[index].get(name, 0.0)) for name in group_names)
        for index in range(target_count)
    }
    dense = repair_core.harmonic_interpolate_boundary_field(
        adjacency, boundary, tolerance=1.0e-12
    )
    complete = {
        index: (
            dict(seam_weights[index])
            if index < target_count
            else repair_core.project_top_four_normalized_weights(
                {
                    name: dense[index][offset]
                    for offset, name in enumerate(group_names)
                }
            )
        )
        for index in range(node_count)
    }
    new_weights = {
        index: complete[index] for index in range(target_count, node_count)
    }
    patch_deltas = [
        weight_distance(complete[first], complete[second])
        for first, second in patch_edges
    ]

    source_faces = design["source_snapshot"]["topology"]
    del source_faces  # The exact source edge envelope is built from the selected mesh below.
    body = design["body"]
    author_faces = [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]
    source_edges = set()
    for face_index in design["selected_faces"]:
        source_edges.update(face_edges(author_faces[face_index]))
    source_deltas = [
        weight_distance(
            {group.group: group.weight for group in body.data.vertices[first].groups},
            {group.group: group.weight for group in body.data.vertices[second].groups},
        )
        for first, second in source_edges
    ]
    # The object-level group indices are converted to names below for an exact
    # comparison; the numeric result above is intentionally discarded.
    source_named = {
        int(vertex.index): {
            body.vertex_groups[int(item.group)].name: float(item.weight)
            for item in vertex.groups
            if float(item.weight) > 0.0
        }
        for vertex in body.data.vertices
    }
    source_deltas = [
        weight_distance(source_named[first], source_named[second])
        for first, second in source_edges
    ]
    source_p99 = percentile(source_deltas, 0.99)
    source_maximum = max(source_deltas, default=0.0)
    patch_p99 = percentile(patch_deltas, 0.99)
    patch_maximum = max(patch_deltas, default=0.0)
    sums = [math.fsum(value.values()) for value in complete.values()]
    counts = [len(value) for value in complete.values()]
    checks = {
        "finite_nonnegative": all(
            math.isfinite(weight) and weight >= 0.0
            for values in complete.values()
            for weight in values.values()
        ),
        "maximum_four": max(counts, default=0) <= 4,
        "normalized": min(sums, default=0.0) >= 0.999999
        and max(sums, default=0.0) <= 1.000001,
        "patch_p99_not_above_r19_selected_p99": patch_p99 <= source_p99 + 1.0e-12,
        "patch_max_not_above_r19_selected_max": patch_maximum
        <= source_maximum + 1.0e-12,
    }
    return new_weights, {
        "native_boundary_group_names": group_names,
        "patch_edge_count": len(patch_edges),
        "r19_selected_edge_count": len(source_edges),
        "r19_selected_weight_delta_p99": source_p99,
        "r19_selected_weight_delta_maximum": source_maximum,
        "patch_weight_delta_p99": patch_p99,
        "patch_weight_delta_maximum": patch_maximum,
        "minimum_weight_sum": min(sums, default=0.0),
        "maximum_weight_sum": max(sums, default=0.0),
        "maximum_positive_count": max(counts, default=0),
        "checks": checks,
        "passed": all(checks.values()),
        "new_weight_sha256": canonical_sha256(new_weights),
    }


def variant_positions(
    design: Mapping[str, Any],
    outer_scale: float,
    donor_scale: float,
    clearance: float,
    repair_core: Any,
) -> tuple[list[tuple[float, float, float]], dict[str, Any]]:
    from mathutils import Vector

    body = design["body"]
    prepared = design["prepared"]
    target_count = len(design["target_cycle"])
    collar_size = int(prepared["collar_ring_size"])
    inverse = body.matrix_world.inverted()
    outward = Vector(
        tuple(
            design["preflight"]["donor_to_r19_projection"]["target_axes_world"][
                "outward"
            ]
        )
    ).normalized()
    positions = [tuple(map(float, value)) for value in prepared["positions_body_local"]]
    endpoint_rows = []
    for offset, (outer, donor) in enumerate(
        zip(design["sampled_target_world"], design["donor_boundary_world"])
    ):
        gap = float((donor - outer).length)
        if gap <= 1.0e-10:
            raise SimulationError("collar endpoints are degenerate")
        raw_outer = design["sampled_source_inward"][offset]
        raw_donor = design["donor_inward"][offset]
        outer_length = min(3.0 * outer_scale * raw_outer.length, 1.25 * gap)
        donor_length = min(3.0 * donor_scale * raw_donor.length, 1.25 * gap)
        outer_tangent = raw_outer.normalized() * outer_length
        donor_tangent = raw_donor.normalized() * donor_length
        for ring_offset, fraction in enumerate((1.0 / 3.0, 2.0 / 3.0)):
            sample = repair_core.cubic_hermite_collar_sample(
                tuple(outer),
                tuple(outer_tangent),
                tuple(donor),
                tuple(donor_tangent),
                fraction,
            )
            bump = 16.0 * fraction**2 * (1.0 - fraction) ** 2
            world = Vector(sample.point) + outward * (clearance * bump)
            local_index = target_count + ring_offset * collar_size + offset
            positions[local_index] = tuple(inverse @ world)
        endpoint_rows.append(
            {
                "gap_m": gap,
                "outer_tangent_m": outer_length,
                "donor_tangent_m": donor_length,
            }
        )
    return positions, {
        "minimum_endpoint_gap_m": min(row["gap_m"] for row in endpoint_rows),
        "maximum_endpoint_gap_m": max(row["gap_m"] for row in endpoint_rows),
        "maximum_outer_tangent_m": max(row["outer_tangent_m"] for row in endpoint_rows),
        "maximum_donor_tangent_m": max(row["donor_tangent_m"] for row in endpoint_rows),
        "position_sha256": canonical_sha256(positions),
    }


def uv_geometry_metrics(
    body: Any, patch_faces: set[int], layer_name: str
) -> dict[str, Any]:
    layer = body.data.uv_layers.get(layer_name)
    if layer is None:
        raise SimulationError(f"candidate lacks UV layer {layer_name}")
    signed = []
    for face_index in patch_faces:
        polygon = body.data.polygons[face_index]
        if len(polygon.loop_indices) < 3:
            raise SimulationError("replacement patch face has fewer than three loops")
        values = [layer.data[index].uv for index in polygon.loop_indices]
        area = 0.5 * math.fsum(
            values[index].x * values[(index + 1) % len(values)].y
            - values[(index + 1) % len(values)].x * values[index].y
            for index in range(len(values))
        )
        signed.append(float(area))
    nonzero = [value for value in signed if abs(value) > 1.0e-14]
    positive = sum(value > 0.0 for value in nonzero)
    negative = sum(value < 0.0 for value in nonzero)
    dominant_positive = positive >= negative
    opposite = sum((value < 0.0) if dominant_positive else (value > 0.0) for value in nonzero)
    return {
        "face_count": len(signed),
        "zero_area_count_at_1e_14": len(signed) - len(nonzero),
        "positive_count": positive,
        "negative_count": negative,
        "opposite_dominant_sign_count": opposite,
        "minimum_absolute_area": min((abs(value) for value in signed), default=0.0),
    }


def cheap_pose_stretch(
    config: Mapping[str, Any],
    body: Any,
    rig: Any,
    patch_faces: set[int],
    seam_cycle: Sequence[int],
    verifier: Any,
    topology: Any,
    bpy: Any,
) -> dict[str, Any]:
    faces = [tuple(map(int, polygon.vertices)) for polygon in body.data.polygons]
    patch_edges = {
        edge
        for face_index in patch_faces
        for edge in topology.face_edges(faces[face_index])
    }
    seam_edges = {
        tuple(sorted((seam_cycle[index], seam_cycle[(index + 1) % len(seam_cycle)])))
        for index in range(len(seam_cycle))
    }
    verifier.apply_pose(rig, {})
    bpy.context.view_layer.update()
    neutral = verifier.evaluated_points(body, bpy)
    neutral_patch = verifier.edge_lengths(neutral, patch_edges)
    new_patch_edges = patch_edges.difference(seam_edges)
    neutral_new_patch = verifier.edge_lengths(neutral, new_patch_edges)
    neutral_seam = verifier.edge_lengths(neutral, seam_edges)
    rows = {}
    for pose in config["poses"]:
        verifier.apply_pose(rig, pose["rotations_degrees"])
        bpy.context.view_layer.update()
        points = verifier.evaluated_points(body, bpy)
        patch_ratio = verifier.ratio_maximum(
            verifier.edge_lengths(points, patch_edges), neutral_patch
        )
        new_patch_ratio = verifier.ratio_maximum(
            verifier.edge_lengths(points, new_patch_edges), neutral_new_patch
        )
        seam_ratio = verifier.ratio_maximum(
            verifier.edge_lengths(points, seam_edges), neutral_seam
        )
        rows[pose["id"]] = {
            "maximum_patch_edge_stretch_ratio": patch_ratio,
            "maximum_new_patch_edge_stretch_ratio": new_patch_ratio,
            "maximum_seam_edge_stretch_ratio": seam_ratio,
        }
    verifier.apply_pose(rig, {})
    bpy.context.view_layer.update()
    return rows


def broad_patch_pairs(
    body: Any, patch_faces: set[int], verifier: Any, exact_module: Any, bpy: Any, bmesh: Any
) -> dict[str, Any]:
    bm = verifier.evaluated_bmesh(body, bpy, bmesh)
    try:
        pairs = exact_module.bvh_nonadjacent_face_pairs(bm)
    finally:
        bm.free()
    patch_pairs = sorted(
        [list(pair) for pair in pairs if any(index in patch_faces for index in pair)]
    )
    return {
        "all_nonadjacent_bvh_pair_count": len(pairs),
        "patch_involving_bvh_pair_count": len(patch_pairs),
        "patch_involving_bvh_pair_sha256": canonical_sha256(patch_pairs),
    }


def run_variant(
    variant: Mapping[str, Any],
    positions: Sequence[Sequence[float]],
    design: Mapping[str, Any],
    author_config: Mapping[str, Any],
    verification_config: Mapping[str, Any],
    repair_overlay: Mapping[str, Any],
    uv_fields: Mapping[str, Any],
    new_weights: Mapping[int, Mapping[str, float]],
    modules: Mapping[str, Any],
    *,
    exact_neutral: bool,
    exact_poses: bool,
) -> dict[str, Any]:
    bpy = modules["bpy"]
    author = modules["author"]
    attempt04 = modules["attempt04"]
    verifier = modules["verifier"]
    topology = modules["topology"]
    exact_module = modules["exact_module"]
    bmesh = modules["bmesh"]
    body = design["body"]
    rig = design["rig"]
    source_mesh = modules["source_mesh"]
    source_name = verification_config["objects"]["r19_body"]
    source_data_name = modules["source_data_name"]
    original_properties = modules["source_properties"]
    base_materials = modules["base_materials"]
    variant_mesh = source_mesh.copy()
    body.data = variant_mesh
    body.name = source_name
    variant_mesh.name = f"__R23_SIMULATION_{variant['id']}"
    attempt04.bind_attempt04_runtime(repair_overlay)
    attempt04.RUNTIME["donor_memberships"] = {
        str(name): {int(value) for value in values}
        for name, values in design["donor_memberships"].items()
    }
    prepared = dict(design["prepared"])
    prepared["positions_body_local"] = [tuple(map(float, value)) for value in positions]
    prepared["uv_fields"] = deepcopy(dict(uv_fields))
    prepared["new_weights"] = deepcopy(dict(new_weights))
    prepared["position_sha256"] = canonical_sha256(prepared["positions_body_local"])
    prepared["uv_sha256"] = canonical_sha256(prepared["uv_fields"])
    prepared["weight_sha256"] = canonical_sha256(prepared["new_weights"])
    try:
        verifier.suspend_rig_action(rig)
        verifier.apply_pose(rig, {})
        bpy.context.scene.frame_set(0)
        bpy.context.view_layer.update()
        applied = attempt04.attempt04_apply_patch(
            body,
            rig,
            design["selected_faces"],
            design["target_cycle"],
            prepared,
            author_config,
        )
        patch_faces = {int(value) for value in applied["patch_face_indices"]}
        topology_result = attempt04.attempt04_topology_gate(
            body, applied["patch_face_indices"], author_config
        )
        freeze = author.post_author_freeze_gate(
            body,
            rig,
            design["target_cycle"],
            applied["target_seam_global_indices"],
            design["preflight"],
        )
        body.data.update(calc_edges=True, calc_edges_loose=True)
        bpy.context.view_layer.update()
        continuity = verifier.seam_continuity(
            body,
            design["source_snapshot"],
            patch_faces,
            topology,
            verification_config["continuity_thresholds"],
        )
        weights = verifier.patch_weights(
            body,
            patch_faces,
            verification_config["expected_candidate_structure"],
            bpy,
        )
        uv_metrics = {
            layer_name: uv_geometry_metrics(body, patch_faces, layer_name)
            for layer_name in uv_fields
        }
        degenerate_faces = [
            int(index)
            for index in patch_faces
            if float(body.data.polygons[index].area) <= 1.0e-14
        ]
        broad = broad_patch_pairs(
            body, patch_faces, verifier, exact_module, bpy, bmesh
        )
        pose_stretch = cheap_pose_stretch(
            verification_config,
            body,
            rig,
            patch_faces,
            applied["target_seam_global_indices"],
            verifier,
            topology,
            bpy,
        )
        worst_patch_stretch = max(
            row["maximum_new_patch_edge_stretch_ratio"] for row in pose_stretch.values()
        )
        normal_failures = sum(
            1
            for row in continuity.get("normal_dots", [])
            if row < verification_config["continuity_thresholds"]["minimum_patch_retained_normal_dot"]
        )
        # seam_continuity exposes only the minimum; use a binary hard count here.
        if not continuity["checks"]["normal_continuity"]:
            normal_failures = max(1, normal_failures)
        hard_checks = {
            "topology": all(topology_result["checks"].values()),
            "freeze": all(freeze["checks"].values()),
            "seam_position_weight_tangent_uv_normal": all(
                continuity["checks"].values()
            ),
            "patch_weights": bool(weights["passed"]),
            "nondegenerate_patch_triangles": not degenerate_faces,
            "new_patch_pose_stretch_at_or_below_1_35": worst_patch_stretch
            <= verification_config["continuity_thresholds"]["maximum_pose_patch_edge_stretch_ratio"],
            "uv_nonzero_area": all(
                row["zero_area_count_at_1e_14"] == 0 for row in uv_metrics.values()
            ),
        }
        row: dict[str, Any] = {
            "id": variant["id"],
            "parameters": dict(variant),
            "prepared_hashes": {
                "topology_sha256": prepared["topology_sha256"],
                "position_sha256": prepared["position_sha256"],
                "uv_sha256": prepared["uv_sha256"],
                "weight_sha256": prepared["weight_sha256"],
            },
            "topology_checks": topology_result["checks"],
            "freeze_checks": freeze["checks"],
            "continuity": continuity,
            "patch_weights": weights,
            "uv_geometry": uv_metrics,
            "degenerate_patch_face_count": len(degenerate_faces),
            "broad_phase": broad,
            "pose_stretch": pose_stretch,
            "worst_patch_edge_stretch_ratio": worst_patch_stretch,
            "normal_failure_count_at_0_7": normal_failures,
            "hard_checks": hard_checks,
            "hard_gate_fail_count": sum(not value for value in hard_checks.values()),
        }
        if exact_neutral or exact_poses:
            exact = verifier.exact_intersections(body, bpy, bmesh, exact_module)
            candidate_pairs = {tuple(value) for value in exact["genuine_index_pairs"]}
            patch_pairs = sorted(
                [list(pair) for pair in candidate_pairs if any(index in patch_faces for index in pair)]
            )
            source_pairs = Counter(
                tuple(value)
                for value in design["source_snapshot"]["exact_intersections"]["genuine_geometry_pairs"]
            )
            candidate_geometry = Counter(
                tuple(value) for value in exact["genuine_geometry_pairs"]
            )
            new_geometry = candidate_geometry - source_pairs
            neutral_checks = {
                "candidate_not_above_inherited_29": len(candidate_pairs)
                <= verification_config["inherited_r19_baseline"]["neutral_exact_genuine_nonadjacent_intersection_pair_count"],
                "zero_new_geometry_pairs": not new_geometry,
                "zero_patch_involving_pairs": not patch_pairs,
            }
            row["exact_neutral"] = {
                "genuine_pair_count": len(candidate_pairs),
                "genuine_geometry_pair_sha256": exact["genuine_geometry_pair_sha256"],
                "new_geometry_pair_count": sum(new_geometry.values()),
                "new_geometry_pair_sha256": canonical_sha256(
                    sorted(new_geometry.elements())
                ),
                "patch_involving_pair_count": len(patch_pairs),
                "patch_involving_pairs": patch_pairs,
                "checks": neutral_checks,
                "passed": all(neutral_checks.values()),
            }
            if exact_poses:
                poses, _points = verifier.deformation_series(
                    verification_config,
                    body,
                    rig,
                    patch_faces,
                    applied["target_seam_global_indices"],
                    exact,
                    bpy,
                    bmesh,
                    exact_module,
                    topology,
                )
                condensed = {}
                for pose_id, pose in poses.items():
                    repairable_checks = dict(pose["checks"])
                    inherited_gate = repairable_checks.pop("seam_edge_stretch_bounded")
                    repairable_checks.pop("patch_edge_stretch_bounded")
                    repairable_checks["new_patch_edge_stretch_bounded"] = (
                        pose_stretch[pose_id]["maximum_new_patch_edge_stretch_ratio"]
                        <= verification_config["continuity_thresholds"]["maximum_pose_patch_edge_stretch_ratio"]
                    )
                    condensed[pose_id] = {
                        "exact_genuine_pair_count": pose["exact_genuine_pair_count"],
                        "new_exact_pair_count": len(pose["new_exact_pairs_vs_candidate_neutral"]),
                        "patch_involving_pair_count": len(pose["patch_involving_exact_pairs"]),
                        "maximum_patch_edge_stretch_ratio": pose["maximum_patch_edge_stretch_ratio"],
                        "maximum_new_patch_edge_stretch_ratio": pose_stretch[pose_id]["maximum_new_patch_edge_stretch_ratio"],
                        "maximum_seam_edge_stretch_ratio": pose["maximum_seam_edge_stretch_ratio"],
                        "repairable_checks": repairable_checks,
                        "repairable_passed": all(repairable_checks.values()),
                        "legacy_absolute_seam_gate_passed": inherited_gate,
                        "contact_proxy": pose["contact_proxy"],
                    }
                row["exact_pose_series"] = condensed
                row["all_repairable_pose_gates_passed"] = all(
                    value["repairable_passed"] for value in condensed.values()
                )
        return row
    finally:
        verifier.apply_pose(rig, {})
        bpy.context.view_layer.update()
        modified_mesh = body.data
        body.data = source_mesh
        body.name = source_name
        source_mesh.name = source_data_name
        for key in list(body.keys()):
            if key not in original_properties:
                del body[key]
        for key, value in original_properties.items():
            body[key] = value
        if modified_mesh != source_mesh and modified_mesh.name in bpy.data.meshes:
            bpy.data.meshes.remove(modified_mesh)
        for material in list(bpy.data.materials):
            if material not in base_materials and material.users == 0:
                bpy.data.materials.remove(material)
        attempt04.RUNTIME.clear()


def run(config_path: Path, explicit_execution: bool) -> int:
    if not explicit_execution:
        raise SimulationError(f"explicit {EXECUTION_FLAG} flag is required")
    config = read_json(config_path)
    if config.get("status") != BOUND_STATUS:
        raise SimulationError("simulation config status drifted")
    bindings = {
        label: require_binding(binding, label)
        for label, binding in config["bindings"].items()
    }
    if bindings["worker"].resolve() != Path(__file__).resolve():
        raise SimulationError("configured worker is not the executing worker")
    restrictions = config["execution_restrictions"]
    for key in (
        "blend_save_forbidden",
        "render_forbidden",
        "export_forbidden",
        "runtime_mutation_forbidden",
        "activation_assignment_publication_forbidden",
    ):
        if restrictions.get(key) is not True:
            raise SimulationError(f"execution restriction weakened: {key}")
    output_dir = project_path(config["output"]["directory"])
    output_path = output_dir / config["output"]["filename"]
    if output_dir.exists():
        raise SimulationError("append-only simulation output already exists")
    source_path = bindings["r19_source"]
    candidate_path = bindings["attempt05_candidate"]
    before = {
        "r19_source": {"bytes": source_path.stat().st_size, "sha256": sha256_file(source_path)},
        "attempt05_candidate": {"bytes": candidate_path.stat().st_size, "sha256": sha256_file(candidate_path)},
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        import bmesh
        import bpy
        from tools import blender_author_kira_r23_cc0_afes_attempt01 as author
        from tools import blender_author_kira_r23_cc0_afes_attempt04_wrapper as attempt04
        from tools import blender_exact_mesh_intersections as exact_module
        from tools import blender_preflight_kira_r23_cc0_afes_expanded_mask as preflight_module
        from tools import blender_verify_kira_r23_postsave_fresh_reopen as verifier
        from tools import kira_r23_blender51_action_serializer as actions_module
        from tools import kira_r23_cc0_afes_preflight_core as topology
        from tools import kira_r23_localized_patch_repair_core as repair_core

        if bpy.data.filepath:
            raise SimulationError("simulation did not start factory-empty")
        author_config = read_json(bindings["author_config"])
        verification_config = read_json(bindings["verification_config"])
        repair_overlay = read_json(bindings["attempt05_repair_overlay"])
        design = capture_design(
            author_config,
            verification_config,
            repair_overlay,
            bpy,
            bmesh,
            author,
            attempt04,
            verifier,
            preflight_module,
            actions_module,
            exact_module,
            topology,
        )
        oriented = repair_core.orient_disk_faces_from_retained_boundary(
            design["prepared"]["faces"], design["retained_directed_edges"]
        )
        orientation_gate = {
            "face_count": len(oriented.faces),
            "boundary_edge_count": oriented.boundary_edge_count,
            "flipped_face_count": len(oriented.flipped_face_indices),
            "accepted_faces_unchanged": list(oriented.faces)
            == [tuple(face) for face in design["prepared"]["faces"]],
        }
        if not orientation_gate["accepted_faces_unchanged"]:
            raise SimulationError("accepted Attempt05 winding is not boundary-consistent")

        uv_fields, uv_evidence = build_uv_fields(design, repair_core)
        new_weights, weight_evidence = build_weight_field(design, repair_core)
        if not weight_evidence["passed"]:
            raise SimulationError(
                f"harmonic weight field failed immutable-source envelope: {weight_evidence['checks']}"
            )

        donor = design["donor"]
        donor_name = donor.name
        bpy.data.objects.remove(donor, do_unlink=True)
        if bpy.data.objects.get(donor_name) is not None:
            raise SimulationError("qualified donor remained after design capture")
        design["donor"] = None

        body = design["body"]
        modules = {
            "bpy": bpy,
            "bmesh": bmesh,
            "author": author,
            "attempt04": attempt04,
            "verifier": verifier,
            "topology": topology,
            "exact_module": exact_module,
            "source_mesh": body.data,
            "source_data_name": body.data.name,
            "source_properties": {key: body[key] for key in body.keys()},
            "base_materials": set(bpy.data.materials),
        }
        variants = []
        position_fields = {}
        for outer_scale in config["parameter_grid"]["outer_scale"]:
            for donor_scale in config["parameter_grid"]["donor_scale"]:
                for clearance in config["parameter_grid"]["clearance_m"]:
                    variant_id = (
                        f"o{float(outer_scale):.2f}_d{float(donor_scale):.2f}_"
                        f"c{float(clearance):.4f}"
                    )
                    variant = {
                        "id": variant_id,
                        "outer_scale": float(outer_scale),
                        "donor_scale": float(donor_scale),
                        "clearance_m": float(clearance),
                    }
                    positions, position_evidence = variant_positions(
                        design,
                        float(outer_scale),
                        float(donor_scale),
                        float(clearance),
                        repair_core,
                    )
                    position_fields[variant_id] = positions
                    row = run_variant(
                        variant,
                        positions,
                        design,
                        author_config,
                        verification_config,
                        repair_overlay,
                        uv_fields,
                        new_weights,
                        modules,
                        exact_neutral=False,
                        exact_poses=False,
                    )
                    row["collar_geometry"] = position_evidence
                    variants.append(row)

        def stage_a_rank(row: Mapping[str, Any]) -> tuple[Any, ...]:
            parameters = row["parameters"]
            return (
                int(row["hard_gate_fail_count"]),
                int(row["broad_phase"]["patch_involving_bvh_pair_count"]),
                int(row["normal_failure_count_at_0_7"]),
                -float(row["continuity"]["minimum_patch_retained_normal_dot"]),
                float(row["worst_patch_edge_stretch_ratio"]),
                float(weight_evidence["patch_weight_delta_maximum"]),
                float(parameters["clearance_m"]),
                abs(float(parameters["outer_scale"]) - 1.0)
                + abs(float(parameters["donor_scale"]) - 1.0),
                str(row["id"]),
            )

        shortlist_ids = [row["id"] for row in sorted(variants, key=stage_a_rank)[:6]]
        neutral_rows = []
        variant_by_id = {row["id"]: row["parameters"] for row in variants}
        for variant_id in shortlist_ids:
            neutral_rows.append(
                run_variant(
                    variant_by_id[variant_id],
                    position_fields[variant_id],
                    design,
                    author_config,
                    verification_config,
                    repair_overlay,
                    uv_fields,
                    new_weights,
                    modules,
                    exact_neutral=True,
                    exact_poses=False,
                )
            )
        neutral_passers = [
            row for row in neutral_rows if row.get("exact_neutral", {}).get("passed")
        ]
        neutral_passers.sort(key=stage_a_rank)
        pose_rows = []
        for row in neutral_passers[:2]:
            variant_id = row["id"]
            pose_rows.append(
                run_variant(
                    variant_by_id[variant_id],
                    position_fields[variant_id],
                    design,
                    author_config,
                    verification_config,
                    repair_overlay,
                    uv_fields,
                    new_weights,
                    modules,
                    exact_neutral=True,
                    exact_poses=True,
                )
            )
        eligible = [
            row
            for row in pose_rows
            if row.get("exact_neutral", {}).get("passed")
            and row.get("all_repairable_pose_gates_passed") is True
            and row["hard_gate_fail_count"] == 0
        ]
        eligible.sort(key=stage_a_rank)
        selected = eligible[0]["id"] if eligible else None
        legacy_source = read_json(bindings["root_cause_metrics"])[
            "r19_exact_seam_pose_stretch"
        ]
        after = {
            "r19_source": {"bytes": source_path.stat().st_size, "sha256": sha256_file(source_path)},
            "attempt05_candidate": {"bytes": candidate_path.stat().st_size, "sha256": sha256_file(candidate_path)},
        }
        if before != after:
            raise SimulationError("bound source or Attempt05 candidate changed")
        status = (
            "LOCALIZED_PATCH_REPAIR_ELIGIBLE_FULL_ACCEPTANCE_STILL_BLOCKED_BY_INHERITED_R19_SEAM_GATE"
            if selected
            else "NO_VARIANT_PASSED_ALL_LOCALIZED_REPAIRABLE_GATES"
        )
        result = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_LOCALIZED_PATCH_REPAIR_READONLY_SIMULATION",
            "created_utc": utc_now(),
            "status": status,
            "selected_variant_id": selected,
            "bindings": {
                label: {
                    "path": relative(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for label, path in bindings.items()
            },
            "orientation_gate": orientation_gate,
            "uv_preparation": uv_evidence,
            "weight_preparation": weight_evidence,
            "stage_a_all_variants": variants,
            "stage_b_neutral_exact_shortlist_ids": shortlist_ids,
            "stage_b_neutral_exact_results": neutral_rows,
            "stage_c_full_pose_results": pose_rows,
            "inherited_r19_absolute_seam_gate": {
                "status": "INHERITED_SOURCE_ABSOLUTE_GATE_FAIL",
                "threshold": verification_config["continuity_thresholds"]["maximum_pose_seam_edge_stretch_ratio"],
                "source_measurements": legacy_source,
                "cannot_be_repaired_by_collar_uv_or_patch_weight_change_while_seam_and_rig_remain_exact": True,
            },
            "immutability": {
                "before": before,
                "after": after,
                "unchanged": before == after,
            },
            "operations": {
                "blend_saved": False,
                "render_performed": False,
                "export_performed": False,
                "runtime_or_person_state_mutated": False,
                "author_candidate_path_created": False,
                "append_only_json_written": True,
            },
            "truth_boundary": [
                "This is engineering simulation evidence, not owner visual approval.",
                "It can validate external topology, UV, weights, intersections, deformation, and contact proxies only.",
                "It does not implement or prove internal urinary, bowel, reproductive, pregnancy, pelvic-floor, continence, subjective sensation, privacy-memory, or biological function.",
            ],
        }
        with output_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(
            json.dumps(
                {
                    "status": status,
                    "selected_variant_id": selected,
                    "stage_a_variants": len(variants),
                    "stage_b_exact": len(neutral_rows),
                    "stage_c_pose": len(pose_rows),
                    "output": relative(output_path),
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception:
        failure_path = output_dir / "FAILURE_EVIDENCE.json"
        failure = {
            "schema_version": 1,
            "artifact_kind": "KIRA_R23_LOCALIZED_PATCH_REPAIR_READONLY_SIMULATION_FAILURE",
            "created_utc": utc_now(),
            "exception_type": type(sys.exc_info()[1]).__name__,
            "exception": str(sys.exc_info()[1]),
            "traceback": traceback.format_exc(),
            "operations": {
                "blend_saved": False,
                "render_performed": False,
                "export_performed": False,
                "runtime_or_person_state_mutated": False,
            },
        }
        with failure_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(failure, handle, indent=2, sort_keys=True)
            handle.write("\n")
        raise


def main() -> int:
    args = arguments()
    return run(project_path(args.config), bool(getattr(args, "execute_readonly_simulation")))


if __name__ == "__main__":
    raise SystemExit(main())
