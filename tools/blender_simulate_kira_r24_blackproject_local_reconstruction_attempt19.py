"""Hash-bound Attempt 19 derivation of the sealed Attempt 18 Blender worker.

This wrapper never edits Attempt 18. It verifies the exact prior worker,
config, logs, and append-only evidence; replaces all three dimension-unsafe
``sum(..., Vector())`` mean/centroid expressions in memory; proves by AST that
none remain; then executes the verified Attempt 19 source. No Blend-save or
runtime-activation path is introduced.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260807"
    / "R24_BLACKPROJECT_LOCAL_RECONSTRUCTION_ATTEMPT19_CONFIG.json"
)
BASE_WORKER = (
    ROOT
    / "tools"
    / "blender_simulate_kira_r24_blackproject_local_reconstruction_attempt18.py"
)
EXPECTED_CONFIG_SHA256 = (
    "75f1d063b6e82fa96f3130230ec582a0f338a4f866a18480e2cf5a84f27595da"
)
EXPECTED_BASE_WORKER_SHA256 = (
    "422e8dc5814ec9f2067b472f85586f0ebae020c8473407cfe2decbea8e9ae77c"
)


MEAN_REPLACEMENTS = (
    (
        "initial_cdt_face_centroids_2d",
        "        sum((base[\"coordinates\"][index] for index in face), Vector()) / 3.0\n",
        "        dimension_safe_vector_mean(\n"
        "            [base[\"coordinates\"][index] for index in face]\n"
        "        )\n",
    ),
    (
        "refinement_candidate_centroid_2d",
        "            sum(points, Vector()) / 3.0,\n",
        "            dimension_safe_vector_mean(points),\n",
    ),
    (
        "surrounding_normal_mean_3d",
        "    average_normal = sum(surrounding_normals, Vector()).normalized()\n",
        "    average_normal = dimension_safe_vector_mean(surrounding_normals).normalized()\n",
    ),
)

CONFIG_LOAD_OLD = (
    '    config = json.loads(config_path.read_text(encoding="utf-8"))\n'
)
CONFIG_LOAD_NEW = "    config = load_attempt19_config(config_path)\n"


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
        raise RuntimeError(f"Attempt 19 binding escapes project: {value}")
    return path


def verify_record(name: str, record: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(record["path"]))
    actual_bytes = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_bytes != int(record["bytes"]):
        raise RuntimeError(
            f"Attempt 19 bound byte count drifted: {name}: {actual_bytes}"
        )
    if actual_sha256 != str(record["sha256"]).lower():
        raise RuntimeError(
            f"Attempt 19 bound hash drifted: {name}: {actual_sha256}"
        )
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": actual_bytes,
        "sha256": actual_sha256,
    }


def load_overlay(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve(strict=True)
    if config_path != DEFAULT_CONFIG.resolve(strict=True):
        raise RuntimeError("Attempt 19 requires the exact sealed overlay config path")
    actual_config_hash = sha256_file(config_path)
    if actual_config_hash != EXPECTED_CONFIG_SHA256:
        raise RuntimeError(
            f"Attempt 19 overlay config hash drifted: {actual_config_hash}"
        )
    overlay = json.loads(config_path.read_text(encoding="utf-8"))
    if (
        overlay.get("attempt_id") != "attempt_19"
        or overlay.get("mode") != "PRIVATE_INACTIVE_NO_SAVE_NO_ACTIVATION"
        or overlay.get("status") != "STATIC_PREPARED_NOT_RUN"
    ):
        raise RuntimeError("Attempt 19 overlay identity drifted")
    if any(
        bool(overlay["scope"][key])
        for key in (
            "blend_save_allowed",
            "export_allowed",
            "runtime_activation_allowed",
            "geometry_algorithm_changes_beyond_vector_means_allowed",
        )
    ):
        raise RuntimeError("Attempt 19 overlay scope is not no-save and bounded")
    return overlay


def verify_overlay_bindings(overlay: Mapping[str, Any]) -> dict[str, Any]:
    verified = {
        name: verify_record(name, record)
        for name, record in overlay["bindings"].items()
    }
    verified["proposal"] = verify_record("proposal", overlay["proposal"])
    if verified["attempt18_worker"]["sha256"] != EXPECTED_BASE_WORKER_SHA256:
        raise RuntimeError("Attempt 19 base-worker constant and binding disagree")
    names = list(overlay["preserved_attempts_15_18"]["binding_names"])
    rows = [verified[name] for name in names]
    if len(rows) != int(overlay["preserved_attempts_15_18"]["file_count"]):
        raise RuntimeError("Attempt 15-18 preserved file count drifted")
    if sum(int(row["bytes"]) for row in rows) != int(
        overlay["preserved_attempts_15_18"]["total_bytes"]
    ):
        raise RuntimeError("Attempt 15-18 preserved total bytes drifted")
    return verified


def load_attempt19_config(config_path: Path) -> dict[str, Any]:
    """Materialize the complete Attempt 19 config from a sealed Attempt 18 base."""
    overlay = load_overlay(config_path)
    verified = verify_overlay_bindings(overlay)
    base_path = project_path(overlay["bindings"]["attempt18_config"]["path"])
    base = json.loads(base_path.read_text(encoding="utf-8"))
    if (
        base.get("attempt_id") != overlay["base"]["expected_config_attempt_id"]
        or base.get("mode") != overlay["mode"]
    ):
        raise RuntimeError("Attempt 18 base config identity drifted")
    merged = copy.deepcopy(base)
    merged["schema"] = (
        "kira.avatar.r24.blackproject_local_reconstruction_attempt19.config.v1"
    )
    merged["attempt_id"] = "attempt_19"
    merged["output"] = copy.deepcopy(overlay["output"])
    merged["attempt19_vector_accumulator_audit"] = copy.deepcopy(
        overlay["repair_contract"]
    )
    merged["attempt19_truth"] = copy.deepcopy(overlay["truth"])
    merged["inputs"].update(
        {
            f"attempt19_bound_{name}": {
                "path": record["path"],
                "bytes": record["bytes"],
                "sha256": record["sha256"],
            }
            for name, record in verified.items()
        }
    )
    return merged


def unsafe_vector_accumulator_locations(source: str) -> list[tuple[int, int]]:
    """Return every ``sum(values, Vector())`` zero-dimensional accumulator."""
    tree = ast.parse(source)
    locations: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "sum":
            continue
        initial = node.args[1]
        if (
            isinstance(initial, ast.Call)
            and isinstance(initial.func, ast.Name)
            and initial.func.id == "Vector"
            and not initial.args
            and not initial.keywords
        ):
            locations.append((int(node.lineno), int(node.col_offset)))
    return sorted(locations)


def derive_attempt19_source(source: str) -> str:
    """Apply only the audited vector means, config loader, and attempt identity."""
    before_locations = unsafe_vector_accumulator_locations(source)
    if len(before_locations) != 3:
        raise RuntimeError(
            "Attempt 18 unsafe Vector accumulator inventory drifted: "
            f"{before_locations}"
        )
    derived = source
    for name, old, new in MEAN_REPLACEMENTS:
        count = derived.count(old)
        if count != 1:
            raise RuntimeError(
                f"Attempt 19 exact replacement occurrence drifted: {name}: {count}"
            )
        derived = derived.replace(old, new, 1)
    if derived.count(CONFIG_LOAD_OLD) != 1:
        raise RuntimeError("Attempt 18 config-load expression drifted")
    derived = derived.replace(CONFIG_LOAD_OLD, CONFIG_LOAD_NEW, 1)
    for old, new in (
        ("attempt_18", "attempt_19"),
        ("attempt18", "attempt19"),
        ("Attempt 18", "Attempt 19"),
    ):
        if old not in derived:
            raise RuntimeError(f"Attempt 18 identity token disappeared: {old}")
        derived = derived.replace(old, new)
    remaining = unsafe_vector_accumulator_locations(derived)
    if remaining or "Vector()" in derived:
        raise RuntimeError(
            f"Attempt 19 retained a zero-dimensional Vector accumulator: {remaining}"
        )
    if any(token in derived for token in ("attempt_18", "attempt18", "Attempt 18")):
        raise RuntimeError("Attempt 19 derived source retained Attempt 18 identity")
    compile(derived, str(Path(__file__).resolve()) + "::derived", "exec")
    return derived


def main() -> None:
    if sha256_file(BASE_WORKER) != EXPECTED_BASE_WORKER_SHA256:
        raise RuntimeError("Attempt 18 worker changed before Attempt 19 derivation")
    before = BASE_WORKER.read_bytes()
    derived = derive_attempt19_source(before.decode("utf-8"))
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(__file__).resolve()),
        "__builtins__": __builtins__,
        "load_attempt19_config": load_attempt19_config,
    }
    try:
        exec(
            compile(
                derived,
                str(Path(__file__).resolve()) + "::derived",
                "exec",
            ),
            namespace,
            namespace,
        )
    finally:
        if BASE_WORKER.read_bytes() != before:
            raise RuntimeError("Attempt 18 worker changed during Attempt 19 execution")


if __name__ == "__main__":
    main()
