"""Read-only annular-label isoline feasibility for Kira R24.

The preceding plane-defined contour families are terminal.  This lane uses
the exact proven E* minus D2 source annulus instead: D2 boundary vertices have the
topological label 0, E* outer-boundary vertices have label 1, and a finite set
of strict dyadic levels is interpolated over the original source triangles.
It is safe to import outside Blender and never mutates mesh data.
"""

from __future__ import annotations

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
from typing import Sequence


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


EDGE_WORKER = TOOLS / "blender_diagnose_kira_r24_edge_complete_carrier_domain_topology_feasibility01.py"
_SPEC = importlib.util.spec_from_file_location("r24_annular_label_edge_parent", EDGE_WORKER)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load preserved edge-complete parent worker")
_EDGE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_EDGE)
_PLANE = _EDGE._PARENT
_BASE = _EDGE._BASE
_NONUNIFORM = _EDGE._NONUNIFORM

DEFAULT_CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_annular_label_isoline_topology_feasibility_01_static/"
    "ANNULAR_LABEL_ISOLINE_TOPOLOGY_FEASIBILITY01_CONFIG.json"
)

LOCAL_FAILURE_ORDER = (
    "exact_annulus_identity",
    "exact_binary_boundary_label_partition",
    "all_crossing_edges_have_two_collar_owners",
    "one_closed_label_isoline_component",
    "exact_inner_outer_projected_separation",
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


def edge_config(config: dict[str, object]) -> dict[str, object]:
    binding = config["immutable_bindings"]["parent_edge_config"]
    verify_binding("parent_edge_config", binding)
    return json.loads(project_path(str(binding["path"])).read_text(encoding="utf-8"))


def consumed_edge_result(config: dict[str, object]) -> dict[str, object]:
    binding = config["immutable_bindings"]["consumed_edge_diagnostic"]
    verify_binding("consumed_edge_diagnostic", binding)
    report = json.loads(project_path(str(binding["path"])).read_text(encoding="utf-8"))
    expected = config["consumed_result"]
    solver = report.get("solver_summary") or {}
    records = solver.get("candidate_records") or []
    if (
        report.get("schema")
        != "kira.avatar.r24.edge_complete_carrier_domain_topology_feasibility.v1"
        or report.get("status") != expected["status"]
        or solver.get("candidate_record_count") != expected["candidate_record_count"]
        or solver.get("eligible_candidate_count") != 0
        or solver.get("all_predeclared_candidates_evaluated") is not True
        or solver.get("finite_termination_reached") is not True
        or solver.get("alternate_plane_evaluated") is not False
        or solver.get("adaptive_retry_used") is not False
        or solver.get("mesh_mutation_used") is not False
        or len(records) != expected["candidate_record_count"]
        or [row.get("dual_ring_expansion") for row in records]
        != expected["candidate_dual_ring_expansions"]
        or [row.get("component_count") for row in records]
        != expected["component_counts"]
        or any(row.get("candidate_eligible") is not False for row in records)
    ):
        raise RuntimeError("consumed edge-complete terminal result drifted")
    base = records[0].get("domain") or {}
    contract = config["annular_label_contract"]
    cycles = base.get("boundary_cycles") or []
    if (
        base.get("face_count") != contract["collar_face_count"]
        or base.get("face_ledger_sha256") != contract["collar_face_ledger_sha256"]
        or base.get("vertex_count") != contract["collar_vertex_count"]
        or base.get("face_component_count") != 1
        or base.get("euler_characteristic") != 0
        or base.get("boundary_cycle_count") != 2
        or base.get("exact_d2_inner_boundary_present") is not True
        or base.get("minimum_vertex_source_graph_rings_from_global_interface")
        != contract["minimum_source_graph_rings_from_global_interface"]
        or contract["inner_d2_boundary_cycle"] not in cycles
        or contract["outer_estar_boundary_cycle"] not in cycles
    ):
        raise RuntimeError("consumed exact annulus identity drifted")
    return report


def validate_config(
    config: dict[str, object],
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    if (
        config.get("schema")
        != "kira.avatar.r24.annular_label_isoline_topology_feasibility.static.v1"
        or config.get("status")
        != "STATIC_PACKAGE_PREPARED_FRESH_INDEPENDENT_AUDIT_REQUIRED_NOT_RUN"
        or config.get("lane")
        != "LOCAL_TRANSITION_ANNULAR_LABEL_ISOLINE_TOPOLOGY_FEASIBILITY"
        or config.get("attempt_id") != "annular_label_isoline_01"
        or config.get("edge_complete_parent_terminal") is not True
    ):
        raise RuntimeError("static package identity drifted")
    contract = config["annular_label_contract"]
    expected_levels = [[value, 32] for value in range(1, 32)]
    if (
        contract.get("kind")
        != "piecewise_linear_binary_boundary_label_on_exact_estar_minus_d2_annulus"
        or contract.get("candidate_levels") != expected_levels
        or contract.get("candidate_count") != 31
        or contract.get("inner_label") != [0, 1]
        or contract.get("outer_label") != [1, 1]
        or contract.get("plane_equation_used") is not False
        or contract.get("source_star_search_used") is not False
        or contract.get("alternate_topology_allowed") is not False
        or contract.get("randomness_allowed") is not False
        or contract.get("adaptive_retry_allowed") is not False
        or contract.get("mutation_package_allowed") is not False
    ):
        raise RuntimeError("bounded annular-label contract drifted")
    if any(bool(value) for value in config["scope"].values()):
        raise RuntimeError("forbidden static scope enabled")
    parent = edge_config(config)
    actual_parent, base = _EDGE.validate_config(parent)
    consumed_edge_result(config)
    return actual_parent, base, parent


def verify_immutable_inputs(config: dict[str, object]) -> dict[str, object]:
    lane = [
        {"name": name, **verify_binding(name, binding)}
        for name, binding in sorted(config["immutable_bindings"].items())
    ]
    parent = edge_config(config)
    parent_state = _EDGE.verify_immutable_inputs(parent)
    protected = []
    for name, expected in sorted(config["protected_inventories"].items()):
        actual = canonical_inventory(ROOT, str(expected["path"]))
        if (
            actual["file_count"] != expected["file_count"]
            or actual["total_bytes"] != expected["total_bytes"]
            or actual["compact_inventory_sha256"] != expected["sha256"]
        ):
            raise RuntimeError(f"protected inventory drifted: {name}")
        protected.append({"name": name, **actual})
    return {
        "lane_bindings": lane,
        "parent_lane_bindings": parent_state["lane_bindings"],
        "inherited_bindings": parent_state["inherited_bindings"],
        "protected_inventories": protected,
        "consumed_parent_runtime_integrity": parent_state[
            "consumed_parent_runtime_integrity"
        ],
    }


def exact_label_partition(
    faces: Sequence[Sequence[int]],
    context: dict[str, object],
    config: dict[str, object],
) -> tuple[dict[int, Fraction], set[int], set[int]]:
    contract = config["annular_label_contract"]
    inner = set(int(value) for value in contract["inner_d2_boundary_cycle"])
    outer = set(int(value) for value in contract["outer_estar_boundary_cycle"])
    collar_vertices = {
        vertex for face_index in context["collar"] for vertex in faces[face_index]
    }
    d2_vertices = set(context["d2_vertices"])
    envelope_vertices = set(context["envelope_vertices"])
    if (
        inner & outer
        or len(inner) != 32
        or len(outer) != 41
        or collar_vertices != inner | outer
        or len(collar_vertices) != 73
        or not inner <= d2_vertices
        or d2_vertices & outer
        or envelope_vertices != d2_vertices | outer
        or set(context["boundary_vertices"]) != outer
    ):
        raise RuntimeError("exact binary boundary-label partition is not present")
    labels = {vertex: Fraction(0) for vertex in d2_vertices}
    labels.update({vertex: Fraction(1) for vertex in outer})
    return labels, inner, outer


def _seed_for_component(
    points: dict[tuple[int, ...], dict[str, object]],
    segments: Sequence[dict[str, object]],
) -> dict[str, object]:
    return {
        "points": [
            {"edge": row["edge"], "k1_t": row["t"]}
            for row in sorted(points.values(), key=lambda value: value["key"])
        ],
        "segments": list(segments),
    }


def _candidate_failure_names(
    inherited: Sequence[str], local: Sequence[str]
) -> list[str]:
    inherited_order = list(_PLANE.FAILURE_ORDER)
    return [name for name in LOCAL_FAILURE_ORDER if name in local] + [
        name for name in inherited_order if name in inherited
    ]


def evaluate_level(
    level: Fraction,
    faces: Sequence[Sequence[int]],
    coordinates: Sequence[Sequence[float]],
    frame,
    context: dict[str, object],
    labels: dict[int, Fraction],
    outer_cycle: Sequence[int],
    config: dict[str, object],
) -> dict[str, object]:
    local_failures: set[str] = set()
    inherited_failures: set[str] = set()
    try:
        points, segments, build_failures, equal_vertices = _PLANE.build_actual_segments(
            faces, labels, level, context
        )
        for record in points.values():
            record["exact_label_residual"] = record.pop("exact_plane_residual")
            record["exact_label_equation_verified"] = record.pop(
                "exact_plane_equation_verified"
            )
    except Exception:
        points, segments, build_failures, equal_vertices = {}, [], [], []
        local_failures.add("exact_binary_boundary_label_partition")
    inherited_failures.update(build_failures)
    if "complete_two_collar_face_edge_ownership" in inherited_failures:
        local_failures.add("all_crossing_edges_have_two_collar_owners")
    components = _PLANE.extract_components(segments)
    if len(components) != 1 or not components[0]["closed_degree_two_cycle"]:
        local_failures.add("one_closed_label_isoline_component")
        inherited_failures.add("single_component_d2_envelope_separation")

    component_records = []
    for component in components:
        seed = _seed_for_component(points, segments)
        k1_distances = _PLANE.k1_graph_distances(
            seed, faces, coordinates, context["envelope"]
        )
        inherited = _PLANE.evaluate_component(
            component,
            points,
            sorted(inherited_failures, key=list(_PLANE.FAILURE_ORDER).index),
            faces,
            coordinates,
            labels,
            level,
            frame,
            context,
            seed,
            config,
            k1_distances,
        )
        outer_ok = _EDGE.outer_boundary_outside_component(
            component,
            points,
            coordinates,
            frame,
            outer_cycle,
            config["chart"]["nonadjacent_segment_minimum_distance_m"],
        )
        if not outer_ok or not inherited["d2_projected_strictly_inside"]:
            local_failures.add("exact_inner_outer_projected_separation")
            inherited_failures.add("single_component_d2_envelope_separation")
        component_records.append({**inherited, "estar_outer_boundary_strictly_outside": outer_ok})

    inherited_names = set(inherited_failures)
    for record in component_records:
        inherited_names.update(record["failure_names"])
    failures = _candidate_failure_names(inherited_names, local_failures)
    point_records = sorted(points.values(), key=lambda row: row["key"])
    serialized = {
        "level": [level.numerator, level.denominator],
        "point_keys": [row["key"] for row in point_records],
        "segments": segments,
    }
    eligible = len(components) == 1 and not failures
    return {
        "schema": "kira.avatar.r24.annular_label_isoline.candidate.v1",
        "level": [level.numerator, level.denominator],
        "candidate_sha256": compact_sha256(serialized),
        "actual_point_count": len(points),
        "actual_segment_count": len(segments),
        "equal_to_target_vertex_count": len(equal_vertices),
        "equal_to_target_vertices": equal_vertices,
        "component_count": len(components),
        "all_actual_components_evaluated": len(component_records) == len(components),
        "actual_point_records": point_records,
        "segment_records": segments,
        "component_records": component_records,
        "failure_names": failures,
        "candidate_eligible": eligible,
    }


def evaluate_annular_levels(
    faces: Sequence[Sequence[int]],
    coordinates: Sequence[Sequence[float]],
    frame,
    context: dict[str, object],
    config: dict[str, object],
) -> dict[str, object]:
    labels, inner, outer = exact_label_partition(faces, context, config)
    outer_cycle = list(config["annular_label_contract"]["outer_estar_boundary_cycle"])
    levels = [Fraction(*value) for value in config["annular_label_contract"]["candidate_levels"]]
    candidates = [
        evaluate_level(level, faces, coordinates, frame, context, labels, outer_cycle, config)
        for level in levels
    ]
    eligible = [row for row in candidates if row["candidate_eligible"]]

    def score(row: dict[str, object]) -> tuple[object, ...]:
        level = Fraction(*row["level"])
        component = row["component_records"][0]
        return (
            abs(level - Fraction(1, 2)),
            -float(component["minimum_projected_interior_angle_degrees"]),
            float(component["maximum_absolute_chart_deviation_m"]),
            row["candidate_sha256"],
        )

    selected = min(eligible, key=score) if eligible else None
    return {
        "schema": "kira.avatar.r24.annular_label_isoline.solver_summary.v1",
        "construction": "exact_binary_boundary_label_piecewise_linear_isoline",
        "inner_d2_boundary_vertex_count": len(inner),
        "outer_estar_boundary_vertex_count": len(outer),
        "candidate_levels": [[value.numerator, value.denominator] for value in levels],
        "candidate_record_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        "all_predeclared_candidates_evaluated": len(candidates) == len(levels) == 31,
        "candidate_records": candidates,
        "selected_eligible_candidate": selected,
        "finite_termination_reached": True,
        "plane_equation_evaluated": False,
        "source_star_search_evaluated": False,
        "alternate_topology_evaluated": False,
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
        claim.get("schema") != "kira.avatar.r24.annular_label_isoline.claim.v1"
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
    actual_parent, base, _ = validate_config(config)
    immutable_before = verify_immutable_inputs(config)
    paths = validate_runtime_claim(config, config_path)
    consumed_edge_result(config)

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
    solver = evaluate_annular_levels(faces, coordinates, frame, context, config)

    immutable_after = verify_immutable_inputs(config)
    if immutable_before != immutable_after:
        raise RuntimeError("immutable inputs changed during read-only annular-label run")
    selected = solver["selected_eligible_candidate"]
    report = {
        "schema": "kira.avatar.r24.annular_label_isoline_topology_feasibility.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_PREMUTATION_NO_RENDER_NO_SAVE",
        "attempt_id": config["attempt_id"],
        "lane": config["lane"],
        "edge_complete_parent_consumed": True,
        "input_records": immutable_after,
        "solver_summary": solver,
        "eligible_proposed_record": selected,
        "status": (
            "ELIGIBLE_ANNULAR_LABEL_ISOLINE_PREMUTATION_ONLY"
            if selected is not None
            else "NO_ELIGIBLE_ANNULAR_LABEL_ISOLINE_FAIL_CLOSED"
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
                        "schema": "kira.avatar.r24.annular_label_isoline.worker_failure.v1",
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
