"""Static-first Attempt 34 BMesh-lifetime correction orchestration.

The exact Attempt 33 append correction and Attempt 31 reconstruction engine
remain byte-bound.  This worker applies one exact in-memory source transform to
the bound Attempt 31 capture: immutable IDs and boundary keys are materialized
before preservation-layer creation, and every BMesh element returned to the
provider is reacquired and revalidated afterward.  Static import is Blender-
free; a later reviewed run remains private, inactive, and no-save.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT34_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = "897e1a35b4334677d6a829f65bdad82b7b310359298ff888bc71bc42e9fd40be"

OLD_CAPTURE_BLOCK = '''            captured["patch_tag_snapshot"] = _begin_tagged_preservation(
                bm,
                {int(vertex.index) for vertex in interior},
                selected_face_ids,
                PATCH_VERTEX_TAG,
                PATCH_FACE_TAG,
            )
            captured["local_boundary_vertex_keys"] = sorted(
                _vector_key(vertex.co) for vertex in cycle
            )
            captured["local_boundary_edge_keys"] = sorted(
                _edge_coordinate_key(edge.verts[0], edge.verts[1])
                for edge in local_boundary_edges
            )
            return {
                "selected_faces": selected_faces,
                "selected_vertices": selected_vertices,
                "selected_edges": selected_edges,
                "local_boundary_edges": local_boundary_edges,
                "local_boundary": set(cycle),
                "interior": interior,
                "cycle": cycle,
                "face_ids": face_ids,
                "vertex_ids": vertex_ids,
                "boundary_edge_ids": boundary_edge_ids,
            }
'''

NEW_CAPTURE_BLOCK = '''            # Materialize every identity and preservation key while the
            # pre-layer BMesh wrappers are still valid. Creating either custom
            # data layer below may invalidate all held BMVert/BMEdge/BMFace
            # Python wrappers even though topology is unchanged.
            selected_face_index_ids = sorted(int(face.index) for face in selected_faces)
            selected_vertex_index_ids = sorted(
                int(vertex.index) for vertex in selected_vertices
            )
            selected_edge_index_ids = sorted(int(edge.index) for edge in selected_edges)
            local_boundary_edge_index_ids = sorted(
                int(edge.index) for edge in local_boundary_edges
            )
            cycle_vertex_index_ids = [int(vertex.index) for vertex in cycle]
            interior_vertex_index_ids = sorted(int(vertex.index) for vertex in interior)
            immutable_boundary_vertex_keys = sorted(
                _vector_key(vertex.co) for vertex in cycle
            )
            immutable_boundary_edge_keys = sorted(
                _edge_coordinate_key(edge.verts[0], edge.verts[1])
                for edge in local_boundary_edges
            )
            captured["local_boundary_vertex_keys"] = immutable_boundary_vertex_keys
            captured["local_boundary_edge_keys"] = immutable_boundary_edge_keys
            captured["patch_tag_snapshot"] = _begin_tagged_preservation(
                bm,
                set(interior_vertex_index_ids),
                set(selected_face_index_ids),
                PATCH_VERTEX_TAG,
                PATCH_FACE_TAG,
            )

            # No pre-layer BMesh element wrapper may cross this boundary.
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            bm.verts.index_update()
            bm.edges.index_update()
            bm.faces.index_update()
            selected_faces = {bm.faces[index] for index in selected_face_index_ids}
            selected_vertices = {
                bm.verts[index] for index in selected_vertex_index_ids
            }
            selected_edges = {bm.edges[index] for index in selected_edge_index_ids}
            local_boundary_edges = {
                bm.edges[index] for index in local_boundary_edge_index_ids
            }
            interior = {bm.verts[index] for index in interior_vertex_index_ids}
            reacquired_cycle = provider.ordered_cycle(local_boundary_edges)
            reacquired_cycle_ids = [int(vertex.index) for vertex in reacquired_cycle]
            matching_reacquired_cycle = next(
                (
                    row
                    for row in _cycle_rotations(reacquired_cycle_ids)
                    if row == cycle_vertex_index_ids
                ),
                None,
            )
            if matching_reacquired_cycle is None:
                raise RuntimeError(
                    "Attempt 34 post-layer boundary cycle identity drifted"
                )
            reacquired_by_id = {
                int(vertex.index): vertex for vertex in reacquired_cycle
            }
            cycle = [
                reacquired_by_id[index] for index in matching_reacquired_cycle
            ]
            reacquired_vertices_from_faces = {
                vertex for face in selected_faces for vertex in face.verts
            }
            reacquired_edges_from_faces = {
                edge for face in selected_faces for edge in face.edges
            }
            reacquired_boundary_edges = {
                edge
                for edge in selected_edges
                if sum(face in selected_faces for face in edge.link_faces) == 1
            }
            reacquired_boundary_edge_ids = sorted(
                sorted((int(edge.verts[0].index), int(edge.verts[1].index)))
                for edge in local_boundary_edges
            )
            post_layer_global_edges = [
                edge for edge in bm.edges if len(edge.link_faces) == 1
            ]
            post_layer_global_vertices = {
                vertex for edge in post_layer_global_edges for vertex in edge.verts
            }
            if (
                sorted(int(face.index) for face in selected_faces)
                != selected_face_index_ids
                or sorted(int(vertex.index) for vertex in selected_vertices)
                != selected_vertex_index_ids
                or sorted(int(edge.index) for edge in selected_edges)
                != selected_edge_index_ids
                or sorted(int(edge.index) for edge in local_boundary_edges)
                != local_boundary_edge_index_ids
                or [int(vertex.index) for vertex in cycle]
                != cycle_vertex_index_ids
                or sorted(int(vertex.index) for vertex in interior)
                != interior_vertex_index_ids
                or reacquired_vertices_from_faces != selected_vertices
                or reacquired_edges_from_faces != selected_edges
                or reacquired_boundary_edges != local_boundary_edges
                or selected_vertices - set(cycle) != interior
                or reacquired_boundary_edge_ids != boundary_edge_ids
                or sorted(_vector_key(vertex.co) for vertex in cycle)
                != immutable_boundary_vertex_keys
                or sorted(
                    _edge_coordinate_key(edge.verts[0], edge.verts[1])
                    for edge in local_boundary_edges
                )
                != immutable_boundary_edge_keys
                or len(post_layer_global_vertices)
                != int(config["unchanged_hard_gates"]["global_seam_vertex_count"])
                or post_layer_global_vertices.intersection(selected_vertices)
            ):
                raise RuntimeError(
                    "Attempt 34 post-layer domain reacquisition drifted"
                )
            return {
                "selected_faces": selected_faces,
                "selected_vertices": selected_vertices,
                "selected_edges": selected_edges,
                "local_boundary_edges": local_boundary_edges,
                "local_boundary": set(cycle),
                "interior": interior,
                "cycle": cycle,
                "face_ids": face_ids,
                "vertex_ids": vertex_ids,
                "boundary_edge_ids": boundary_edge_ids,
            }
'''


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def project_path(relative: str, *, must_exist: bool = True) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as error:
        raise RuntimeError(f"Attempt 34 path escapes project: {relative}") from error
    if must_exist and not path.is_file():
        raise RuntimeError(f"Attempt 34 bound file is absent: {relative}")
    return path


def file_record(path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def require_record(label: str, record: Mapping[str, object]) -> dict[str, object]:
    path = project_path(str(record["path"]))
    actual = file_record(path)
    if actual["bytes"] != int(record["bytes"]):
        raise RuntimeError(f"Attempt 34 bound byte count drifted: {label}")
    if actual["sha256"] != str(record["sha256"]):
        raise RuntimeError(f"Attempt 34 bound SHA-256 drifted: {label}")
    return actual


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 34 cannot load provider: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def patch_attempt31_source(source: str, config: Mapping[str, Any]) -> str:
    patch = config["lifecycle_patch"]
    if sha256_text(OLD_CAPTURE_BLOCK) != patch["old_block_sha256"]:
        raise RuntimeError("Attempt 34 old lifecycle block hash drifted")
    if sha256_text(NEW_CAPTURE_BLOCK) != patch["new_block_sha256"]:
        raise RuntimeError("Attempt 34 new lifecycle block hash drifted")
    if source.count(OLD_CAPTURE_BLOCK) != 1:
        raise RuntimeError("Attempt 34 exact old lifecycle block is not unique")
    result = source.replace(OLD_CAPTURE_BLOCK, NEW_CAPTURE_BLOCK, 1)
    if OLD_CAPTURE_BLOCK in result or result.count(NEW_CAPTURE_BLOCK) != 1:
        raise RuntimeError("Attempt 34 lifecycle source transform is not exact")
    if sha256_text(result) != patch["derived_source_sha256"]:
        raise RuntimeError("Attempt 34 derived Attempt 31 source hash drifted")
    return result


def load_derived_attempt31(
    name: str, path: Path, config: Mapping[str, Any], writer_metadata: Mapping[str, Any]
) -> Any:
    source = path.read_text(encoding="utf-8")
    patched = patch_attempt31_source(source, config)
    compile(patched, str(path), "exec")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    sys.modules[name] = module
    exec(compile(patched, str(path), "exec"), module.__dict__)
    raw_writer = module._exclusive_write_once

    def attempt34_writer(target: Path, value: Mapping[str, Any]) -> None:
        result = deepcopy(dict(value))
        if isinstance(result.get("schema"), str):
            result["schema"] = result["schema"].replace("attempt33", "attempt34")
        if result.get("attempt_id") == "attempt_33":
            result["attempt_id"] = "attempt_34"
        if isinstance(result.get("status"), str):
            result["status"] = result["status"].replace("ATTEMPT33", "ATTEMPT34")
        result["attempt34_lifecycle_patch"] = deepcopy(dict(writer_metadata))
        raw_writer(target, result)

    module._exclusive_write_once = attempt34_writer
    return module


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 34 requires the exact configured manifest path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 34 config SHA-256 drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_34"
        or config.get("status") != "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 34 identity drifted")
    scope = config["scope"]
    for key in (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "later_reviewed_blender_launch_required",
        "in_memory_lifecycle_source_patch_allowed_only_for_exact_bound_block",
        "in_memory_reconstruction_and_graft_allowed_only_after_exact_gates",
        "append_only_json_evidence_allowed_during_later_run",
    ):
        if scope.get(key) is not True:
            raise RuntimeError(f"Attempt 34 required scope drifted: {key}")
    for key in (
        "source_file_mutation_allowed",
        "prior_evidence_mutation_allowed",
        "repair_domain_change_allowed",
        "reconstruction_algorithm_change_allowed",
        "quality_gate_reduction_allowed",
        "render_allowed",
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "assignment_allowed",
        "publication_allowed",
        "automatic_retry_allowed",
    ):
        if scope.get(key) is not False:
            raise RuntimeError(f"Attempt 34 forbidden scope drifted: {key}")
    output = config["runtime_overlay"]["output"]
    if output != {
        "root": "RecoverySprint/continuation_20260803/kira_r24_internal_midpoint_fair_surface/attempt_34",
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "TRIANGULATION_RECONSTRUCTION_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }:
        raise RuntimeError("Attempt 34 output overlay drifted")
    patch = config["lifecycle_patch"]
    if (
        patch["old_block_sha256"] != sha256_text(OLD_CAPTURE_BLOCK)
        or patch["new_block_sha256"] != sha256_text(NEW_CAPTURE_BLOCK)
        or patch["derived_source_sha256"]
        != "0311bc721f9872fc76262b883bdb3f79b7424c70053dc5d3105714d4867fa2f0"
        or patch["exact_replacement_count"] != 1
        or patch["pre_layer_immutable_domains"]
        != [
            "selected_face_indices",
            "selected_vertex_indices",
            "selected_edge_indices",
            "local_boundary_edge_indices",
            "cycle_vertex_indices",
            "interior_vertex_indices",
            "boundary_vertex_coordinate_keys",
            "boundary_edge_coordinate_keys",
        ]
        or patch["post_layer_reacquired_domains"]
        != [
            "selected_faces",
            "selected_vertices",
            "selected_edges",
            "local_boundary_edges",
            "local_boundary",
            "cycle",
            "interior",
        ]
        or patch["require_exact_post_layer_ids_topology_coordinates_and_seam"]
        is not True
        or patch["permit_pre_layer_bmesh_wrapper_escape"] is not False
    ):
        raise RuntimeError("Attempt 34 lifecycle patch contract drifted")
    if project_path(str(output["root"]), must_exist=False).exists():
        raise RuntimeError("Attempt 34 output already exists")
    if config["launch_contract"]["executed_during_static_preparation"] is not False:
        raise RuntimeError("Attempt 34 launch truth drifted")


def verify_overlay(config: Mapping[str, Any]) -> dict[str, object]:
    records = {
        str(label): require_record(str(label), record)
        for label, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    failure = json.loads(
        project_path(str(records["attempt33_failure"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    if (
        failure["error_type"] != "ReferenceError"
        or failure["error"] != "BMesh data of type BMVert has been removed"
        or "line 1708, in attempt31_capture_local_domain" not in failure["traceback"]
        or "line 1709, in <genexpr>" not in failure["traceback"]
        or failure["render_reached"]
        or failure["blend_saved"]
        or failure["runtime_changed"]
    ):
        raise RuntimeError("Attempt 34 bound Attempt 33 failure truth drifted")
    append = json.loads(
        project_path(str(records["attempt33_append_inventory"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    if (
        append["status"]
        != "PASS_EXACT_SEVEN_OBJECT_HIERARCHY_NO_NEW_COLLECTIONS_BEFORE_CLEANUP"
        or append["actual_appended_object_names_sha256"]
        != "ef4ed395b5f7fc8c0a2d549a23c547d20d74cd45137e16cd68cc08482e08bb85"
        or append["actual_new_collection_names"] != []
    ):
        raise RuntimeError("Attempt 34 bound Attempt 33 append pass drifted")
    external = json.loads(
        project_path(str(records["attempt33_external_integrity"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    if (
        external["blender_exit_code"] != 1
        or external["native_invocation_error"] is not None
        or external["pre_post_exact"] is not True
        or external["before"] != external["after"]
        or len(external["before"]) != 180
    ):
        raise RuntimeError("Attempt 34 bound Attempt 33 external integrity drifted")
    base_path = project_path(str(records["attempt31_worker"]["path"]))
    patch_attempt31_source(base_path.read_text(encoding="utf-8"), config)
    return {"records": records, "failure": failure, "append": append}


def run_blender(config_path: Path, config: Mapping[str, Any]) -> None:
    verify_overlay(config)
    attempt33_path = project_path(str(config["bindings"]["attempt33_worker"]["path"]))
    attempt33 = load_module("attempt34_bound_attempt33", attempt33_path)
    attempt33_config_path = project_path(
        str(config["bindings"]["attempt33_config"]["path"])
    )
    attempt33_config = json.loads(attempt33_config_path.read_text(encoding="utf-8"))
    runtime_config = deepcopy(attempt33_config)
    runtime_config["runtime_overlay"]["output"] = deepcopy(
        config["runtime_overlay"]["output"]
    )
    lifecycle_metadata = {
        "worker": file_record(Path(__file__).resolve()),
        "config": file_record(config_path),
        "attempt31_source": require_record(
            "attempt31_worker", config["bindings"]["attempt31_worker"]
        ),
        "old_block_sha256": config["lifecycle_patch"]["old_block_sha256"],
        "new_block_sha256": config["lifecycle_patch"]["new_block_sha256"],
        "derived_source_sha256": config["lifecycle_patch"]["derived_source_sha256"],
        "no_pre_layer_bmesh_wrapper_escapes": True,
        "render_permitted": False,
        "blend_save_permitted": False,
    }
    original_loader = attempt33.load_module
    original_relabel = attempt33.relabel_base_evidence
    original_file = attempt33.__file__

    def attempt34_loader(name: str, path: Path) -> Any:
        if path.resolve() == project_path(
            str(config["bindings"]["attempt31_worker"]["path"])
        ):
            return load_derived_attempt31(
                name, path, config, lifecycle_metadata
            )
        return original_loader(name, path)

    def attempt34_relabel(
        value: Mapping[str, Any], orchestration: Mapping[str, Any]
    ) -> dict[str, Any]:
        result = original_relabel(value, orchestration)
        if isinstance(result.get("schema"), str):
            result["schema"] = result["schema"].replace("attempt33", "attempt34")
        if result.get("attempt_id") == "attempt_33":
            result["attempt_id"] = "attempt_34"
        if isinstance(result.get("status"), str):
            result["status"] = result["status"].replace("ATTEMPT33", "ATTEMPT34")
        prior = result.pop("attempt33_orchestration", None)
        result["attempt34_orchestration"] = {
            "append_orchestration": prior,
            "lifecycle_patch": deepcopy(lifecycle_metadata),
        }
        return result

    attempt33.load_module = attempt34_loader
    attempt33.relabel_base_evidence = attempt34_relabel
    attempt33.__file__ = str(Path(__file__).resolve())
    try:
        attempt33.run_blender(config_path, runtime_config)
    finally:
        attempt33.load_module = original_loader
        attempt33.relabel_base_evidence = original_relabel
        attempt33.__file__ = original_file


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    verify_overlay(config)
    run_blender(config_path, config)


if __name__ == "__main__":
    main()
