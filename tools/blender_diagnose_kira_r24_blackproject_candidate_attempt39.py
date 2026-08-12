"""Static-first Attempt 39 constrained-edge seed-relocation repair.

The exact Attempt 38 pipeline and launch ownership remain bound.  A later,
independently reviewed no-save run may replace only the refinement candidate
block.  The replacement recognizes a bad face made from one fixed boundary
segment and one uniquely matched accepted seed, then evaluates isolated
removal/relocation trials.  No accepted state changes until a complete trial
proves non-degrading deterministic quality progress and every numerical gate.
Static import is Blender-free and never launches Blender.
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
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT39_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = "1c2a11a0f3a7ac3d90cc87a6d91d1d1968bb869f6f0e5fa120dcad4c458c4b87"


ATTEMPT39_WRITER_NEW = '''        def attempt39_writer(target: Path, value: Mapping[str, Any]) -> None:
            result = deepcopy(dict(value))
            if isinstance(result.get("schema"), str):
                result["schema"] = result["schema"].replace("attempt33", "attempt39")
                result["schema"] = result["schema"].replace("attempt34", "attempt39")
                result["schema"] = result["schema"].replace("attempt35", "attempt39")
                result["schema"] = result["schema"].replace("attempt38", "attempt39")
            if result.get("attempt_id") in {
                "attempt_33", "attempt_34", "attempt_35", "attempt_38"
            }:
                result["attempt_id"] = "attempt_39"
            if isinstance(result.get("status"), str):
                result["status"] = result["status"].replace("ATTEMPT33", "ATTEMPT39")
                result["status"] = result["status"].replace("ATTEMPT34", "ATTEMPT39")
                result["status"] = result["status"].replace("ATTEMPT35", "ATTEMPT39")
                result["status"] = result["status"].replace("ATTEMPT38", "ATTEMPT39")
            result["attempt35_dimension_patch"] = deepcopy(dimension_metadata)
            result["attempt37_nondegrading_cdt_repair"] = deepcopy(
                ATTEMPT37_REPAIR_METADATA
            )
            result["attempt38_launch_target_ownership_repair"] = deepcopy(
                ATTEMPT38_LAUNCH_METADATA
            )
            result["attempt39_constrained_edge_seed_relocation"] = deepcopy(
                ATTEMPT39_RELOCATION_METADATA
            )
            raw_writer(target, result)

        module._load_module = attempt35_provider_loader
        module._exclusive_write_once = attempt39_writer
'''


ATTEMPT39_CANDIDATE_NEW = '''        quality_sorted = sorted(
            quality, key=lambda value: (value[0], tuple(value[1]))
        )
        _angle, _face, points = quality_sorted[0]
        improvement_tolerance_degrees = 1.0e-9
        minimum_edge_floor_m = epsilon * 16.0
        minimum_absolute_double_area_floor_m2 = epsilon * epsilon * 16.0
        current_floor_face_count = sum(
            1
            for value in quality_sorted
            if value[0] <= minimum + improvement_tolerance_degrees
        )
        current_coordinate_keys = [
            (round(float(value.x), 14), round(float(value.y), 14))
            for value in result["coordinates"]
        ]
        output_to_boundary = {
            int(output_index): int(source_index)
            for source_index, output_index in result["boundary_output"].items()
        }
        constrained_face_edges = []
        for edge_offset in range(3):
            first_output = int(_face[edge_offset])
            second_output = int(_face[(edge_offset + 1) % 3])
            if (
                first_output not in output_to_boundary
                or second_output not in output_to_boundary
            ):
                continue
            first_source = output_to_boundary[first_output]
            second_source = output_to_boundary[second_output]
            if (first_source + 1) % len(boundary) == second_source:
                ordered_sources = (first_source, second_source)
            elif (second_source + 1) % len(boundary) == first_source:
                ordered_sources = (second_source, first_source)
            else:
                continue
            constrained_face_edges.append({
                "output_indices": [first_output, second_output],
                "ordered_boundary_sources": list(ordered_sources),
            })
        nonboundary_face_outputs = [
            int(output_index)
            for output_index in _face
            if int(output_index) not in output_to_boundary
        ]
        matched_seed_rows = []
        for output_index in nonboundary_face_outputs:
            coordinate = result["coordinates"][output_index]
            coordinate_key = (
                round(float(coordinate.x), 14),
                round(float(coordinate.y), 14),
            )
            matching_seed_indices = [
                seed_index
                for seed_index, seed in enumerate(seeds)
                if (
                    round(float(seed.x), 14),
                    round(float(seed.y), 14),
                ) == coordinate_key
            ]
            if len(matching_seed_indices) == 1:
                matched_seed_rows.append({
                    "output_index": output_index,
                    "seed_index": matching_seed_indices[0],
                    "coordinate_key": coordinate_key,
                })
        precondition_rejections = []
        if len(constrained_face_edges) != 1:
            precondition_rejections.append(
                "worst_face_does_not_have_exactly_one_constrained_boundary_edge"
            )
        if len(nonboundary_face_outputs) != 1:
            precondition_rejections.append(
                "worst_face_does_not_have_exactly_one_nonboundary_vertex"
            )
        if len(matched_seed_rows) != 1:
            precondition_rejections.append(
                "nonboundary_vertex_does_not_match_exactly_one_accepted_seed"
            )
        trial_specs = []
        matched_seed = matched_seed_rows[0] if len(matched_seed_rows) == 1 else None
        if not precondition_rejections:
            edge_record = constrained_face_edges[0]
            first_source, second_source = edge_record["ordered_boundary_sources"]
            edge_first = boundary[first_source]
            edge_second = boundary[second_source]
            edge_vector = edge_second - edge_first
            edge_length = edge_vector.length
            if edge_length <= minimum_edge_floor_m:
                precondition_rejections.append(
                    "constrained_boundary_edge_below_minimum_edge_floor"
                )
            else:
                trial_specs.append(("remove_seed_only", None, None))
                midpoint = (edge_first + edge_second) / 2.0
                inward = Vector((
                    -float(edge_vector.y) / edge_length,
                    float(edge_vector.x) / edge_length,
                ))
                for target_angle_degrees in (12.5, 18.0, 24.0):
                    height = (
                        edge_length
                        * 0.5
                        * math.tan(math.radians(target_angle_degrees))
                    )
                    candidate = midpoint + inward * height
                    trial_specs.append((
                        f"relocate_offcenter_{target_angle_degrees:g}_degrees",
                        candidate,
                        target_angle_degrees,
                    ))
        trial_records = []
        valid_trials = []
        if not precondition_rejections:
            old_seed_index = int(matched_seed["seed_index"])
            old_key = tuple(matched_seed["coordinate_key"])
            for trial_order, (trial_kind, candidate, target_angle) in enumerate(
                trial_specs
            ):
                trial_record = {
                    "trial_order": trial_order,
                    "trial_kind": trial_kind,
                    "matched_seed_index": old_seed_index,
                    "removed_seed_key_rounded_14": list(old_key),
                    "offcenter_target_angle_degrees": target_angle,
                    "candidate": (
                        None
                        if candidate is None
                        else [float(candidate.x), float(candidate.y)]
                    ),
                    "current_minimum_angle_degrees": float(minimum),
                    "current_floor_face_count": current_floor_face_count,
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
                trial_seeds = list(seeds)
                removed_seed = trial_seeds.pop(old_seed_index)
                if (
                    round(float(removed_seed.x), 14),
                    round(float(removed_seed.y), 14),
                ) != old_key:
                    trial_record["rejection_reasons"].append(
                        "matched_seed_identity_drifted"
                    )
                candidate_key = None
                if candidate is not None:
                    candidate_key = (
                        round(float(candidate.x), 14),
                        round(float(candidate.y), 14),
                    )
                    trial_record["candidate_key_rounded_14"] = list(candidate_key)
                    if candidate_key == old_key:
                        trial_record["rejection_reasons"].append(
                            "candidate_equals_removed_seed"
                        )
                    if candidate_key in {
                        (round(float(value.x), 14), round(float(value.y), 14))
                        for value in boundary + trial_seeds
                    }:
                        trial_record["rejection_reasons"].append(
                            "candidate_duplicates_retained_coordinate"
                        )
                    if not all(
                        (candidate - value).length > minimum_edge_floor_m
                        for value in boundary + trial_seeds
                    ):
                        trial_record["rejection_reasons"].append(
                            "candidate_below_existing_distance_floor"
                        )
                    first_source, second_source = constrained_face_edges[0][
                        "ordered_boundary_sources"
                    ]
                    if orient2d(
                        boundary[first_source], boundary[second_source], candidate
                    ) <= epsilon * epsilon:
                        trial_record["rejection_reasons"].append(
                            "candidate_not_strictly_on_ccw_interior_side"
                        )
                    trial_seeds.append(candidate)
                if not trial_record["rejection_reasons"]:
                    try:
                        trial = run_cdt(boundary, trial_seeds, epsilon)
                    except Exception as trial_error:
                        trial_record["trial_error_type"] = type(trial_error).__name__
                        trial_record["trial_error"] = str(trial_error)
                        trial_record["rejection_reasons"].append("trial_cdt_raised")
                    else:
                        trial_coordinates = list(trial["coordinates"])
                        trial_faces = list(trial["faces"])
                        trial_coordinate_keys = [
                            (round(float(value.x), 14), round(float(value.y), 14))
                            for value in trial_coordinates
                        ]
                        removed_coordinate_keys = sorted(
                            set(current_coordinate_keys)
                            - set(trial_coordinate_keys)
                        )
                        added_coordinate_keys = sorted(
                            set(trial_coordinate_keys)
                            - set(current_coordinate_keys)
                        )
                        expected_added = [] if candidate_key is None else [candidate_key]
                        expected_count = len(current_coordinate_keys) + (
                            -1 if candidate_key is None else 0
                        )
                        exact_coordinate_transition = (
                            current_coordinate_keys.count(old_key) == 1
                            and removed_coordinate_keys == [old_key]
                            and added_coordinate_keys == expected_added
                            and len(trial_coordinate_keys) == expected_count
                            and (
                                candidate_key is None
                                or trial_coordinate_keys.count(candidate_key) == 1
                            )
                        )
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
                        trial_floor_face_count = sum(
                            1
                            for row in trial_rows
                            if row[0]
                            <= minimum + improvement_tolerance_degrees
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
                        output_coordinates_unique = (
                            len(trial_coordinate_keys)
                            == len(set(trial_coordinate_keys))
                        )
                        global_minimum_nondegrading = (
                            trial_minimum_angle >= minimum
                        )
                        strict_global_minimum_improvement = (
                            trial_minimum_angle
                            > minimum + improvement_tolerance_degrees
                        )
                        tied_floor_face_count_reduction = (
                            not strict_global_minimum_improvement
                            and trial_floor_face_count < current_floor_face_count
                        )
                        deterministic_quality_progress = (
                            strict_global_minimum_improvement
                            or tied_floor_face_count_reduction
                        )
                        checks = {
                            "exact_one_seed_remove_or_relocation_coordinate_transition": exact_coordinate_transition,
                            "boundary_coordinates_exact": boundary_coordinates_exact,
                            "output_coordinates_unique_rounded_14": output_coordinates_unique,
                            "zero_angle_face_count_is_zero": zero_angle_face_count == 0,
                            "minimum_edge_above_floor": trial_minimum_edge
                            > minimum_edge_floor_m,
                            "minimum_absolute_double_area_above_floor": trial_minimum_area
                            > minimum_absolute_double_area_floor_m2,
                            "global_minimum_angle_nondegrading": global_minimum_nondegrading,
                            "deterministic_quality_progress": deterministic_quality_progress,
                        }
                        trial_record.update({
                            "output_coordinate_count": len(trial_coordinates),
                            "output_face_count": len(trial_faces),
                            "removed_coordinate_keys_rounded_14": [
                                list(value) for value in removed_coordinate_keys
                            ],
                            "added_coordinate_keys_rounded_14": [
                                list(value) for value in added_coordinate_keys
                            ],
                            "minimum_angle_degrees": float(trial_minimum_angle),
                            "minimum_edge_m": float(trial_minimum_edge),
                            "minimum_absolute_double_area_m2": float(
                                trial_minimum_area
                            ),
                            "zero_angle_face_count": zero_angle_face_count,
                            "floor_face_count": trial_floor_face_count,
                            "strict_global_minimum_improvement": strict_global_minimum_improvement,
                            "tied_floor_face_count_reduction": tied_floor_face_count_reduction,
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
                                    -int(trial_floor_face_count),
                                    float(trial_minimum_edge),
                                    float(trial_minimum_area),
                                    -trial_order,
                                ),
                                "seeds": trial_seeds,
                                "result": trial,
                                "minimum_angle": float(trial_minimum_angle),
                                "record": trial_record,
                            })
                trial_records.append(trial_record)
        iteration_record = {
            "iteration": iteration,
            "accepted_seed_count_before": len(seeds),
            "current_minimum_angle_degrees": float(minimum),
            "current_floor_face_count": current_floor_face_count,
            "worst_face": list(_face),
            "constrained_face_edges": constrained_face_edges,
            "nonboundary_face_outputs": nonboundary_face_outputs,
            "matched_seed_rows": [
                {
                    **value,
                    "coordinate_key": list(value["coordinate_key"]),
                }
                for value in matched_seed_rows
            ],
            "precondition_rejections": precondition_rejections,
            "trial_order": [
                "remove_seed_only",
                "relocate_offcenter_12.5_degrees",
                "relocate_offcenter_18_degrees",
                "relocate_offcenter_24_degrees",
            ],
            "trials": trial_records,
            "selected_trial_kind": None,
        }
        if precondition_rejections or not valid_trials:
            ATTEMPT39_CDT_REFINEMENT_TRACE.append(iteration_record)
            raise RuntimeError(
                "quality_refined_cdt_no_guarded_seed_relocation_progress:"
                f"current={minimum}:iteration={iteration}:seeds={len(seeds)}"
            )
        best = max(valid_trials, key=lambda value: value["score"])
        best["record"]["selected"] = True
        iteration_record["selected_trial_kind"] = best["record"]["trial_kind"]
        iteration_record["selected_score"] = list(best["score"])
        ATTEMPT39_CDT_REFINEMENT_TRACE.append(iteration_record)
        seeds = list(best["seeds"])
        seen = {
            (round(float(value.x), 14), round(float(value.y), 14))
            for value in seeds
        }
        result = best["result"]
        if best["minimum_angle"] >= threshold:
            result["quality_refinement_iterations"] = iteration + 1
            result["seed_count"] = len(seeds)
            result["minimum_2d_triangle_angle_degrees"] = best[
                "minimum_angle"
            ]
            return result
'''


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    )


def project_path(relative: str, *, must_exist: bool = True) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as error:
        raise RuntimeError(f"Attempt 39 path escapes project: {relative}") from error
    if must_exist and not path.is_file():
        raise RuntimeError(f"Attempt 39 bound file is absent: {relative}")
    return path


def file_record(path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def require_record(label: str, record: Mapping[str, object]) -> dict[str, object]:
    actual = file_record(project_path(str(record["path"])))
    if actual["bytes"] != int(record["bytes"]):
        raise RuntimeError(f"Attempt 39 bound byte count drifted: {label}")
    if actual["sha256"] != str(record["sha256"]):
        raise RuntimeError(f"Attempt 39 bound SHA-256 drifted: {label}")
    return actual


def _load_static_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 39 cannot load bound module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _exec_source_module(name: str, path: Path, source: str) -> Any:
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    sys.modules[name] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def _exact_replace(
    source: str,
    old: str,
    new: str,
    label: str,
    record: Mapping[str, Any],
) -> str:
    if sha256_text(old) != record["old_block_sha256"]:
        raise RuntimeError(f"Attempt 39 old block hash drifted: {label}")
    if sha256_text(new) != record["new_block_sha256"]:
        raise RuntimeError(f"Attempt 39 new block hash drifted: {label}")
    if int(record["exact_replacement_count"]) != 1 or source.count(old) != 1:
        raise RuntimeError(f"Attempt 39 exact old block is not unique: {label}")
    result = source.replace(old, new, 1)
    if old in result or result.count(new) != 1:
        raise RuntimeError(f"Attempt 39 source transform is not exact: {label}")
    return result


def load_attempt38(config: Mapping[str, Any]) -> Any:
    record = config["bindings"]["attempt38_worker"]
    path = project_path(str(record["path"]))
    require_record("attempt38_worker", record)
    return _load_static_module("attempt39_exact_bound_attempt38", path)


def patch_attempt35_source(
    source: str, config: Mapping[str, Any], attempt38: Any, attempt37: Any
) -> str:
    attempt38_config = json.loads(
        project_path(str(config["bindings"]["attempt38_config"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    derived38 = attempt38.patch_attempt35_source(
        source, attempt38_config, attempt37
    )
    result = _exact_replace(
        derived38,
        attempt38.ATTEMPT38_WRITER_NEW,
        ATTEMPT39_WRITER_NEW,
        "attempt38_to_attempt39_append_only_evidence_writer",
        config["evidence_writer_patch"],
    )
    if sha256_text(result) != config["evidence_writer_patch"][
        "derived_attempt35_source_sha256"
    ]:
        raise RuntimeError("Attempt 39 derived Attempt 35 source hash drifted")
    return result


def patch_attempt15_candidate_source(
    source: str, config: Mapping[str, Any], attempt38: Any, attempt37: Any
) -> str:
    attempt38_config = json.loads(
        project_path(str(config["bindings"]["attempt38_config"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    derived38 = attempt38.patch_attempt15_candidate_source(
        source, attempt38_config, attempt37
    )
    result = _exact_replace(
        derived38,
        attempt37.ATTEMPT37_CANDIDATE_NEW,
        ATTEMPT39_CANDIDATE_NEW,
        "attempt38_to_attempt39_quality_refinement_candidate_block",
        config["candidate_selection_patch"],
    )
    if sha256_text(result) != config["candidate_selection_patch"][
        "derived_attempt15_source_sha256"
    ]:
        raise RuntimeError("Attempt 39 derived Attempt 15 source hash drifted")
    return result


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 39 requires the exact configured manifest path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 39 config SHA-256 drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_39"
        or config.get("status") != "STATIC_REPAIR_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 39 identity drifted")
    scope = config["scope"]
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "later_independently_reviewed_blender_launch_required",
        "exact_attempt38_pipeline_and_launch_contract_required",
        "initial_bootstrap_generation_unchanged",
        "one_candidate_selection_block_replacement_allowed",
        "isolated_seed_relocation_trials_allowed",
        "append_only_json_evidence_allowed_during_later_run",
        "wrapper_owns_external_runtime_targets",
        "worker_owns_runtime_output_root",
    )
    forbidden = (
        "source_file_mutation_allowed",
        "prior_evidence_mutation_allowed",
        "repair_domain_change_allowed",
        "boundary_change_allowed",
        "quality_gate_reduction_allowed",
        "seed_cap_increase_allowed",
        "iteration_cap_increase_allowed",
        "render_allowed",
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "assignment_allowed",
        "publication_allowed",
        "automatic_retry_allowed",
    )
    if not all(scope.get(name) is True for name in required_true):
        raise RuntimeError("Attempt 39 required scope drifted")
    if any(scope.get(name) is not False for name in forbidden):
        raise RuntimeError("Attempt 39 forbidden scope drifted")
    repair = config["guarded_seed_relocation"]
    if (
        repair["trial_order"]
        != [
            "remove_seed_only",
            "relocate_offcenter_12.5_degrees",
            "relocate_offcenter_18_degrees",
            "relocate_offcenter_24_degrees",
        ]
        or repair["initial_bootstrap_centroid_count_unchanged"] != 38
        or repair["strict_improvement_tolerance_degrees"] != 1e-9
        or repair["minimum_angle_gate_degrees_unchanged"] != 12.0
        or repair["cdt_epsilon_m_unchanged"] != 1e-12
        or repair["maximum_seed_count_unchanged"] != 160
        or repair["maximum_quality_refinement_iterations_unchanged"] != 192
    ):
        raise RuntimeError("Attempt 39 relocation contract drifted")
    output = config["runtime_overlay"]["output"]
    if output != {
        "root": "RecoverySprint/continuation_20260803/kira_r24_internal_midpoint_fair_surface/attempt_39",
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "TRIANGULATION_RECONSTRUCTION_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "candidate_trials": "CDT_SEED_RELOCATION_TRIALS.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }:
        raise RuntimeError("Attempt 39 output overlay drifted")
    if project_path(str(output["root"]), must_exist=False).exists():
        raise RuntimeError("Attempt 39 output already exists")
    launch = config["launch_contract"]
    if (
        launch["executed_during_static_preparation"] is not False
        or launch["wrapper_owns_stdout_stderr_and_integrity"] is not True
        or launch["worker_checks_only_runtime_output_root_absent"] is not True
        or launch["worker_writes_external_targets"] is not False
    ):
        raise RuntimeError("Attempt 39 launch contract drifted")


def verify_overlay(config: Mapping[str, Any]) -> dict[str, Any]:
    records = {
        str(label): require_record(str(label), record)
        for label, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    trials = json.loads(
        project_path(str(records["attempt38_trials"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    failure = json.loads(
        project_path(str(records["attempt38_failure"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    expected_error = (
        "quality_refined_cdt_no_nondegrading_candidate:"
        "current=2.635073748299402:iteration=0:seeds=38"
    )
    if (
        trials["error"] != expected_error
        or failure["error"] != expected_error
        or trials["iteration_count"] != 1
        or trials["iterations"][0]["worst_face"] != [77, 23, 24]
        or failure["render_reached"]
        or failure["blend_saved"]
        or failure["runtime_changed"]
    ):
        raise RuntimeError("Attempt 39 bound Attempt 38 failure truth drifted")
    trial_rows = trials["iterations"][0]["trials"]
    if (
        trial_rows[0]["candidate_kind"] != "circumcenter"
        or trial_rows[0]["minimum_angle_degrees"] != 2.635073748299402
        or trial_rows[1]["candidate_kind"] != "centroid"
        or trial_rows[1]["minimum_angle_degrees"] != 0.9799868976552613
    ):
        raise RuntimeError("Attempt 39 bound Attempt 38 trial evidence drifted")
    integrity = json.loads(
        project_path(str(records["attempt38_external_integrity"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    if (
        integrity["blender_exit_code"] != 1
        or integrity["native_invocation_error"] is not None
        or integrity["pre_post_exact"] is not True
        or integrity["before"] != integrity["after"]
        or len(integrity["before"]) != 240
    ):
        raise RuntimeError("Attempt 39 bound Attempt 38 integrity truth drifted")
    attempt38 = load_attempt38(config)
    attempt38_config = json.loads(
        project_path(str(records["attempt38_config"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    attempt37 = attempt38.load_attempt37(attempt38_config)
    attempt35_path = project_path(str(records["attempt35_worker"]["path"]))
    derived35 = patch_attempt35_source(
        attempt35_path.read_text(encoding="utf-8"), config, attempt38, attempt37
    )
    compile(derived35, str(attempt35_path), "exec")
    attempt35_static = _load_static_module(
        "attempt39_static_bound_attempt35", attempt35_path
    )
    attempt35_config = json.loads(
        project_path(str(records["attempt35_config"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    attempt15_path = project_path(str(records["attempt15_worker"]["path"]))
    derived15_base = attempt35_static.derive_attempt15_source(
        attempt15_path.read_text(encoding="utf-8"), attempt35_config
    )
    derived15 = patch_attempt15_candidate_source(
        derived15_base, config, attempt38, attempt37
    )
    compile(derived15, str(attempt15_path), "exec")
    return {
        "records": records,
        "trials": trials,
        "failure": failure,
        "attempt38": attempt38,
        "attempt37": attempt37,
        "derived_attempt35_sha256": sha256_text(derived35),
        "derived_attempt15_sha256": sha256_text(derived15),
    }


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)


def run_blender(config_path: Path, config: Mapping[str, Any]) -> None:
    verified = verify_overlay(config)
    attempt38 = verified["attempt38"]
    attempt37 = verified["attempt37"]
    attempt35_path = project_path(str(config["bindings"]["attempt35_worker"]["path"]))
    derived35 = patch_attempt35_source(
        attempt35_path.read_text(encoding="utf-8"), config, attempt38, attempt37
    )
    module_name = "attempt39_bound_attempt35"
    missing = object()
    prior_module = sys.modules.get(module_name, missing)
    attempt35 = _exec_source_module(module_name, attempt35_path, derived35)
    attempt35_config = json.loads(
        project_path(str(config["bindings"]["attempt35_config"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    runtime_config = deepcopy(attempt35_config)
    runtime_config["runtime_overlay"]["output"] = {
        key: value
        for key, value in config["runtime_overlay"]["output"].items()
        if key != "candidate_trials"
    }
    attempt37_metadata = {
        "source_attempt": "attempt_37_preserved_nondegrading_predecessor",
        "worker": verified["records"]["attempt37_worker"],
        "minimum_angle_gate_degrees": 12.0,
        "render_permitted": False,
        "blend_save_permitted": False,
    }
    attempt38_metadata = {
        "source_attempt": "attempt_38_preserved_launch_contract_and_failure",
        "worker": verified["records"]["attempt38_worker"],
        "config": verified["records"]["attempt38_config"],
        "runtime_checkpoint": verified["records"]["attempt38_runtime_checkpoint"],
        "wrapper_owns_stdout_stderr_and_integrity": True,
        "worker_owns_runtime_output_root": True,
        "worker_writes_external_targets": False,
    }
    relocation_metadata = {
        "worker": file_record(Path(__file__).resolve()),
        "config": file_record(config_path),
        "proposal": verified["records"]["proposal"],
        "attempt38_trials": verified["records"]["attempt38_trials"],
        "attempt38_failure": verified["records"]["attempt38_failure"],
        "trial_order": config["guarded_seed_relocation"]["trial_order"],
        "strict_improvement_tolerance_degrees": 1e-9,
        "minimum_angle_gate_degrees": 12.0,
        "maximum_seed_count": 160,
        "render_permitted": False,
        "blend_save_permitted": False,
    }
    attempt35.ATTEMPT37_REPAIR_METADATA = attempt37_metadata
    attempt35.ATTEMPT38_LAUNCH_METADATA = attempt38_metadata
    attempt35.ATTEMPT39_RELOCATION_METADATA = relocation_metadata
    original_exec = attempt35._exec_source_module
    provider_holder: dict[str, Any] = {}

    def attempt39_exec(name: str, path: Path, source: str) -> Any:
        exact_attempt15 = project_path(
            str(config["bindings"]["attempt15_worker"]["path"])
        )
        if path.resolve() != exact_attempt15.resolve():
            return original_exec(name, path, source)
        patched = patch_attempt15_candidate_source(
            source, config, attempt38, attempt37
        )
        provider = original_exec(name, path, patched)
        provider.ATTEMPT39_CDT_REFINEMENT_TRACE = []
        provider_holder["provider"] = provider
        return provider

    attempt35._exec_source_module = attempt39_exec
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
            deepcopy(provider.ATTEMPT39_CDT_REFINEMENT_TRACE)
            if provider is not None
            else []
        )
        evidence = {
            "schema": "kira.avatar.r24.blackproject_attempt39.seed_relocation_trials.v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": (
                "TRIAL_EVIDENCE_CAPTURED_AFTER_PIPELINE_RETURN"
                if caught is None
                else "TRIAL_EVIDENCE_CAPTURED_AFTER_PIPELINE_FAILURE"
            ),
            "attempt_id": "attempt_39",
            "attempt38_launch_contract": attempt38_metadata,
            "repair": relocation_metadata,
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
