"""One-shot read-only R24 nonuniform source-edge feasibility diagnostic.

The module is intentionally safe to import in ordinary Python.  Blender is
imported only inside ``run`` after the wrapper claim and every immutable input
have been verified.  The worker reads one sealed mesh, evaluates a finite
nonuniform cut-point family, and writes one append-only diagnostic.  It has no
mesh/datablock write, save, render, export, activation, or retry path.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import argparse
import hashlib
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


BASE_WORKER = TOOLS / "blender_diagnose_kira_r24_local_transition_geometric_attempt01.py"
_SPEC = importlib.util.spec_from_file_location("r24_nonuniform_preserved_base", BASE_WORKER)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load preserved Attempt 01 worker")
_BASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BASE)

DEFAULT_CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_nonuniform_source_edge_feasibility_01_static/"
    "NONUNIFORM_SOURCE_EDGE_FEASIBILITY01_CONFIG.json"
)

FAILURE_ORDER = (
    "input_topology_identity",
    "open_edge_parameter",
    "fixed_edge_triangle_topology",
    "exact_owner_opposite_provenance",
    "one_cycle_d2_envelope_separation",
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


def inherited_config(config: dict[str, object]) -> dict[str, object]:
    binding = config["immutable_bindings"]["attempt01_config"]
    verify_binding("attempt01_config", binding)
    return json.loads(project_path(str(binding["path"])).read_text(encoding="utf-8"))


def validate_config(config: dict[str, object]) -> dict[str, object]:
    if config.get("schema") != "kira.avatar.r24.nonuniform_source_edge_feasibility.static.v1":
        raise RuntimeError("nonuniform feasibility schema drifted")
    if (
        config.get("attempt_id") != "nonuniform_feasibility_01"
        or config.get("lane") != "LOCAL_TRANSITION_NONUNIFORM_SOURCE_EDGE_FEASIBILITY"
        or config.get("uniform_attempt_id") != "attempt_01"
        or not config.get("uniform_attempt_consumed")
        or not config.get("uniform_level_family_terminal")
        or not config.get("source_star_lane_terminal")
        or not config.get("not_attempt_48")
    ):
        raise RuntimeError("lane/attempt/terminal identity drifted")

    base = inherited_config(config)
    _BASE.validate_config(base)
    for section, expected in config["inherited_section_sha256"].items():
        if compact_sha256(base[section]) != expected:
            raise RuntimeError(f"inherited section drifted: {section}")

    seed = config["topology_seed"]
    if (
        seed["source_k"] != 1
        or seed["source_tau"] != [1, 193]
        or seed["point_count"] != 70
        or seed["segment_count"] != 70
        or seed["canonical_payload_sha256"]
        != "fcda32fa49dcabdb60ae0f63c690047ce65ec30665b3b1243da53495ba4007dc"
    ):
        raise RuntimeError("fixed k=1 topology-seed contract drifted")

    solver = config["solver"]
    if (
        solver["edge_parameter_denominator"] != 16777216
        or solver["plane_sample_intervals"] != 190
        or solver["maximum_generated_records"] != 192
        or not solver["include_exact_k1_record"]
        or solver["randomness_allowed"]
        or solver["adaptive_retry_allowed"]
        or solver["free_world_space_points_allowed"]
        or solver["alternate_edge_or_triangle_topology_allowed"]
        or solver["global_continuous_minimax_claimed"]
        or solver["global_gate_constrained_optimality_claimed"]
    ):
        raise RuntimeError("finite deterministic solver contract drifted")
    if solver["objective_scope"] != (
        "exact_complete_selection_only_over_the_declared_finite_at_most_192_record_"
        "family_not_over_the_continuous_or_full_dyadic_cartesian_product"
    ):
        raise RuntimeError("bounded solver objective scope drifted")
    if solver["lexicographic_objectives"] != [
        "all_inherited_hard_gates_pass",
        "minimum_maximum_absolute_chart_deviation",
        "minimum_maximum_source_edge_displacement_from_k1",
        "minimum_total_source_edge_displacement_from_k1",
        "minimum_exact_edge_barycentric_record",
    ]:
        raise RuntimeError("solver objective order drifted")

    base_hard = base["hard_gates"]
    hard = config["hard_gates"]
    if hard != base_hard:
        raise RuntimeError("an inherited hard gate changed")
    if config["chart"] != base["chart"]:
        raise RuntimeError("the inherited chart contract changed")
    if hard["cut_loop_numeric_guard_minimum_angle_degrees"] != 12.000001:
        raise RuntimeError("angle guard weakened")
    if hard["cut_loop_numeric_guard_maximum_chart_deviation_m"] != 0.001099999999:
        raise RuntimeError("chart-deviation guard weakened")

    launch = config["launch_contract"]
    if (
        launch["maximum_blender_invocations"] != 1
        or launch["automatic_retry_allowed"]
        or not launch["explicit_invocation_guard_required"]
        or launch["invocation_guard"] != "INVOKE_AUDITED_NONUNIFORM_FEASIBILITY_01_ONCE"
    ):
        raise RuntimeError("one-shot invocation guard drifted")

    output = config["output_contract"]
    if (
        output["root"]
        != "RecoverySprint/continuation_20260808/kira_r24_nonuniform_source_edge_feasibility/nonuniform_feasibility_01"
        or output["runtime_cache_root"]
        != "RecoverySprint/runtime_cache/kira_r24_nonuniform_source_edge_feasibility/nonuniform_feasibility_01"
        or not output["append_only"]
    ):
        raise RuntimeError("bounded append-only output contract drifted")
    if output["root"] == base["output_contract"]["root"]:
        raise RuntimeError("new output collides with consumed Attempt 01")
    expected_output_names = {
        "attempt_started": "ATTEMPT_STARTED.json",
        "diagnostic": "NONUNIFORM_SOURCE_EDGE_FEASIBILITY.json",
        "worker_failure": "WORKER_FAILURE.json",
        "wrapper_failure": "WRAPPER_FAILURE.json",
        "stdout": "BLENDER_STDOUT.log",
        "stderr": "BLENDER_STDERR.log",
        "wrapper_completion": "WRAPPER_COMPLETION.json",
        "external_integrity": "EXTERNAL_PRE_POST_INTEGRITY.json",
    }
    if any(output[name] != expected for name, expected in expected_output_names.items()):
        raise RuntimeError("bounded output evidence filename drifted")
    if (
        launch["blender_executable"]
        != "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"
        or launch["worker"]
        != "tools/blender_diagnose_kira_r24_nonuniform_source_edge_feasibility01.py"
        or launch["wrapper"]
        != "RecoverySprint/continuation_20260808/kira_r24_nonuniform_source_edge_feasibility_01_static/run_nonuniform_source_edge_feasibility01_once.ps1"
    ):
        raise RuntimeError("fixed executable/worker/wrapper path drifted")

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
    return base


def verify_immutable_inputs(config: dict[str, object]) -> dict[str, object]:
    base = validate_config(config)
    records = {
        name: verify_binding(name, binding)
        for name, binding in sorted(config["immutable_bindings"].items())
    }
    inherited = _BASE.verify_immutable_bindings(base)
    inventories = []
    for expected in base["protected_inventories"]:
        actual = canonical_inventory(ROOT, expected["root"])
        if actual != expected:
            raise RuntimeError(f"protected inventory drifted: {expected['root']}")
        inventories.append(actual)
    return {
        "lane_bindings": records,
        "inherited_bindings": inherited,
        "protected_inventories": inventories,
    }


def fraction_record(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def exact_edge_weights(
    triangle: Sequence[int], first: int, second: int, t: Fraction
) -> tuple[Fraction, Fraction, Fraction]:
    if len(triangle) != 3 or len(set(triangle)) != 3:
        raise ValueError("source triangle is degenerate")
    if first == second or first not in triangle or second not in triangle:
        raise ValueError("source edge is absent from triangle")
    if not Fraction(0) < t < Fraction(1):
        raise ValueError("source-edge parameter is not strictly interior")
    by_vertex = {first: Fraction(1) - t, second: t}
    weights = tuple(by_vertex.get(vertex, Fraction(0)) for vertex in triangle)
    if (
        sum(weights, Fraction(0)) != Fraction(1)
        or any(weight < 0 or weight > 1 for weight in weights)
        or sum(weight == 0 for weight in weights) != 1
    ):
        raise ValueError("exact barycentric weight proof failed")
    return weights


def reconstruct_triangle(
    triangle: Sequence[int],
    weights: Sequence[Fraction],
    coordinates: Sequence[Sequence[float]],
) -> tuple[float, float, float]:
    return tuple(
        math.fsum(
            float(weight) * float(coordinates[vertex][axis])
            for vertex, weight in zip(triangle, weights)
        )
        for axis in range(3)
    )


def derive_topology_seed(
    faces: Sequence[Sequence[int]],
    collar: set[int],
    diagnostic: dict[str, object],
    config: dict[str, object],
) -> dict[str, object]:
    if (
        diagnostic.get("schema")
        != "kira.avatar.r24.local_transition_geometric_diagnostic.attempt01.v1"
        or diagnostic.get("attempt_id") != "attempt_01"
        or diagnostic.get("candidate_record_count") != 192
        or diagnostic.get("eligible_candidate_count") != 0
        or diagnostic.get("selected_candidate") is not None
        or diagnostic.get("status") != "NO_ELIGIBLE_LEVEL_FAIL_CLOSED"
    ):
        raise RuntimeError("consumed diagnostic status drifted")
    rows = [row for row in diagnostic["candidate_records"] if row.get("k") == 1]
    if len(rows) != 1:
        raise RuntimeError("consumed diagnostic lacks unique k=1 record")
    source = rows[0]
    expected_seed = config["topology_seed"]
    if (
        source.get("tau") != [1, 193]
        or source.get("point_count") != 70
        or source.get("segment_count") != 70
        or source.get("failure_names") != ["chart_deviation_gate"]
        or source.get("minimum_projected_interior_angle_degrees")
        != expected_seed["k1_minimum_projected_angle_degrees"]
        or source.get("maximum_absolute_chart_deviation_m")
        != expected_seed["k1_maximum_chart_deviation_m"]
    ):
        raise RuntimeError("k=1 source record drifted")

    keys = [tuple(int(value) for value in row) for row in source["ordered_loop"]]
    if len(keys) != 70 or len(set(keys)) != 70:
        raise RuntimeError("k=1 ordered edge loop is not exactly 70 unique points")
    full_incidence = _BASE.edge_incidence(faces)
    edge_to_index: dict[tuple[int, int], int] = {}
    points = []
    for index, key in enumerate(keys):
        if len(key) != 4:
            raise RuntimeError("k=1 point key arity drifted")
        first, second, numerator, denominator = key
        edge = _BASE.canonical_edge(first, second)
        if edge != (first, second) or edge in edge_to_index:
            raise RuntimeError("k=1 edge identity drifted")
        t = Fraction(numerator, denominator)
        if not Fraction(0) < t < Fraction(1):
            raise RuntimeError("k=1 source point is not open-edge")
        incident = sorted(full_incidence.get(edge, []))
        if len(incident) != 2 or not set(incident) <= collar:
            raise RuntimeError("k=1 edge is not owned by two collar triangles")
        owner, other = incident
        edge_to_index[edge] = index
        points.append(
            {
                "index": index,
                "edge": [first, second],
                "k1_t": [numerator, denominator],
                "incident_collar_faces": incident,
                "owner_face": owner,
                "owner_triangle": list(_BASE.canonical_triangle(faces[owner])),
                "other_face": other,
                "other_triangle_stored_order": list(faces[other]),
            }
        )

    segments = []
    for face_index in sorted(collar):
        point_indices = sorted(
            edge_to_index[edge]
            for edge in _BASE.triangle_edges(faces[face_index])
            if edge in edge_to_index
        )
        if point_indices:
            if len(point_indices) != 2:
                raise RuntimeError("fixed carrier triangle does not have two seed points")
            segments.append(
                {"source_face_index": face_index, "point_indices": point_indices}
            )
    if len(segments) != 70:
        raise RuntimeError("fixed k=1 carrier is not exactly 70 triangles")
    adjacency: dict[int, set[int]] = defaultdict(set)
    for segment in segments:
        first, second = segment["point_indices"]
        adjacency[first].add(second)
        adjacency[second].add(first)
    if _BASE.canonical_cycle(adjacency) != list(range(70)):
        raise RuntimeError("fixed k=1 carrier does not reproduce its ordered cycle")

    binding = config["immutable_bindings"]["attempt01_diagnostic"]
    payload = {
        "schema": "kira.avatar.r24.nonuniform_source_edge_topology_seed.v1",
        "source_diagnostic": {
            "bytes": int(binding["bytes"]),
            "sha256": binding["sha256"],
        },
        "source_record": {
            "k": 1,
            "tau": [1, 193],
            "point_count": 70,
            "segment_count": 70,
            "minimum_projected_interior_angle_degrees": source[
                "minimum_projected_interior_angle_degrees"
            ],
            "maximum_absolute_chart_deviation_m": source[
                "maximum_absolute_chart_deviation_m"
            ],
        },
        "points": points,
        "segments": segments,
    }
    actual_hash = compact_sha256(payload)
    if actual_hash != expected_seed["canonical_payload_sha256"]:
        raise RuntimeError("fixed 70-edge/triangle topology-seed hash drifted")
    return payload


def build_source_context(
    faces: Sequence[Sequence[int]], config: dict[str, object], base: dict[str, object]
) -> dict[str, object]:
    if (
        len(faces) != base["source_mesh"]["face_count"]
        or compact_sha256([list(face) for face in faces])
        != base["source_mesh"]["stored_winding_face_loops_sha256"]
    ):
        raise RuntimeError("source topology identity drifted")
    domain = json.loads(
        project_path(base["immutable_bindings"]["repair_domains"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    by_ring = {row["face_ring_expansion"]: row for row in domain["domains"]}
    d2 = set(int(value) for value in by_ring[2]["face_indices"])
    d4 = set(int(value) for value in by_ring[4]["face_indices"])
    envelope = d4 | set(base["domains"]["strict_envelope_added_faces"])
    collar = envelope - d2
    d2_summary = _BASE.selected_topology(faces, d2)
    envelope_summary = _BASE.selected_topology(faces, envelope)
    expected = base["domains"]
    checks = (
        (len(d2), expected["d2_face_count"]),
        (compact_sha256(sorted(d2)), expected["d2_face_indices_sha256"]),
        (compact_sha256(d2_summary["cycle"]), expected["d2_boundary_cycle_sha256"]),
        (len(envelope), expected["strict_envelope_face_count"]),
        (compact_sha256(sorted(envelope)), expected["strict_envelope_faces_sha256"]),
        (len(collar), expected["strict_envelope_collar_face_count"]),
        (compact_sha256(sorted(collar)), expected["strict_envelope_collar_faces_sha256"]),
        (
            compact_sha256(envelope_summary["cycle"]),
            expected["strict_envelope_ordered_boundary_cycle_sha256"],
        ),
    )
    if any(actual != wanted for actual, wanted in checks):
        raise RuntimeError("D2/E-star/collar identity drifted")
    if (
        d2_summary["face_components"] != 1
        or d2_summary["euler"] != 1
        or envelope_summary["face_components"] != 1
        or envelope_summary["euler"] != 1
    ):
        raise RuntimeError("D2 or E-star is not one disk")
    d2_vertices = set(d2_summary["vertices"])
    boundary_vertices = set(envelope_summary["cycle"])
    if d2_vertices & boundary_vertices:
        raise RuntimeError("D2 is no longer strictly inside E-star")

    full_incidence = _BASE.edge_incidence(faces)
    outside = set(range(len(faces))) - envelope
    exterior_adjacent = {
        face_index
        for edge in envelope_summary["boundary"]
        for face_index in full_incidence[edge]
        if face_index not in envelope
    }
    if (
        len(outside) != expected["strict_envelope_outside_face_count"]
        or compact_sha256(sorted(outside)) != expected["strict_envelope_outside_faces_sha256"]
        or len(exterior_adjacent) != expected["strict_envelope_exterior_adjacent_face_count"]
        or compact_sha256(sorted(exterior_adjacent))
        != expected["strict_envelope_exterior_adjacent_faces_sha256"]
    ):
        raise RuntimeError("exterior-adjacent ledger drifted")

    global_interface = set(
        int(value) for value in domain["global_interface"]["boundary_vertex_indices"]
    )
    full_adjacency: dict[int, set[int]] = defaultdict(set)
    for first, second in full_incidence:
        full_adjacency[first].add(second)
        full_adjacency[second].add(first)
    seam_distance = _BASE.graph_distances(full_adjacency, global_interface)
    minimum_seam_rings = min(
        seam_distance[vertex] for vertex in envelope_summary["vertices"]
    )
    if minimum_seam_rings < expected["minimum_source_graph_rings_from_global_interface"]:
        raise RuntimeError("global seam separation drifted")
    return {
        "domain": domain,
        "d2": d2,
        "d2_vertices": d2_vertices,
        "envelope": envelope,
        "envelope_vertices": set(envelope_summary["vertices"]),
        "boundary_vertices": boundary_vertices,
        "collar": collar,
        "full_incidence": full_incidence,
        "exterior_adjacent": exterior_adjacent,
        "minimum_seam_rings": minimum_seam_rings,
    }


def projected_segment_clearance(a, b, c, d) -> float:
    return _BASE.segment_distance_2d(a, b, c, d)


def independent_direct_evaluate(
    t_values: Sequence[Fraction],
    seed: dict[str, object],
    faces: Sequence[Sequence[int]],
    coordinates: Sequence[Sequence[float]],
    frame,
    context: dict[str, object],
    config: dict[str, object],
) -> dict[str, object]:
    """Rebuild and evaluate a solver record without trusting solver metrics."""
    failures: set[str] = set()
    hard = config["hard_gates"]
    chart = config["chart"]
    points = seed["points"]
    segments = seed["segments"]
    if len(t_values) != 70 or len(points) != 70 or len(segments) != 70:
        failures.add("fixed_edge_triangle_topology")
    world = []
    provenance = []
    maximum_owner_delta = 0.0
    maximum_other_delta = 0.0
    for index, point in enumerate(points):
        if index >= len(t_values):
            break
        t = t_values[index]
        if not Fraction(0) < t < Fraction(1):
            failures.add("open_edge_parameter")
            continue
        first, second = point["edge"]
        incident = sorted(context["full_incidence"].get((first, second), []))
        if (
            point["index"] != index
            or incident != point["incident_collar_faces"]
            or len(incident) != 2
            or point["owner_face"] != min(incident)
            or point["other_face"] != max(incident)
            or point["owner_face"] == point["other_face"]
            or not set(incident) <= context["collar"]
            or list(_BASE.canonical_triangle(faces[point["owner_face"]]))
            != point["owner_triangle"]
            or list(faces[point["other_face"]]) != point["other_triangle_stored_order"]
        ):
            failures.add("fixed_edge_triangle_topology")
            continue
        try:
            owner_weights = exact_edge_weights(point["owner_triangle"], first, second, t)
            other_weights = exact_edge_weights(
                point["other_triangle_stored_order"], first, second, t
            )
            direct = tuple(
                math.fsum(
                    (
                        float(Fraction(1) - t) * coordinates[first][axis],
                        float(t) * coordinates[second][axis],
                    )
                )
                for axis in range(3)
            )
            owner_reconstruction = reconstruct_triangle(
                point["owner_triangle"], owner_weights, coordinates
            )
            other_reconstruction = reconstruct_triangle(
                point["other_triangle_stored_order"], other_weights, coordinates
            )
            owner_delta = _BASE.distance(direct, owner_reconstruction)
            other_delta = _BASE.distance(direct, other_reconstruction)
            maximum_owner_delta = max(maximum_owner_delta, owner_delta)
            maximum_other_delta = max(maximum_other_delta, other_delta)
            if (
                owner_delta > chart["barycentric_reconstruction_maximum_delta_m"]
                or other_delta > chart["barycentric_reconstruction_maximum_delta_m"]
            ):
                failures.add("exact_owner_opposite_provenance")
            world.append(direct)
            provenance.append(
                {
                    "index": index,
                    "edge": [first, second],
                    "t": fraction_record(t),
                    "owner_face": point["owner_face"],
                    "owner_triangle": point["owner_triangle"],
                    "owner_barycentric": [fraction_record(value) for value in owner_weights],
                    "other_face": point["other_face"],
                    "other_triangle_stored_order": point["other_triangle_stored_order"],
                    "other_barycentric": [fraction_record(value) for value in other_weights],
                }
            )
        except (ValueError, ArithmeticError, OverflowError):
            failures.add("exact_owner_opposite_provenance")

    adjacency: dict[int, set[int]] = defaultdict(set)
    split_faces = set()
    seed_index_by_edge = {
        tuple(point["edge"]): point["index"] for point in points
    }
    for segment in segments:
        face_index = segment["source_face_index"]
        if face_index not in context["collar"]:
            failures.add("fixed_edge_triangle_topology")
        if face_index in context["exterior_adjacent"]:
            failures.add("exterior_adjacent_face_preservation")
        split_faces.add(face_index)
        first, second = segment["point_indices"]
        actual_face_points = sorted(
            seed_index_by_edge[edge]
            for edge in _BASE.triangle_edges(faces[face_index])
            if edge in seed_index_by_edge
        )
        if actual_face_points != sorted((first, second)):
            failures.add("fixed_edge_triangle_topology")
        adjacency[first].add(second)
        adjacency[second].add(first)
    try:
        ordered = _BASE.canonical_cycle(adjacency)
        if ordered != list(range(70)) or len(split_faces) != 70:
            failures.add("one_cycle_d2_envelope_separation")
    except ValueError:
        ordered = []
        failures.add("one_cycle_d2_envelope_separation")
    if (
        context["d2_vertices"] & context["boundary_vertices"]
        or not set(split_faces) <= context["collar"]
    ):
        failures.add("one_cycle_d2_envelope_separation")
    if context["minimum_seam_rings"] < config["domains"]["minimum_source_graph_rings_from_global_interface"]:
        failures.add("global_seam_disjointness")

    minimum_angle = None
    maximum_deviation = None
    projected = []
    if len(world) == 70 and not {
        "open_edge_parameter",
        "fixed_edge_triangle_topology",
        "exact_owner_opposite_provenance",
        "one_cycle_d2_envelope_separation",
    } & failures:
        try:
            u, v, n, _ = frame
            origin = tuple(
                math.fsum(point[axis] for point in world) / 70 for axis in range(3)
            )
            projected = [
                (
                    _BASE.dot(_BASE.vector_sub(point, origin), u),
                    _BASE.dot(_BASE.vector_sub(point, origin), v),
                    _BASE.dot(_BASE.vector_sub(point, origin), n),
                )
                for point in world
            ]
            if any(not math.isfinite(value) for point in projected for value in point):
                raise ValueError("nonfinite chart point")
            if any(
                math.hypot(
                    projected[(index + 1) % 70][0] - projected[index][0],
                    projected[(index + 1) % 70][1] - projected[index][1],
                )
                <= chart["projected_edge_minimum_m"]
                for index in range(70)
            ):
                raise ValueError("projected edge degeneracy")
            twice_area = math.fsum(
                projected[index][0] * projected[(index + 1) % 70][1]
                - projected[(index + 1) % 70][0] * projected[index][1]
                for index in range(70)
            )
            if abs(twice_area) <= chart["twice_shoelace_area_minimum_m2"]:
                raise ValueError("projected disk area degeneracy")
            epsilon = chart["nonadjacent_segment_minimum_distance_m"]
            for first_index in range(70):
                a = projected[first_index]
                b = projected[(first_index + 1) % 70]
                for second_index in range(first_index + 1, 70):
                    if (
                        second_index in (first_index, (first_index + 1) % 70)
                        or (second_index + 1) % 70 == first_index
                    ):
                        continue
                    c = projected[second_index]
                    d = projected[(second_index + 1) % 70]
                    if projected_segment_clearance(a, b, c, d) <= epsilon:
                        failures.add("projected_simplicity_one_disk")
                        break
                if "projected_simplicity_one_disk" in failures:
                    break
            angles = []
            for index in range(70):
                before = projected[index - 1]
                current = projected[index]
                after = projected[(index + 1) % 70]
                incoming = (before[0] - current[0], before[1] - current[1])
                outgoing = (after[0] - current[0], after[1] - current[1])
                in_norm = math.hypot(*incoming)
                out_norm = math.hypot(*outgoing)
                if in_norm <= 0.0 or out_norm <= 0.0:
                    raise ValueError("projected angle degeneracy")
                cosine = max(
                    -1.0,
                    min(
                        1.0,
                        (incoming[0] * outgoing[0] + incoming[1] * outgoing[1])
                        / (in_norm * out_norm),
                    ),
                )
                angles.append(math.degrees(math.acos(cosine)))
            minimum_angle = min(angles)
            maximum_deviation = max(abs(point[2]) for point in projected)
            if minimum_angle < hard["cut_loop_numeric_guard_minimum_angle_degrees"]:
                failures.add("boundary_angle_gate")
            if maximum_deviation > hard["cut_loop_numeric_guard_maximum_chart_deviation_m"]:
                failures.add("chart_deviation_gate")
        except (ValueError, ArithmeticError, OverflowError):
            failures.add("chart_frame_validity")

    t_records = [fraction_record(value) for value in t_values]
    k1_values = [Fraction(*point["k1_t"]) for point in points]
    displacements = [
        _BASE.distance(coordinates[point["edge"][0]], coordinates[point["edge"][1]])
        * float(abs(t_values[index] - k1_values[index]))
        for index, point in enumerate(points)
    ] if len(t_values) == 70 else []
    serialized = {
        "topology_seed_sha256": config["topology_seed"]["canonical_payload_sha256"],
        "edge_parameters": t_records,
        "provenance": provenance,
        "segments": segments,
    }
    vector = [1 if name in failures else 0 for name in FAILURE_ORDER]
    provenance_valid = (
        "exact_owner_opposite_provenance" not in failures
        and "fixed_edge_triangle_topology" not in failures
        and len(provenance) == 70
    )
    return {
        "schema": "kira.avatar.r24.nonuniform_source_edge_proposed_record.v1",
        "hard_failure_order": list(FAILURE_ORDER),
        "hard_failure_vector": vector,
        "failure_names": [name for name in FAILURE_ORDER if name in failures],
        "passes_all_inherited_premutation_gates": not any(vector),
        "point_count": len(t_values),
        "segment_count": len(segments),
        "edge_parameters": t_records,
        "minimum_projected_interior_angle_degrees": minimum_angle,
        "maximum_absolute_chart_deviation_m": maximum_deviation,
        "maximum_source_edge_displacement_from_k1_m": max(displacements) if displacements else None,
        "total_source_edge_displacement_from_k1_m": math.fsum(displacements) if displacements else None,
        "owner_triangle_maximum_direct_delta_m": maximum_owner_delta,
        "opposite_triangle_maximum_direct_delta_m": maximum_other_delta,
        "actual_opposite_triangle_vertex_order_used": provenance_valid,
        "exact_sum_range_and_one_zero_asserted": provenance_valid,
        "direct_edge_interpolation_independently_compared": provenance_valid,
        "open_edge_fixed_carrier_isotopy_from_k1_asserted": (
            provenance_valid
            and "open_edge_parameter" not in failures
            and "one_cycle_d2_envelope_separation" not in failures
        ),
        "global_seam_minimum_source_graph_rings": context["minimum_seam_rings"],
        "exterior_adjacent_faces_crossed_or_split": sorted(split_faces & context["exterior_adjacent"]),
        "record_sha256": compact_sha256(serialized),
    }


def nearest_dyadic_parameter(
    target: Fraction,
    first_normal: Fraction,
    second_normal: Fraction,
    k1_t: Fraction,
    denominator: int,
) -> Fraction:
    if first_normal == second_normal:
        desired = k1_t
    else:
        desired = (target - first_normal) / (second_normal - first_normal)
    scaled = desired * denominator
    floor_value = scaled.numerator // scaled.denominator
    candidates = {
        max(1, min(denominator - 1, floor_value + offset))
        for offset in (-1, 0, 1, 2)
    }
    return min(
        (Fraction(value, denominator) for value in candidates),
        key=lambda value: (
            abs((first_normal + (second_normal - first_normal) * value) - target),
            abs(value - k1_t),
            value,
        ),
    )


def exact_objective_score(
    record: dict[str, object],
    t_values: Sequence[Fraction],
    seed: dict[str, object],
    coordinates: Sequence[Sequence[float]],
    normal_endpoints: Sequence[tuple[Fraction, Fraction]],
) -> tuple[object, ...]:
    normal_values = [
        first + (second - first) * t
        for (first, second), t in zip(normal_endpoints, t_values)
    ]
    mean = sum(normal_values, Fraction(0)) / len(normal_values)
    maximum_deviation = max(abs(value - mean) for value in normal_values)
    k1_values = [Fraction(*point["k1_t"]) for point in seed["points"]]
    exact_displacements = []
    for index, point in enumerate(seed["points"]):
        first, second = point["edge"]
        length = Fraction.from_float(_BASE.distance(coordinates[first], coordinates[second]))
        exact_displacements.append(length * abs(t_values[index] - k1_values[index]))
    return (
        0 if record["passes_all_inherited_premutation_gates"] else 1,
        maximum_deviation,
        max(exact_displacements),
        sum(exact_displacements, Fraction(0)),
        tuple(t_values),
    )


def solve_bounded_nonuniform_family(
    seed: dict[str, object],
    faces: Sequence[Sequence[int]],
    coordinates: Sequence[Sequence[float]],
    frame,
    context: dict[str, object],
    config: dict[str, object],
) -> dict[str, object]:
    """Generate a finite deterministic family and retain exactly one record."""
    denominator = config["solver"]["edge_parameter_denominator"]
    intervals = config["solver"]["plane_sample_intervals"]
    n = frame[2]
    normal_endpoints = []
    for point in seed["points"]:
        first, second = point["edge"]
        normal_endpoints.append(
            (
                Fraction.from_float(_BASE.dot(coordinates[first], n)),
                Fraction.from_float(_BASE.dot(coordinates[second], n)),
            )
        )
    lower = min(value for pair in normal_endpoints for value in pair)
    upper = max(value for pair in normal_endpoints for value in pair)
    if lower == upper:
        raise RuntimeError("all fixed source edges have zero chart-normal span")

    generated: dict[tuple[Fraction, ...], str] = {}
    exact_k1 = tuple(Fraction(*point["k1_t"]) for point in seed["points"])
    generated[exact_k1] = "exact_k1_baseline"
    for sample in range(intervals + 1):
        target = lower + (upper - lower) * Fraction(sample, intervals)
        values = tuple(
            nearest_dyadic_parameter(
                target,
                normal_endpoints[index][0],
                normal_endpoints[index][1],
                exact_k1[index],
                denominator,
            )
            for index in range(70)
        )
        generated.setdefault(values, f"plane_sample_{sample}_of_{intervals}")
    if len(generated) > config["solver"]["maximum_generated_records"]:
        raise RuntimeError("bounded solver exceeded its record ceiling")

    best = None
    eligible_count = 0
    evaluated_parameter_records = []
    for t_values, origin in generated.items():
        record = independent_direct_evaluate(
            t_values, seed, faces, coordinates, frame, context, config
        )
        if record["passes_all_inherited_premutation_gates"]:
            eligible_count += 1
        score = exact_objective_score(
            record, t_values, seed, coordinates, normal_endpoints
        )
        evaluated_parameter_records.append(
            [fraction_record(value) for value in t_values]
        )
        if best is None or score < best[0]:
            best = (score, origin, record)
    if best is None:
        raise RuntimeError("bounded solver generated no records")
    return {
        "schema": "kira.avatar.r24.nonuniform_source_edge_solver_summary.v1",
        "numeric_semantics": config["solver"]["numeric_semantics"],
        "plane_sample_intervals": intervals,
        "edge_parameter_denominator": denominator,
        "generated_record_count": len(generated),
        "eligible_record_count": eligible_count,
        "objective_order": config["solver"]["lexicographic_objectives"],
        "objective_scope": config["solver"]["objective_scope"],
        "all_generated_records_directly_evaluated": True,
        "selection_domain_sha256": compact_sha256(evaluated_parameter_records),
        "proposed_record_origin": best[1],
        "proposed_record": best[2],
        "proposed_record_rejected": not best[2]["passes_all_inherited_premutation_gates"],
        "global_continuous_minimax_claimed": False,
        "global_gate_constrained_optimality_claimed": False,
        "finite_termination_reached": True,
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
        != "kira.avatar.r24.nonuniform_source_edge_feasibility.claim.v1"
        or claim.get("attempt_id") != config["attempt_id"]
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
    base = validate_config(config)
    immutable_before = verify_immutable_inputs(config)
    paths = validate_runtime_claim(config, config_path)

    # Imported only by a separately audited and explicitly guarded invocation.
    import bpy  # type: ignore

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
    config["chart"] = base["chart"]
    config["domains"] = base["domains"]
    context = build_source_context(faces, config, base)
    diagnostic = json.loads(
        project_path(config["immutable_bindings"]["attempt01_diagnostic"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    seed = derive_topology_seed(faces, context["collar"], diagnostic, config)
    solver_summary = solve_bounded_nonuniform_family(
        seed, faces, coordinates, frame, context, config
    )

    immutable_after = verify_immutable_inputs(config)
    if immutable_before != immutable_after:
        raise RuntimeError("immutable inputs changed during read-only feasibility run")
    proposed = solver_summary["proposed_record"]
    eligible = proposed["passes_all_inherited_premutation_gates"]
    report = {
        "schema": "kira.avatar.r24.nonuniform_source_edge_feasibility.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_PREMUTATION_NO_RENDER_NO_SAVE",
        "attempt_id": config["attempt_id"],
        "lane": config["lane"],
        "uniform_attempt_consumed": True,
        "uniform_level_family_terminal": True,
        "source_star_lane_terminal": True,
        "input_records": immutable_after,
        "topology_seed_sha256": config["topology_seed"]["canonical_payload_sha256"],
        "solver_summary": solver_summary,
        "proposed_record": proposed,
        "eligible_proposed_record": proposed if eligible else None,
        "status": (
            "ELIGIBLE_NONUNIFORM_RECORD_PREMUTATION_ONLY"
            if eligible
            else "NO_ELIGIBLE_NONUNIFORM_RECORD_FAIL_CLOSED"
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
                        "schema": "kira.avatar.r24.nonuniform_source_edge_feasibility.worker_failure.v1",
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
