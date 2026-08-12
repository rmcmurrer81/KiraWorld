"""Static-first Attempt 38 launch-target ownership repair.

Attempt 38 carries the exact Attempt 37 non-degrading CDT candidate patch and
all geometry/quality gates unchanged.  Its sole executable correction is that
the launcher owns external stdout, stderr, and integrity files while this
worker owns and requires absence only for its append-only runtime output root.
Static import is Blender-free and never launches the runtime attempt.
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
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT38_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = "88f70401e42b1cbdb607276ed7c1abe91dbf0bdc2f9634e7bccf6e867bd98556"

ATTEMPT38_WRITER_NEW = '''        def attempt38_writer(target: Path, value: Mapping[str, Any]) -> None:
            result = deepcopy(dict(value))
            if isinstance(result.get("schema"), str):
                result["schema"] = result["schema"].replace("attempt33", "attempt38")
                result["schema"] = result["schema"].replace("attempt34", "attempt38")
                result["schema"] = result["schema"].replace("attempt35", "attempt38")
            if result.get("attempt_id") in {"attempt_33", "attempt_34", "attempt_35"}:
                result["attempt_id"] = "attempt_38"
            if isinstance(result.get("status"), str):
                result["status"] = result["status"].replace("ATTEMPT33", "ATTEMPT38")
                result["status"] = result["status"].replace("ATTEMPT34", "ATTEMPT38")
                result["status"] = result["status"].replace("ATTEMPT35", "ATTEMPT38")
            result["attempt35_dimension_patch"] = deepcopy(dimension_metadata)
            result["attempt37_nondegrading_cdt_repair"] = deepcopy(
                ATTEMPT37_REPAIR_METADATA
            )
            result["attempt38_launch_target_ownership_repair"] = deepcopy(
                ATTEMPT38_LAUNCH_METADATA
            )
            raw_writer(target, result)

        module._load_module = attempt35_provider_loader
        module._exclusive_write_once = attempt38_writer
'''


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return sha256_bytes(payload)


def project_path(relative: str, *, must_exist: bool = True) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as error:
        raise RuntimeError(f"Attempt 38 path escapes project: {relative}") from error
    if must_exist and not path.is_file():
        raise RuntimeError(f"Attempt 38 bound file is absent: {relative}")
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
        raise RuntimeError(f"Attempt 38 bound byte count drifted: {label}")
    if actual["sha256"] != str(record["sha256"]):
        raise RuntimeError(f"Attempt 38 bound SHA-256 drifted: {label}")
    return actual


def _load_static_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 38 cannot load bound module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _exec_source_module(name: str, path: Path, source: str) -> Any:
    code = compile(source, str(path), "exec")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    sys.modules[name] = module
    exec(code, module.__dict__)
    return module


def load_attempt37(config: Mapping[str, Any]) -> Any:
    record = config["bindings"]["attempt37_worker"]
    path = project_path(str(record["path"]))
    require_record("attempt37_worker", record)
    return _load_static_module("attempt38_exact_bound_attempt37", path)


def _exact_replace(
    source: str,
    old: str,
    new: str,
    label: str,
    record: Mapping[str, Any],
) -> str:
    if sha256_text(old) != record["old_block_sha256"]:
        raise RuntimeError(f"Attempt 38 old block hash drifted: {label}")
    if sha256_text(new) != record["new_block_sha256"]:
        raise RuntimeError(f"Attempt 38 new block hash drifted: {label}")
    if int(record["exact_replacement_count"]) != 1 or source.count(old) != 1:
        raise RuntimeError(f"Attempt 38 exact old block is not unique: {label}")
    result = source.replace(old, new, 1)
    if old in result or result.count(new) != 1:
        raise RuntimeError(f"Attempt 38 source transform is not exact: {label}")
    return result


def patch_attempt35_source(
    source: str, config: Mapping[str, Any], attempt37: Any
) -> str:
    record = config["evidence_writer_patch"]
    result = _exact_replace(
        source,
        attempt37.ATTEMPT35_WRITER_OLD,
        ATTEMPT38_WRITER_NEW,
        "attempt35_append_only_evidence_writer",
        record,
    )
    if sha256_text(result) != record["derived_attempt35_source_sha256"]:
        raise RuntimeError("Attempt 38 derived Attempt 35 source hash drifted")
    return result


def patch_attempt15_candidate_source(
    source: str, config: Mapping[str, Any], attempt37: Any
) -> str:
    # Reuse the exact Attempt 37 candidate strings and exact-hash contract.
    record = config["candidate_selection_patch"]
    result = _exact_replace(
        source,
        attempt37.ATTEMPT35_CANDIDATE_OLD,
        attempt37.ATTEMPT37_CANDIDATE_NEW,
        "quality_refined_cdt_candidate_selection_and_acceptance",
        record,
    )
    if sha256_text(result) != record["derived_attempt15_source_sha256"]:
        raise RuntimeError("Attempt 38 derived Attempt 15 source hash drifted")
    return result


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 38 requires the exact configured manifest path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 38 config SHA-256 drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_38"
        or config.get("status") != "STATIC_REPAIR_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 38 identity drifted")
    scope = config["scope"]
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "later_independently_reviewed_blender_launch_required",
        "exact_attempt37_geometry_required",
        "wrapper_owns_external_runtime_targets",
        "worker_owns_runtime_output_root",
        "append_only_json_evidence_allowed_during_later_run",
    )
    forbidden = (
        "source_file_mutation_allowed",
        "prior_evidence_mutation_allowed",
        "geometry_change_allowed",
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
        raise RuntimeError("Attempt 38 required scope drifted")
    if any(scope.get(name) is not False for name in forbidden):
        raise RuntimeError("Attempt 38 forbidden scope drifted")
    output = config["runtime_overlay"]["output"]
    if output != {
        "root": "RecoverySprint/continuation_20260803/kira_r24_internal_midpoint_fair_surface/attempt_38",
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "TRIANGULATION_RECONSTRUCTION_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "candidate_trials": "CDT_NONDEGRADING_TRIALS.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }:
        raise RuntimeError("Attempt 38 output overlay drifted")
    # Worker-owned target only. Wrapper-owned logs/integrity already exist
    # during worker startup and must never be asserted absent here.
    if project_path(str(output["root"]), must_exist=False).exists():
        raise RuntimeError("Attempt 38 output already exists")
    launch = config["launch_contract"]
    if (
        launch["executed_during_static_preparation"] is not False
        or launch["wrapper_owns_stdout_stderr_and_integrity"] is not True
        or launch["worker_checks_only_runtime_output_root_absent"] is not True
        or launch["worker_writes_external_targets"] is not False
    ):
        raise RuntimeError("Attempt 38 launch ownership truth drifted")


def verify_overlay(config: Mapping[str, Any]) -> dict[str, object]:
    records = {
        str(label): require_record(str(label), record)
        for label, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    attempt37_config = json.loads(
        project_path(str(records["attempt37_config"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    for exact_section in (
        "candidate_selection_patch",
        "nondegrading_repair",
        "unchanged_geometry_and_quality_contract",
    ):
        if config[exact_section] != attempt37_config[exact_section]:
            raise RuntimeError(
                f"Attempt 38 changed exact Attempt 37 geometry: {exact_section}"
            )
    stderr_bytes = project_path(str(records["attempt37_stderr"]["path"])).read_bytes()
    stderr = stderr_bytes.decode(
        "utf-16" if stderr_bytes.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8",
        errors="replace",
    )
    if "Attempt 37 runtime target already exists: stdout" not in stderr:
        raise RuntimeError("Attempt 38 bound launch-contract failure drifted")
    integrity = json.loads(
        project_path(str(records["attempt37_external_integrity"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    if (
        integrity["blender_exit_code"] != 1
        or integrity["native_invocation_error"] is not None
        or integrity["pre_post_exact"] is not True
        or integrity["before"] != integrity["after"]
        or len(integrity["before"]) != 230
    ):
        raise RuntimeError("Attempt 38 bound Attempt 37 integrity truth drifted")
    if project_path(
        "RecoverySprint/continuation_20260803/"
        "kira_r24_internal_midpoint_fair_surface/attempt_37",
        must_exist=False,
    ).exists():
        raise RuntimeError("Attempt 38 expected absent Attempt 37 output drifted")
    attempt37 = load_attempt37(config)
    attempt35_path = project_path(str(records["attempt35_worker"]["path"]))
    derived35 = patch_attempt35_source(
        attempt35_path.read_text(encoding="utf-8"), config, attempt37
    )
    compile(derived35, str(attempt35_path), "exec")
    attempt35_module = _load_static_module(
        "attempt38_static_bound_attempt35", attempt35_path
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
    derived15 = patch_attempt15_candidate_source(
        attempt15_derived35, config, attempt37
    )
    compile(derived15, str(attempt15_path), "exec")
    return {
        "records": records,
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
    attempt37 = verified["attempt37"]
    attempt35_path = project_path(str(config["bindings"]["attempt35_worker"]["path"]))
    derived35 = patch_attempt35_source(
        attempt35_path.read_text(encoding="utf-8"), config, attempt37
    )
    module_name = "attempt38_bound_attempt35"
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
    geometry_metadata = {
        "source_attempt": "attempt_37_exact_unexecuted_candidate_patch",
        "attempt37_worker": verified["records"]["attempt37_worker"],
        "attempt37_config": verified["records"]["attempt37_config"],
        "candidate_patch_sha256": config["candidate_selection_patch"][
            "new_block_sha256"
        ],
        "derived_attempt15_source_sha256": config["candidate_selection_patch"][
            "derived_attempt15_source_sha256"
        ],
        "candidate_order": ["circumcenter", "centroid"],
        "incenter_reachable": False,
        "strict_improvement_tolerance_degrees": 1e-9,
        "minimum_angle_gate_degrees": 12.0,
        "maximum_seed_count": 160,
        "render_permitted": False,
        "blend_save_permitted": False,
    }
    launch_metadata = {
        "worker": file_record(Path(__file__).resolve()),
        "config": file_record(config_path),
        "proposal": verified["records"]["proposal"],
        "attempt37_runtime_checkpoint": verified["records"][
            "attempt37_runtime_checkpoint"
        ],
        "wrapper_owns_stdout_stderr_and_integrity": True,
        "worker_owns_runtime_output_root": True,
        "worker_writes_external_targets": False,
    }
    attempt35.ATTEMPT37_REPAIR_METADATA = geometry_metadata
    attempt35.ATTEMPT38_LAUNCH_METADATA = launch_metadata
    original_exec = attempt35._exec_source_module
    provider_holder: dict[str, Any] = {}

    def attempt38_exec(name: str, path: Path, source: str) -> Any:
        exact_attempt15 = project_path(
            str(config["bindings"]["attempt15_worker"]["path"])
        )
        if path.resolve() != exact_attempt15.resolve():
            return original_exec(name, path, source)
        patched = patch_attempt15_candidate_source(source, config, attempt37)
        provider = original_exec(name, path, patched)
        provider.ATTEMPT37_CDT_REFINEMENT_TRACE = []
        provider_holder["provider"] = provider
        return provider

    attempt35._exec_source_module = attempt38_exec
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
            "schema": "kira.avatar.r24.blackproject_attempt38.nondegrading_cdt_trials.v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": (
                "TRIAL_EVIDENCE_CAPTURED_AFTER_PIPELINE_RETURN"
                if caught is None
                else "TRIAL_EVIDENCE_CAPTURED_AFTER_PIPELINE_FAILURE"
            ),
            "attempt_id": "attempt_38",
            "exact_attempt37_geometry": geometry_metadata,
            "launch_target_ownership_repair": launch_metadata,
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
