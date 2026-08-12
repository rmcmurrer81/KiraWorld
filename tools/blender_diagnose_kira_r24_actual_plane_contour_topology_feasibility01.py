"""One-shot read-only actual-plane contour topology feasibility diagnostic.

This lane consumes the failed uniform and fixed-carrier nonuniform R24
families.  It changes only the carrier-cycle topology: the exact previously
selected chart-normal plane is intersected with every triangle of the sealed
73-face E-star collar without endpoint clamping.  The module is safe to import
outside Blender; ``bpy`` is imported only by :func:`run` after all static and
runtime claims have been verified.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import argparse
import hashlib
import heapq
import importlib.util
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Iterable, Sequence


sys.dont_write_bytecode = True
THIS_FILE = Path(__file__).resolve()
TOOLS = THIS_FILE.parent
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from r24_local_transition_canonical_inventory import (  # noqa: E402
    canonical_inventory,
    sha256_file,
)


PARENT_WORKER = TOOLS / "blender_diagnose_kira_r24_nonuniform_source_edge_feasibility01.py"
_SPEC = importlib.util.spec_from_file_location("r24_actual_plane_parent", PARENT_WORKER)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load preserved nonuniform feasibility worker")
_PARENT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PARENT)
_BASE = _PARENT._BASE

DEFAULT_CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_actual_plane_contour_topology_feasibility_01_static/"
    "ACTUAL_PLANE_CONTOUR_TOPOLOGY_FEASIBILITY01_CONFIG.json"
)

FAILURE_ORDER = (
    "input_topology_identity",
    "consumed_nonuniform_identity",
    "target_plane_vertex_or_edge_degeneracy",
    "collar_triangle_crossing_count",
    "complete_two_collar_face_edge_ownership",
    "exact_owner_opposite_provenance",
    "single_component_d2_envelope_separation",
    "chart_frame_validity",
    "projected_simplicity_one_disk",
    "boundary_angle_gate",
    "chart_deviation_gate",
    "global_seam_disjointness",
    "exterior_adjacent_face_preservation",
)


def compact_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def compact_sha256(value: object) -> str:
    return hashlib.sha256(compact_json(value)).hexdigest()


def project_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError(f"path escapes project root: {relative}") from exc
    return path


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_binding(name: str, binding: dict[str, object]) -> dict[str, object]:
    path = project_path(str(binding["path"]))
    if not path.is_file():
        raise RuntimeError(f"immutable binding absent: {name}")
    actual = {
        "path": str(binding["path"]),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if actual["bytes"] != int(binding["bytes"]) or actual["sha256"] != binding["sha256"]:
        raise RuntimeError(f"immutable binding drifted: {name}")
    return actual


def parent_config(config: dict[str, object]) -> dict[str, object]:
    binding = config["immutable_bindings"]["parent_nonuniform_config"]
    verify_binding("parent_nonuniform_config", binding)
    return json.loads(project_path(str(binding["path"])).read_text(encoding="utf-8"))


def consumed_nonuniform_result(config: dict[str, object]) -> dict[str, object]:
    binding = config["immutable_bindings"]["consumed_nonuniform_diagnostic"]
    verify_binding("consumed_nonuniform_diagnostic", binding)
    result = json.loads(project_path(str(binding["path"])).read_text(encoding="utf-8"))
    proposed = result.get("proposed_record") or {}
    summary = result.get("solver_summary") or {}
    expected = config["consumed_result"]
    if (
        result.get("schema")
        != "kira.avatar.r24.nonuniform_source_edge_feasibility.v1"
        or result.get("status") != "NO_ELIGIBLE_NONUNIFORM_RECORD_FAIL_CLOSED"
        or summary.get("generated_record_count") != 192
        or summary.get("eligible_record_count") != 0
        or summary.get("proposed_record_origin") != "plane_sample_112_of_190"
        or proposed.get("failure_names") != ["boundary_angle_gate"]
        or proposed.get("point_count") != 70
        or proposed.get("segment_count") != 70
        or proposed.get("minimum_projected_interior_angle_degrees")
        != expected["minimum_projected_interior_angle_degrees"]
        or proposed.get("maximum_absolute_chart_deviation_m")
        != expected["maximum_absolute_chart_deviation_m"]
        or proposed.get("record_sha256") != expected["proposed_record_sha256"]
    ):
        raise RuntimeError("consumed nonuniform result identity drifted")
    parameters = proposed.get("edge_parameters") or []
    denominator = 1 << 24
    low = sum(row == [1, denominator] for row in parameters)
    high = sum(row == [denominator - 1, denominator] for row in parameters)
    near = sum(
        (Fraction(int(row[0]), int(row[1])) < Fraction(1, 100))
        or (Fraction(int(row[0]), int(row[1])) > Fraction(99, 100))
        for row in parameters
    )
    if [low, high, near] != expected["endpoint_saturation_counts"]:
        raise RuntimeError("consumed endpoint-saturation evidence drifted")
    return result


def verify_consumed_parent_integrity(config: dict[str, object]) -> dict[str, object]:
    """Recheck the parent run's append-only external-integrity manifest.

    The direct binding pins the manifest itself.  This second layer proves
    that the manifest still describes an exact pre/post state and that every
    recursively listed file, protected inventory, and output artifact still
    matches it.  A hash-pinned manifest alone is not treated as proof.
    """

    binding = config["immutable_bindings"]["parent_nonuniform_external_integrity"]
    verified_manifest = verify_binding("parent_nonuniform_external_integrity", binding)
    manifest_path = project_path(str(binding["path"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema")
        != "kira.avatar.r24.nonuniform_source_edge_feasibility.external_integrity.v1"
        or manifest.get("before") != manifest.get("after")
        or manifest.get("pre_post_exact") is not True
        or manifest.get("blender_invocation_count") != 1
        or manifest.get("blender_exit_code") != 0
        or manifest.get("native_invocation_error") is not None
        or manifest.get("post_capture_errors") != []
        or manifest.get("finalization_errors") != []
        or manifest.get("retry_permitted") is not False
    ):
        raise RuntimeError("consumed parent external-integrity truth drifted")

    before = manifest["before"]
    recursive_files: list[dict[str, object]] = []
    for section in ("lane_bindings", "inherited_bindings"):
        rows = before.get(section)
        if not isinstance(rows, list):
            raise RuntimeError(f"consumed parent integrity missing {section}")
        for row in rows:
            actual = verify_binding(f"parent_integrity:{section}:{row['name']}", row)
            recursive_files.append({"section": section, "name": row["name"], **actual})

    recursive_inventories: list[dict[str, object]] = []
    inventory_rows = before.get("protected_inventories")
    if not isinstance(inventory_rows, list):
        raise RuntimeError("consumed parent integrity missing protected inventories")
    for row in inventory_rows:
        actual = canonical_inventory(ROOT, str(row["root"]))
        expected = {
            "root": row["root"],
            "file_count": row["file_count"],
            "total_bytes": row["total_bytes"],
            "compact_inventory_sha256": row["compact_inventory_sha256"],
        }
        if actual != expected:
            raise RuntimeError(f"parent protected inventory drifted: {row['root']}")
        recursive_inventories.append(actual)

    outputs: list[dict[str, object]] = []
    output_rows = manifest.get("output_files")
    if not isinstance(output_rows, list) or len(output_rows) != 5:
        raise RuntimeError("consumed parent output manifest drifted")
    for row in output_rows:
        output_path = manifest_path.parent / str(row["name"])
        actual = {
            "name": row["name"],
            "bytes": output_path.stat().st_size if output_path.is_file() else None,
            "sha256": sha256_file(output_path) if output_path.is_file() else None,
        }
        if actual != row:
            raise RuntimeError(f"consumed parent output drifted: {row['name']}")
        outputs.append(actual)

    return {
        "manifest": verified_manifest,
        "recursive_files": recursive_files,
        "recursive_inventories": recursive_inventories,
        "output_files": outputs,
    }


def validate_config(config: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    if config.get("schema") != "kira.avatar.r24.actual_plane_contour_topology_feasibility.static.v1":
        raise RuntimeError("actual-plane contour schema drifted")
    if (
        config.get("attempt_id") != "actual_plane_contour_01"
        or config.get("lane")
        != "LOCAL_TRANSITION_ACTUAL_PLANE_CONTOUR_TOPOLOGY_FEASIBILITY"
        or not config.get("uniform_attempt_consumed")
        or not config.get("nonuniform_attempt_consumed")
        or not config.get("uniform_level_family_terminal")
        or not config.get("fixed_source_edge_family_terminal")
        or not config.get("source_star_lane_terminal")
        or not config.get("not_attempt_48")
    ):
        raise RuntimeError("lane/attempt/terminal identity drifted")

    parent = parent_config(config)
    base = _PARENT.validate_config(parent)
    if compact_sha256(parent) != config["parent_config_canonical_sha256"]:
        raise RuntimeError("parent config canonical payload drifted")

    contour = config["contour_contract"]
    if (
        contour["kind"] != "single_exact_actual_unclamped_piecewise_linear_plane_contour"
        or contour["source_plane_origin"] != "consumed_plane_sample_112_of_190"
        or contour["sample_numerator"] != 112
        or contour["sample_denominator"] != 190
        or contour["collar_face_count"] != 73
        or contour["maximum_segment_count"] != 73
        or contour["endpoint_clamping_allowed"]
        or contour["reuse_fixed_70_edge_carrier_allowed"]
        or contour["alternate_plane_allowed"]
        or contour["randomness_allowed"]
        or contour["adaptive_retry_allowed"]
        or contour["free_world_space_points_allowed"]
        or not contour["evaluate_every_actual_component"]
        or not contour["single_proposed_output_record"]
    ):
        raise RuntimeError("single-plane actual-contour contract drifted")
    if contour["selection_order"] != [
        "all_inherited_hard_gates_pass",
        "minimum_carrier_face_symmetric_difference_from_k1",
        "minimum_maximum_source_graph_displacement_from_k1_carrier",
        "minimum_sum_source_graph_displacement_from_k1_carrier",
        "minimum_split_collar_face_count",
        "minimum_curvature_normal_mismatch",
        "minimum_canonical_component_sha256",
    ]:
        raise RuntimeError("actual-contour selection order drifted")

    if config["chart"] != parent["chart"] or config["hard_gates"] != parent["hard_gates"]:
        raise RuntimeError("inherited chart or hard gate changed")
    if (
        config["hard_gates"]["cut_loop_numeric_guard_minimum_angle_degrees"]
        != 12.000001
        or config["hard_gates"]["cut_loop_numeric_guard_maximum_chart_deviation_m"]
        != 0.001099999999
    ):
        raise RuntimeError("angle/chart guard weakened")

    output = config["output_contract"]
    if (
        output["root"]
        != "RecoverySprint/continuation_20260808/kira_r24_actual_plane_contour_topology_feasibility/actual_plane_contour_01"
        or output["runtime_cache_root"]
        != "RecoverySprint/runtime_cache/kira_r24_actual_plane_contour_topology_feasibility/actual_plane_contour_01"
        or not output["append_only"]
    ):
        raise RuntimeError("append-only output contract drifted")
    expected_names = {
        "attempt_started": "ATTEMPT_STARTED.json",
        "diagnostic": "ACTUAL_PLANE_CONTOUR_TOPOLOGY_FEASIBILITY.json",
        "worker_failure": "WORKER_FAILURE.json",
        "wrapper_failure": "WRAPPER_FAILURE.json",
        "stdout": "BLENDER_STDOUT.log",
        "stderr": "BLENDER_STDERR.log",
        "wrapper_completion": "WRAPPER_COMPLETION.json",
        "external_integrity": "EXTERNAL_PRE_POST_INTEGRITY.json",
    }
    if any(output.get(name) != expected for name, expected in expected_names.items()):
        raise RuntimeError("output evidence filename drifted")

    launch = config["launch_contract"]
    if (
        launch["blender_executable"]
        != "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"
        or launch["worker"]
        != "tools/blender_diagnose_kira_r24_actual_plane_contour_topology_feasibility01.py"
        or launch["wrapper"]
        != "RecoverySprint/continuation_20260808/kira_r24_actual_plane_contour_topology_feasibility_01_static/run_actual_plane_contour_topology_feasibility01_once.ps1"
        or launch["maximum_blender_invocations"] != 1
        or launch["automatic_retry_allowed"]
        or launch["invocation_guard"]
        != "INVOKE_AUDITED_ACTUAL_PLANE_CONTOUR_FEASIBILITY_01_ONCE"
        or launch["blender_arguments"]
        != [
            "--background",
            "--factory-startup",
            "--disable-autoexec",
            "--python-exit-code",
            "1",
            "--python",
        ]
    ):
        raise RuntimeError("guarded one-shot launch contract drifted")

    for key in (
        "mesh_mutation_allowed",
        "datablock_mutation_allowed",
        "blend_save_allowed",
        "render_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "assignment_allowed",
        "publication_allowed",
        "retry_allowed",
    ):
        if config["scope"][key]:
            raise RuntimeError(f"forbidden scope became enabled: {key}")
    consumed_nonuniform_result(config)
    return parent, base


def verify_immutable_inputs(config: dict[str, object]) -> dict[str, object]:
    parent, base = validate_config(config)
    lane = {
        name: verify_binding(name, binding)
        for name, binding in sorted(config["immutable_bindings"].items())
    }
    parent_state = _PARENT.verify_immutable_inputs(parent)
    consumed_parent_integrity = verify_consumed_parent_integrity(config)
    return {
        "lane_bindings": lane,
        "parent_lane_bindings": parent_state["lane_bindings"],
        "inherited_bindings": parent_state["inherited_bindings"],
        "protected_inventories": parent_state["protected_inventories"],
        "source_mesh": base["source_mesh"],
        "consumed_parent_integrity": consumed_parent_integrity,
    }


def fraction_record(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def derive_target_plane(
    seed: dict[str, object],
    coordinates: Sequence[Sequence[float]],
    frame,
    config: dict[str, object],
) -> tuple[Fraction, dict[str, object], dict[int, Fraction]]:
    normal = frame[2]
    normal_by_vertex = {
        index: Fraction.from_float(_BASE.dot(point, normal))
        for index, point in enumerate(coordinates)
    }
    endpoint_values = [
        normal_by_vertex[vertex]
        for point in seed["points"]
        for vertex in point["edge"]
    ]
    lower = min(endpoint_values)
    upper = max(endpoint_values)
    if lower == upper:
        raise RuntimeError("consumed seed edge normals have no span")
    contract = config["contour_contract"]
    sample = Fraction(contract["sample_numerator"], contract["sample_denominator"])
    target = lower + (upper - lower) * sample
    return target, {
        "schema": "kira.avatar.r24.actual_plane_contour.target_plane.v1",
        "origin": contract["source_plane_origin"],
        "sample": fraction_record(sample),
        "lower_seed_endpoint_normal": fraction_record(lower),
        "upper_seed_endpoint_normal": fraction_record(upper),
        "target_normal": fraction_record(target),
        "target_payload_sha256": compact_sha256(
            {
                "lower": fraction_record(lower),
                "upper": fraction_record(upper),
                "sample": fraction_record(sample),
                "target": fraction_record(target),
            }
        ),
    }, normal_by_vertex


def strict_crossing(first: Fraction, second: Fraction, target: Fraction) -> bool:
    return (first < target < second) or (second < target < first)


def exact_point_record(
    edge: tuple[int, int],
    target: Fraction,
    normal_by_vertex: dict[int, Fraction],
    faces: Sequence[Sequence[int]],
    incident: Sequence[int],
) -> tuple[tuple[int, int, int, int], dict[str, object]]:
    first, second = edge
    denominator = normal_by_vertex[second] - normal_by_vertex[first]
    if denominator == 0:
        raise ValueError("plane-parallel edge cannot cross strictly")
    t = (target - normal_by_vertex[first]) / denominator
    if not Fraction(0) < t < Fraction(1):
        raise ValueError("actual contour point is not open-edge")
    key = (first, second, t.numerator, t.denominator)
    owner, other = sorted(int(value) for value in incident)
    owner_triangle = _BASE.canonical_triangle(faces[owner])
    other_triangle = tuple(int(value) for value in faces[other])
    owner_weights = _PARENT.exact_edge_weights(owner_triangle, first, second, t)
    other_weights = _PARENT.exact_edge_weights(other_triangle, first, second, t)
    exact_residual = (
        normal_by_vertex[first]
        + t * (normal_by_vertex[second] - normal_by_vertex[first])
        - target
    )
    if exact_residual != 0:
        raise ArithmeticError("exact rational plane residual is nonzero")
    return key, {
        "key": list(key),
        "edge": [first, second],
        "t": fraction_record(t),
        "incident_source_faces": [owner, other],
        "owner_face": owner,
        "owner_triangle": list(owner_triangle),
        "owner_barycentric": [fraction_record(value) for value in owner_weights],
        "other_face": other,
        "other_triangle_stored_order": list(other_triangle),
        "other_barycentric": [fraction_record(value) for value in other_weights],
        "exact_plane_residual": fraction_record(exact_residual),
        "exact_plane_equation_verified": True,
    }


def build_actual_segments(
    faces: Sequence[Sequence[int]],
    normal_by_vertex: dict[int, Fraction],
    target: Fraction,
    context: dict[str, object],
) -> tuple[dict[tuple[int, ...], dict[str, object]], list[dict[str, object]], list[str], list[int]]:
    points: dict[tuple[int, ...], dict[str, object]] = {}
    segments: list[dict[str, object]] = []
    failures: set[str] = set()
    equal_vertices = sorted(
        vertex
        for vertex in context["envelope_vertices"]
        if normal_by_vertex[vertex] == target
    )
    if equal_vertices:
        failures.add("target_plane_vertex_or_edge_degeneracy")
    for face_index in sorted(context["collar"]):
        face = faces[face_index]
        crossed = [
            edge
            for edge in _BASE.triangle_edges(face)
            if strict_crossing(
                normal_by_vertex[edge[0]], normal_by_vertex[edge[1]], target
            )
        ]
        if len(crossed) not in (0, 2):
            failures.add("collar_triangle_crossing_count")
            continue
        if not crossed:
            continue
        keys = []
        segment_failures: set[str] = set()
        for edge in crossed:
            incident = sorted(context["full_incidence"].get(edge, []))
            if len(incident) != 2 or not set(incident) <= context["collar"]:
                failures.add("complete_two_collar_face_edge_ownership")
                segment_failures.add("complete_two_collar_face_edge_ownership")
                continue
            try:
                key, record = exact_point_record(
                    edge, target, normal_by_vertex, faces, incident
                )
            except (ValueError, ArithmeticError):
                failures.add("exact_owner_opposite_provenance")
                segment_failures.add("exact_owner_opposite_provenance")
                continue
            points.setdefault(key, record)
            keys.append(key)
        if len(keys) == 2:
            low, high = sorted(keys)
            segments.append(
                {
                    "source_face_index": face_index,
                    "point_keys": [list(low), list(high)],
                    "local_failures": sorted(segment_failures),
                }
            )
    return points, segments, sorted(failures, key=FAILURE_ORDER.index), equal_vertices


def extract_components(segments: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    adjacency: dict[tuple[int, ...], set[tuple[int, ...]]] = defaultdict(set)
    for segment in segments:
        first, second = (tuple(value) for value in segment["point_keys"])
        adjacency[first].add(second)
        adjacency[second].add(first)
    remaining = set(adjacency)
    components = []
    while remaining:
        start = min(remaining)
        stack = [start]
        vertices = set()
        while stack:
            current = stack.pop()
            if current in vertices:
                continue
            vertices.add(current)
            stack.extend(sorted(adjacency[current] - vertices, reverse=True))
        remaining -= vertices
        sub = {vertex: set(adjacency[vertex]) & vertices for vertex in vertices}
        degree_histogram: dict[int, int] = defaultdict(int)
        for neighbors in sub.values():
            degree_histogram[len(neighbors)] += 1
        closed = len(vertices) >= 3 and all(len(neighbors) == 2 for neighbors in sub.values())
        ordered = []
        if closed:
            try:
                ordered = _BASE.canonical_cycle(sub)
            except ValueError:
                closed = False
        component_segments = [
            row
            for row in segments
            if tuple(row["point_keys"][0]) in vertices
            and tuple(row["point_keys"][1]) in vertices
        ]
        components.append(
            {
                "component_key": list(min(vertices)),
                "point_count": len(vertices),
                "segment_count": len(component_segments),
                "closed_degree_two_cycle": closed,
                "degree_histogram": {
                    str(key): value for key, value in sorted(degree_histogram.items())
                },
                "ordered_loop": ordered,
                "segments": component_segments,
            }
        )
    return sorted(components, key=lambda row: tuple(row["component_key"]))


def strict_point_in_polygon(
    point: Sequence[float], polygon: Sequence[Sequence[float]], epsilon: float
) -> bool:
    inside = False
    px, py = point[0], point[1]
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        if _BASE.point_segment_distance_2d((px, py), first, second) <= epsilon:
            return False
        y_cross = (first[1] > py) != (second[1] > py)
        if y_cross:
            crossing_x = first[0] + (py - first[1]) * (
                (second[0] - first[0]) / (second[1] - first[1])
            )
            if crossing_x > px:
                inside = not inside
    return inside


def k1_graph_distances(
    seed: dict[str, object],
    faces: Sequence[Sequence[int]],
    coordinates: Sequence[Sequence[float]],
    envelope: set[int],
) -> dict[int, float]:
    adjacency: dict[int, dict[int, float]] = defaultdict(dict)
    for face_index in envelope:
        for first, second in _BASE.triangle_edges(faces[face_index]):
            length = _BASE.distance(coordinates[first], coordinates[second])
            adjacency[first][second] = min(adjacency[first].get(second, math.inf), length)
            adjacency[second][first] = min(adjacency[second].get(first, math.inf), length)
    distances = {vertex: math.inf for vertex in adjacency}
    queue = []
    for point in seed["points"]:
        first, second = point["edge"]
        t = Fraction(*point["k1_t"])
        length = _BASE.distance(coordinates[first], coordinates[second])
        for vertex, value in (
            (first, float(t) * length),
            (second, float(Fraction(1) - t) * length),
        ):
            if value < distances[vertex]:
                distances[vertex] = value
                heapq.heappush(queue, (value, vertex))
    while queue:
        distance, vertex = heapq.heappop(queue)
        if distance != distances[vertex]:
            continue
        for neighbor, length in sorted(adjacency[vertex].items()):
            proposed = distance + length
            if proposed < distances[neighbor]:
                distances[neighbor] = proposed
                heapq.heappush(queue, (proposed, neighbor))
    return distances


def evaluate_component(
    component: dict[str, object],
    points: dict[tuple[int, ...], dict[str, object]],
    global_failures: Sequence[str],
    faces: Sequence[Sequence[int]],
    coordinates: Sequence[Sequence[float]],
    normal_by_vertex: dict[int, Fraction],
    target: Fraction,
    frame,
    context: dict[str, object],
    seed: dict[str, object],
    config: dict[str, object],
    k1_distances: dict[int, float],
) -> dict[str, object]:
    failures = set(global_failures)
    ordered = list(component["ordered_loop"])
    if not component["closed_degree_two_cycle"]:
        failures.add("single_component_d2_envelope_separation")
    world_by_key: dict[tuple[int, ...], tuple[float, float, float]] = {}
    maximum_owner_delta = 0.0
    maximum_other_delta = 0.0
    for key in ordered:
        record = points[key]
        first, second = record["edge"]
        t = Fraction(*record["t"])
        direct = _BASE.vector_add(
            _BASE.vector_scale(coordinates[first], float(Fraction(1) - t)),
            _BASE.vector_scale(coordinates[second], float(t)),
        )
        owner = _PARENT.reconstruct_triangle(
            record["owner_triangle"],
            [Fraction(*value) for value in record["owner_barycentric"]],
            coordinates,
        )
        other = _PARENT.reconstruct_triangle(
            record["other_triangle_stored_order"],
            [Fraction(*value) for value in record["other_barycentric"]],
            coordinates,
        )
        maximum_owner_delta = max(maximum_owner_delta, _BASE.distance(direct, owner))
        maximum_other_delta = max(maximum_other_delta, _BASE.distance(direct, other))
        world_by_key[key] = direct
    tolerance = config["chart"]["barycentric_reconstruction_maximum_delta_m"]
    if maximum_owner_delta > tolerance or maximum_other_delta > tolerance:
        failures.add("exact_owner_opposite_provenance")

    projected = []
    minimum_angle = None
    maximum_deviation = None
    angle_details = []
    d2_inside = False
    boundary_outside = False
    if ordered and not {"exact_owner_opposite_provenance"} & failures:
        try:
            u, v, normal, _ = frame
            world = [world_by_key[key] for key in ordered]
            count = len(world)
            origin = tuple(
                math.fsum(point[axis] for point in world) / count for axis in range(3)
            )
            projected = [
                (
                    _BASE.dot(_BASE.vector_sub(point, origin), u),
                    _BASE.dot(_BASE.vector_sub(point, origin), v),
                    _BASE.dot(_BASE.vector_sub(point, origin), normal),
                )
                for point in world
            ]
            minimum_edge = config["chart"]["projected_edge_minimum_m"]
            if any(
                math.hypot(
                    projected[(index + 1) % count][0] - projected[index][0],
                    projected[(index + 1) % count][1] - projected[index][1],
                )
                <= minimum_edge
                for index in range(count)
            ):
                raise ValueError("projected edge degeneracy")
            twice_area = math.fsum(
                projected[index][0] * projected[(index + 1) % count][1]
                - projected[(index + 1) % count][0] * projected[index][1]
                for index in range(count)
            )
            if abs(twice_area) <= config["chart"]["twice_shoelace_area_minimum_m2"]:
                raise ValueError("projected area degeneracy")
            if twice_area < 0:
                ordered = [ordered[0], *reversed(ordered[1:])]
                world = [world_by_key[key] for key in ordered]
                projected = [
                    (
                        _BASE.dot(_BASE.vector_sub(point, origin), u),
                        _BASE.dot(_BASE.vector_sub(point, origin), v),
                        _BASE.dot(_BASE.vector_sub(point, origin), normal),
                    )
                    for point in world
                ]
            epsilon = config["chart"]["nonadjacent_segment_minimum_distance_m"]
            for first_index in range(count):
                for second_index in range(first_index + 1, count):
                    if second_index in (first_index, (first_index + 1) % count):
                        continue
                    if (second_index + 1) % count == first_index:
                        continue
                    if _BASE.segment_distance_2d(
                        projected[first_index],
                        projected[(first_index + 1) % count],
                        projected[second_index],
                        projected[(second_index + 1) % count],
                    ) <= epsilon:
                        failures.add("projected_simplicity_one_disk")
            for index in range(count):
                before = projected[index - 1]
                current = projected[index]
                after = projected[(index + 1) % count]
                incoming = (before[0] - current[0], before[1] - current[1])
                outgoing = (after[0] - current[0], after[1] - current[1])
                in_norm = math.hypot(*incoming)
                out_norm = math.hypot(*outgoing)
                cosine = max(
                    -1.0,
                    min(
                        1.0,
                        (incoming[0] * outgoing[0] + incoming[1] * outgoing[1])
                        / (in_norm * out_norm),
                    ),
                )
                angle_details.append(
                    {
                        "ordered_index": index,
                        "point_key": list(ordered[index]),
                        "degrees": math.degrees(math.acos(cosine)),
                    }
                )
            minimum_angle = min(row["degrees"] for row in angle_details)
            maximum_deviation = max(abs(row[2]) for row in projected)
            if minimum_angle < config["hard_gates"]["cut_loop_numeric_guard_minimum_angle_degrees"]:
                failures.add("boundary_angle_gate")
            if maximum_deviation > config["hard_gates"]["cut_loop_numeric_guard_maximum_chart_deviation_m"]:
                failures.add("chart_deviation_gate")

            polygon = [(row[0], row[1]) for row in projected]
            d2_inside = all(
                strict_point_in_polygon(
                    (
                        _BASE.dot(_BASE.vector_sub(coordinates[vertex], origin), u),
                        _BASE.dot(_BASE.vector_sub(coordinates[vertex], origin), v),
                    ),
                    polygon,
                    epsilon,
                )
                for vertex in context["d2_vertices"]
            )
            boundary_outside = all(
                not strict_point_in_polygon(
                    (
                        _BASE.dot(_BASE.vector_sub(coordinates[vertex], origin), u),
                        _BASE.dot(_BASE.vector_sub(coordinates[vertex], origin), v),
                    ),
                    polygon,
                    epsilon,
                )
                for vertex in context["boundary_vertices"]
            )
            d2_signs = {
                -1 if normal_by_vertex[vertex] < target else 1
                for vertex in context["d2_vertices"]
                if normal_by_vertex[vertex] != target
            }
            boundary_signs = {
                -1 if normal_by_vertex[vertex] < target else 1
                for vertex in context["boundary_vertices"]
                if normal_by_vertex[vertex] != target
            }
            scalar_separated = (
                len(d2_signs) == 1
                and len(boundary_signs) == 1
                and d2_signs != boundary_signs
            )
            if not (d2_inside and boundary_outside and scalar_separated):
                failures.add("single_component_d2_envelope_separation")
        except (ValueError, ArithmeticError, OverflowError, ZeroDivisionError):
            failures.add("chart_frame_validity")

    segment_faces = {row["source_face_index"] for row in component["segments"]}
    point_incident_faces = {
        face
        for key in ordered
        for face in points[key]["incident_source_faces"]
    }
    split_ledger = segment_faces | point_incident_faces
    exterior_hits = split_ledger & context["exterior_adjacent"]
    if not split_ledger <= context["collar"] or exterior_hits:
        failures.add("exterior_adjacent_face_preservation")
    if context["minimum_seam_rings"] < 4:
        failures.add("global_seam_disjointness")

    seed_faces = {row["source_face_index"] for row in seed["segments"]}
    carrier_symmetric_difference = sorted(segment_faces ^ seed_faces)
    displacements = []
    for key in ordered:
        first, second, numerator, denominator = key
        t = Fraction(numerator, denominator)
        length = _BASE.distance(coordinates[first], coordinates[second])
        displacements.append(
            min(
                k1_distances[first] + float(t) * length,
                k1_distances[second] + float(Fraction(1) - t) * length,
            )
        )
    carrier_by_pair = {
        frozenset(tuple(value) for value in row["point_keys"]): row["source_face_index"]
        for row in component["segments"]
    }
    curvature = None
    if ordered and all(
        frozenset((ordered[index], ordered[(index + 1) % len(ordered)]))
        in carrier_by_pair
        for index in range(len(ordered))
    ):
        normals = []
        for index, key in enumerate(ordered):
            following = ordered[(index + 1) % len(ordered)]
            face = faces[carrier_by_pair[frozenset((key, following))]]
            normals.append(
                _BASE.normalize(
                    _BASE.cross(
                        _BASE.vector_sub(coordinates[face[1]], coordinates[face[0]]),
                        _BASE.vector_sub(coordinates[face[2]], coordinates[face[0]]),
                    ),
                    1e-15,
                )
            )
        curvature = math.fsum(
            1.0
            - max(
                -1.0,
                min(1.0, _BASE.dot(normals[index], normals[(index + 1) % len(normals)])),
            )
            for index in range(len(normals))
        )

    serialized = {
        "target": fraction_record(target),
        "ordered_loop": [list(key) for key in ordered],
        "carrier_faces": sorted(segment_faces),
        "split_ledger": sorted(split_ledger),
    }
    digest = compact_sha256(serialized)
    ordered_failures = [name for name in FAILURE_ORDER if name in failures]
    record = {
        "schema": "kira.avatar.r24.actual_plane_contour.component.v1",
        "component_sha256": digest,
        "hard_failure_order": list(FAILURE_ORDER),
        "hard_failure_vector": [1 if name in failures else 0 for name in FAILURE_ORDER],
        "failure_names": ordered_failures,
        "passes_all_inherited_premutation_gates": not ordered_failures,
        "point_count": len(ordered),
        "segment_count": len(component["segments"]),
        "ordered_loop": [list(key) for key in ordered],
        "carrier_faces": sorted(segment_faces),
        "carrier_face_symmetric_difference_from_k1": carrier_symmetric_difference,
        "carrier_face_symmetric_difference_count": len(carrier_symmetric_difference),
        "split_collar_face_ledger": sorted(split_ledger),
        "split_ledger_outside_collar": sorted(split_ledger - context["collar"]),
        "exterior_adjacent_faces_crossed_or_split": sorted(exterior_hits),
        "minimum_projected_interior_angle_degrees": minimum_angle,
        "minimum_angle_detail": (
            min(angle_details, key=lambda row: (row["degrees"], row["point_key"]))
            if angle_details
            else None
        ),
        "all_angle_details": angle_details,
        "maximum_absolute_chart_deviation_m": maximum_deviation,
        "d2_projected_strictly_inside": d2_inside,
        "envelope_boundary_projected_outside": boundary_outside,
        "owner_triangle_maximum_direct_delta_m": maximum_owner_delta,
        "opposite_triangle_maximum_direct_delta_m": maximum_other_delta,
        "actual_opposite_triangle_vertex_order_used": True,
        "maximum_source_graph_displacement_from_k1_carrier_m": (
            max(displacements) if displacements else None
        ),
        "sum_source_graph_displacement_from_k1_carrier_m": (
            math.fsum(displacements) if displacements else None
        ),
        "curvature_normal_mismatch": curvature,
        "global_seam_minimum_source_graph_rings": context["minimum_seam_rings"],
    }
    return record


def component_score(record: dict[str, object]) -> tuple[object, ...]:
    maximum_displacement = record["maximum_source_graph_displacement_from_k1_carrier_m"]
    total_displacement = record["sum_source_graph_displacement_from_k1_carrier_m"]
    curvature = record["curvature_normal_mismatch"]
    return (
        0 if record["passes_all_inherited_premutation_gates"] else 1,
        sum(record["hard_failure_vector"]),
        record["carrier_face_symmetric_difference_count"],
        math.inf if maximum_displacement is None else maximum_displacement,
        math.inf if total_displacement is None else total_displacement,
        len(record["split_collar_face_ledger"]),
        math.inf if curvature is None else curvature,
        record["component_sha256"],
    )


def evaluate_actual_plane_contour(
    seed: dict[str, object],
    faces: Sequence[Sequence[int]],
    coordinates: Sequence[Sequence[float]],
    frame,
    context: dict[str, object],
    config: dict[str, object],
) -> dict[str, object]:
    target, target_record, normal_by_vertex = derive_target_plane(
        seed, coordinates, frame, config
    )
    points, segments, global_failures, equal_vertices = build_actual_segments(
        faces, normal_by_vertex, target, context
    )
    components = extract_components(segments)
    if len(components) != 1:
        global_failures = sorted(
            set(global_failures) | {"single_component_d2_envelope_separation"},
            key=FAILURE_ORDER.index,
        )
    distances = k1_graph_distances(seed, faces, coordinates, context["envelope"])
    records = [
        evaluate_component(
            component,
            points,
            global_failures,
            faces,
            coordinates,
            normal_by_vertex,
            target,
            frame,
            context,
            seed,
            config,
            distances,
        )
        for component in components
    ]
    eligible = [row for row in records if row["passes_all_inherited_premutation_gates"]]
    best = min(records, key=component_score) if records else None
    selected = min(eligible, key=component_score) if eligible else None
    return {
        "schema": "kira.avatar.r24.actual_plane_contour.solver_summary.v1",
        "target_plane": target_record,
        "collar_face_count": len(context["collar"]),
        "actual_segment_count": len(segments),
        "actual_point_count": len(points),
        "actual_point_records": [points[key] for key in sorted(points)],
        "component_count": len(components),
        "eligible_component_count": len(eligible),
        "target_equal_source_vertices": equal_vertices,
        "global_failure_names": global_failures,
        "all_actual_components_evaluated": True,
        "collar_face_visit_ledger": sorted(context["collar"]),
        "collar_face_visit_ledger_sha256": compact_sha256(sorted(context["collar"])),
        "every_declared_collar_face_inspected": (
            len(context["collar"]) == config["contour_contract"]["collar_face_count"]
        ),
        "component_records": records,
        "best_diagnostic_component": best,
        "selected_eligible_component": selected,
        "finite_termination_reached": True,
        "alternate_plane_evaluated": False,
        "old_fixed_70_edge_carrier_reused": False,
        "endpoint_clamping_used": False,
    }


def runtime_output_paths(config: dict[str, object]) -> dict[str, Path]:
    output = config["output_contract"]
    root = project_path(output["root"])
    names = (
        "attempt_started",
        "diagnostic",
        "worker_failure",
        "wrapper_failure",
        "stdout",
        "stderr",
        "wrapper_completion",
        "external_integrity",
    )
    return {name: root / output[name] for name in names} | {"root": root}


def validate_runtime_claim(config: dict[str, object], config_path: Path) -> dict[str, Path]:
    paths = runtime_output_paths(config)
    if not paths["root"].is_dir() or not paths["attempt_started"].is_file():
        raise RuntimeError("wrapper-owned append-only claim is absent")
    for name in (
        "diagnostic",
        "worker_failure",
        "wrapper_failure",
        "stdout",
        "stderr",
        "wrapper_completion",
        "external_integrity",
    ):
        if paths[name].exists():
            raise RuntimeError(f"final runtime evidence existed before worker: {name}")
    claim = json.loads(paths["attempt_started"].read_text(encoding="utf-8"))
    if (
        claim.get("schema")
        != "kira.avatar.r24.actual_plane_contour_topology_feasibility.claim.v1"
        or claim.get("attempt_id") != config["attempt_id"]
        or claim.get("lane") != config["lane"]
        or claim.get("invocation_guard_verified") is not True
        or claim.get("maximum_blender_invocations") != 1
        or claim.get("automatic_retry_allowed") is not False
        or claim.get("config_sha256") != sha256_file(config_path)
        or claim.get("worker_sha256") != sha256_file(THIS_FILE)
        or claim.get("wrapper_sha256")
        != sha256_file(project_path(config["launch_contract"]["wrapper"]))
    ):
        raise RuntimeError("wrapper-owned claim drifted")
    return paths


def write_new_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write("\n")


def run(config_path: Path) -> dict[str, object]:
    config = load_config(config_path)
    parent, base = validate_config(config)
    immutable_before = verify_immutable_inputs(config)
    paths = validate_runtime_claim(config, config_path)

    import bpy  # type: ignore  # imported only by a separately audited invocation

    source_path = project_path(base["immutable_bindings"]["source_blend"]["path"])
    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    matching = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and obj.name == base["source_mesh"]["object_name"]
        and obj.data.name == base["source_mesh"]["mesh_name"]
    ]
    if len(matching) != 1:
        raise RuntimeError("sealed source mesh identity is not unique")
    obj = matching[0]
    mesh = obj.data
    if (
        len(mesh.vertices) != base["source_mesh"]["vertex_count"]
        or len(mesh.edges) != base["source_mesh"]["edge_count"]
        or len(mesh.polygons) != base["source_mesh"]["face_count"]
    ):
        raise RuntimeError("sealed source mesh counts drifted")
    faces = [tuple(int(value) for value in polygon.vertices) for polygon in mesh.polygons]
    if any(len(face) != 3 or len(set(face)) != 3 for face in faces):
        raise RuntimeError("sealed source is not exact nondegenerate triangles")
    coordinates = [
        tuple(float(value) for value in (obj.matrix_world @ vertex.co))
        for vertex in mesh.vertices
    ]
    if any(not math.isfinite(value) for point in coordinates for value in point):
        raise RuntimeError("source coordinate is nonfinite")
    matrix = [
        [float(obj.matrix_world[row][column]) for column in range(3)]
        for row in range(3)
    ]
    frame = _BASE.chart_frame(matrix, base)
    context = _PARENT.build_source_context(faces, parent, base)
    uniform_diagnostic = json.loads(
        project_path(parent["immutable_bindings"]["attempt01_diagnostic"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    seed = _PARENT.derive_topology_seed(
        faces, context["collar"], uniform_diagnostic, parent
    )
    solver = evaluate_actual_plane_contour(
        seed, faces, coordinates, frame, context, config
    )

    immutable_after = verify_immutable_inputs(config)
    if immutable_before != immutable_after:
        raise RuntimeError("immutable inputs changed during read-only contour run")
    selected = solver["selected_eligible_component"]
    report = {
        "schema": "kira.avatar.r24.actual_plane_contour_topology_feasibility.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_PREMUTATION_NO_RENDER_NO_SAVE",
        "attempt_id": config["attempt_id"],
        "lane": config["lane"],
        "uniform_attempt_consumed": True,
        "nonuniform_attempt_consumed": True,
        "source_star_lane_terminal": True,
        "input_records": immutable_after,
        "solver_summary": solver,
        "eligible_proposed_record": selected,
        "status": (
            "ELIGIBLE_ACTUAL_PLANE_CONTOUR_PREMUTATION_ONLY"
            if selected is not None
            else "NO_ELIGIBLE_ACTUAL_PLANE_CONTOUR_FAIL_CLOSED"
        ),
        "truth": {
            "mesh_mutated": False,
            "datablock_mutated": False,
            "blend_saved": False,
            "rendered": False,
            "exported": False,
            "runtime_changed": False,
            "body_repair_proven": False,
            "owner_approval_claimed": False,
        },
    }
    write_new_json(paths["diagnostic"], report)
    return {
        "report": str(paths["diagnostic"]),
        "sha256": sha256_file(paths["diagnostic"]),
        "status": report["status"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else None
    )
    config_path = args.config.resolve()
    try:
        result = run(config_path)
        print(json.dumps(result, sort_keys=True))
    except Exception as exc:
        try:
            config = load_config(config_path)
            validate_config(config)
            paths = runtime_output_paths(config)
            if paths["root"].is_dir() and not paths["worker_failure"].exists():
                write_new_json(
                    paths["worker_failure"],
                    {
                        "schema": "kira.avatar.r24.actual_plane_contour_topology_feasibility.worker_failure.v1",
                        "created_utc": datetime.now(timezone.utc).isoformat(),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                        "mutation_reached": False,
                        "save_reached": False,
                        "render_reached": False,
                        "retry_permitted": False,
                    },
                )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
