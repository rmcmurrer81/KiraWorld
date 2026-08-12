"""Attempt 46 static-first repair of the Attempt 45 runtime probe-key contract.

This module preserves the exact Attempt 45 program and evidence, derives the
same one-candidate read-only mapper, and changes only the four inherited
Attempt 44 semantic probe-key references. Importing it is Blender-free and
creates no Attempt 46 evidence.
"""

from __future__ import annotations

import sys

# This must precede importlib and every bound-module load.
sys.dont_write_bytecode = True

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT46_CONFIG.json"
)
EXPECTED_CONFIG_SHA256 = (
    "c9b2db89e58726b82a22146c1af2eacb7a3c121156f0f1336951792131881780"
)
ATTEMPT45_WORKER = ROOT / (
    "tools/blender_diagnose_kira_r24_blackproject_"
    "compound_local_blocker_stars_attempt45.py"
)
EXPECTED_ATTEMPT45_WORKER_SHA256 = (
    "98801efef8fd8c7118b25e9475b827193869098b4156456f645004cc14212784"
)
EXPECTED_ATTEMPT45_CONFIG_SHA256 = (
    "41144f0b470c078312cc35aae6368dd75c0a1b1079b0a56b6808f81a1fd4117b"
)
EXPECTED_ATTEMPT45_DERIVED_SHA256 = (
    "481dd0105147edef6f39b2f682f2def99388355c325429b02e5d11e214c11ccf"
)
EXPECTED_CACHE_SHA256 = (
    "340ddf1fcbb97d8bd309280061f05dd6a914b79c1e36abce69134501902c162f"
)
EXPECTED_DERIVED_SHA256 = (
    "82d2332c4a39fea67a968c3d1ed31abd3e06a209e903161741db54121741c066"
)

SEMANTIC_PROBE_KEYS = (
    "attempt44_chart_maximum_boundary_index",
    "attempt44_chart_maximum_mesh_vertex_index",
    "attempt44_forced_ear_obstruction_boundary_index",
    "attempt44_forced_ear_obstruction_mesh_vertex_index",
)
FAULTY_AFTER_IDENTITY_COUNTS = {
    "attempt46_chart_maximum_boundary_index": 1,
    "attempt46_chart_maximum_mesh_vertex_index": 1,
    "attempt46_forced_ear_obstruction_boundary_index": 2,
    "attempt46_forced_ear_obstruction_mesh_vertex_index": 1,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def project_path(value: str, *, must_exist: bool = True) -> Path:
    path = (ROOT / value).resolve(strict=must_exist)
    root = ROOT.resolve()
    if root != path and root not in path.parents:
        raise RuntimeError(f"Attempt 46 path escapes project: {value}")
    return path


def file_record(path: Path) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    return {
        "path": str(exact.relative_to(ROOT)).replace("\\", "/"),
        "bytes": exact.stat().st_size,
        "sha256": sha256_file(exact),
    }


def require_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    actual = file_record(project_path(str(record["path"])))
    if actual["bytes"] != int(record["bytes"]):
        raise RuntimeError(f"Attempt 46 binding byte count drifted: {name}")
    if actual["sha256"] != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 46 binding hash drifted: {name}")
    return actual


def load_static_module(name: str, path: Path) -> Any:
    if sys.dont_write_bytecode is not True:
        raise RuntimeError("Attempt 46 bytecode containment was disabled")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Attempt 46 cannot load bound worker: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    exact = path.resolve(strict=True)
    if exact != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 46 requires the exact sealed config path")
    actual = sha256_file(exact)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 46 config hash drifted: {actual}")
    config = json.loads(exact.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("attempt_id") != "attempt_46"
        or config.get("status")
        != "STATIC_READ_ONLY_PROBE_KEY_CONTRACT_REPAIR_PREPARED_NOT_RUN"
        or config.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 46 identity drifted")
    scope = config["scope"]
    required_true = (
        "append_only",
        "private",
        "inactive",
        "unassigned",
        "unpublished",
        "diagnostic_only",
        "later_independently_reviewed_blender_launch_required",
        "read_existing_source_mesh_allowed_during_later_reviewed_run",
        "in_memory_scene_open_allowed_during_later_reviewed_run",
        "ordered_topology_identity_required_before_mapping",
        "bounded_numeric_sanity_required_before_mapping",
        "exact_attempt43_base_domain_reverification_required",
        "exact_attempt44_candidate_reverification_required",
        "exact_one_compound_blocker_vertex_star_mapping_allowed",
        "exact_runtime_probe_key_contract_required_before_blender",
        "per_boundary_chart_deviation_attribution_required",
        "forced_ear_necessary_feasibility_test_required",
        "append_only_json_evidence_allowed_during_later_run",
    )
    forbidden = (
        "source_file_mutation_allowed",
        "prior_evidence_mutation_allowed",
        "body_geometry_mutation_allowed",
        "patch_geometry_mutation_allowed",
        "blender_datablock_transform_assignment_allowed",
        "triangulation_allowed",
        "reconstruction_allowed",
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
        "uniform_face_ring_allowed",
        "separate_blocker_star_candidates_allowed",
        "automatic_alternate_candidate_allowed",
        "automatic_retry_allowed",
    )
    if not all(bool(scope[name]) for name in required_true):
        raise RuntimeError("Attempt 46 lost a required read-only scope")
    if any(bool(scope[name]) for name in forbidden):
        raise RuntimeError("Attempt 46 permits a forbidden operation")
    expected_output = {
        "root": (
            "RecoverySprint/continuation_20260803/"
            "kira_r24_internal_midpoint_fair_surface/attempt_46"
        ),
        "started": "ATTEMPT_STARTED.json",
        "diagnostic": "COMPOUND_LOCAL_BLOCKER_STARS_DIAGNOSTIC.json",
        "failure": "FAILURE.json",
        "blend_save_permitted": False,
        "render_permitted": False,
    }
    if config["output"] != expected_output:
        raise RuntimeError("Attempt 46 output contract drifted")
    if project_path(expected_output["root"], must_exist=False).exists():
        raise RuntimeError("Attempt 46 output already exists")
    candidate = config["one_candidate_contract"]
    if (
        candidate["candidate"]
        != "complete_attempt44_domain_plus_complete_mesh_vertex_stars_218_508"
        or candidate["base_candidate"]
        != "complete_attempt43_domain_plus_complete_mesh_vertex_star_241"
        or candidate["required_complete_source_mesh_vertex_stars"] != [241, 218, 508]
        or candidate["new_compound_blocker_source_mesh_vertex_stars"] != [218, 508]
        or not bool(candidate["one_indivisible_compound_candidate"])
        or bool(candidate["separate_star_candidates_allowed"])
        or bool(candidate["uniform_face_ring_candidates_allowed"])
        or bool(candidate["alternate_target_sets_allowed"])
        or bool(candidate["coordinate_suppression_allowed"])
    ):
        raise RuntimeError("Attempt 46 one-candidate contract drifted")
    repair = config["probe_key_repair"]
    if (
        repair["faulty_derived_source_sha256"] != EXPECTED_ATTEMPT45_DERIVED_SHA256
        or repair["failure_type"] != "KeyError"
        or repair["failure_message"] != "'attempt45_chart_maximum_boundary_index'"
        or tuple(repair["exact_semantic_keys"]) != SEMANTIC_PROBE_KEYS
        or repair["faulty_literal_occurrence_counts"]
        != {
            key.replace("attempt46", "attempt45"): count
            for key, count in FAULTY_AFTER_IDENTITY_COUNTS.items()
        }
        or not bool(repair["all_literal_probe_subscript_keys_must_exist_in_runtime_manifest"])
        or not bool(repair["ast_contract_required_before_blender"])
    ):
        raise RuntimeError("Attempt 46 probe-key repair contract drifted")
    evidence = config["attempt45_runtime_evidence"]
    if (
        evidence["status"] != "NO_SAVE_ATTEMPT45_DIAGNOSTIC_STOP_PRESERVED"
        or evidence["diagnostic_exists"] is not False
        or evidence["error_type"] != "KeyError"
        or evidence["error"] != "'attempt45_chart_maximum_boundary_index'"
        or int(evidence["protected_entry_count"]) != 331
        or evidence["pre_post_exact"] is not True
        or evidence["relevant_bytecode_cache_inventory_exact"] is not True
        or int(evidence["blender_exit_code"]) != 1
        or evidence["native_invocation_error"] is not None
        or any(
            bool(evidence[name])
            for name in (
                "mesh_mutated",
                "body_mutated",
                "render_reached",
                "blend_saved",
                "runtime_changed",
            )
        )
    ):
        raise RuntimeError("Attempt 46 bound Attempt 45 failure truth drifted")
    launch = config["launch_contract"]
    if (
        launch["arguments_before_python"]
        != ["--background", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1"]
        or not bool(launch["wrapper_unions_attempt45_331_entry_inventory"])
        or not bool(launch["wrapper_verifies_all_attempt45_records_before_blender"])
        or not bool(launch["wrapper_protects_attempt40_generated_cpython313_cache"])
        or not bool(launch["wrapper_refuses_any_new_relevant_worker_cache"])
        or not bool(launch["worker_sets_sys_dont_write_bytecode_before_bound_worker_load"])
        or not bool(launch["exactly_one_blender_invocation_required"])
        or not bool(launch["refuse_any_overwrite"])
        or bool(launch["executed_during_static_preparation"])
    ):
        raise RuntimeError("Attempt 46 launch contract drifted")
    forbidden_truth = (
        "attempt46_blender_execution_performed",
        "attempt46_source_domain_mapping_performed",
        "attempt46_candidate_feasibility_proven",
        "attempt46_triangulation_performed",
        "attempt46_reconstruction_performed",
        "attempt46_body_mutation_performed",
        "attempt46_render_reached",
        "attempt46_blend_saved",
        "runtime_changed",
        "executable_body_repair_justified",
        "body_repair_proven",
        "owner_approval_claimed",
    )
    if any(bool(config["truth"][name]) for name in forbidden_truth):
        raise RuntimeError("Attempt 46 static truth overclaims execution or repair")


def verify_attempt45_runtime(
    config: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    def read(name: str) -> Any:
        return json.loads(
            project_path(str(records[name]["path"])).read_text(encoding="utf-8")
        )

    started = read("attempt45_started")
    failure = read("attempt45_failure")
    integrity = read("attempt45_external_integrity")
    if (
        started.get("status") != "READ_ONLY_SOURCE_BOUNDARY_DIAGNOSTIC_STARTED"
        or started.get("worker_sha256") != EXPECTED_ATTEMPT45_WORKER_SHA256
        or started.get("config_sha256") != EXPECTED_ATTEMPT45_CONFIG_SHA256
    ):
        raise RuntimeError("Attempt 46 bound Attempt 45 start identity drifted")
    if (
        failure.get("status") != "NO_SAVE_ATTEMPT45_DIAGNOSTIC_STOP_PRESERVED"
        or failure.get("error_type") != "KeyError"
        or failure.get("error") != "'attempt45_chart_maximum_boundary_index'"
        or failure.get("diagnostic_exists") is not False
        or any(
            bool(failure.get(name))
            for name in (
                "mesh_mutated",
                "body_mutated",
                "render_reached",
                "blend_saved",
                "runtime_changed",
            )
        )
    ):
        raise RuntimeError("Attempt 46 bound Attempt 45 failure record drifted")
    cache_path = project_path(str(config["preserved_existing_bytecode_cache"]["path"]))
    expected_cache = {
        "path": str(cache_path.resolve()),
        "bytes": 36680,
        "sha256": EXPECTED_CACHE_SHA256,
    }
    if (
        integrity.get("blender_exit_code") != 1
        or integrity.get("native_invocation_error") is not None
        or integrity.get("pre_post_exact") is not True
        or integrity.get("before") != integrity.get("after")
        or len(integrity.get("before", [])) != 331
        or integrity.get("relevant_bytecode_cache_inventory_exact") is not True
        or integrity.get("expected_relevant_bytecode_cache_paths")
        != [str(cache_path.resolve())]
        or integrity.get("relevant_bytecode_caches_before") != [expected_cache]
        or integrity.get("relevant_bytecode_caches_after") != [expected_cache]
    ):
        raise RuntimeError("Attempt 46 bound Attempt 45 integrity drifted")
    protected = []
    seen: set[Path] = set()
    for row in integrity["before"]:
        path = Path(str(row["path"])).resolve(strict=True)
        if ROOT.resolve() != path and ROOT.resolve() not in path.parents:
            raise RuntimeError(f"Attempt 46 protected path escapes project: {path}")
        if path in seen:
            raise RuntimeError(f"Attempt 46 duplicate protected path: {path}")
        seen.add(path)
        actual = file_record(path)
        if (
            actual["bytes"] != int(row["bytes"])
            or actual["sha256"] != str(row["sha256"]).lower()
        ):
            raise RuntimeError(f"Attempt 46 protected file drifted: {path}")
        protected.append(actual)
    if len(protected) != 331:
        raise RuntimeError("Attempt 46 did not verify all 331 protected records")
    if cache_path.stat().st_size != 36680 or sha256_file(cache_path) != EXPECTED_CACHE_SHA256:
        raise RuntimeError("Attempt 46 preserved Attempt 40 cache drifted")
    return {
        "started": started,
        "failure": failure,
        "integrity": integrity,
        "protected_records": protected,
        "cache_record": file_record(cache_path),
    }


def exact_count_replace(
    source: str, old: str, new: str, expected_count: int, label: str
) -> str:
    count = source.count(old)
    if count != expected_count:
        raise RuntimeError(
            f"Attempt 46 source replacement drifted: {label}: {count}"
        )
    return source.replace(old, new)


def probe_literal_key_counts(source: str) -> dict[str, int]:
    tree = ast.parse(source)
    counts: dict[str, int] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.value, ast.Name) or node.value.id != "probe":
            continue
        key = node.slice
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            raise RuntimeError("Attempt 46 derived AST has a dynamic probe subscript")
        counts[key.value] = counts.get(key.value, 0) + 1
    return dict(sorted(counts.items()))


def validate_probe_key_contract(source: str, probe: Mapping[str, Any]) -> dict[str, int]:
    counts = probe_literal_key_counts(source)
    missing = sorted(set(counts).difference(str(key) for key in probe))
    if missing:
        raise RuntimeError(f"Attempt 46 derived probe keys are absent: {missing}")
    if not set(SEMANTIC_PROBE_KEYS).issubset(counts):
        raise RuntimeError("Attempt 46 derived semantic probe references are incomplete")
    faulty = sorted(key for key in counts if key.startswith(("attempt45_", "attempt46_")))
    if faulty:
        raise RuntimeError(f"Attempt 46 retained renamed semantic probe keys: {faulty}")
    return counts


def derive_attempt46_source(source45: str) -> str:
    if sha256_text(source45) != EXPECTED_ATTEMPT45_DERIVED_SHA256:
        raise RuntimeError("Attempt 46 exact Attempt 45 derived source drifted")
    source = exact_count_replace(
        source45,
        EXPECTED_ATTEMPT45_CONFIG_SHA256,
        EXPECTED_CONFIG_SHA256,
        1,
        "bind Attempt 46 config hash",
    )
    source = exact_count_replace(
        source,
        "STATIC_READ_ONLY_COMPOUND_LOCAL_BLOCKER_STARS_PROOF_PREPARED_NOT_RUN",
        "STATIC_READ_ONLY_PROBE_KEY_CONTRACT_REPAIR_PREPARED_NOT_RUN",
        1,
        "bind Attempt 46 static status",
    )
    for old, new in (
        ("attempt_45", "attempt_46"),
        ("attempt45", "attempt46"),
        ("Attempt 45", "Attempt 46"),
        ("ATTEMPT45", "ATTEMPT46"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 46 source identity token disappeared: {old}")
        source = source.replace(old, new)
    for faulty, count in FAULTY_AFTER_IDENTITY_COUNTS.items():
        repaired = faulty.replace("attempt46", "attempt44")
        source = exact_count_replace(
            source,
            f'probe["{faulty}"]',
            f'probe["{repaired}"]',
            count,
            f"restore inherited semantic key {repaired}",
        )
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "attempt46_source_identity_evidence",
        "attempt46_forced_ear_feasibility",
        "run_blender_diagnostic",
        "_domain_diagnostic",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 46 derived read-only helpers are absent")
    for token in (
        '"compound_source_star_rows"',
        '"one_indivisible_compound_candidate"',
        '"attempt44_runtime_result"',
        '"attempt44_complete_candidate_reverified"',
        '"attempt44_complete_candidate_used_only_as_read_only_base"',
        '"boundary_deviation_attribution"',
    ):
        if token not in source:
            raise RuntimeError(f"Attempt 46 derived evidence is absent: {token}")
    for token in (
        "bpy.ops.wm.save",
        "bpy.ops.render",
        "bpy.ops.export",
        "bpy.ops.object.join",
        "bmesh.ops.delete",
        "to_mesh(",
    ):
        if token in source:
            raise RuntimeError(f"Attempt 46 derived source is forbidden: {token}")
    return source


def build_runtime_config(
    config: Mapping[str, Any],
    runtime45: Mapping[str, Any],
) -> dict[str, Any]:
    runtime = json.loads(json.dumps(runtime45))
    runtime["attempt_id"] = config["attempt_id"]
    runtime["status"] = config["status"]
    runtime["mode"] = config["mode"]
    runtime["scope"] = json.loads(json.dumps(config["scope"]))
    runtime["output"] = json.loads(json.dumps(config["output"]))
    runtime["proposal"] = json.loads(json.dumps(config["proposal"]))
    runtime["truth"] = json.loads(json.dumps(config["truth"]))
    runtime["bindings"].update(json.loads(json.dumps(config["bindings"])))
    runtime["probe_key_repair"] = json.loads(json.dumps(config["probe_key_repair"]))
    return runtime


def verify_package(config: Mapping[str, Any]) -> dict[str, Any]:
    if sys.dont_write_bytecode is not True:
        raise RuntimeError("Attempt 46 bytecode containment is not active")
    records = {
        str(name): require_record(str(name), record)
        for name, record in config["bindings"].items()
    }
    records["proposal"] = require_record("proposal", config["proposal"])
    if records["attempt45_worker"]["sha256"] != EXPECTED_ATTEMPT45_WORKER_SHA256:
        raise RuntimeError("Attempt 46 bound Attempt 45 worker disagrees")
    if records["attempt45_config"]["sha256"] != EXPECTED_ATTEMPT45_CONFIG_SHA256:
        raise RuntimeError("Attempt 46 bound Attempt 45 config disagrees")
    evidence45 = verify_attempt45_runtime(config, records)
    attempt45 = load_static_module("attempt46_bound_attempt45", ATTEMPT45_WORKER)
    config45 = json.loads(
        project_path(str(config["bindings"]["attempt45_config"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    records45 = {
        str(name): attempt45.require_record(str(name), record)
        for name, record in config45["bindings"].items()
    }
    records45["proposal"] = attempt45.require_record("proposal", config45["proposal"])
    evidence44 = attempt45.verify_attempt44_runtime(config45, records45)
    attempt44 = attempt45.load_static_module(
        "attempt46_bound_attempt44", attempt45.ATTEMPT44_WORKER
    )
    config44 = json.loads(
        project_path(str(config45["bindings"]["attempt44_config"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    context = attempt45.derive_attempt44_context(attempt44, config44)
    source45 = attempt45.derive_attempt45_source(context["source44"])
    if sha256_text(source45) != EXPECTED_ATTEMPT45_DERIVED_SHA256:
        raise RuntimeError("Attempt 46 reproduced a different Attempt 45 source")
    runtime45 = attempt45.build_runtime_config(
        config45, context["runtime44"], evidence44["diagnostic"]
    )
    runtime = build_runtime_config(config, runtime45)
    source = derive_attempt46_source(source45)
    probe_counts = validate_probe_key_contract(source, runtime["one_candidate_probe"])
    namespace = {
        "__name__": "attempt46_static_runtime_contract",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
    }
    exec(
        compile(source, str(Path(__file__).resolve()) + "::derived-contract", "exec"),
        namespace,
        namespace,
    )
    namespace["validate_config"](runtime)
    derived_hash = sha256_text(source)
    if (
        EXPECTED_DERIVED_SHA256 != "TO_BE_BOUND_AFTER_STATIC_DERIVATION"
        and derived_hash != EXPECTED_DERIVED_SHA256
    ):
        raise RuntimeError(f"Attempt 46 derived source hash drifted: {derived_hash}")
    return {
        "records": records,
        "attempt45_evidence": evidence45,
        "attempt44_evidence": evidence44,
        "attempt45": attempt45,
        "attempt44": attempt44,
        "attempt44_context": context,
        "runtime_config": runtime,
        "source45": source45,
        "derived_source": source,
        "derived_source_sha256": derived_hash,
        "probe_literal_key_counts": probe_counts,
    }


def run_blender(config: Mapping[str, Any], verified: Mapping[str, Any]) -> None:
    if sys.dont_write_bytecode is not True:
        raise RuntimeError("Attempt 46 Blender bytecode containment is not active")
    # Recheck the exact schema boundary immediately before executable source.
    validate_probe_key_contract(
        str(verified["derived_source"]), verified["runtime_config"]["one_candidate_probe"]
    )
    config45 = json.loads(
        project_path(str(config["bindings"]["attempt45_config"]["path"])).read_text(
            encoding="utf-8"
        )
    )
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "ATTEMPT46_RUNTIME_CONFIG": verified["runtime_config"],
        "ATTEMPT46_RUNTIME_RESULT": json.loads(
            json.dumps(config45["attempt44_runtime_result"])
        ),
        "ATTEMPT46_RUNTIME_BASE_DOMAIN": json.loads(
            json.dumps(config45["attempt43_base_domain"])
        ),
        "ATTEMPT46_RUNTIME_PROBE": json.loads(
            json.dumps(config45["one_candidate_probe"])
        ),
        "ATTEMPT46_BOUND_COORDINATE_ONLY": json.loads(
            json.dumps(
                verified["attempt44_evidence"]["diagnostic"]["coordinate_only_analysis"]
            )
        ),
    }
    exec(
        compile(
            str(verified["derived_source"]),
            str(Path(__file__).resolve()) + "::derived",
            "exec",
        ),
        namespace,
        namespace,
    )


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    values = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args(values)


def main() -> None:
    args = parse_args()
    config = load_config(Path(args.config).resolve(strict=True))
    verified = verify_package(config)
    run_blender(config, verified)


if __name__ == "__main__":
    main()
