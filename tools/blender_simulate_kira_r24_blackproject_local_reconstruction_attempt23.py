"""Hash-bound Attempt 23 diagnostic schema and boundary-mapping repair.

This derives the sealed Attempt 22 diagnostic source. It replaces only the
invalid deep `config['output']` lookup, validates the real boundary-source to
compact-output mapping contract, captures exact mismatch data, and stops before
reconstruction. Blender is not imported during static inspection.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260807"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT23_CONFIG.json"
)
ATTEMPT22_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt22.py"
)
ATTEMPT21_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt21.py"
)
ATTEMPT20_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt20.py"
)
ATTEMPT19_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt19.py"
)
ATTEMPT18_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt18.py"
)
EXPECTED_CONFIG_SHA256 = (
    "c28b329dbe5775e677a937b1d6cc1cd2f7b5fa1486b66a56e8c231cc9219e190"
)
EXPECTED_ATTEMPT22_WORKER_SHA256 = (
    "628b3312e7335564428f402c32f3fedb0e4dda577213b2ff5ca2292959783900"
)


def load_attempt22_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "attempt23_sealed_attempt22_provider", ATTEMPT22_WORKER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Attempt 23 could not load the sealed Attempt 22 provider")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        raise RuntimeError(f"Attempt 23 binding escapes project: {value}")
    return path


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    actual_bytes = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_bytes != int(record["bytes"]):
        raise RuntimeError(f"Attempt 23 bound byte count drifted: {name}")
    if actual_sha256 != str(record["sha256"]).lower():
        raise RuntimeError(f"Attempt 23 bound hash drifted: {name}: {actual_sha256}")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
    }


def load_overlay(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve(strict=True)
    if config_path != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 23 requires the exact sealed overlay config path")
    actual = sha256_file(config_path)
    if actual != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(f"Attempt 23 overlay config hash drifted: {actual}")
    overlay = json.loads(config_path.read_text(encoding="utf-8"))
    if (
        overlay.get("attempt_id") != "attempt_23"
        or overlay.get("status") != "STATIC_DIAGNOSTIC_PREPARED_NOT_RUN"
        or overlay.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
    ):
        raise RuntimeError("Attempt 23 overlay identity drifted")
    forbidden = (
        "blend_save_allowed",
        "export_allowed",
        "runtime_activation_allowed",
        "boundary_or_seam_movement_allowed",
        "quality_gate_reduction_allowed",
        "geometry_mutation_allowed",
        "render_allowed",
        "boundary_repair_allowed",
        "generic_hole_fill_allowed",
        "whole_polygon_retriangulation_allowed",
    )
    if any(bool(overlay["scope"][name]) for name in forbidden):
        raise RuntimeError("Attempt 23 scope is not diagnostic-only and no-save")
    return overlay


def verify_overlay_bindings(overlay: Mapping[str, Any]) -> dict[str, Any]:
    verified = {
        name: verify_record(name, record)
        for name, record in overlay["bindings"].items()
    }
    verified["proposal"] = verify_record("proposal", overlay["proposal"])
    if verified["attempt22_worker"]["sha256"] != EXPECTED_ATTEMPT22_WORKER_SHA256:
        raise RuntimeError("Attempt 23 provider constant and binding disagree")
    preserved = overlay["preserved_attempt22_package"]
    rows = [verified[name] for name in preserved["binding_names"]]
    if len(rows) != int(preserved["file_count"]):
        raise RuntimeError("Attempt 22 preserved package file count drifted")
    if sum(int(row["bytes"]) for row in rows) != int(preserved["total_bytes"]):
        raise RuntimeError("Attempt 22 preserved package byte total drifted")
    return verified


def load_attempt23_config(config_path: Path) -> dict[str, Any]:
    overlay = load_overlay(config_path)
    verified = verify_overlay_bindings(overlay)
    provider = load_attempt22_module()
    base_config_path = project_path(overlay["bindings"]["attempt22_config"]["path"])
    merged = provider.load_attempt22_config(base_config_path)
    if merged.get("attempt_id") != overlay["base"]["expected_config_attempt_id"]:
        raise RuntimeError("Attempt 22 materialized base identity drifted")
    merged = copy.deepcopy(merged)
    merged["schema"] = (
        "kira.avatar.r24.blackproject_local_reconstruction_attempt23.config.v1"
    )
    merged["attempt_id"] = "attempt_23"
    merged["output"] = copy.deepcopy(overlay["output"])
    path_contract = overlay["diagnostic_path_contract"]
    expected_relative = (
        f'{overlay["output"]["root"]}/'
        f'{overlay["output"]["cdt_boundary_mismatch"]}'
    )
    if path_contract["project_relative_path"] != expected_relative:
        raise RuntimeError("Attempt 23 diagnostic path contract disagrees with output")
    merged["replacement"][path_contract["replacement_key"]] = expected_relative
    if "output" in merged["replacement"]:
        raise RuntimeError("Attempt 23 replacement-domain mapping unexpectedly has output")
    merged["attempt23_diagnosis"] = copy.deepcopy(overlay["diagnosis"])
    merged["attempt23_diagnostic_path_contract"] = copy.deepcopy(path_contract)
    merged["attempt23_boundary_mapping_contract"] = copy.deepcopy(
        overlay["boundary_mapping_contract"]
    )
    merged["attempt23_capture_contract"] = copy.deepcopy(overlay["capture_contract"])
    merged["attempt23_unchanged_hard_gates"] = copy.deepcopy(
        overlay["unchanged_hard_gates"]
    )
    merged["attempt23_evidence_label_contract"] = copy.deepcopy(
        overlay["evidence_label_contract"]
    )
    merged["attempt23_truth"] = copy.deepcopy(overlay["truth"])
    merged["inputs"].update(
        {
            f"attempt23_bound_{name}": {
                "path": record["path"],
                "bytes": record["bytes"],
                "sha256": record["sha256"],
            }
            for name, record in verified.items()
        }
    )
    unchanged = overlay["unchanged_hard_gates"]
    for location in ("replacement", "hard_gates"):
        if float(merged[location]["minimum_new_triangle_angle_degrees"]) != float(
            unchanged["minimum_new_triangle_angle_degrees"]
        ):
            raise RuntimeError(f"Attempt 23 {location} minimum-angle gate drifted")
    if float(merged["replacement"]["minimum_new_triangle_world_area_m2"]) != float(
        unchanged["minimum_new_triangle_world_area_m2"]
    ):
        raise RuntimeError("Attempt 23 minimum-area gate drifted")
    return merged


SCHEMA_MAPPING_HELPERS = r'''
def normalize_boundary_source_to_output_mapping(
    boundary_source_to_output: Mapping[int, int],
    boundary_count: int,
    coordinate_count: int,
) -> dict[int, int]:
    normalized = {
        int(source): int(output)
        for source, output in boundary_source_to_output.items()
    }
    required_sources = set(range(int(boundary_count)))
    if set(normalized) != required_sources:
        raise RuntimeError(
            "boundary source-to-output mapping does not contain exact source keys"
        )
    outputs = list(normalized.values())
    if len(set(outputs)) != len(outputs):
        raise RuntimeError("boundary source-to-output mapping has duplicate outputs")
    if any(value < 0 or value >= int(coordinate_count) for value in outputs):
        raise RuntimeError("boundary source-to-output mapping escaped coordinates")
    return {source: normalized[source] for source in range(int(boundary_count))}


def resolve_attempt23_diagnostic_path(config: Mapping[str, Any]) -> Path:
    relative_value = str(config["attempt23_cdt_boundary_mismatch_project_path"])
    relative = Path(relative_value)
    if relative.is_absolute():
        raise RuntimeError("Attempt 23 diagnostic path must be project-relative")
    root = ROOT.resolve()
    resolved = (root / relative).resolve()
    if root != resolved and root not in resolved.parents:
        raise RuntimeError("Attempt 23 diagnostic path escapes project")
    return resolved
'''


def exact_replace(source: str, old: str, new: str, name: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Attempt 23 replacement drifted: {name}: {count}")
    return source.replace(old, new, 1)


def derive_attempt23_source(source22: str) -> str:
    source = source22
    source = exact_replace(
        source,
        "def capture_exact_cdt_boundary_mismatch(\n",
        SCHEMA_MAPPING_HELPERS + "\n\ndef capture_exact_cdt_boundary_mismatch(\n",
        "insert exact mapping and path validators",
    )
    source = exact_replace(
        source,
        "    seed_sanitation: Mapping[str, Any],\n"
        "    cdt_sanitation: Mapping[str, Any],\n"
        ") -> dict[str, Any]:\n"
        "    tolerances = cdt_tolerances(boundary, epsilon, config)\n",
        "    seed_sanitation: Mapping[str, Any],\n"
        "    cdt_sanitation: Mapping[str, Any],\n"
        ") -> dict[str, Any]:\n"
        "    boundary_output = normalize_boundary_source_to_output_mapping(\n"
        "        boundary_output, boundary_count, len(coordinates)\n"
        "    )\n"
        "    tolerances = cdt_tolerances(boundary, epsilon, config)\n",
        "normalize exact source-to-output mapping before capture",
    )
    source = exact_replace(
        source,
        "    mismatch_path = (\n"
        "        ROOT\n"
        "        / config[\"output\"][\"root\"]\n"
        "        / config[\"output\"][\"cdt_boundary_mismatch\"]\n"
        "    ).resolve()\n",
        "    mismatch_path = resolve_attempt23_diagnostic_path(config)\n",
        "replace invalid deep output schema lookup",
    )
    source = exact_replace(
        source,
        "    config = load_attempt22_config(config_path)\n",
        "    config = load_attempt23_config(config_path)\n",
        "Attempt 23 config loader",
    )
    for old, new in (
        ("attempt_22", "attempt_23"),
        ("attempt22", "attempt23"),
        ("Attempt 22", "Attempt 23"),
        ("ATTEMPT22", "ATTEMPT23"),
    ):
        if old not in source:
            raise RuntimeError(f"Attempt 22 identity token disappeared: {old}")
        source = source.replace(old, new)
    if any(
        token in source
        for token in ("ATTEMPT22", "attempt_22", "attempt22", "Attempt 22")
    ):
        raise RuntimeError("Attempt 23 derived source retained a stale evidence identity")
    tree = ast.parse(source)
    compile(source, str(Path(__file__).resolve()) + "::derived", "exec")
    names = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    required = {
        "normalize_boundary_source_to_output_mapping",
        "resolve_attempt23_diagnostic_path",
        "capture_exact_cdt_boundary_mismatch",
    }
    if not required.issubset(names):
        raise RuntimeError("Attempt 23 diagnostic schema helpers were not inserted")
    capture_index = source.index("boundary_mismatch = capture_exact_cdt_boundary_mismatch(")
    write_index = source.index("atomic_write_json(mismatch_path, boundary_mismatch)")
    terminal_index = source.index(
        "Attempt 23 captured exact sanitized CDT boundary state"
    )
    recovery_index = source.index(
        "faces, boundary_segmentation_recovery = restore_exact_boundary_segmentation("
    )
    if not (capture_index < write_index < terminal_index < recovery_index):
        raise RuntimeError("Attempt 23 capture is not terminal before reconstruction")
    return source


def materialize_attempt22_source(provider: Any) -> str:
    provider21 = provider.load_attempt21_module()
    source21 = provider.materialize_attempt21_source(provider21)
    return provider.derive_attempt22_source(source21)


def main() -> None:
    if sha256_file(ATTEMPT22_WORKER) != EXPECTED_ATTEMPT22_WORKER_SHA256:
        raise RuntimeError("Attempt 22 worker changed before Attempt 23 derivation")
    provider = load_attempt22_module()
    preserved_paths = (
        ATTEMPT22_WORKER,
        ATTEMPT21_WORKER,
        ATTEMPT20_WORKER,
        ATTEMPT19_WORKER,
        ATTEMPT18_WORKER,
    )
    before = {path: path.read_bytes() for path in preserved_paths}
    source22 = materialize_attempt22_source(provider)
    source23 = derive_attempt23_source(source22)
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "load_attempt23_config": load_attempt23_config,
    }
    try:
        exec(
            compile(
                source23,
                str(Path(__file__).resolve()) + "::derived",
                "exec",
            ),
            namespace,
            namespace,
        )
    finally:
        for path in preserved_paths:
            if path.read_bytes() != before[path]:
                raise RuntimeError(
                    f"{path.name} changed during Attempt 23 execution"
                )


if __name__ == "__main__":
    main()
