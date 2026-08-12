"""Read-only R24 local-transition geometric diagnostic, attempt_01.

This module is safe to import without Blender.  A later independently
authorized execution may open the exact sealed source Blend to measure the
192 fixed rational cuts on E*.  It never edits a datablock, saves, renders,
exports, retries, or creates a body candidate.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from fractions import Fraction
import argparse
import hashlib
import heapq
import json
import math
from pathlib import Path
import sys
import traceback
from typing import Iterable, Sequence


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_local_transition_geometric_diagnostic_attempt_01_static/"
    "LOCAL_TRANSITION_GEOMETRIC_DIAGNOSTIC_ATTEMPT01_CONFIG.json"
)
FAILURE_ORDER = (
    "input_topology_identity",
    "level_vertex_degeneracy",
    "collar_triangle_crossing_count",
    "complete_two_collar_face_edge_ownership",
    "exact_rational_provenance",
    "one_cycle_d2_envelope_separation",
    "chart_frame_validity",
    "projected_simplicity_one_disk",
    "boundary_angle_gate",
    "chart_deviation_gate",
    "global_seam_disjointness",
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError(f"path escapes project root: {relative}") from exc
    return path


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_immutable_bindings(config: dict[str, object]) -> dict[str, object]:
    records: dict[str, object] = {}
    for name, binding in config["immutable_bindings"].items():
        path = project_path(binding["path"])
        if not path.is_file():
            raise RuntimeError(f"sealed input absent: {name}")
        actual_bytes = path.stat().st_size
        actual_sha = sha256_file(path)
        if actual_bytes != binding["bytes"] or actual_sha != binding["sha256"]:
            raise RuntimeError(f"sealed input drifted: {name}")
        records[name] = {
            "path": binding["path"],
            "bytes": actual_bytes,
            "sha256": actual_sha,
        }
    return records


def validate_config(config: dict[str, object]) -> None:
    if config.get("schema") != (
        "kira.avatar.r24.local_transition_geometric_diagnostic."
        "attempt01.config.v1"
    ):
        raise RuntimeError("local-transition diagnostic schema drifted")
    if config.get("attempt_id") != "attempt_01" or not config.get("not_attempt_48"):
        raise RuntimeError("attempt identity drifted")
    if not config.get("source_star_lane_terminal"):
        raise RuntimeError("terminal source-star rule was weakened")
    generator = config["candidate_generator"]
    if (
        generator["levels"] != 192
        or generator["k_first"] != 1
        or generator["k_last"] != 192
        or generator["tau_denominator"] != 193
        or generator["adaptive_refinement_allowed"]
        or generator["randomness_allowed"]
        or generator["alternate_envelope_allowed"]
        or generator["least_bad_candidate_allowed"]
    ):
        raise RuntimeError("finite candidate generator drifted")
    scope = config["scope"]
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
        if scope[key]:
            raise RuntimeError(f"forbidden scope became enabled: {key}")
    launch = config["launch_contract"]
    if (
        launch["maximum_blender_invocations"] != 1
        or launch["automatic_retry_allowed"]
        or not launch["wrapper_redirects_only_to_controlled_temporary_logs"]
        or not launch["final_stdout_stderr_created_only_by_atomic_move_after_worker_exit"]
    ):
        raise RuntimeError("one-shot/log-ownership contract drifted")


def canonical_edge(first: int, second: int) -> tuple[int, int]:
    if first == second:
        raise ValueError("edge endpoints must differ")
    return (first, second) if first < second else (second, first)


def triangle_edges(face: Sequence[int]) -> tuple[tuple[int, int], ...]:
    return tuple(
        canonical_edge(face[index], face[(index + 1) % 3]) for index in range(3)
    )


def canonical_triangle(face: Sequence[int]) -> tuple[int, int, int]:
    rotations = tuple(
        tuple(face[(offset + index) % 3] for index in range(3))
        for offset in range(3)
    )
    return min(rotations)


def edge_incidence(
    faces: Sequence[Sequence[int]], selected: Iterable[int] | None = None
) -> dict[tuple[int, int], list[int]]:
    rows: dict[tuple[int, int], list[int]] = defaultdict(list)
    indices = range(len(faces)) if selected is None else sorted(selected)
    for face_index in indices:
        for edge in triangle_edges(faces[face_index]):
            rows[edge].append(face_index)
    return {key: sorted(value) for key, value in rows.items()}


def selected_topology(
    faces: Sequence[Sequence[int]], selected: set[int]
) -> dict[str, object]:
    incidence = edge_incidence(faces, selected)
    vertices = sorted({v for f in selected for v in faces[f]})
    edges = sorted(incidence)
    boundary = sorted(edge for edge, linked in incidence.items() if len(linked) == 1)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for first, second in boundary:
        adjacency[first].add(second)
        adjacency[second].add(first)
    cycle: list[int] = []
    if adjacency and all(len(value) == 2 for value in adjacency.values()):
        start = min(adjacency)
        previous: int | None = None
        current = start
        while True:
            cycle.append(current)
            choices = sorted(value for value in adjacency[current] if value != previous)
            following = choices[0]
            if following == start:
                break
            if following in cycle:
                cycle = []
                break
            previous, current = current, following
        if len(cycle) != len(adjacency):
            cycle = []
    face_adjacency: dict[int, set[int]] = {index: set() for index in selected}
    for linked in incidence.values():
        if len(linked) == 2:
            first, second = linked
            face_adjacency[first].add(second)
            face_adjacency[second].add(first)
    components = 0
    unseen = set(selected)
    while unseen:
        components += 1
        queue = deque([min(unseen)])
        unseen.remove(queue[0])
        while queue:
            current = queue.popleft()
            for neighbor in sorted(face_adjacency[current]):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
    return {
        "vertices": vertices,
        "edges": edges,
        "boundary": boundary,
        "cycle": cycle,
        "face_components": components,
        "euler": len(vertices) - len(edges) + len(selected),
    }


def graph_distances(
    adjacency: dict[int, set[int]], seeds: Iterable[int]
) -> dict[int, int]:
    distance = {value: 0 for value in sorted(set(seeds))}
    queue = deque(sorted(distance))
    while queue:
        current = queue.popleft()
        for neighbor in sorted(adjacency[current]):
            if neighbor not in distance:
                distance[neighbor] = distance[current] + 1
                queue.append(neighbor)
    return distance


def fraction_record(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def vector_add(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return tuple(a[index] + b[index] for index in range(3))


def vector_sub(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return tuple(a[index] - b[index] for index in range(3))


def vector_scale(a: Sequence[float], scale: float) -> tuple[float, float, float]:
    return tuple(a[index] * scale for index in range(3))


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return math.fsum(a[index] * b[index] for index in range(3))


def norm(a: Sequence[float]) -> float:
    return math.sqrt(dot(a, a))


def normalize(a: Sequence[float], minimum: float) -> tuple[float, float, float]:
    length = norm(a)
    if not math.isfinite(length) or length < minimum:
        raise ValueError("degenerate chart vector")
    return tuple(value / length for value in a)


def cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def distance(a: Sequence[float], b: Sequence[float]) -> float:
    return norm(vector_sub(a, b))


def chart_frame(matrix: Sequence[Sequence[float]], config: dict[str, object]):
    chart = config["chart"]
    determinant = (
        matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )
    if not math.isfinite(determinant) or abs(determinant) < chart["matrix_determinant_minimum_absolute"]:
        raise ValueError("degenerate source matrix")

    def multiply(value: Sequence[float]) -> tuple[float, float, float]:
        return tuple(math.fsum(matrix[row][column] * value[column] for column in range(3)) for row in range(3))

    minimum = chart["axis_norm_minimum_m"]
    u = normalize(multiply(chart["u_local_axis"]), minimum)
    raw_n = multiply(chart["normal_local_axis"])
    n = normalize(vector_sub(raw_n, vector_scale(u, dot(raw_n, u))), minimum)
    v = normalize(cross(n, u), minimum)
    residual = chart["unit_orthogonality_maximum_residual"]
    if max(abs(norm(axis) - 1.0) for axis in (u, v, n)) > residual:
        raise ValueError("chart unit residual")
    if max(abs(dot(first, second)) for first, second in ((u, v), (u, n), (v, n))) > residual:
        raise ValueError("chart orthogonality residual")
    if dot(n, chart["reference_d2_normal"]) < chart["minimum_reference_normal_dot"]:
        raise ValueError("fixed chart normal disagrees with D2 reference")
    return u, v, n, determinant


def orient2d(a: Sequence[float], b: Sequence[float], c: Sequence[float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def point_segment_distance_2d(p, a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    if length2 <= 0.0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def segment_distance_2d(a, b, c, d) -> float:
    values = (orient2d(a, b, c), orient2d(a, b, d), orient2d(c, d, a), orient2d(c, d, b))
    if values[0] * values[1] <= 0.0 and values[2] * values[3] <= 0.0:
        return 0.0
    return min(
        point_segment_distance_2d(a, c, d),
        point_segment_distance_2d(b, c, d),
        point_segment_distance_2d(c, a, b),
        point_segment_distance_2d(d, a, b),
    )


def canonical_cycle(adjacency: dict[tuple[int, ...], set[tuple[int, ...]]]):
    if len(adjacency) < 3 or any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise ValueError("cut graph is not degree-two")
    start = min(adjacency)
    cycle = [start]
    previous = None
    current = start
    following = min(adjacency[start])
    while True:
        if following == start:
            break
        if following in cycle:
            raise ValueError("cut graph revisits a node")
        cycle.append(following)
        candidates = sorted(value for value in adjacency[following] if value != current)
        if len(candidates) != 1:
            raise ValueError("cut graph traversal is ambiguous")
        previous, current, following = current, following, candidates[0]
    if len(cycle) != len(adjacency):
        raise ValueError("cut graph has multiple components")
    return cycle


def dijkstra_world(
    adjacency: dict[int, set[int]], coordinates: Sequence[Sequence[float]], seeds: Iterable[int]
) -> dict[int, float]:
    result = {vertex: 0.0 for vertex in sorted(set(seeds))}
    heap = [(0.0, vertex) for vertex in sorted(result)]
    heapq.heapify(heap)
    while heap:
        current_distance, current = heapq.heappop(heap)
        if current_distance != result[current]:
            continue
        for neighbor in sorted(adjacency[current]):
            candidate = current_distance + distance(coordinates[current], coordinates[neighbor])
            if candidate < result.get(neighbor, math.inf):
                result[neighbor] = candidate
                heapq.heappush(heap, (candidate, neighbor))
    return result


def evaluate_level(
    k: int,
    faces: Sequence[Sequence[int]],
    coordinates: Sequence[Sequence[float]],
    full_incidence: dict[tuple[int, int], list[int]],
    collar: set[int],
    d2_vertices: set[int],
    boundary_vertices: set[int],
    seed_faces: set[int],
    phi: dict[int, Fraction],
    frame,
    config: dict[str, object],
    d2_boundary: Sequence[int],
    envelope_adjacency: dict[int, set[int]],
) -> dict[str, object]:
    tau = Fraction(k, config["candidate_generator"]["tau_denominator"])
    failures: set[str] = set()
    stage = "level"
    points: dict[tuple[int, int, int, int], dict[str, object]] = {}
    segments: list[dict[str, object]] = []
    if any(value == tau for value in phi.values()):
        failures.add("level_vertex_degeneracy")
    else:
        stage = "march"
        for face_index in sorted(collar):
            face = faces[face_index]
            crossed = []
            for edge in triangle_edges(face):
                first, second = edge
                if (phi[first] < tau < phi[second]) or (phi[second] < tau < phi[first]):
                    crossed.append(edge)
            if len(crossed) not in (0, 2):
                failures.add("collar_triangle_crossing_count")
                continue
            if not crossed:
                continue
            keys = []
            for edge in crossed:
                first, second = edge
                incident = full_incidence.get(edge, [])
                if len(incident) != 2 or not set(incident) <= collar:
                    failures.add("complete_two_collar_face_edge_ownership")
                    continue
                t = (tau - phi[first]) / (phi[second] - phi[first])
                if not Fraction(0) < t < Fraction(1):
                    failures.add("exact_rational_provenance")
                    continue
                key = (first, second, t.numerator, t.denominator)
                owner = min(incident)
                triangle = canonical_triangle(faces[owner])
                weights = {first: Fraction(1) - t, second: t}
                barycentric = [weights.get(vertex, Fraction(0)) for vertex in triangle]
                if (
                    sum(barycentric, Fraction(0)) != 1
                    or any(value < 0 or value > 1 for value in barycentric)
                    or sum(value == 0 for value in barycentric) != 1
                ):
                    failures.add("exact_rational_provenance")
                    continue
                points.setdefault(
                    key,
                    {
                        "key": list(key),
                        "edge": [first, second],
                        "incident_source_faces": incident,
                        "owner_face": owner,
                        "owner_triangle_vertices": list(triangle),
                        "t": fraction_record(t),
                        "barycentric": [fraction_record(value) for value in barycentric],
                    },
                )
                keys.append(key)
            if len(keys) == 2:
                low, high = sorted(keys)
                segments.append(
                    {"source_face_index": face_index, "points": [list(low), list(high)]}
                )

    ordered_loop: list[tuple[int, ...]] = []
    projected: list[tuple[float, float, float]] = []
    minimum_angle = None
    maximum_deviation = None
    candidate_sha = None
    selection_metrics = None
    if not failures:
        stage = "topology"
        adjacency: dict[tuple[int, ...], set[tuple[int, ...]]] = defaultdict(set)
        for segment in segments:
            first, second = (tuple(value) for value in segment["points"])
            adjacency[first].add(second)
            adjacency[second].add(first)
        try:
            ordered_loop = canonical_cycle(adjacency)
        except ValueError:
            failures.add("one_cycle_d2_envelope_separation")
        if not (
            all(phi[vertex] < tau for vertex in d2_vertices)
            and all(phi[vertex] > tau for vertex in boundary_vertices)
            and seed_faces <= set(config["_runtime_d2_faces"])
        ):
            failures.add("one_cycle_d2_envelope_separation")

    world_by_key: dict[tuple[int, ...], tuple[float, float, float]] = {}
    if not failures:
        stage = "provenance"
        tolerance = config["chart"]["barycentric_reconstruction_maximum_delta_m"]
        sum_tolerance = config["chart"]["binary64_barycentric_sum_maximum_residual"]
        for key in ordered_loop:
            point = points[key]
            t = Fraction(point["t"][0], point["t"][1])
            first, second = point["edge"]
            direct = vector_add(
                vector_scale(coordinates[first], float(Fraction(1) - t)),
                vector_scale(coordinates[second], float(t)),
            )
            bary = [Fraction(row[0], row[1]) for row in point["barycentric"]]
            if abs(math.fsum(float(value) for value in bary) - 1.0) > sum_tolerance:
                failures.add("exact_rational_provenance")
                break
            owner_reconstruction = (0.0, 0.0, 0.0)
            for vertex, weight in zip(point["owner_triangle_vertices"], bary):
                owner_reconstruction = vector_add(
                    owner_reconstruction, vector_scale(coordinates[vertex], float(weight))
                )
            other_face = max(point["incident_source_faces"])
            other_triangle = faces[other_face]
            other_reconstruction = vector_add(
                vector_scale(coordinates[first], float(Fraction(1) - t)),
                vector_scale(coordinates[second], float(t)),
            )
            if (
                distance(direct, owner_reconstruction) > tolerance
                or distance(direct, other_reconstruction) > tolerance
            ):
                failures.add("exact_rational_provenance")
                break
            world_by_key[key] = direct

    if not failures:
        stage = "chart"
        try:
            u, v, n, _ = frame
            world = [world_by_key[key] for key in ordered_loop]
            count = len(world)
            origin = tuple(math.fsum(point[axis] for point in world) / count for axis in range(3))
            projected = [
                (dot(vector_sub(point, origin), u), dot(vector_sub(point, origin), v), dot(vector_sub(point, origin), n))
                for point in world
            ]
            minimum_edge = config["chart"]["projected_edge_minimum_m"]
            if any(
                math.hypot(
                    projected[(index + 1) % count][0] - projected[index][0],
                    projected[(index + 1) % count][1] - projected[index][1],
                ) <= minimum_edge
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
                ordered_loop = [ordered_loop[0], *reversed(ordered_loop[1:])]
                world = [world_by_key[key] for key in ordered_loop]
                projected = [
                    (dot(vector_sub(point, origin), u), dot(vector_sub(point, origin), v), dot(vector_sub(point, origin), n))
                    for point in world
                ]
            epsilon = config["chart"]["nonadjacent_segment_minimum_distance_m"]
            for first_index in range(count):
                a = projected[first_index]
                b = projected[(first_index + 1) % count]
                for second_index in range(first_index + 1, count):
                    if second_index in (first_index, (first_index + 1) % count) or (second_index + 1) % count == first_index:
                        continue
                    c = projected[second_index]
                    d = projected[(second_index + 1) % count]
                    if segment_distance_2d(a, b, c, d) <= epsilon:
                        failures.add("projected_simplicity_one_disk")
                        break
                if "projected_simplicity_one_disk" in failures:
                    break
            angles = []
            for index in range(count):
                before = projected[index - 1]
                current = projected[index]
                after = projected[(index + 1) % count]
                incoming = (before[0] - current[0], before[1] - current[1])
                outgoing = (after[0] - current[0], after[1] - current[1])
                in_norm = math.hypot(*incoming)
                out_norm = math.hypot(*outgoing)
                cosine = max(-1.0, min(1.0, (incoming[0] * outgoing[0] + incoming[1] * outgoing[1]) / (in_norm * out_norm)))
                angles.append(math.degrees(math.acos(cosine)))
            minimum_angle = min(angles)
            maximum_deviation = max(abs(row[2]) for row in projected)
            if minimum_angle < config["hard_gates"]["cut_loop_numeric_guard_minimum_angle_degrees"]:
                failures.add("boundary_angle_gate")
            if maximum_deviation > config["hard_gates"]["cut_loop_numeric_guard_maximum_chart_deviation_m"]:
                failures.add("chart_deviation_gate")
        except (ValueError, ArithmeticError, OverflowError):
            failures.add("chart_frame_validity")

    if not failures:
        stage = "selection_metrics"
        serialized = {
            "source_topology_sha256": config["source_mesh"]["stored_winding_face_loops_sha256"],
            "d2_sha256": config["domains"]["d2_face_indices_sha256"],
            "envelope_sha256": config["domains"]["strict_envelope_faces_sha256"],
            "collar_sha256": config["domains"]["strict_envelope_collar_faces_sha256"],
            "k": k,
            "tau": fraction_record(tau),
            "points": [points[key] for key in sorted(points)],
            "segments": sorted(segments, key=lambda row: (row["source_face_index"], row["points"])),
            "ordered_loop": [list(key) for key in ordered_loop],
        }
        candidate_sha = compact_sha256(serialized)
        distances = dijkstra_world(envelope_adjacency, coordinates, d2_boundary)
        point_displacements = []
        for key in ordered_loop:
            first, second, numerator, denominator = key
            t = numerator / denominator
            edge_length = distance(coordinates[first], coordinates[second])
            point_displacements.append(
                min(distances[first] + t * edge_length, distances[second] + (1.0 - t) * edge_length)
            )
        carrier_by_edge = {
            frozenset(tuple(value) for value in segment["points"]): segment["source_face_index"]
            for segment in segments
        }
        normals = []
        for index, key in enumerate(ordered_loop):
            following = ordered_loop[(index + 1) % len(ordered_loop)]
            face = faces[carrier_by_edge[frozenset((key, following))]]
            normals.append(normalize(cross(vector_sub(coordinates[face[1]], coordinates[face[0]]), vector_sub(coordinates[face[2]], coordinates[face[0]])), 1e-15))
        curvature = math.fsum(1.0 - max(-1.0, min(1.0, dot(normals[index], normals[(index + 1) % len(normals)]))) for index in range(len(normals)))
        selection_metrics = {
            "maximum_graph_geodesic_displacement_m": max(point_displacements),
            "sum_graph_geodesic_displacement_m": math.fsum(point_displacements),
            "split_collar_face_count": len({row["source_face_index"] for row in segments}),
            "curvature_normal_mismatch": curvature,
            "k": k,
            "candidate_sha256": candidate_sha,
        }

    vector = [1 if name in failures else 0 for name in FAILURE_ORDER]
    return {
        "k": k,
        "tau": fraction_record(tau),
        "evaluation_stage_reached": stage,
        "hard_failure_order": list(FAILURE_ORDER),
        "hard_failure_vector": vector,
        "failure_names": sorted(failures, key=FAILURE_ORDER.index),
        "passes_all_premutation_gates": not any(vector),
        "point_count": len(points),
        "segment_count": len(segments),
        "ordered_loop": [list(key) for key in ordered_loop],
        "minimum_projected_interior_angle_degrees": minimum_angle,
        "maximum_absolute_chart_deviation_m": maximum_deviation,
        "candidate_sha256": candidate_sha,
        "selection_metrics": selection_metrics,
    }


def write_new_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True, allow_nan=False)
        stream.write("\n")


def runtime_output_paths(config: dict[str, object]) -> dict[str, Path]:
    output = config["output_contract"]
    root = project_path(output["root"])
    return {name: root / output[name] for name in ("attempt_started", "diagnostic", "worker_failure", "wrapper_failure", "stdout", "stderr", "wrapper_completion", "external_integrity")} | {"root": root}


def validate_runtime_claim(config: dict[str, object], config_path: Path) -> dict[str, Path]:
    paths = runtime_output_paths(config)
    if not paths["root"].is_dir() or not paths["attempt_started"].is_file():
        raise RuntimeError("wrapper-owned append-only attempt claim is absent")
    for name in ("diagnostic", "worker_failure", "wrapper_failure", "stdout", "stderr", "wrapper_completion", "external_integrity"):
        if paths[name].exists():
            raise RuntimeError(f"final runtime evidence existed before worker: {name}")
    claim = json.loads(paths["attempt_started"].read_text(encoding="utf-8"))
    if (
        claim.get("schema") != "kira.avatar.r24.local_transition_geometric_diagnostic.attempt01.claim.v1"
        or claim.get("maximum_blender_invocations") != 1
        or claim.get("automatic_retry_allowed") is not False
        or claim.get("config_sha256") != sha256_file(config_path)
        or claim.get("worker_sha256") != sha256_file(Path(__file__))
    ):
        raise RuntimeError("wrapper-owned attempt claim drifted")
    return paths


def run(config_path: Path) -> dict[str, object]:
    config = load_config(config_path)
    validate_config(config)
    immutable_before = verify_immutable_bindings(config)
    paths = validate_runtime_claim(config, config_path)

    # Imported only in an actually authorized Blender process.
    import bpy  # type: ignore

    source_path = project_path(config["immutable_bindings"]["source_blend"]["path"])
    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    matching = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and obj.name == config["source_mesh"]["object_name"]
        and obj.data.name == config["source_mesh"]["mesh_name"]
    ]
    if len(matching) != 1:
        raise RuntimeError("sealed source mesh identity is not unique")
    obj = matching[0]
    mesh = obj.data
    if len(mesh.vertices) != 736 or len(mesh.edges) != 2171 or len(mesh.polygons) != 1436:
        raise RuntimeError("sealed source mesh counts drifted")
    faces = [tuple(int(value) for value in polygon.vertices) for polygon in mesh.polygons]
    if any(len(face) != 3 or len(set(face)) != 3 for face in faces):
        raise RuntimeError("sealed source is not exact nondegenerate triangles")
    if compact_sha256([list(face) for face in faces]) != config["source_mesh"]["stored_winding_face_loops_sha256"]:
        raise RuntimeError("stored-winding source topology drifted")
    coordinates = [tuple(float(value) for value in (obj.matrix_world @ vertex.co)) for vertex in mesh.vertices]
    if any(not math.isfinite(value) for point in coordinates for value in point):
        raise RuntimeError("source coordinate is nonfinite")

    domain = json.loads(project_path(config["immutable_bindings"]["repair_domains"]["path"]).read_text(encoding="utf-8"))
    by_ring = {row["face_ring_expansion"]: row for row in domain["domains"]}
    d2 = set(int(value) for value in by_ring[2]["face_indices"])
    d4 = set(int(value) for value in by_ring[4]["face_indices"])
    envelope = d4 | set(config["domains"]["strict_envelope_added_faces"])
    collar = envelope - d2
    summaries = {"d2": selected_topology(faces, d2), "envelope": selected_topology(faces, envelope)}
    expected = config["domains"]
    checks = (
        (len(d2), expected["d2_face_count"]),
        (compact_sha256(sorted(d2)), expected["d2_face_indices_sha256"]),
        (len(summaries["d2"]["vertices"]), expected["d2_vertex_count"]),
        (compact_sha256(summaries["d2"]["vertices"]), expected["d2_vertex_indices_sha256"]),
        (len(envelope), expected["strict_envelope_face_count"]),
        (compact_sha256(sorted(envelope)), expected["strict_envelope_faces_sha256"]),
        (len(summaries["envelope"]["vertices"]), expected["strict_envelope_vertex_count"]),
        (compact_sha256(summaries["envelope"]["vertices"]), expected["strict_envelope_vertices_sha256"]),
        (len(summaries["envelope"]["edges"]), expected["strict_envelope_edge_count"]),
        (compact_sha256([list(value) for value in summaries["envelope"]["edges"]]), expected["strict_envelope_edges_sha256"]),
        (len(summaries["envelope"]["boundary"]), expected["strict_envelope_boundary_edge_count"]),
        (compact_sha256([list(value) for value in summaries["envelope"]["boundary"]]), expected["strict_envelope_boundary_edges_sha256"]),
        (len(collar), expected["strict_envelope_collar_face_count"]),
        (compact_sha256(sorted(collar)), expected["strict_envelope_collar_faces_sha256"]),
    )
    if any(actual != wanted for actual, wanted in checks):
        raise RuntimeError("D2/E* topology or hash drifted")
    if summaries["envelope"]["face_components"] != 1 or summaries["envelope"]["euler"] != 1 or not summaries["envelope"]["cycle"]:
        raise RuntimeError("E* is not one disk")
    if compact_sha256(summaries["d2"]["cycle"]) != expected["d2_boundary_cycle_sha256"]:
        raise RuntimeError("D2 ordered boundary cycle drifted")
    if compact_sha256(summaries["envelope"]["cycle"]) != expected["strict_envelope_ordered_boundary_cycle_sha256"]:
        raise RuntimeError("E* ordered boundary cycle drifted")
    d2_vertices = set(summaries["d2"]["vertices"])
    boundary_vertices = set(summaries["envelope"]["cycle"])
    if d2_vertices & boundary_vertices:
        raise RuntimeError("E* strict separation regressed")

    full_incidence = edge_incidence(faces)
    outside = sorted(set(range(len(faces))) - envelope)
    exterior_adjacent = sorted(
        {
            face_index
            for edge in summaries["envelope"]["boundary"]
            for face_index in full_incidence[edge]
            if face_index not in envelope
        }
    )
    if (
        len(outside) != expected["strict_envelope_outside_face_count"]
        or compact_sha256(outside) != expected["strict_envelope_outside_faces_sha256"]
        or len(exterior_adjacent) != expected["strict_envelope_exterior_adjacent_face_count"]
        or compact_sha256(exterior_adjacent) != expected["strict_envelope_exterior_adjacent_faces_sha256"]
        or any(len(full_incidence[edge]) != 2 for edge in summaries["envelope"]["boundary"])
    ):
        raise RuntimeError("E* exterior-adjacent preservation ledger drifted")
    global_interface = set(int(value) for value in domain["global_interface"]["boundary_vertex_indices"])
    if len(global_interface) != expected["global_interface_vertex_count"] or global_interface & set(summaries["envelope"]["vertices"]):
        raise RuntimeError("E* global-interface disjointness drifted")
    full_vertex_adjacency: dict[int, set[int]] = defaultdict(set)
    for first, second in full_incidence:
        full_vertex_adjacency[first].add(second)
        full_vertex_adjacency[second].add(first)
    seam_distance = graph_distances(full_vertex_adjacency, global_interface)
    if min(seam_distance[vertex] for vertex in summaries["envelope"]["vertices"]) < expected["minimum_source_graph_rings_from_global_interface"]:
        raise RuntimeError("E* global-interface distance gate drifted")
    envelope_adjacency: dict[int, set[int]] = defaultdict(set)
    for edge in summaries["envelope"]["edges"]:
        envelope_adjacency[edge[0]].add(edge[1])
        envelope_adjacency[edge[1]].add(edge[0])
    din = graph_distances(envelope_adjacency, d2_vertices)
    dout = graph_distances(envelope_adjacency, boundary_vertices)
    if set(din) != set(summaries["envelope"]["vertices"]) or set(dout) != set(din):
        raise RuntimeError("E* graph-distance field is incomplete")
    phi = {}
    for vertex in sorted(din):
        denominator = din[vertex] + dout[vertex]
        if denominator <= 0:
            raise RuntimeError("invalid scalar-field denominator")
        phi[vertex] = Fraction(din[vertex], denominator)

    matrix = [[float(obj.matrix_world[row][column]) for column in range(3)] for row in range(3)]
    frame = chart_frame(matrix, config)
    seed_faces = set(int(value) for value in domain["exact_collision"]["seed_face_indices"])
    if len(seed_faces) != 29 or not seed_faces <= d2:
        raise RuntimeError("collision seed containment drifted")
    config["_runtime_d2_faces"] = sorted(d2)
    records = [
        evaluate_level(
            k,
            faces,
            coordinates,
            full_incidence,
            collar,
            d2_vertices,
            boundary_vertices,
            seed_faces,
            phi,
            frame,
            config,
            summaries["d2"]["cycle"],
            envelope_adjacency,
        )
        for k in range(1, 193)
    ]
    passing = [row for row in records if row["passes_all_premutation_gates"]]
    selected = min(
        passing,
        key=lambda row: (
            row["selection_metrics"]["maximum_graph_geodesic_displacement_m"],
            row["selection_metrics"]["sum_graph_geodesic_displacement_m"],
            row["selection_metrics"]["split_collar_face_count"],
            row["selection_metrics"]["curvature_normal_mismatch"],
            row["selection_metrics"]["k"],
            row["selection_metrics"]["candidate_sha256"],
        ),
        default=None,
    )
    immutable_after = verify_immutable_bindings(config)
    if immutable_before != immutable_after or sha256_file(source_path) != config["immutable_bindings"]["source_blend"]["sha256"]:
        raise RuntimeError("sealed input changed during read-only diagnostic")
    report = {
        "schema": "kira.avatar.r24.local_transition_geometric_diagnostic.attempt01.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_PREMUTATION_NO_RENDER_NO_SAVE",
        "attempt_id": "attempt_01",
        "lane": config["lane"],
        "not_attempt_48": True,
        "source_star_lane_terminal": True,
        "input_records": immutable_after,
        "source_mesh": config["source_mesh"],
        "envelope": {
            "face_count": len(envelope),
            "face_indices_sha256": compact_sha256(sorted(envelope)),
            "collar_face_count": len(collar),
            "collar_face_indices_sha256": compact_sha256(sorted(collar)),
            "outer_boundary_edge_count": len(summaries["envelope"]["boundary"]),
            "outer_boundary_edges_sha256": compact_sha256([list(value) for value in summaries["envelope"]["boundary"]]),
            "d2_boundary_disjoint": not bool(d2_vertices & boundary_vertices),
        },
        "candidate_record_count": len(records),
        "candidate_records": records,
        "eligible_candidate_count": len(passing),
        "selected_candidate": selected,
        "status": "ELIGIBLE_BOUNDARY_FOUND_PREMUTATION_ONLY" if selected else "NO_ELIGIBLE_LEVEL_FAIL_CLOSED",
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
    return {"report": str(paths["diagnostic"]), "sha256": sha256_file(paths["diagnostic"]), "status": report["status"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else None)
    config_path = args.config.resolve()
    try:
        result = run(config_path)
        print(json.dumps(result, sort_keys=True))
    except Exception as exc:
        try:
            config = load_config(config_path)
            paths = runtime_output_paths(config)
            if paths["root"].is_dir() and not paths["worker_failure"].exists():
                write_new_json(
                    paths["worker_failure"],
                    {
                        "schema": "kira.avatar.r24.local_transition_geometric_diagnostic.attempt01.worker_failure.v1",
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
