"""Static-first Attempt 37 non-degrading CDT candidate repair.

The exact Attempt 35 pipeline remains byte-bound.  A later independently
reviewed run may replace one exact candidate-selection/acceptance block in the
derived Attempt 15 ``quality_refined_cdt`` function.  The replacement keeps
the fixed boundary, bootstrap, seed cap, and quality gates; it evaluates
circumcenter then centroid trials without mutating accepted seeds and accepts
only a numerically valid strict global-angle improvement.  Static import is
Blender-free and never launches the runtime attempt.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
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
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT37_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = "f581395a6ddd24f730dfdcd8e8ae87229fca3e2bff4972035ab0118f5ce2bfd1"

ATTEMPT35_WRITER_OLD = '''        def attempt35_writer(target: Path, value: Mapping[str, Any]) -> None:
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
'''

ATTEMPT35_WRITER_NEW = '''        def attempt37_writer(target: Path, value: Mapping[str, Any]) -> None:
            result = deepcopy(dict(value))
            if isinstance(result.get("schema"), str):
                result["schema"] = result["schema"].replace("attempt33", "attempt37")
                result["schema"] = result["schema"].replace("attempt34", "attempt37")
                result["schema"] = result["schema"].replace("attempt35", "attempt37")
            if result.get("attempt_id") in {"attempt_33", "attempt_34", "attempt_35"}:
                result["attempt_id"] = "attempt_37"
            if isinstance(result.get("status"), str):
                result["status"] = result["status"].replace("ATTEMPT33", "ATTEMPT37")
                result["status"] = result["status"].replace("ATTEMPT34", "ATTEMPT37")
                result["status"] = result["status"].replace("ATTEMPT35", "ATTEMPT37")
            result["attempt35_dimension_patch"] = deepcopy(dimension_metadata)
            result["attempt37_nondegrading_cdt_repair"] = deepcopy(
                ATTEMPT37_REPAIR_METADATA
            )
            raw_writer(target, result)

        module._load_module = attempt35_provider_loader
        module._exclusive_write_once = attempt37_writer
'''

ATTEMPT35_CANDIDATE_OLD = '''        _angle, _face, points = min(quality, key=lambda value: value[0])
        candidates = [
            triangle_incenter(points),
            sum(points, Vector((0.0, 0.0))) / 3.0,
        ]
        added = False
        for candidate in candidates:
            key = (round(float(candidate.x), 14), round(float(candidate.y), 14))
            if key not in seen and all(
                (candidate - value).length > epsilon * 16.0
                for value in boundary + list(seeds)
            ):
                seeds.append(candidate)
                seen.add(key)
                added = True
                break
        if not added:
            break
'''

ATTEMPT37_CANDIDATE_NEW = '''        _angle, _face, points = min(
            quality, key=lambda value: (value[0], tuple(value[1]))
        )
        first, second, third = points
        ax, ay = float(first.x), float(first.y)
        bx, by = float(second.x), float(second.y)
        cx, cy = float(third.x), float(third.y)
        denominator = 2.0 * (
            ax * (by - cy) + bx * (cy - ay) + cx * (ay - by)
        )
        trial_specs = []
        if abs(denominator) > epsilon * epsilon:
            first_square = ax * ax + ay * ay
            second_square = bx * bx + by * by
            third_square = cx * cx + cy * cy
            circumcenter = Vector((
                (
                    first_square * (by - cy)
                    + second_square * (cy - ay)
                    + third_square * (ay - by)
                ) / denominator,
                (
                    first_square * (cx - bx)
                    + second_square * (ax - cx)
                    + third_square * (bx - ax)
                ) / denominator,
            ))
            trial_specs.append(("circumcenter", circumcenter, None))
        else:
            trial_specs.append((
                "circumcenter",
                None,
                "circumcenter_denominator_below_epsilon_squared",
            ))
        trial_specs.append((
            "centroid",
            sum(points, Vector((0.0, 0.0))) / 3.0,
            None,
        ))
        current_coordinate_keys = [
            (round(float(value.x), 14), round(float(value.y), 14))
            for value in result["coordinates"]
        ]
        minimum_edge_floor_m = epsilon * 16.0
        minimum_absolute_double_area_floor_m2 = epsilon * epsilon * 16.0
        improvement_tolerance_degrees = 1.0e-9
        trial_records = []
        valid_trials = []
        for candidate_order, (candidate_kind, candidate, unavailable) in enumerate(
            trial_specs
        ):
            trial_record = {
                "candidate_order": candidate_order,
                "candidate_kind": candidate_kind,
                "candidate": (
                    None
                    if candidate is None
                    else [float(candidate.x), float(candidate.y)]
                ),
                "current_minimum_angle_degrees": float(minimum),
                "minimum_edge_floor_m": float(minimum_edge_floor_m),
                "minimum_absolute_double_area_floor_m2": float(
                    minimum_absolute_double_area_floor_m2
                ),
                "strict_improvement_tolerance_degrees": float(
                    improvement_tolerance_degrees
                ),
                "rejection_reasons": [],
                "accepted": False,
                "selected": False,
            }
            if unavailable is not None:
                trial_record["rejection_reasons"].append(unavailable)
            else:
                key = (
                    round(float(candidate.x), 14),
                    round(float(candidate.y), 14),
                )
                trial_record["candidate_key_rounded_14"] = list(key)
                if key in seen:
                    trial_record["rejection_reasons"].append(
                        "candidate_duplicate_of_accepted_seed"
                    )
                if not all(
                    (candidate - value).length > epsilon * 16.0
                    for value in boundary + list(seeds)
                ):
                    trial_record["rejection_reasons"].append(
                        "candidate_below_existing_distance_floor"
                    )
                if not trial_record["rejection_reasons"]:
                    trial_seeds = list(seeds)
                    trial_seeds.append(candidate)
                    try:
                        trial = run_cdt(boundary, trial_seeds, epsilon)
                    except Exception as trial_error:
                        trial_record["trial_error_type"] = type(trial_error).__name__
                        trial_record["trial_error"] = str(trial_error)
                        trial_record["rejection_reasons"].append(
                            "trial_cdt_raised"
                        )
                    else:
                        trial_coordinates = list(trial["coordinates"])
                        trial_faces = list(trial["faces"])
                        trial_coordinate_keys = [
                            (round(float(value.x), 14), round(float(value.y), 14))
                            for value in trial_coordinates
                        ]
                        trial_rows = []
                        for trial_face in trial_faces:
                            trial_points = [
                                trial_coordinates[index] for index in trial_face
                            ]
                            trial_angles = triangle_angles(trial_points)
                            trial_edges = [
                                (
                                    trial_points[(edge_index + 1) % 3]
                                    - trial_points[edge_index]
                                ).length
                                for edge_index in range(3)
                            ]
                            trial_rows.append((
                                min(trial_angles),
                                min(trial_edges),
                                abs(orient2d(
                                    trial_points[0],
                                    trial_points[1],
                                    trial_points[2],
                                )),
                            ))
                        trial_minimum_angle = min(row[0] for row in trial_rows)
                        trial_minimum_edge = min(row[1] for row in trial_rows)
                        trial_minimum_area = min(row[2] for row in trial_rows)
                        zero_angle_face_count = sum(
                            1 for row in trial_rows if row[0] == 0.0
                        )
                        boundary_coordinates_exact = (
                            len(trial["boundary_output"]) == len(boundary)
                            and all(
                                float(
                                    trial_coordinates[
                                        trial["boundary_output"][source_index]
                                    ].x
                                ) == float(boundary[source_index].x)
                                and float(
                                    trial_coordinates[
                                        trial["boundary_output"][source_index]
                                    ].y
                                ) == float(boundary[source_index].y)
                                for source_index in range(len(boundary))
                            )
                        )
                        new_coordinate_keys = sorted(
                            set(trial_coordinate_keys)
                            - set(current_coordinate_keys)
                        )
                        candidate_represented_once = (
                            trial_coordinate_keys.count(key) == 1
                            and len(trial_coordinate_keys)
                            == len(current_coordinate_keys) + 1
                            and new_coordinate_keys == [key]
                        )
                        output_coordinates_unique = (
                            len(trial_coordinate_keys)
                            == len(set(trial_coordinate_keys))
                        )
                        strict_improvement = (
                            trial_minimum_angle
                            > minimum + improvement_tolerance_degrees
                        )
                        checks = {
                            "candidate_represented_once_as_only_new_output_coordinate": candidate_represented_once,
                            "boundary_coordinates_exact": boundary_coordinates_exact,
                            "output_coordinates_unique_rounded_14": output_coordinates_unique,
                            "zero_angle_face_count_is_zero": zero_angle_face_count == 0,
                            "minimum_edge_above_floor": trial_minimum_edge
                            > minimum_edge_floor_m,
                            "minimum_absolute_double_area_above_floor": trial_minimum_area
                            > minimum_absolute_double_area_floor_m2,
                            "strict_global_minimum_angle_improvement": strict_improvement,
                        }
                        trial_record.update({
                            "output_coordinate_count": len(trial_coordinates),
                            "output_face_count": len(trial_faces),
                            "new_output_coordinate_keys_rounded_14": [
                                list(value) for value in new_coordinate_keys
                            ],
                            "minimum_angle_degrees": float(trial_minimum_angle),
                            "minimum_edge_m": float(trial_minimum_edge),
                            "minimum_absolute_double_area_m2": float(
                                trial_minimum_area
                            ),
                            "zero_angle_face_count": zero_angle_face_count,
                            "checks": checks,
                        })
                        trial_record["rejection_reasons"].extend(
                            name for name, passed in checks.items() if not passed
                        )
                        if not trial_record["rejection_reasons"]:
                            trial_record["accepted"] = True
                            valid_trials.append({
                                "score": (
                                    float(trial_minimum_angle),
                                    float(trial_minimum_edge),
                                    float(trial_minimum_area),
                                    -candidate_order,
                                ),
                                "candidate": candidate,
                                "key": key,
                                "result": trial,
                                "minimum_angle": float(trial_minimum_angle),
                                "record": trial_record,
                            })
            trial_records.append(trial_record)
        iteration_record = {
            "iteration": iteration,
            "accepted_seed_count_before": len(seeds),
            "current_minimum_angle_degrees": float(minimum),
            "worst_face": list(_face),
            "candidate_order": ["circumcenter", "centroid"],
            "trials": trial_records,
            "selected_candidate_kind": None,
        }
        if not valid_trials:
            ATTEMPT37_CDT_REFINEMENT_TRACE.append(iteration_record)
            raise RuntimeError(
                "quality_refined_cdt_no_nondegrading_candidate:"
                f"current={minimum}:iteration={iteration}:seeds={len(seeds)}"
            )
        best = max(valid_trials, key=lambda value: value["score"])
        best["record"]["selected"] = True
        iteration_record["selected_candidate_kind"] = best["record"][
            "candidate_kind"
        ]
        iteration_record["selected_score"] = list(best["score"])
        ATTEMPT37_CDT_REFINEMENT_TRACE.append(iteration_record)
        seeds.append(best["candidate"])
        seen.add(best["key"])
        result = best["result"]
        if best["minimum_angle"] >= threshold:
            result["quality_refinement_iterations"] = iteration + 1
            result["seed_count"] = len(seeds)
            result["minimum_2d_triangle_angle_degrees"] = best[
                "minimum_angle"
            ]
            return result
'''


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def project_path(relative: str, *, must_exist: bool = True) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as error:
        raise RuntimeError(f"Attempt 37 path escapes project: {relative}") from error
    if must_exist and not path.is_file():
        raise RuntimeError(f"Attempt 37 bound file is absent: {relative}")
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
        raise RuntimeError(f"Attempt 37 bound byte count drifted: {label}")
    if actual["sha256"] != str(record["sha256"]):
        raise RuntimeError(f"Attempt 37 bound SHA-256 drifted: {label}")
    return actual


def _exact_replace(
    source: str,
    old: str,
    new: str,
    label: str,
    record: Mapping[str, Any],
) -> str:
    if sha256_text(old) != record["old_block_sha256"]:
        raise RuntimeError(f"Attempt 37 old block hash drifted: {label}")
    if sha256_text(new) != record["new_block_sha256"]:
        raise RuntimeError(f"Attempt 37 new block hash drifted: {label}")
    if int(record["exact_replacement_count"]) != 1 or source.count(old) != 1:
        raise RuntimeError(f"Attempt 37 exact old block is not unique: {label}")
    result = source.replace(old, new, 1)
    if old in result or result.count(new) != 1:
        raise RuntimeError(f"Attempt 37 source transform is not exact: {label}")
    return result


def patch_attempt35_source(source: str, config: Mapping[str, Any]) -> str:
    record = config["evidence_writer_patch"]
    result = _exact_replace(
        source,
        ATTEMPT35_WRITER_OLD,
        ATTEMPT35_WRITER_NEW,
        "attempt35_append_only_evidence_writer",
        record,
    )
    if sha256_text(result) != record["derived_attempt35_source_sha256"]:
        raise RuntimeError("Attempt 37 derived Attempt 35 source hash drifted")
    return result


def patch_attempt15_candidate_source(source: str, config: Mapping[str, Any]) -> str:
    record = config["candidate_selection_patch"]
    result = _exact_replace(
        source,
        ATTEMPT35_CANDIDATE_OLD,
        ATTEMPT37_CANDIDATE_NEW,
        "quality_refined_cdt_candidate_selection_and_acceptance",
        record,
    )
    if sha256_text(result) != record["derived_attempt15_source_sha256"]:
        raise RuntimeError("Attempt 37 derived Attempt 15 source hash drifted")
    return result


def _exec_source_module(name: str, path: Path, source: str) -> Any:
    code = compile(source, str(path), "exec")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    sys.modules[name] = module
    exec(code, module.__dict__)
    return module


def _load_static_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 37 cannot load bound module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 37 requires the exact configured manifest path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 37 config SHA-256 drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_37"
        or config.get("status") != "STATIC_REPAIR_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 37 identity drifted")
    scope = config["scope"]
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "later_independently_reviewed_blender_launch_required",
        "exact_attempt35_pipeline_required",
        "exact_attempt36_evidence_required",
        "one_candidate_selection_block_replacement_allowed",
        "append_only_json_evidence_allowed_during_later_run",
    )
    forbidden = (
        "source_file_mutation_allowed",
        "prior_evidence_mutation_allowed",
        "repair_domain_change_allowed",
        "boundary_change_allowed",
        "bootstrap_change_allowed",
        "quality_gate_reduction_allowed",
        "seed_cap_change_allowed",
        "render_allowed",
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "assignment_allowed",
        "publication_allowed",
        "automatic_retry_allowed",
    )
    if not all(scope.get(name) is True for name in required_true):
        raise RuntimeError("Attempt 37 required scope drifted")
    if any(scope.get(name) is not False for name in forbidden):
        raise RuntimeError("Attempt 37 forbidden scope drifted")
    repair = config["nondegrading_repair"]
    if (
        repair["candidate_order"] != ["circumcenter", "centroid"]
        or repair["incenter_reachable"] is not False
        or repair["trial_mutates_accepted_seed_list"] is not False
        or repair["strict_minimum_angle_improvement_tolerance_degrees"]
        != 1e-9
        or repair["minimum_edge_floor_epsilon_multiplier"] != 16.0
        or repair["minimum_absolute_double_area_floor_epsilon_squared_multiplier"]
        != 16.0
        or repair["minimum_angle_gate_degrees_unchanged"] != 12.0
        or repair["maximum_seed_count_unchanged"] != 160
        or repair["cdt_epsilon_m_unchanged"] != 1e-12
    ):
        raise RuntimeError("Attempt 37 repair contract drifted")
    output = config["runtime_overlay"]["output"]
    if output != {
        "root": "RecoverySprint/continuation_20260803/kira_r24_internal_midpoint_fair_surface/attempt_37",
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "TRIANGULATION_RECONSTRUCTION_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "candidate_trials": "CDT_NONDEGRADING_TRIALS.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }:
        raise RuntimeError("Attempt 37 output overlay drifted")
    if project_path(str(output["root"]), must_exist=False).exists():
        raise RuntimeError("Attempt 37 output already exists")
    launch = config["launch_contract"]
    if launch["executed_during_static_preparation"] is not False:
        raise RuntimeError("Attempt 37 launch truth drifted")
    for key in ("stdout", "stderr", "external_integrity"):
        if project_path(str(launch[key]), must_exist=False).exists():
            raise RuntimeError(f"Attempt 37 runtime target already exists: {key}")


def verify_overlay(config: Mapping[str, Any]) -> dict[str, object]:
    records = {
        str(label): require_record(str(label), record)
        for label, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    trace = json.loads(
        project_path(str(records["attempt36_quality_trace"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    failure = json.loads(
        project_path(str(records["attempt36_failure"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    expected_error = (
        "quality_refined_cdt_failed_minimum_angle:"
        "achieved=0.0:required=12.0:seeds=160"
    )
    if (
        trace["call_count"] != 124
        or trace["calls_sha256"]
        != "99aefc4c3ef4b8d8bdf290d7f39721a8244760df93770cbb74d83ab4f5b186fe"
        or trace["error"] != expected_error
        or failure["error"] != expected_error
        or failure["render_reached"]
        or failure["blend_saved"]
        or failure["runtime_changed"]
    ):
        raise RuntimeError("Attempt 37 bound Attempt 36 failure truth drifted")
    external = json.loads(
        project_path(str(records["attempt36_external_integrity"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    if (
        external["blender_exit_code"] != 1
        or external["native_invocation_error"] is not None
        or external["pre_post_exact"] is not True
        or external["before"] != external["after"]
        or len(external["before"]) != 216
    ):
        raise RuntimeError("Attempt 37 bound Attempt 36 integrity truth drifted")
    attempt35_path = project_path(str(records["attempt35_worker"]["path"]))
    derived35 = patch_attempt35_source(
        attempt35_path.read_text(encoding="utf-8"), config
    )
    compile(derived35, str(attempt35_path), "exec")
    attempt35_module = _load_static_module(
        "attempt37_static_bound_attempt35", attempt35_path
    )
    attempt35_config = json.loads(
        project_path(str(records["attempt35_config"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    attempt15_path = project_path(str(records["attempt15_worker"]["path"]))
    attempt15_derived35 = attempt35_module.derive_attempt15_source(
        attempt15_path.read_text(encoding="utf-8"), attempt35_config
    )
    derived15 = patch_attempt15_candidate_source(attempt15_derived35, config)
    compile(derived15, str(attempt15_path), "exec")
    return {
        "records": records,
        "trace": trace,
        "failure": failure,
        "derived_attempt35_sha256": sha256_text(derived35),
        "derived_attempt15_sha256": sha256_text(derived15),
    }


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)


def run_blender(config_path: Path, config: Mapping[str, Any]) -> None:
    verified = verify_overlay(config)
    attempt35_path = project_path(str(config["bindings"]["attempt35_worker"]["path"]))
    derived35 = patch_attempt35_source(
        attempt35_path.read_text(encoding="utf-8"), config
    )
    module_name = "attempt37_bound_attempt35"
    missing = object()
    prior_module = sys.modules.get(module_name, missing)
    attempt35 = _exec_source_module(module_name, attempt35_path, derived35)
    attempt35_config_path = project_path(
        str(config["bindings"]["attempt35_config"]["path"])
    )
    attempt35_config = json.loads(attempt35_config_path.read_text(encoding="utf-8"))
    runtime_config = deepcopy(attempt35_config)
    runtime_config["runtime_overlay"]["output"] = {
        key: value
        for key, value in config["runtime_overlay"]["output"].items()
        if key != "candidate_trials"
    }
    repair_metadata = {
        "worker": file_record(Path(__file__).resolve()),
        "config": file_record(config_path),
        "proposal": verified["records"]["proposal"],
        "attempt36_quality_trace": verified["records"]["attempt36_quality_trace"],
        "attempt36_failure": verified["records"]["attempt36_failure"],
        "derived_attempt35_source_sha256": config["evidence_writer_patch"][
            "derived_attempt35_source_sha256"
        ],
        "derived_attempt15_source_sha256": config["candidate_selection_patch"][
            "derived_attempt15_source_sha256"
        ],
        "candidate_order": ["circumcenter", "centroid"],
        "incenter_reachable": False,
        "strict_improvement_tolerance_degrees": 1e-9,
        "minimum_edge_floor_m_at_bound_epsilon": 1.6e-11,
        "minimum_absolute_double_area_floor_m2_at_bound_epsilon": 1.6e-23,
        "render_permitted": False,
        "blend_save_permitted": False,
    }
    attempt35.ATTEMPT37_REPAIR_METADATA = repair_metadata
    original_exec = attempt35._exec_source_module
    provider_holder: dict[str, Any] = {}

    def attempt37_exec(name: str, path: Path, source: str) -> Any:
        exact_attempt15 = project_path(
            str(config["bindings"]["attempt15_worker"]["path"])
        )
        if path.resolve() != exact_attempt15.resolve():
            return original_exec(name, path, source)
        patched = patch_attempt15_candidate_source(source, config)
        provider = original_exec(name, path, patched)
        provider.ATTEMPT37_CDT_REFINEMENT_TRACE = []
        provider_holder["provider"] = provider
        return provider

    attempt35._exec_source_module = attempt37_exec
    attempt35.__file__ = str(Path(__file__).resolve())
    output = project_path(
        str(config["runtime_overlay"]["output"]["root"]), must_exist=False
    )
    trace_path = output / str(
        config["runtime_overlay"]["output"]["candidate_trials"]
    )
    caught: BaseException | None = None
    try:
        attempt35.run_blender(config_path, runtime_config)
    except BaseException as error:
        caught = error
    finally:
        attempt35._exec_source_module = original_exec
        provider = provider_holder.get("provider")
        trial_rows = (
            deepcopy(provider.ATTEMPT37_CDT_REFINEMENT_TRACE)
            if provider is not None
            else []
        )
        evidence = {
            "schema": "kira.avatar.r24.blackproject_attempt37.nondegrading_cdt_trials.v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": (
                "TRIAL_EVIDENCE_CAPTURED_AFTER_PIPELINE_RETURN"
                if caught is None
                else "TRIAL_EVIDENCE_CAPTURED_AFTER_PIPELINE_FAILURE"
            ),
            "attempt_id": "attempt_37",
            "repair": repair_metadata,
            "error_type": None if caught is None else type(caught).__name__,
            "error": None if caught is None else str(caught),
            "iteration_count": len(trial_rows),
            "iterations_sha256": canonical_sha256(trial_rows),
            "iterations": trial_rows,
        }
        if output.is_dir():
            _write_once(trace_path, evidence)
        if prior_module is missing:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = prior_module
    if caught is not None:
        raise caught


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
