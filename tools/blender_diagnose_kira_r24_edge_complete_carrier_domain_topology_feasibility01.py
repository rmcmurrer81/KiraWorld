"""Read-only bounded carrier-domain topology feasibility for Kira R24.

The exact audited actual-plane result is terminal for its strict 73-face
collar.  This lane keeps that exact plane and enumerates only the predeclared
face-dual expansions 0..4, asking whether any expanded carrier gives every
crossing edge two owners and exactly one closed simple cycle while preserving
all inherited gates.  The module is safe to import outside Blender.
"""

from __future__ import annotations

from collections import defaultdict, deque
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


PARENT_WORKER = TOOLS / "blender_diagnose_kira_r24_actual_plane_contour_topology_feasibility01.py"
_SPEC = importlib.util.spec_from_file_location("r24_edge_complete_parent", PARENT_WORKER)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load preserved actual-plane feasibility worker")
_PARENT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PARENT)
_NONUNIFORM = _PARENT._PARENT
_BASE = _PARENT._BASE

DEFAULT_CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_edge_complete_carrier_domain_topology_feasibility_01_static/"
    "EDGE_COMPLETE_CARRIER_DOMAIN_TOPOLOGY_FEASIBILITY01_CONFIG.json"
)

DOMAIN_FAILURE_ORDER = (
    "carrier_domain_base_or_d2_identity",
    "carrier_domain_global_seam_clearance",
    "carrier_domain_connected_annulus",
    "carrier_domain_exact_d2_inner_boundary",
    "candidate_outer_boundary_separation",
)
FAILURE_ORDER = DOMAIN_FAILURE_ORDER + tuple(_PARENT.FAILURE_ORDER)


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
    binding = config["immutable_bindings"]["parent_actual_plane_config"]
    verify_binding("parent_actual_plane_config", binding)
    return json.loads(project_path(str(binding["path"])).read_text(encoding="utf-8"))


def consumed_actual_plane_result(config: dict[str, object]) -> dict[str, object]:
    binding = config["immutable_bindings"]["consumed_actual_plane_diagnostic"]
    verify_binding("consumed_actual_plane_diagnostic", binding)
    report = json.loads(project_path(str(binding["path"])).read_text(encoding="utf-8"))
    solver = report.get("solver_summary") or {}
    expected = config["consumed_result"]
    target = solver.get("target_plane") or {}
    if (
        report.get("schema")
        != "kira.avatar.r24.actual_plane_contour_topology_feasibility.v1"
        or report.get("status") != expected["status"]
        or solver.get("collar_face_count") != expected["declared_collar_face_count"]
        or len(solver.get("collar_face_visit_ledger") or [])
        != expected["collar_faces_visited"]
        or solver.get("actual_segment_count") != expected["actual_segment_count"]
        or solver.get("actual_point_count") != expected["actual_point_count"]
        or solver.get("component_count") != expected["component_count"]
        or solver.get("eligible_component_count") != expected["eligible_component_count"]
        or solver.get("global_failure_names") != expected["global_failure_names"]
        or solver.get("collar_face_visit_ledger_sha256")
        != expected["collar_face_visit_ledger_sha256"]
        or target.get("target_payload_sha256")
        != expected["target_plane_payload_sha256"]
        or solver.get("selected_eligible_component") is not None
    ):
        raise RuntimeError("consumed actual-plane result identity drifted")
    truth = report.get("truth") or {}
    if any(
        truth.get(key) is not False
        for key in (
            "mesh_mutated",
            "datablock_mutated",
            "blend_saved",
            "rendered",
            "exported",
            "runtime_changed",
            "body_repair_proven",
            "owner_approval_claimed",
        )
    ):
        raise RuntimeError("consumed actual-plane read-only truth drifted")
    return report


def verify_parent_runtime_integrity(config: dict[str, object]) -> dict[str, object]:
    binding = config["immutable_bindings"]["parent_actual_plane_external_integrity"]
    verified = verify_binding("parent_actual_plane_external_integrity", binding)
    path = project_path(str(binding["path"]))
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema")
        != "kira.avatar.r24.actual_plane_contour_topology_feasibility.external_integrity.v1"
        or manifest.get("before") != manifest.get("after")
        or manifest.get("pre_post_exact") is not True
        or manifest.get("blender_invocation_count") != 1
        or manifest.get("blender_exit_code") != 0
        or manifest.get("native_invocation_error") is not None
        or manifest.get("post_capture_errors", []) != []
        or manifest.get("finalization_errors") != []
        or manifest.get("retry_permitted") is not False
    ):
        raise RuntimeError("parent actual-plane external-integrity truth drifted")

    recursive_files = []
    for section in ("lane_bindings",):
        rows = manifest["before"].get(section)
        if not isinstance(rows, list):
            raise RuntimeError(f"parent integrity missing {section}")
        for row in rows:
            recursive_files.append(
                {"section": section, "name": row["name"], **verify_binding(
                    f"parent_integrity:{section}:{row['name']}", row
                )}
            )

    inventories = []
    rows = manifest["before"].get("protected_inventories")
    if not isinstance(rows, list):
        raise RuntimeError("parent integrity missing protected inventories")
    for row in rows:
        actual = canonical_inventory(ROOT, str(row["root"]))
        expected = {
            "root": row["root"],
            "file_count": row["file_count"],
            "total_bytes": row["total_bytes"],
            "compact_inventory_sha256": row["compact_inventory_sha256"],
        }
        if actual != expected:
            raise RuntimeError(f"parent protected inventory drifted: {row['root']}")
        inventories.append(actual)

    outputs = []
    if not isinstance(manifest.get("output_files"), list) or len(manifest["output_files"]) != 5:
        raise RuntimeError("parent output manifest drifted")
    for row in manifest["output_files"]:
        artifact = path.parent / str(row["name"])
        actual = {
            "name": row["name"],
            "bytes": artifact.stat().st_size if artifact.is_file() else None,
            "sha256": sha256_file(artifact) if artifact.is_file() else None,
        }
        if actual != row:
            raise RuntimeError(f"parent output drifted: {row['name']}")
        outputs.append(actual)
    return {
        "manifest": verified,
        "recursive_files": recursive_files,
        "protected_inventories": inventories,
        "output_files": outputs,
    }


def validate_config(config: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    if config.get("schema") != "kira.avatar.r24.edge_complete_carrier_domain_topology_feasibility.static.v1":
        raise RuntimeError("edge-complete carrier schema drifted")
    if (
        config.get("attempt_id") != "edge_complete_carrier_domain_01"
        or config.get("lane")
        != "LOCAL_TRANSITION_EDGE_COMPLETE_CARRIER_DOMAIN_TOPOLOGY_FEASIBILITY"
        or config.get("actual_plane_parent_terminal") is not True
        or config.get("parent_result_status")
        != "NO_ELIGIBLE_ACTUAL_PLANE_CONTOUR_FAIL_CLOSED"
    ):
        raise RuntimeError("lane/attempt/parent terminal identity drifted")

    parent = parent_config(config)
    actual_parent, base = _PARENT.validate_config(parent)
    if compact_sha256(parent) != config["parent_config_canonical_sha256"]:
        raise RuntimeError("parent config canonical payload drifted")
    if config["chart"] != parent["chart"] or config["hard_gates"] != parent["hard_gates"]:
        raise RuntimeError("inherited chart or hard gates changed")

    contract = config["carrier_domain_contract"]
    if (
        contract["kind"]
        != "bounded_edge_complete_dual_ring_expansion_of_exact_73_face_collar"
        or contract["source_plane_origin"] != "consumed_exact_actual_plane_target"
        or contract["base_collar_face_count"] != 73
        or contract["candidate_dual_ring_expansions"] != [0, 1, 2, 3, 4]
        or contract["candidate_count"] != 5
        or contract["maximum_dual_ring_expansion"] != 4
        or contract["minimum_vertex_source_graph_rings_from_global_interface"] != 4
        or not all(
            contract[key]
            for key in (
                "require_base_collar_subset",
                "exclude_d2_faces",
                "require_connected_annulus",
                "require_exact_d2_inner_boundary",
                "require_complete_two_face_ownership_for_every_crossing_edge",
                "require_exactly_one_closed_degree_two_cycle",
                "require_original_estar_boundary_outside_cycle",
                "require_candidate_outer_boundary_outside_cycle",
                "preserve_original_exterior_adjacent_gate",
            )
        )
        or any(
            contract[key]
            for key in (
                "endpoint_clamping_allowed",
                "alternate_plane_allowed",
                "randomness_allowed",
                "adaptive_retry_allowed",
                "free_world_space_points_allowed",
                "mutation_package_allowed",
            )
        )
    ):
        raise RuntimeError("bounded carrier-domain contract drifted")
    if contract["selection_order"] != [
        "all_inherited_and_carrier_domain_hard_gates_pass",
        "minimum_dual_ring_expansion",
        "minimum_added_face_count",
        "minimum_canonical_candidate_sha256",
    ]:
        raise RuntimeError("carrier-domain selection order drifted")

    output = config["output_contract"]
    if (
        output["root"]
        != "RecoverySprint/continuation_20260808/kira_r24_edge_complete_carrier_domain_topology_feasibility/edge_complete_carrier_domain_01"
        or output["runtime_cache_root"]
        != "RecoverySprint/runtime_cache/kira_r24_edge_complete_carrier_domain_topology_feasibility/edge_complete_carrier_domain_01"
        or output["append_only"] is not True
    ):
        raise RuntimeError("append-only output contract drifted")
    expected_names = {
        "attempt_started": "ATTEMPT_STARTED.json",
        "diagnostic": "EDGE_COMPLETE_CARRIER_DOMAIN_TOPOLOGY_FEASIBILITY.json",
        "worker_failure": "WORKER_FAILURE.json",
        "wrapper_failure": "WRAPPER_FAILURE.json",
        "stdout": "BLENDER_STDOUT.log",
        "stderr": "BLENDER_STDERR.log",
        "wrapper_completion": "WRAPPER_COMPLETION.json",
        "external_integrity": "EXTERNAL_PRE_POST_INTEGRITY.json",
    }
    if any(output.get(key) != value for key, value in expected_names.items()):
        raise RuntimeError("output filename contract drifted")

    launch = config["launch_contract"]
    if (
        launch["blender_executable"]
        != "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"
        or launch["worker"]
        != "tools/blender_diagnose_kira_r24_edge_complete_carrier_domain_topology_feasibility01.py"
        or launch["wrapper"]
        != "RecoverySprint/continuation_20260808/kira_r24_edge_complete_carrier_domain_topology_feasibility_01_static/run_edge_complete_carrier_domain_topology_feasibility01_once.ps1"
        or launch["maximum_blender_invocations"] != 1
        or launch["automatic_retry_allowed"] is not False
        or launch["invocation_guard"]
        != "INVOKE_AUDITED_EDGE_COMPLETE_CARRIER_DOMAIN_FEASIBILITY_01_ONCE"
        or launch["blender_arguments"]
        != ["--background", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1", "--python"]
    ):
        raise RuntimeError("guarded launch contract drifted")
    if any(config["scope"].values()):
        raise RuntimeError("forbidden scope became enabled")
    consumed_actual_plane_result(config)
    return actual_parent, base


def verify_immutable_inputs(config: dict[str, object]) -> dict[str, object]:
    parent = parent_config(config)
    actual_parent, base = validate_config(config)
    lane = {
        name: verify_binding(name, binding)
        for name, binding in sorted(config["immutable_bindings"].items())
    }
    parent_state = _PARENT.verify_immutable_inputs(parent)
    parent_runtime = verify_parent_runtime_integrity(config)
    protected = []
    for name, row in sorted(config["protected_inventories"].items()):
        actual = canonical_inventory(ROOT, row["path"])
        expected = {
            "root": row["path"],
            "file_count": row["file_count"],
            "total_bytes": row["total_bytes"],
            "compact_inventory_sha256": row["sha256"],
        }
        if actual != expected:
            raise RuntimeError(f"protected inventory drifted: {name}")
        protected.append({"name": name, **actual})
    return {
        "lane_bindings": lane,
        "parent_lane_bindings": parent_state["lane_bindings"],
        "inherited_bindings": parent_state["inherited_bindings"],
        "protected_inventories": protected,
        "source_mesh": base["source_mesh"],
        "consumed_parent_runtime_integrity": parent_runtime,
        "actual_parent_config": actual_parent,
    }


def canonical_cycle_int(cycle: Sequence[int]) -> list[int]:
    values = list(cycle)
    if not values:
        return []
    minimum = min(values)
    candidates = []
    for ordered in (values, list(reversed(values))):
        index = ordered.index(minimum)
        candidates.append(ordered[index:] + ordered[:index])
    return min(candidates)


def boundary_cycles(
    faces: Sequence[Sequence[int]], selected: set[int]
) -> tuple[list[list[int]], list[tuple[int, int]], bool]:
    incidence = _BASE.edge_incidence(faces, selected)
    boundary = sorted(edge for edge, owners in incidence.items() if len(owners) == 1)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for first, second in boundary:
        adjacency[first].add(second)
        adjacency[second].add(first)
    if not adjacency:
        return [], boundary, False
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        return [], boundary, False
    cycles = []
    unseen = set(adjacency)
    while unseen:
        start = min(unseen)
        cycle = [start]
        previous = None
        current = start
        while True:
            choices = sorted(value for value in adjacency[current] if value != previous)
            if not choices:
                return [], boundary, False
            following = choices[0]
            if following == start:
                break
            if following in cycle:
                return [], boundary, False
            cycle.append(following)
            previous, current = current, following
        unseen -= set(cycle)
        cycles.append(canonical_cycle_int(cycle))
    return sorted(cycles), boundary, True


def cycle_edges(cycle: Sequence[int]) -> set[tuple[int, int]]:
    return {
        _BASE.canonical_edge(cycle[index], cycle[(index + 1) % len(cycle)])
        for index in range(len(cycle))
    }


def full_face_dual_adjacency(
    face_count: int, incidence: dict[tuple[int, int], list[int]]
) -> dict[int, set[int]]:
    adjacency = {index: set() for index in range(face_count)}
    for owners in incidence.values():
        if len(owners) == 2:
            first, second = owners
            adjacency[first].add(second)
            adjacency[second].add(first)
    return adjacency


def vertex_seam_distances(
    faces: Sequence[Sequence[int]], context: dict[str, object]
) -> dict[int, int]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for edge in context["full_incidence"]:
        first, second = edge
        adjacency[first].add(second)
        adjacency[second].add(first)
    interface = context["domain"]["global_interface"]["boundary_vertex_indices"]
    return _BASE.graph_distances(adjacency, interface)


def bounded_candidate_domains(
    faces: Sequence[Sequence[int]],
    context: dict[str, object],
    config: dict[str, object],
) -> list[dict[str, object]]:
    contract = config["carrier_domain_contract"]
    seam_distance = vertex_seam_distances(faces, context)
    minimum = contract["minimum_vertex_source_graph_rings_from_global_interface"]
    d2 = set(context["d2"])
    base = set(context["collar"])
    permitted = {
        face_index
        for face_index, face in enumerate(faces)
        if face_index not in d2
        and min(seam_distance[vertex] for vertex in face) >= minimum
    }
    dual = full_face_dual_adjacency(len(faces), context["full_incidence"])
    distance = {face: 0 for face in sorted(base)}
    queue = deque(sorted(base))
    while queue:
        current = queue.popleft()
        if distance[current] >= contract["maximum_dual_ring_expansion"]:
            continue
        for neighbor in sorted(dual[current]):
            if neighbor not in permitted or neighbor in distance:
                continue
            distance[neighbor] = distance[current] + 1
            queue.append(neighbor)
    return [
        {
            "dual_ring_expansion": radius,
            "faces": {face for face, value in distance.items() if value <= radius},
            "permitted_face_count": len(permitted),
            "reached_face_count": len(distance),
            "seam_distance": seam_distance,
        }
        for radius in contract["candidate_dual_ring_expansions"]
    ]


def carrier_domain_summary(
    faces: Sequence[Sequence[int]],
    candidate: set[int],
    context: dict[str, object],
    seam_distance: dict[int, int],
    config: dict[str, object],
) -> dict[str, object]:
    base = set(context["collar"])
    d2 = set(context["d2"])
    failures = set()
    if not base <= candidate or candidate & d2:
        failures.add("carrier_domain_base_or_d2_identity")
    vertices = {vertex for face in candidate for vertex in faces[face]}
    minimum_seam = min((seam_distance[vertex] for vertex in vertices), default=-1)
    if minimum_seam < config["carrier_domain_contract"]["minimum_vertex_source_graph_rings_from_global_interface"]:
        failures.add("carrier_domain_global_seam_clearance")
    topology = _BASE.selected_topology(faces, candidate)
    cycles, boundary, boundary_valid = boundary_cycles(faces, candidate)
    annulus = (
        topology["face_components"] == 1
        and topology["euler"] == 0
        and boundary_valid
        and len(cycles) == 2
    )
    if not annulus:
        failures.add("carrier_domain_connected_annulus")
    d2_topology = _BASE.selected_topology(faces, d2)
    d2_edges = set(d2_topology["boundary"])
    matching = [cycle for cycle in cycles if cycle_edges(cycle) == d2_edges]
    if len(matching) != 1:
        failures.add("carrier_domain_exact_d2_inner_boundary")
    outer = [cycle for cycle in cycles if cycle_edges(cycle) != d2_edges]
    if len(outer) != 1:
        outer = []
    return {
        "face_count": len(candidate),
        "added_face_count": len(candidate - base),
        "face_ledger": sorted(candidate),
        "face_ledger_sha256": compact_sha256(sorted(candidate)),
        "vertex_count": len(vertices),
        "minimum_vertex_source_graph_rings_from_global_interface": minimum_seam,
        "face_component_count": topology["face_components"],
        "euler_characteristic": topology["euler"],
        "boundary_edge_count": len(boundary),
        "boundary_cycle_count": len(cycles),
        "boundary_cycles": cycles,
        "exact_d2_inner_boundary_present": len(matching) == 1,
        "outer_boundary_cycle": outer[0] if outer else [],
        "domain_failure_names": [name for name in DOMAIN_FAILURE_ORDER if name in failures],
    }


def outer_boundary_outside_component(
    component: dict[str, object],
    points: dict[tuple[int, ...], dict[str, object]],
    coordinates: Sequence[Sequence[float]],
    frame,
    outer_boundary: Sequence[int],
    epsilon: float,
) -> bool:
    ordered = [tuple(value) for value in component.get("ordered_loop") or []]
    if len(ordered) < 3 or not outer_boundary:
        return False
    world = []
    for key in ordered:
        record = points[key]
        first, second = record["edge"]
        t = Fraction(*record["t"])
        world.append(
            _BASE.vector_add(
                _BASE.vector_scale(coordinates[first], float(Fraction(1) - t)),
                _BASE.vector_scale(coordinates[second], float(t)),
            )
        )
    origin = tuple(math.fsum(point[axis] for point in world) / len(world) for axis in range(3))
    u, v, _, _ = frame
    polygon = [
        (
            _BASE.dot(_BASE.vector_sub(point, origin), u),
            _BASE.dot(_BASE.vector_sub(point, origin), v),
        )
        for point in world
    ]
    projected_outer = [
        (
            _BASE.dot(_BASE.vector_sub(coordinates[vertex], origin), u),
            _BASE.dot(_BASE.vector_sub(coordinates[vertex], origin), v),
        )
        for vertex in outer_boundary
    ]
    for point in projected_outer:
        if _PARENT.strict_point_in_polygon(point, polygon, epsilon):
            return False
        if any(
            _BASE.point_segment_distance_2d(
                point,
                polygon[index],
                polygon[(index + 1) % len(polygon)],
            )
            <= epsilon
            for index in range(len(polygon))
        ):
            return False
    for outer_index in range(len(projected_outer)):
        outer_first = projected_outer[outer_index]
        outer_second = projected_outer[(outer_index + 1) % len(projected_outer)]
        for contour_index in range(len(polygon)):
            if _BASE.segment_distance_2d(
                outer_first,
                outer_second,
                polygon[contour_index],
                polygon[(contour_index + 1) % len(polygon)],
            ) <= epsilon:
                return False
    return True


def evaluate_candidate_domain(
    candidate_data: dict[str, object],
    seed: dict[str, object],
    faces: Sequence[Sequence[int]],
    coordinates: Sequence[Sequence[float]],
    normal_by_vertex: dict[int, Fraction],
    target: Fraction,
    frame,
    base_context: dict[str, object],
    config: dict[str, object],
) -> dict[str, object]:
    candidate = set(candidate_data["faces"])
    domain = carrier_domain_summary(
        faces,
        candidate,
        base_context,
        candidate_data["seam_distance"],
        config,
    )
    candidate_vertices = {vertex for face in candidate for vertex in faces[face]}
    expanded_context = dict(base_context)
    expanded_context["collar"] = candidate
    expanded_context["envelope"] = candidate | set(base_context["d2"])
    expanded_context["envelope_vertices"] = candidate_vertices | set(base_context["d2_vertices"])
    expanded_context["minimum_seam_rings"] = domain[
        "minimum_vertex_source_graph_rings_from_global_interface"
    ]
    points, segments, global_failures, equal_vertices = _PARENT.build_actual_segments(
        faces, normal_by_vertex, target, expanded_context
    )
    components = _PARENT.extract_components(segments)
    if len(components) != 1:
        global_failures = sorted(
            set(global_failures) | {"single_component_d2_envelope_separation"},
            key=_PARENT.FAILURE_ORDER.index,
        )
    distances = _PARENT.k1_graph_distances(
        seed, faces, coordinates, expanded_context["envelope"]
    )
    records = []
    for component in components:
        record = _PARENT.evaluate_component(
            component,
            points,
            global_failures,
            faces,
            coordinates,
            normal_by_vertex,
            target,
            frame,
            expanded_context,
            seed,
            config,
            distances,
        )
        outside = outer_boundary_outside_component(
            component,
            points,
            coordinates,
            frame,
            domain["outer_boundary_cycle"],
            config["chart"]["nonadjacent_segment_minimum_distance_m"],
        )
        combined = set(domain["domain_failure_names"]) | set(record["failure_names"])
        if not outside:
            combined.add("candidate_outer_boundary_separation")
        ordered_failures = [name for name in FAILURE_ORDER if name in combined]
        record["candidate_outer_boundary_projected_outside"] = outside
        record["hard_failure_order"] = list(FAILURE_ORDER)
        record["hard_failure_vector"] = [1 if name in combined else 0 for name in FAILURE_ORDER]
        record["failure_names"] = ordered_failures
        record["passes_all_inherited_and_carrier_domain_gates"] = not ordered_failures
        record["passes_all_inherited_premutation_gates"] = not ordered_failures
        records.append(record)

    eligible = [row for row in records if row["passes_all_inherited_and_carrier_domain_gates"]]
    candidate_digest = compact_sha256(
        {
            "radius": candidate_data["dual_ring_expansion"],
            "faces": domain["face_ledger"],
            "component_digests": [row["component_sha256"] for row in records],
        }
    )
    return {
        "schema": "kira.avatar.r24.edge_complete_carrier_domain.candidate.v1",
        "dual_ring_expansion": candidate_data["dual_ring_expansion"],
        "candidate_sha256": candidate_digest,
        "domain": domain,
        "target_equal_candidate_vertices": equal_vertices,
        "actual_segment_count": len(segments),
        "actual_point_count": len(points),
        "actual_point_records": [points[key] for key in sorted(points)],
        "component_count": len(components),
        "eligible_component_count": len(eligible),
        "all_actual_components_evaluated": True,
        "global_contour_failures": global_failures,
        "component_records": records,
        "eligible_component": eligible[0] if len(eligible) == 1 else None,
        "candidate_eligible": len(eligible) == 1,
    }


def evaluate_edge_complete_domains(
    seed: dict[str, object],
    faces: Sequence[Sequence[int]],
    coordinates: Sequence[Sequence[float]],
    frame,
    context: dict[str, object],
    config: dict[str, object],
    consumed: dict[str, object],
) -> dict[str, object]:
    target, target_record, normal_by_vertex = _PARENT.derive_target_plane(
        seed, coordinates, frame, parent_config(config)
    )
    consumed_target = consumed["solver_summary"]["target_plane"]
    if target_record != consumed_target:
        raise RuntimeError("exact target plane no longer matches consumed diagnostic")
    candidates = [
        evaluate_candidate_domain(
            row,
            seed,
            faces,
            coordinates,
            normal_by_vertex,
            target,
            frame,
            context,
            config,
        )
        for row in bounded_candidate_domains(faces, context, config)
    ]
    eligible = [row for row in candidates if row["candidate_eligible"]]
    selected = min(
        eligible,
        key=lambda row: (
            row["dual_ring_expansion"],
            row["domain"]["added_face_count"],
            row["candidate_sha256"],
        ),
    ) if eligible else None
    return {
        "schema": "kira.avatar.r24.edge_complete_carrier_domain.solver_summary.v1",
        "target_plane": target_record,
        "candidate_dual_ring_expansions": [row["dual_ring_expansion"] for row in candidates],
        "candidate_record_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        "all_predeclared_candidates_evaluated": len(candidates) == 5,
        "candidate_records": candidates,
        "selected_eligible_candidate": selected,
        "finite_termination_reached": True,
        "alternate_plane_evaluated": False,
        "endpoint_clamping_used": False,
        "adaptive_retry_used": False,
        "mesh_mutation_used": False,
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
        "diagnostic", "worker_failure", "wrapper_failure", "stdout", "stderr",
        "wrapper_completion", "external_integrity",
    ):
        if paths[name].exists():
            raise RuntimeError(f"final runtime evidence existed before worker: {name}")
    claim = json.loads(paths["attempt_started"].read_text(encoding="utf-8"))
    if (
        claim.get("schema")
        != "kira.avatar.r24.edge_complete_carrier_domain_topology_feasibility.claim.v1"
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
    actual_parent, base = validate_config(config)
    immutable_before = verify_immutable_inputs(config)
    paths = validate_runtime_claim(config, config_path)
    consumed = consumed_actual_plane_result(config)

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
    context = _NONUNIFORM.build_source_context(faces, actual_parent, base)
    uniform_diagnostic = json.loads(
        project_path(actual_parent["immutable_bindings"]["attempt01_diagnostic"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    seed = _NONUNIFORM.derive_topology_seed(
        faces, context["collar"], uniform_diagnostic, actual_parent
    )
    solver = evaluate_edge_complete_domains(
        seed, faces, coordinates, frame, context, config, consumed
    )

    immutable_after = verify_immutable_inputs(config)
    if immutable_before != immutable_after:
        raise RuntimeError("immutable inputs changed during read-only carrier-domain run")
    selected = solver["selected_eligible_candidate"]
    report = {
        "schema": "kira.avatar.r24.edge_complete_carrier_domain_topology_feasibility.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_PREMUTATION_NO_RENDER_NO_SAVE",
        "attempt_id": config["attempt_id"],
        "lane": config["lane"],
        "actual_plane_parent_consumed": True,
        "input_records": immutable_after,
        "solver_summary": solver,
        "eligible_proposed_record": selected,
        "status": (
            "ELIGIBLE_EDGE_COMPLETE_CARRIER_DOMAIN_PREMUTATION_ONLY"
            if selected is not None
            else "NO_ELIGIBLE_EDGE_COMPLETE_CARRIER_DOMAIN_FAIL_CLOSED"
        ),
        "truth": {
            "mesh_mutated": False,
            "datablock_mutated": False,
            "blend_saved": False,
            "rendered": False,
            "exported": False,
            "runtime_changed": False,
            "mutation_package_prepared": False,
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
        print(json.dumps(run(config_path), sort_keys=True))
    except Exception as exc:
        try:
            config = load_config(config_path)
            validate_config(config)
            paths = runtime_output_paths(config)
            if paths["root"].is_dir() and not paths["worker_failure"].exists():
                write_new_json(
                    paths["worker_failure"],
                    {
                        "schema": "kira.avatar.r24.edge_complete_carrier_domain_topology_feasibility.worker_failure.v1",
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
