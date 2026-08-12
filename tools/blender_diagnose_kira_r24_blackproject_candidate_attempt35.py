"""Static-first Attempt 35 explicit vector-dimension orchestration.

Attempt 34's exact append and BMesh-lifetime repairs remain byte-bound. This
worker derives only the two bound provider modules whose later no-save path
contains dimensionless ``Vector()`` sum identities: four reachable operations
in Attempt 15 and one in R20's preserved-normal restore. Every identity becomes
an explicit operand-matched 2D or 3D zero. Static import remains Blender-free;
no Blender process is started during preparation.
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
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT35_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = "e92df1cc085b2a2d667a77923e76e379cd10c5d5315e31dc9287470872b5635f"

ATTEMPT15_R21_IMPORT_OLD = (
    "from tools import blender_author_kira_r21_pelvis_attempt01 as r21  # noqa: E402\n"
)
ATTEMPT15_R21_IMPORT_NEW = (
    'r21 = sys.modules["attempt35_bound_r21"]  # exact in-memory bound R21 helper\n'
)

ATTEMPT15_CDT_SEED_OLD = (
    '        sum((base["coordinates"][index] for index in face), Vector()) / 3.0\n'
)
ATTEMPT15_CDT_SEED_NEW = (
    '        sum((base["coordinates"][index] for index in face), '
    'Vector((0.0, 0.0))) / 3.0\n'
)

ATTEMPT15_CDT_CENTROID_OLD = "            sum(points, Vector()) / 3.0,\n"
ATTEMPT15_CDT_CENTROID_NEW = (
    "            sum(points, Vector((0.0, 0.0))) / 3.0,\n"
)

ATTEMPT15_NORMAL_OLD = (
    "    average_normal = sum(surrounding_normals, Vector()).normalized()\n"
)
ATTEMPT15_NORMAL_NEW = (
    "    average_normal = sum(\n"
    "        surrounding_normals, Vector((0.0, 0.0, 0.0))\n"
    "    ).normalized()\n"
)

ATTEMPT15_UV_OLD = "        value = sum(samples, Vector()) / len(samples)\n"
ATTEMPT15_UV_NEW = (
    "        value = sum(samples, Vector((0.0, 0.0))) / len(samples)\n"
)

R20_NORMAL_RESTORE_OLD = '''        patch_normals_by_vertex[vertex_index].append(actual)
        if exterior_by_vertex[vertex_index]:
            exterior = sum(exterior_by_vertex[vertex_index], Vector()).normalized()
            seam_patch_dots.append(max(-1.0, min(1.0, actual.dot(exterior))))
'''

R20_NORMAL_RESTORE_NEW = '''        patch_normals_by_vertex[vertex_index].append(actual)
        if exterior_by_vertex[vertex_index]:
            exterior = sum(
                exterior_by_vertex[vertex_index], Vector((0.0, 0.0, 0.0))
            ).normalized()
            seam_patch_dots.append(max(-1.0, min(1.0, actual.dot(exterior))))
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
        raise RuntimeError(f"Attempt 35 path escapes project: {relative}") from error
    if must_exist and not path.is_file():
        raise RuntimeError(f"Attempt 35 bound file is absent: {relative}")
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
        raise RuntimeError(f"Attempt 35 bound byte count drifted: {label}")
    if actual["sha256"] != str(record["sha256"]):
        raise RuntimeError(f"Attempt 35 bound SHA-256 drifted: {label}")
    return actual


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 35 cannot load provider: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _exact_replace(
    source: str, old: str, new: str, label: str, record: Mapping[str, Any]
) -> str:
    if sha256_text(old) != record["old_block_sha256"]:
        raise RuntimeError(f"Attempt 35 old block hash drifted: {label}")
    if sha256_text(new) != record["new_block_sha256"]:
        raise RuntimeError(f"Attempt 35 new block hash drifted: {label}")
    expected_count = int(record["exact_replacement_count"])
    if expected_count != 1 or source.count(old) != expected_count:
        raise RuntimeError(f"Attempt 35 exact old block is not unique: {label}")
    result = source.replace(old, new, 1)
    if old in result or result.count(new) != 1:
        raise RuntimeError(f"Attempt 35 source transform is not exact: {label}")
    return result


def derive_attempt15_source(source: str, config: Mapping[str, Any]) -> str:
    records = config["dimension_patch"]["attempt15"]["replacements"]
    blocks = (
        ("r21_provider_link", ATTEMPT15_R21_IMPORT_OLD, ATTEMPT15_R21_IMPORT_NEW),
        ("quality_refined_cdt_initial_face_centroids", ATTEMPT15_CDT_SEED_OLD, ATTEMPT15_CDT_SEED_NEW),
        ("quality_refined_cdt_candidate_centroid", ATTEMPT15_CDT_CENTROID_OLD, ATTEMPT15_CDT_CENTROID_NEW),
        ("reconstruct_local_domain_surrounding_normal", ATTEMPT15_NORMAL_OLD, ATTEMPT15_NORMAL_NEW),
        ("reconstruct_local_domain_boundary_uv", ATTEMPT15_UV_OLD, ATTEMPT15_UV_NEW),
    )
    result = source
    for label, old, new in blocks:
        result = _exact_replace(result, old, new, label, records[label])
    expected = config["dimension_patch"]["attempt15"]["derived_source_sha256"]
    if sha256_text(result) != expected:
        raise RuntimeError("Attempt 35 derived Attempt 15 source hash drifted")
    return result


def derive_r20_source(source: str, config: Mapping[str, Any]) -> str:
    record = config["dimension_patch"]["r20"]["replacement"]
    result = _exact_replace(
        source,
        R20_NORMAL_RESTORE_OLD,
        R20_NORMAL_RESTORE_NEW,
        "restore_exact_preserved_loop_normals_exterior_average",
        record,
    )
    expected = config["dimension_patch"]["r20"]["derived_source_sha256"]
    if sha256_text(result) != expected:
        raise RuntimeError("Attempt 35 derived R20 source hash drifted")
    return result


def _exec_source_module(name: str, path: Path, source: str) -> Any:
    code = compile(source, str(path), "exec")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    sys.modules[name] = module
    exec(code, module.__dict__)
    return module


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 35 requires the exact configured manifest path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 35 config SHA-256 drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_35"
        or config.get("status") != "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 35 identity drifted")
    scope = config["scope"]
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "later_reviewed_blender_launch_required",
        "exact_attempt34_append_and_lifecycle_repairs_required",
        "in_memory_dimension_source_patch_allowed_only_for_exact_bound_blocks",
        "in_memory_reconstruction_and_graft_allowed_only_after_exact_gates",
        "append_only_json_evidence_allowed_during_later_run",
    )
    forbidden = (
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
    )
    if not all(scope.get(name) is True for name in required_true):
        raise RuntimeError("Attempt 35 required scope drifted")
    if any(scope.get(name) is not False for name in forbidden):
        raise RuntimeError("Attempt 35 forbidden scope drifted")
    output = config["runtime_overlay"]["output"]
    if output != {
        "root": "RecoverySprint/continuation_20260803/kira_r24_internal_midpoint_fair_surface/attempt_35",
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "TRIANGULATION_RECONSTRUCTION_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }:
        raise RuntimeError("Attempt 35 output overlay drifted")
    patch = config["dimension_patch"]
    if (
        patch["reachable_dimensionless_accumulators_before"] != 5
        or patch["reachable_dimensionless_accumulators_after"] != 0
        or patch["dimensions"] != {"2d": 3, "3d": 2}
        or patch["algorithm_change_allowed"] is not False
        or patch["operand_or_iteration_order_change_allowed"] is not False
    ):
        raise RuntimeError("Attempt 35 dimension patch contract drifted")
    reach = config["reachability"]
    if reach["mandatory_functions"] != [
        "attempt15.quality_refined_cdt",
        "attempt15.reconstruct_local_domain",
        "r20._restore_exact_preserved_loop_normals",
    ]:
        raise RuntimeError("Attempt 35 reachability manifest drifted")
    if reach["render_reachable"] is not False or reach["r21.render_review"] != "EXCLUDED_NO_RENDER_GATE":
        raise RuntimeError("Attempt 35 render reachability drifted")
    if project_path(str(output["root"]), must_exist=False).exists():
        raise RuntimeError("Attempt 35 output already exists")
    if config["launch_contract"]["executed_during_static_preparation"] is not False:
        raise RuntimeError("Attempt 35 launch truth drifted")


def verify_overlay(config: Mapping[str, Any]) -> dict[str, object]:
    records = {
        str(label): require_record(str(label), record)
        for label, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    failure = json.loads(
        project_path(str(records["attempt34_failure"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    if (
        failure["error_type"] != "AttributeError"
        or failure["error"]
        != "Vector addition: vectors must have the same dimensions for this operation"
        or "line 557, in reconstruct_local_domain" not in failure["traceback"]
        or "sum(samples, Vector())" not in failure["traceback"]
        or failure["render_reached"]
        or failure["blend_saved"]
        or failure["runtime_changed"]
    ):
        raise RuntimeError("Attempt 35 bound Attempt 34 failure truth drifted")
    append = json.loads(
        project_path(str(records["attempt34_append_inventory"]["path"])).read_text(
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
        raise RuntimeError("Attempt 35 bound Attempt 34 append pass drifted")
    external = json.loads(
        project_path(str(records["attempt34_external_integrity"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    if (
        external["blender_exit_code"] != 1
        or external["native_invocation_error"] is not None
        or external["pre_post_exact"] is not True
        or external["before"] != external["after"]
        or len(external["before"]) != 192
    ):
        raise RuntimeError("Attempt 35 bound Attempt 34 external integrity drifted")
    attempt15 = project_path(str(records["attempt15_worker"]["path"]))
    derived15 = derive_attempt15_source(
        attempt15.read_text(encoding="utf-8"), config
    )
    compile(derived15, str(attempt15), "exec")
    r20 = project_path(str(records["r20_pelvis_helper"]["path"]))
    derived20 = derive_r20_source(r20.read_text(encoding="utf-8"), config)
    compile(derived20, str(r20), "exec")
    return {
        "records": records,
        "failure": failure,
        "append": append,
        "derived_attempt15_sha256": sha256_text(derived15),
        "derived_r20_sha256": sha256_text(derived20),
    }


def run_blender(config_path: Path, config: Mapping[str, Any]) -> None:
    verified = verify_overlay(config)
    module_names = (
        "attempt35_bound_attempt34",
        "attempt34_bound_attempt33",
        "attempt33_bound_attempt31",
        "attempt31_bound_attempt15",
        "attempt35_bound_r20",
        "attempt35_bound_r21",
        "blender_author_kira_r20_pelvis_only",
    )
    missing = object()
    prior_modules = {name: sys.modules.get(name, missing) for name in module_names}
    attempt34_path = project_path(str(config["bindings"]["attempt34_worker"]["path"]))
    attempt34 = load_module("attempt35_bound_attempt34", attempt34_path)
    attempt34_config_path = project_path(
        str(config["bindings"]["attempt34_config"]["path"])
    )
    attempt34_config = json.loads(attempt34_config_path.read_text(encoding="utf-8"))
    runtime_config = deepcopy(attempt34_config)
    runtime_config["runtime_overlay"]["output"] = deepcopy(
        config["runtime_overlay"]["output"]
    )
    dimension_metadata = {
        "worker": file_record(Path(__file__).resolve()),
        "config": file_record(config_path),
        "attempt15_source": verified["records"]["attempt15_worker"],
        "attempt15_derived_source_sha256": config["dimension_patch"]["attempt15"]["derived_source_sha256"],
        "r20_source": verified["records"]["r20_pelvis_helper"],
        "r20_derived_source_sha256": config["dimension_patch"]["r20"]["derived_source_sha256"],
        "reachable_dimensionless_accumulators_before": 5,
        "reachable_dimensionless_accumulators_after": 0,
        "explicit_2d_zero_count": 3,
        "explicit_3d_zero_count": 2,
        "algorithm_or_operand_order_changed": False,
        "render_permitted": False,
        "blend_save_permitted": False,
    }
    original_derived_loader = attempt34.load_derived_attempt31
    original_attempt34_file = attempt34.__file__

    def attempt35_load_derived_attempt31(
        name: str,
        path: Path,
        inner_config: Mapping[str, Any],
        writer_metadata: Mapping[str, Any],
    ) -> Any:
        module = original_derived_loader(name, path, inner_config, writer_metadata)
        original_provider_loader = module._load_module
        raw_writer = module._exclusive_write_once

        def attempt35_provider_loader(provider_name: str, provider_path: Path) -> Any:
            exact_attempt15 = project_path(
                str(config["bindings"]["attempt15_worker"]["path"])
            )
            if provider_path.resolve() != exact_attempt15.resolve():
                return original_provider_loader(provider_name, provider_path)
            r20_path = project_path(
                str(config["bindings"]["r20_pelvis_helper"]["path"])
            )
            r20_source = derive_r20_source(
                r20_path.read_text(encoding="utf-8"), config
            )
            r20_module = _exec_source_module(
                "attempt35_bound_r20", r20_path, r20_source
            )
            sys.modules["blender_author_kira_r20_pelvis_only"] = r20_module
            r21_path = project_path(
                str(config["bindings"]["r21_graft_helper"]["path"])
            )
            r21_module = load_module("attempt35_bound_r21", r21_path)
            if r21_module.r20 is not r20_module:
                raise RuntimeError("Attempt 35 exact R21 did not bind derived R20")
            attempt15_source = derive_attempt15_source(
                exact_attempt15.read_text(encoding="utf-8"), config
            )
            provider = _exec_source_module(
                provider_name, exact_attempt15, attempt15_source
            )
            if provider.r21 is not r21_module or provider.r21.r20 is not r20_module:
                raise RuntimeError("Attempt 35 derived provider linkage drifted")
            return provider

        def attempt35_writer(target: Path, value: Mapping[str, Any]) -> None:
            result = deepcopy(dict(value))
            if isinstance(result.get("schema"), str):
                result["schema"] = result["schema"].replace("attempt33", "attempt35")
                result["schema"] = result["schema"].replace("attempt34", "attempt35")
            if result.get("attempt_id") in {"attempt_33", "attempt_34"}:
                result["attempt_id"] = "attempt_35"
            if isinstance(result.get("status"), str):
                result["status"] = result["status"].replace("ATTEMPT33", "ATTEMPT35")
                result["status"] = result["status"].replace("ATTEMPT34", "ATTEMPT35")
            result["attempt35_dimension_patch"] = deepcopy(dimension_metadata)
            raw_writer(target, result)

        module._load_module = attempt35_provider_loader
        module._exclusive_write_once = attempt35_writer
        return module

    attempt34.load_derived_attempt31 = attempt35_load_derived_attempt31
    attempt34.__file__ = str(Path(__file__).resolve())
    try:
        attempt34.run_blender(config_path, runtime_config)
    finally:
        attempt34.load_derived_attempt31 = original_derived_loader
        attempt34.__file__ = original_attempt34_file
        for module_name, prior in prior_modules.items():
            if prior is missing:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = prior


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
