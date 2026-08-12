"""Static-first Attempt 36 quality-refinement trace orchestration.

The exact Attempt 35 pipeline remains byte-bound. A later reviewed run wraps
only its derived Attempt 15 ``run_cdt`` callable to observe inputs and returned
geometry. The wrapper returns the exact original result and changes no
candidate, decision, coordinate, threshold, seed cap, domain, or algorithm.
Static import is Blender-free and does not run the diagnostic.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import types
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT36_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = "4cafcc80ad746975bbb66ffe2ba3b58c2264d9ddbe8e1ccb5b9433c03a327cc1"

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

ATTEMPT35_WRITER_NEW = '''        def attempt36_writer(target: Path, value: Mapping[str, Any]) -> None:
            result = deepcopy(dict(value))
            if isinstance(result.get("schema"), str):
                result["schema"] = result["schema"].replace("attempt33", "attempt36")
                result["schema"] = result["schema"].replace("attempt34", "attempt36")
                result["schema"] = result["schema"].replace("attempt35", "attempt36")
            if result.get("attempt_id") in {"attempt_33", "attempt_34", "attempt_35"}:
                result["attempt_id"] = "attempt_36"
            if isinstance(result.get("status"), str):
                result["status"] = result["status"].replace("ATTEMPT33", "ATTEMPT36")
                result["status"] = result["status"].replace("ATTEMPT34", "ATTEMPT36")
                result["status"] = result["status"].replace("ATTEMPT35", "ATTEMPT36")
            result["attempt35_dimension_patch"] = deepcopy(dimension_metadata)
            result["attempt36_quality_instrumentation"] = deepcopy(
                ATTEMPT36_INSTRUMENTATION_METADATA
            )
            raw_writer(target, result)

        module._load_module = attempt35_provider_loader
        module._exclusive_write_once = attempt36_writer
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
        raise RuntimeError(f"Attempt 36 path escapes project: {relative}") from error
    if must_exist and not path.is_file():
        raise RuntimeError(f"Attempt 36 bound file is absent: {relative}")
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
        raise RuntimeError(f"Attempt 36 bound byte count drifted: {label}")
    if actual["sha256"] != str(record["sha256"]):
        raise RuntimeError(f"Attempt 36 bound SHA-256 drifted: {label}")
    return actual


def patch_attempt35_source(source: str, config: Mapping[str, Any]) -> str:
    record = config["evidence_writer_patch"]
    if sha256_text(ATTEMPT35_WRITER_OLD) != record["old_block_sha256"]:
        raise RuntimeError("Attempt 36 old writer block hash drifted")
    if sha256_text(ATTEMPT35_WRITER_NEW) != record["new_block_sha256"]:
        raise RuntimeError("Attempt 36 new writer block hash drifted")
    if int(record["exact_replacement_count"]) != 1 or source.count(ATTEMPT35_WRITER_OLD) != 1:
        raise RuntimeError("Attempt 36 exact old writer block is not unique")
    result = source.replace(ATTEMPT35_WRITER_OLD, ATTEMPT35_WRITER_NEW, 1)
    if ATTEMPT35_WRITER_OLD in result or result.count(ATTEMPT35_WRITER_NEW) != 1:
        raise RuntimeError("Attempt 36 writer source transform is not exact")
    if sha256_text(result) != record["derived_attempt35_source_sha256"]:
        raise RuntimeError("Attempt 36 derived Attempt 35 source hash drifted")
    return result


def _exec_source_module(name: str, path: Path, source: str) -> Any:
    code = compile(source, str(path), "exec")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    sys.modules[name] = module
    exec(code, module.__dict__)
    return module


def _float_record(value: float) -> dict[str, Any]:
    exact = float(value)
    return {"value": exact, "hex": exact.hex()}


def _vector_record(value: Any) -> list[dict[str, Any]]:
    return [_float_record(float(value[index])) for index in range(2)]


def _face_record(face: Sequence[int], coordinates: Sequence[Any]) -> dict[str, Any]:
    return {
        "indices": [int(value) for value in face],
        "coordinates": [_vector_record(coordinates[int(index)]) for index in face],
    }


def _minimum_pair_distance(values: Sequence[Any]) -> float | None:
    if len(values) < 2:
        return None
    return min(
        float((values[first] - values[second]).length)
        for first in range(len(values))
        for second in range(first + 1, len(values))
    )


def measure_cdt_call(
    provider: Any,
    boundary: Sequence[Any],
    seeds: Sequence[Any],
    epsilon: float,
    result: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
    call_index: int,
) -> dict[str, Any]:
    coordinates = list(result["coordinates"])
    faces = [list(map(int, face)) for face in result["faces"]]
    rows = []
    for face in faces:
        points = [coordinates[index] for index in face]
        angles = [float(value) for value in provider.triangle_angles(points)]
        edges = [
            float((points[(index + 1) % 3] - points[index]).length)
            for index in range(3)
        ]
        signed_double_area = float(provider.orient2d(points[0], points[1], points[2]))
        rows.append(
            {
                "minimum_angle_degrees": min(angles),
                "minimum_edge_length_m": min(edges),
                "signed_double_area_m2": signed_double_area,
                "face": face,
                "points": points,
            }
        )
    worst = min(rows, key=lambda value: value["minimum_angle_degrees"])
    zero_rows = [row for row in rows if row["minimum_angle_degrees"] == 0.0]
    zero_records = [_face_record(row["face"], coordinates) for row in zero_rows]
    coordinate_keys = [
        (round(float(value[0]), 14), round(float(value[1]), 14))
        for value in coordinates
    ]
    seed_keys = [
        (round(float(value[0]), 14), round(float(value[1]), 14))
        for value in seeds
    ]
    coordinate_duplicates = [
        {"rounded_coordinate": list(key), "count": count}
        for key, count in sorted(Counter(coordinate_keys).items())
        if count > 1
    ]
    seed_duplicates = [
        {"rounded_coordinate": list(key), "count": count}
        for key, count in sorted(Counter(seed_keys).items())
        if count > 1
    ]
    worst_points = list(worst["points"])
    incenter = provider.triangle_incenter(worst_points)
    centroid = (worst_points[0] + worst_points[1] + worst_points[2]) / 3.0
    new_seeds = []
    previous_seed_count = int(previous["seed_count"]) if previous else 0
    for value in list(seeds)[previous_seed_count:]:
        classification = "INITIAL_BASE_FACE_CENTROID"
        distances = None
        if previous and int(previous["seed_count"]) > 0:
            prior_candidates = previous["worst_candidates_numeric"]
            incenter_distance = math.dist(
                (float(value[0]), float(value[1])), tuple(prior_candidates["incenter"])
            )
            centroid_distance = math.dist(
                (float(value[0]), float(value[1])), tuple(prior_candidates["centroid"])
            )
            classification = (
                "WORST_FACE_INCENTER"
                if incenter_distance <= centroid_distance
                else "WORST_FACE_CENTROID"
            )
            distances = {
                "to_prior_worst_incenter_m": incenter_distance,
                "to_prior_worst_centroid_m": centroid_distance,
            }
        new_seeds.append(
            {
                "coordinate": _vector_record(value),
                "classification": classification,
                "candidate_distances": distances,
            }
        )
    return {
        "call_index": int(call_index),
        "epsilon_m": _float_record(float(epsilon)),
        "boundary_count": len(boundary),
        "seed_count": len(seeds),
        "new_seed_count": len(new_seeds),
        "new_seeds": new_seeds,
        "seed_unique_rounded_14_count": len(set(seed_keys)),
        "seed_duplicate_groups": seed_duplicates,
        "minimum_seed_pair_distance_m": _minimum_pair_distance(list(seeds)),
        "output_coordinate_count": len(coordinates),
        "output_face_count": len(faces),
        "output_unique_rounded_14_coordinate_count": len(set(coordinate_keys)),
        "output_duplicate_coordinate_groups": coordinate_duplicates,
        "minimum_triangle_angle_degrees": float(worst["minimum_angle_degrees"]),
        "minimum_edge_length_m": min(row["minimum_edge_length_m"] for row in rows),
        "minimum_absolute_double_area_m2": min(
            abs(row["signed_double_area_m2"]) for row in rows
        ),
        "zero_angle_face_count": len(zero_rows),
        "zero_angle_faces_sha256": canonical_sha256(zero_records),
        "zero_angle_faces_first_16": zero_records[:16],
        "worst_face": _face_record(worst["face"], coordinates),
        "worst_candidates": {
            "incenter": _vector_record(incenter),
            "centroid": _vector_record(centroid),
        },
        "worst_candidates_numeric": {
            "incenter": [float(incenter[0]), float(incenter[1])],
            "centroid": [float(centroid[0]), float(centroid[1])],
        },
        "maximum_boundary_delta_2d_m": float(result["maximum_boundary_delta_2d_m"]),
    }


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 36 requires the exact configured manifest path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 36 config SHA-256 drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_36"
        or config.get("status") != "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 36 identity drifted")
    scope = config["scope"]
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "later_reviewed_blender_launch_required",
        "exact_attempt35_pipeline_required",
        "observational_run_cdt_wrapper_allowed_only_after_exact_binding",
        "append_only_json_evidence_allowed_during_later_run",
    )
    forbidden = (
        "source_file_mutation_allowed",
        "prior_evidence_mutation_allowed",
        "repair_domain_change_allowed",
        "candidate_change_allowed",
        "reconstruction_algorithm_change_allowed",
        "quality_gate_reduction_allowed",
        "seed_cap_change_allowed",
        "refinement_decision_change_allowed",
        "render_allowed",
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "assignment_allowed",
        "publication_allowed",
        "automatic_retry_allowed",
    )
    if not all(scope.get(name) is True for name in required_true):
        raise RuntimeError("Attempt 36 required scope drifted")
    if any(scope.get(name) is not False for name in forbidden):
        raise RuntimeError("Attempt 36 forbidden scope drifted")
    output = config["runtime_overlay"]["output"]
    if output != {
        "root": "RecoverySprint/continuation_20260803/kira_r24_internal_midpoint_fair_surface/attempt_36",
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "TRIANGULATION_RECONSTRUCTION_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "quality_trace": "CDT_QUALITY_TRACE.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }:
        raise RuntimeError("Attempt 36 output overlay drifted")
    instrument = config["quality_instrumentation"]
    if (
        instrument["wrapped_callable"] != "attempt15.run_cdt"
        or instrument["original_call_count_per_wrapper_call"] != 1
        or instrument["return_exact_original_result"] is not True
        or instrument["mutate_inputs_or_result"] is not False
        or instrument["change_quality_decisions"] is not False
        or instrument["measurement_error_must_not_change_pipeline_outcome"] is not True
        or instrument["maximum_seed_count_unchanged"] != 160
        or instrument["minimum_angle_gate_degrees_unchanged"] != 12.0
    ):
        raise RuntimeError("Attempt 36 instrumentation contract drifted")
    if project_path(str(output["root"]), must_exist=False).exists():
        raise RuntimeError("Attempt 36 output already exists")
    if config["launch_contract"]["executed_during_static_preparation"] is not False:
        raise RuntimeError("Attempt 36 launch truth drifted")


def verify_overlay(config: Mapping[str, Any]) -> dict[str, object]:
    records = {
        str(label): require_record(str(label), record)
        for label, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    failure = json.loads(
        project_path(str(records["attempt35_failure"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    expected_error = (
        "quality_refined_cdt_failed_minimum_angle:"
        "achieved=0.0:required=12.0:seeds=160"
    )
    if (
        failure["error_type"] != "RuntimeError"
        or failure["error"] != expected_error
        or "line 330, in quality_refined_cdt" not in failure["traceback"]
        or failure["render_reached"]
        or failure["blend_saved"]
        or failure["runtime_changed"]
    ):
        raise RuntimeError("Attempt 36 bound Attempt 35 failure truth drifted")
    external = json.loads(
        project_path(str(records["attempt35_external_integrity"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    if (
        external["blender_exit_code"] != 1
        or external["native_invocation_error"] is not None
        or external["pre_post_exact"] is not True
        or external["before"] != external["after"]
        or len(external["before"]) != 204
    ):
        raise RuntimeError("Attempt 36 bound Attempt 35 external integrity drifted")
    source_path = project_path(str(records["attempt35_worker"]["path"]))
    derived = patch_attempt35_source(source_path.read_text(encoding="utf-8"), config)
    compile(derived, str(source_path), "exec")
    return {
        "records": records,
        "failure": failure,
        "derived_attempt35_sha256": sha256_text(derived),
    }


def _write_trace_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)


def run_blender(config_path: Path, config: Mapping[str, Any]) -> None:
    verified = verify_overlay(config)
    attempt35_path = project_path(str(config["bindings"]["attempt35_worker"]["path"]))
    derived_source = patch_attempt35_source(
        attempt35_path.read_text(encoding="utf-8"), config
    )
    module_name = "attempt36_bound_attempt35"
    missing = object()
    prior_module = sys.modules.get(module_name, missing)
    attempt35 = _exec_source_module(module_name, attempt35_path, derived_source)
    attempt35_config_path = project_path(
        str(config["bindings"]["attempt35_config"]["path"])
    )
    attempt35_config = json.loads(attempt35_config_path.read_text(encoding="utf-8"))
    runtime_config = deepcopy(attempt35_config)
    runtime_config["runtime_overlay"]["output"] = {
        key: value
        for key, value in config["runtime_overlay"]["output"].items()
        if key != "quality_trace"
    }
    instrumentation_metadata = {
        "worker": file_record(Path(__file__).resolve()),
        "config": file_record(config_path),
        "base_attempt35_worker": verified["records"]["attempt35_worker"],
        "derived_attempt35_source_sha256": config["evidence_writer_patch"]["derived_attempt35_source_sha256"],
        "wrapped_callable": "attempt15.run_cdt",
        "original_call_count_per_wrapper_call": 1,
        "returns_exact_original_result": True,
        "mutates_inputs_or_result": False,
        "changes_refinement_decisions": False,
        "render_permitted": False,
        "blend_save_permitted": False,
    }
    attempt35.ATTEMPT36_INSTRUMENTATION_METADATA = instrumentation_metadata
    original_exec = attempt35._exec_source_module
    state: dict[str, Any] = {
        "schema": "kira.avatar.r24.blackproject_attempt36.cdt_quality_trace.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "TRACE_STARTED_EXACT_ATTEMPT35_DECISIONS_UNCHANGED",
        "attempt_id": "attempt_36",
        "instrumentation": instrumentation_metadata,
        "calls": [],
    }

    def traced_exec(name: str, path: Path, source: str) -> Any:
        provider = original_exec(name, path, source)
        exact_attempt15 = project_path(
            str(config["bindings"]["attempt15_worker"]["path"])
        )
        if path.resolve() != exact_attempt15.resolve():
            return provider
        original_run_cdt = provider.run_cdt

        def traced_run_cdt(boundary: Sequence[Any], seeds: Sequence[Any], epsilon: float) -> Any:
            result = original_run_cdt(boundary, seeds, epsilon)
            previous = state["calls"][-1] if state["calls"] else None
            try:
                record = measure_cdt_call(
                    provider,
                    boundary,
                    seeds,
                    epsilon,
                    result,
                    previous,
                    len(state["calls"]),
                )
            except Exception as measurement_error:
                record = {
                    "call_index": len(state["calls"]),
                    "boundary_count": len(boundary),
                    "seed_count": len(seeds),
                    "measurement_error_type": type(measurement_error).__name__,
                    "measurement_error": str(measurement_error),
                    "exact_original_result_returned_despite_measurement_error": True,
                }
            state["calls"].append(record)
            return result

        provider.run_cdt = traced_run_cdt
        state["provider_source"] = file_record(path)
        state["derived_provider_source_sha256"] = sha256_text(source)
        return provider

    attempt35._exec_source_module = traced_exec
    attempt35.__file__ = str(Path(__file__).resolve())
    output = project_path(str(config["runtime_overlay"]["output"]["root"]), must_exist=False)
    trace_path = output / str(config["runtime_overlay"]["output"]["quality_trace"])
    caught: BaseException | None = None
    try:
        attempt35.run_blender(config_path, runtime_config)
        state["status"] = "TRACE_CAPTURED_QUALITY_FUNCTION_RETURNED"
    except BaseException as error:
        caught = error
        state["status"] = "TRACE_CAPTURED_AFTER_UNCHANGED_ATTEMPT35_FAILURE"
        state["error_type"] = type(error).__name__
        state["error"] = str(error)
    finally:
        attempt35._exec_source_module = original_exec
        state["completed_utc"] = datetime.now(timezone.utc).isoformat()
        state["call_count"] = len(state["calls"])
        state["calls_sha256"] = canonical_sha256(state["calls"])
        state["final_call"] = state["calls"][-1] if state["calls"] else None
        _write_trace_once(trace_path, state)
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
