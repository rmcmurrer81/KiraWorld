"""Hash-bound Attempt 29 chart-mismatch capture wrapper.

The wrapper derives the sealed Attempt 28 worker and instruments its existing
fatal chart-alignment boundary.  Blender remains lazily imported only inside
the derived live entry point.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260808"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT29_CONFIG.json"
)
ATTEMPT28_WORKER = (
    ROOT
    / "tools"
    / "blender_diagnose_kira_r24_blackproject_replacement_boundary_attempt28.py"
)
EXPECTED_CONFIG_SHA256 = "c661c47c68b4468f96e3c168a2ca1d7329e508a4695d382142abe608063d9358"
EXPECTED_ATTEMPT28_WORKER_SHA256 = "ea2b14773a56f955b7e68e756d11519f8abb8653e983b70285e5fd416af6e521"
ATTEMPT28_CONFIG_SHA256 = "08ab7d73637d41accc10a3e52058e9a1e0b3b3bafcd8b009649881d0e0af7a11"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = (ROOT / value).resolve(strict=True)
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 29 binding escapes project: {value}")
    return path


def load_overlay(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 29 requires the exact sealed config path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 29 config hash drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_overlay(config)
    return config


def validate_overlay(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_29"
        or config.get("status") != "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 29 identity drifted")
    scope = config["scope"]
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "read_existing_source_mesh_allowed_during_later_reviewed_run",
        "in_memory_scene_open_allowed_during_later_reviewed_run",
        "chart_mismatch_capture_only",
    )
    forbidden = (
        "body_geometry_mutation_allowed",
        "patch_geometry_mutation_allowed",
        "blender_datablock_transform_assignment_allowed",
        "triangulation_allowed",
        "boundary_candidate_mapping_allowed",
        "render_allowed",
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "assignment_allowed",
        "publication_allowed",
        "boundary_or_seam_movement_allowed",
        "arbitrary_new_coordinate_allowed",
        "quality_gate_reduction_allowed",
        "generic_hole_fill_allowed",
        "sanitation_weakening_allowed",
    )
    if not all(bool(scope[name]) for name in required_true):
        raise RuntimeError("Attempt 29 lost a required diagnostic gate")
    if any(bool(scope[name]) for name in forbidden):
        raise RuntimeError("Attempt 29 permits a forbidden operation")
    if float(config["diagnosis"]["required_minimum_angle_degrees"]) != 12.0:
        raise RuntimeError("Attempt 29 lowered the 12-degree gate")
    if config["diagnosis"]["convex_boundary_source_indices_below_target"] != [
        2,
        7,
        21,
        28,
    ]:
        raise RuntimeError("Attempt 29 fixed-boundary diagnosis drifted")
    contract = config["chart_mismatch_contract"]
    if (
        not bool(contract["capture_before_original_attempt28_fatal_check"])
        or not bool(contract["stop_before_boundary_candidate_mapping"])
        or not bool(contract["compute_alternative_chart_without_datablock_assignment"])
        or float(contract["match_tolerance_m"]) != 1.0e-10
    ):
        raise RuntimeError("Attempt 29 mismatch-capture contract drifted")
    hard = config["unchanged_hard_gates"]
    if (
        float(hard["minimum_new_triangle_angle_degrees"]) != 12.0
        or float(hard["minimum_new_triangle_world_area_m2"]) != 1.0e-10
        or int(hard["global_seam_vertex_count"]) != 34
        or float(hard["global_seam_coordinate_delta_m"]) != 0.0
    ):
        raise RuntimeError("Attempt 29 hard gate drifted")


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(record["bytes"]):
        raise RuntimeError(f"Attempt 29 bound byte count drifted: {name}")
    if digest != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 29 bound hash drifted: {name}: {digest}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": size,
        "sha256": digest,
    }


def verify_bindings(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    records = {
        name: verify_record(name, record)
        for name, record in config["bindings"].items()
    }
    records["proposal"] = verify_record("proposal", config["proposal"])
    for key in ("preserved_attempt27_package", "preserved_attempt28_package"):
        preserved = config[key]
        rows = [records[name] for name in preserved["binding_names"]]
        if len(rows) != int(preserved["file_count"]):
            raise RuntimeError(f"{key} file count drifted")
        if sum(int(row["bytes"]) for row in rows) != int(preserved["total_bytes"]):
            raise RuntimeError(f"{key} byte total drifted")
    if records["attempt28_worker"]["sha256"] != EXPECTED_ATTEMPT28_WORKER_SHA256:
        raise RuntimeError("Attempt 29 provider constant and binding disagree")
    failure = json.loads(
        project_path(config["bindings"]["attempt28_failure"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    if (
        failure.get("error") != config["diagnosis"]["attempt28_error"]
        or failure.get("diagnostic_exists") is not False
        or failure.get("blend_saved") is not False
        or failure.get("runtime_changed") is not False
    ):
        raise RuntimeError("Attempt 29 is not bound to the exact Attempt 28 failure")
    return records


ATTEMPT29_CAPTURE_HELPERS = r'''
def attempt29_matrix_rows(matrix: Any) -> list[list[float]]:
    return [
        [float(matrix[row][column]) for column in range(4)]
        for row in range(4)
    ]


def attempt29_object_transform(obj: Any) -> dict[str, Any]:
    return {
        "name": obj.name,
        "parent_name": obj.parent.name if obj.parent is not None else None,
        "location": [float(value) for value in obj.location],
        "rotation_mode": str(obj.rotation_mode),
        "rotation_euler": [float(value) for value in obj.rotation_euler],
        "scale": [float(value) for value in obj.scale],
        "matrix_basis": attempt29_matrix_rows(obj.matrix_basis),
        "matrix_local": attempt29_matrix_rows(obj.matrix_local),
        "matrix_parent_inverse": attempt29_matrix_rows(obj.matrix_parent_inverse),
        "matrix_world": attempt29_matrix_rows(obj.matrix_world),
    }


def attempt29_chart_with_matrix(
    matrix: Any,
    obj: Any,
    bm: Any,
    cycle_ids: Sequence[int],
    selected: set[int],
    np: Any,
    Vector: Any,
) -> dict[str, Any]:
    lateral = Vector((0.9999999403953552, 0.0, 0.0)).normalized()
    longitudinal = Vector((0.0, -0.3000001609325409, 0.9539390802383423)).normalized()
    vertices = [bm.verts[int(index)] for index in cycle_ids]
    world = [matrix @ vertex.co for vertex in vertices]
    centroid_array = np.mean(np.asarray([tuple(value) for value in world]), axis=0)
    centroid = Vector(tuple(float(value) for value in centroid_array))
    centered = np.asarray([tuple(value - centroid) for value in world])
    _u, singular_values, vh = np.linalg.svd(centered, full_matrices=False)
    normal = Vector(tuple(float(value) for value in vh[-1])).normalized()
    surrounding = []
    for vertex in vertices:
        for face in vertex.link_faces:
            if int(face.index) not in selected:
                transformed = matrix.to_3x3() @ face.normal
                if transformed.length:
                    surrounding.append(transformed.normalized())
    if surrounding:
        average = sum(surrounding, Vector()).normalized()
        if normal.dot(average) < 0.0:
            normal.negate()
    elif normal.dot(longitudinal) < 0.0:
        normal.negate()
    u_axis = lateral - normal * lateral.dot(normal)
    if u_axis.length < 1.0e-8:
        u_axis = Vector(tuple(float(value) for value in vh[0]))
    u_axis.normalize()
    v_axis = normal.cross(u_axis).normalized()
    if v_axis.dot(longitudinal) < 0.0:
        u_axis.negate()
        v_axis.negate()
    coordinates = [
        [float((value - centroid).dot(u_axis)), float((value - centroid).dot(v_axis))]
        for value in world
    ]
    heights = [float((value - centroid).dot(normal)) for value in world]
    if signed_twice_area(coordinates) < 0.0:
        cycle_ids = list(reversed(cycle_ids))
        coordinates.reverse()
        heights.reverse()
    return {
        "cycle_mesh_vertex_indices": [int(value) for value in cycle_ids],
        "coordinates_xy_m": coordinates,
        "centroid_world_m": [float(value) for value in centroid],
        "normal_world": [float(value) for value in normal],
        "singular_values": [float(value) for value in singular_values],
        "maximum_absolute_boundary_deviation_m": max(abs(value) for value in heights),
        "rms_absolute_boundary_deviation_m": math.sqrt(
            sum(value * value for value in heights) / len(heights)
        ),
    }


def attempt29_alignment_details(
    expected_xy: Sequence[Sequence[float]],
    chart: Mapping[str, Any],
) -> dict[str, Any]:
    alignment = _align_capture_to_current(expected_xy, chart)
    coordinate_by_mesh_id = {
        int(mesh_id): [float(value) for value in coordinate]
        for mesh_id, coordinate in zip(
            chart["cycle_mesh_vertex_indices"], chart["coordinates_xy_m"]
        )
    }
    aligned_xy = [
        coordinate_by_mesh_id[int(mesh_id)]
        for mesh_id in alignment["capture_source_index_to_mesh_vertex_index"]
    ]
    delta_rows = []
    for source_index, (expected, actual, mesh_id) in enumerate(
        zip(
            expected_xy,
            aligned_xy,
            alignment["capture_source_index_to_mesh_vertex_index"],
        )
    ):
        dx = float(actual[0]) - float(expected[0])
        dy = float(actual[1]) - float(expected[1])
        delta_rows.append(
            {
                "capture_source_index": int(source_index),
                "mesh_vertex_index": int(mesh_id),
                "expected_xy_m": [float(value) for value in expected],
                "computed_xy_m": [float(value) for value in actual],
                "delta_xy_m": [dx, dy],
                "distance_m": math.hypot(dx, dy),
            }
        )
    worst = max(delta_rows, key=lambda row: row["distance_m"])
    return {
        "alignment": alignment,
        "aligned_computed_xy_m": aligned_xy,
        "aligned_computed_xy_sha256": canonical_sha256(aligned_xy),
        "delta_rows": delta_rows,
        "maximum_distance_m": float(worst["distance_m"]),
        "rms_distance_m": math.sqrt(
            sum(row["distance_m"] ** 2 for row in delta_rows) / len(delta_rows)
        ),
        "worst_capture_source_index": int(worst["capture_source_index"]),
        "worst_mesh_vertex_index": int(worst["mesh_vertex_index"]),
    }


def attempt29_build_chart_mismatch_diagnostic(
    config: Mapping[str, Any],
    obj: Any,
    bm: Any,
    selected: set[int],
    current_row: Mapping[str, Any],
    expected_xy: Sequence[Sequence[float]],
    direct_alignment: Mapping[str, Any],
    global_seam_vertices: set[int],
    global_seam_world: Sequence[Sequence[float]],
    bpy: Any,
    np: Any,
    Vector: Any,
) -> dict[str, Any]:
    body_path = project_existing_path(
        config["bindings"]["sealed_r24_source_blend"]["path"]
    )
    body_name = config["chart_mismatch_contract"]["sealed_body_object_name"]
    before_objects = set(bpy.data.objects)
    with bpy.data.libraries.load(str(body_path), link=False) as (source, target):
        if body_name not in source.objects:
            raise RuntimeError("Attempt 29 sealed body object is absent")
        target.objects = [body_name]
    loaded_body = target.objects[0] if target.objects else None
    appended = [value for value in bpy.data.objects if value not in before_objects]
    body = loaded_body
    if body is None or body.type != "MESH":
        raise RuntimeError("Attempt 29 exact sealed body signature is absent")
    direct_transform = attempt29_object_transform(obj)
    body_transform = attempt29_object_transform(body)
    body_chart = attempt29_chart_with_matrix(
        body.matrix_world.copy(),
        obj,
        bm,
        current_row["boundary_cycle_mesh_vertex_indices"],
        selected,
        np,
        Vector,
    )
    direct_chart = {
        "cycle_mesh_vertex_indices": list(
            current_row["boundary_cycle_mesh_vertex_indices"]
        ),
        "coordinates_xy_m": list(current_row["projected_boundary_xy_m"]),
    }
    direct_details = attempt29_alignment_details(expected_xy, direct_chart)
    body_details = attempt29_alignment_details(expected_xy, body_chart)
    tolerance = float(config["chart_mismatch_contract"]["match_tolerance_m"])
    body_matrix_matches = bool(body_details["maximum_distance_m"] <= tolerance)
    classification = (
        config["chart_mismatch_contract"]["classification_if_body_matrix_matches"]
        if body_matrix_matches
        else config["chart_mismatch_contract"]["classification_otherwise"]
    )
    direct_matrix = direct_transform["matrix_world"]
    body_matrix = body_transform["matrix_world"]
    matrix_delta = [
        [body_matrix[row][column] - direct_matrix[row][column] for column in range(4)]
        for row in range(4)
    ]
    return {
        "schema": "kira.avatar.r24.blackproject_attempt29.chart_mismatch_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CAPTURED_COMPUTED_VS_EXPECTED_CHART_MISMATCH_NO_REPAIR",
        "attempt_id": "attempt_29",
        "classification": classification,
        "classification_is_repair_proof": False,
        "match_tolerance_m": tolerance,
        "expected_attempt27_xy_m": [list(map(float, value)) for value in expected_xy],
        "expected_attempt27_xy_sha256": canonical_sha256(expected_xy),
        "attempt28_direct_chart": direct_details,
        "attempt18_body_matrix_chart": {
            "chart": body_chart,
            "details": body_details,
            "matches_tolerance": body_matrix_matches,
        },
        "direct_patch_object_transform": direct_transform,
        "sealed_body_object_transform": body_transform,
        "body_minus_direct_matrix_world": matrix_delta,
        "body_minus_direct_matrix_world_sha256": canonical_sha256(matrix_delta),
        "loaded_body_dependency_object_names": sorted(
            value.name for value in appended if value is not body
        ),
        "boundary_cycle_mesh_vertex_indices": list(
            current_row["boundary_cycle_mesh_vertex_indices"]
        ),
        "boundary_cycle_mesh_vertex_indices_sha256": canonical_sha256(
            current_row["boundary_cycle_mesh_vertex_indices"]
        ),
        "global_seam": {
            "vertex_count": len(global_seam_vertices),
            "world_coordinates_sha256": canonical_sha256(global_seam_world),
            "coordinates_mutated": False,
        },
        "original_attempt28_alignment": dict(direct_alignment),
        "truth": {
            "boundary_candidate_mapping_reached": False,
            "triangulation_performed": False,
            "mesh_mutated": False,
            "body_mutated": False,
            "blender_datablock_transform_assigned": False,
            "render_reached": False,
            "blend_saved": False,
            "runtime_changed": False,
            "repair_applied": False,
        },
    }
'''


def exact_replace(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 29 source replacement drifted: {label}: {count}")
    return source.replace(old, new, 1)


def derive_attempt29_source(source28: str) -> str:
    source = exact_replace(
        source28,
        ATTEMPT28_CONFIG_SHA256,
        EXPECTED_CONFIG_SHA256,
        "config hash",
    )
    source = exact_replace(
        source,
        "def run_blender_diagnostic(",
        ATTEMPT29_CAPTURE_HELPERS + "\n\ndef run_blender_diagnostic(",
        "insert chart mismatch helpers",
    )
    old_terminal = (
        '        if alignment["maximum_xy_distance_m"] > float(\n'
        '            source_contract["captured_xy_match_tolerance_m"]\n'
        '        ):\n'
        '            raise RuntimeError("Attempt 28 source chart does not match Attempt 27 capture")\n'
    )
    new_terminal = (
        "        mismatch = attempt29_build_chart_mismatch_diagnostic(\n"
        "            config, obj, bm, current, current_row, captured_xy, alignment,\n"
        "            global_seam_vertices, global_seam_world, bpy, np, Vector,\n"
        "        )\n"
        "        _atomic_write_once(output / config[\"output\"][\"diagnostic\"], mismatch)\n"
        "        raise RuntimeError(\n"
        "            \"Attempt 29 captured computed-versus-expected chart mismatch; \"\n"
        "            \"diagnostic-only stop before boundary candidate mapping\"\n"
        "        )\n"
    )
    source = exact_replace(source, old_terminal, new_terminal, "instrument fatal chart boundary")
    for old, new in (
        ("attempt_28", "attempt_29"),
        ("attempt28", "attempt29"),
        ("Attempt 28", "Attempt 29"),
        ("ATTEMPT28", "ATTEMPT29"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 29 source identity token disappeared: {old}")
        source = source.replace(old, new)
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "attempt29_build_chart_mismatch_diagnostic",
        "attempt29_chart_with_matrix",
        "attempt29_alignment_details",
        "run_blender_diagnostic",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 29 derived diagnostic helpers are absent")
    for stale in ("attempt_28", "attempt28", "Attempt 28", "ATTEMPT28"):
        if stale in source:
            raise RuntimeError(f"Attempt 29 derived source retained stale token: {stale}")
    return source


def main() -> None:
    if sha256_file(ATTEMPT28_WORKER) != EXPECTED_ATTEMPT28_WORKER_SHA256:
        raise RuntimeError("Attempt 28 worker changed before Attempt 29 derivation")
    config = load_overlay(DEFAULT_CONFIG)
    verify_bindings(config)
    source28 = ATTEMPT28_WORKER.read_text(encoding="utf-8")
    source29 = derive_attempt29_source(source28)
    preserved_paths = [
        project_path(config["bindings"][name]["path"])
        for name in config["preserved_attempt28_package"]["binding_names"]
    ]
    before = {path: path.read_bytes() for path in preserved_paths}
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
    }
    try:
        exec(
            compile(source29, str(Path(__file__).resolve()) + "::derived", "exec"),
            namespace,
            namespace,
        )
    finally:
        for path in preserved_paths:
            if path.read_bytes() != before[path]:
                raise RuntimeError(f"{path.name} changed during Attempt 29 execution")


if __name__ == "__main__":
    main()
