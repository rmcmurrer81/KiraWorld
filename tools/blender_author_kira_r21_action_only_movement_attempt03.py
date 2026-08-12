#!/usr/bin/env python3
"""Attempt 03: Attempt 02 plus only the missing proxy mapping behavior."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import traceback
from typing import Any

import bpy


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_author_kira_r21_action_only_movement_attempt02 as attempt02  # noqa: E402


OVERLAY_PATH = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_action_only_movement_correction/"
    "MOVEMENT_CONFIG_ATTEMPT_03_OVERLAY.json"
)
EXPANDED_CONFIG_PATH = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_action_only_movement_correction/"
    "MOVEMENT_CONFIG_ATTEMPT_03_EXPANDED.json"
)
FAILURE_PATH = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_action_only_movement_correction/"
    "attempt_03_failure.json"
)


class PersistentActionProxy:
    """Keep the action name usable after reopen while delegating Action access."""

    def __init__(self, action: bpy.types.Action):
        self.raw = action
        self.name = str(action.name)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.raw, name)

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]


def expanded_config() -> dict[str, Any]:
    overlay = json.loads(OVERLAY_PATH.read_text(encoding="utf-8"))
    inherited_path = PROJECT_ROOT / str(overlay["inherits"])
    if attempt02.sha256_file(inherited_path) != str(overlay["inherits_sha256"]):
        raise RuntimeError("Attempt-01 config changed; refusing Attempt-03 expansion")
    config = json.loads(inherited_path.read_text(encoding="utf-8"))
    config.update(dict(overlay["overrides"]))
    config["signature_serializer_contract"] = {
        "geometry_uv": "R21 brow mesh_geometry_digest",
        "weights": "R21 brow weight_digest",
        "rig_rest": "R21 brow armature_digest",
        "invariants_weakened": False,
    }
    config["attempt_03_harness_correction"] = dict(
        overlay["only_attempt_02_harness_correction"]
    )
    attempt02.write_json(EXPANDED_CONFIG_PATH, config)
    return config


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def normalize_attempt03_outputs(config: dict[str, Any]) -> None:
    recovery_dir = PROJECT_ROOT / str(config["recovery_output_dir"])
    owner_dir = PROJECT_ROOT / str(config["owner_review_output_dir"])
    old_blend = owner_dir / "KIRA_R21_BALD_PRIVATE_INACTIVE_ACTION_ONLY_MOVEMENT_ATTEMPT01.blend"
    new_blend = owner_dir / "KIRA_R21_BALD_PRIVATE_INACTIVE_ACTION_ONLY_MOVEMENT_ATTEMPT03.blend"
    if not old_blend.is_file() or new_blend.exists():
        raise RuntimeError("Attempt-03 output normalization found an unexpected Blend inventory")
    old_blend.replace(new_blend)

    evidence_path = recovery_dir / "BUILD_EVIDENCE.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["artifact_kind"] = "KIRA_R21_ACTION_ONLY_MOVEMENT_CORRECTION_ATTEMPT03_BUILD_EVIDENCE"
    evidence["status"] = (
        "PRIVATE_INACTIVE_ONE_CORRECTED_BOUNDED_ACTION_ONLY_MOVEMENT_ATTEMPT_PENDING_VISUAL_REVIEW"
    )
    evidence["attempt"] = "attempt_03"
    evidence["preflight"]["signature_serializer_contract"] = {
        "geometry_uv": "R21 brow mesh_geometry_digest",
        "weights": "R21 brow weight_digest",
        "rig_rest": "R21 brow armature_digest",
        "invariants_weakened": False,
    }
    evidence["preflight"]["attempt_03_harness_correction"] = {
        "only_added_behavior": "PersistentActionProxy.__getitem__",
        "focused_non_blender_unit_test": (
            "Tools/test_kira_movement_persistent_action_proxy_attempt03.py"
        ),
        "poses_source_gates_thresholds_unchanged": True,
    }
    evidence["preflight"]["body_geometry_uv_sha256_r21_brow_serializer"] = str(
        config["body_geometry_uv_sha256"]
    )
    evidence["preflight"]["body_positive_weight_assignment_sha256_r21_brow_serializer"] = str(
        config["body_positive_weight_assignment_sha256"]
    )
    evidence["preflight"]["rig_rest_sha256_r21_brow_serializer"] = str(
        config["rig_rest_sha256"]
    )
    evidence["output"]["blend"] = rel(new_blend)
    evidence["output"]["blend_sha256"] = attempt02.sha256_file(new_blend)
    evidence["output"]["blend_bytes"] = new_blend.stat().st_size
    evidence["output"]["worker"] = rel(Path(__file__))
    evidence["output"]["worker_sha256"] = attempt02.sha256_file(Path(__file__))
    evidence["output"]["expanded_config"] = rel(EXPANDED_CONFIG_PATH)
    evidence["output"]["expanded_config_sha256"] = attempt02.sha256_file(
        EXPANDED_CONFIG_PATH
    )
    attempt02.write_json(evidence_path, evidence)

    readme = owner_dir / "OWNER_REVIEW_README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        .replace("Attempt 01", "Attempt 03")
        .replace("Attempt-01", "Attempt-03"),
        encoding="utf-8",
    )
    attempt02.refresh_manifest(recovery_dir, owner_dir)


def main() -> int:
    try:
        config = expanded_config()
        attempt02.base.find_components = attempt02.corrected_find_components
        attempt02.base.ACTION_PREFIX = "KIRA_R21_MOVEMENT_ATTEMPT03_"
        attempt02.base.TEMP_COLLECTION = "KIRA_R21_MOVEMENT_ATTEMPT03_TEMP_RENDER_ONLY"
        attempt02.PersistentActionProxy = PersistentActionProxy
        attempt02.install_reopen_safe_transition_adapter()
        result = attempt02.base.run(EXPANDED_CONFIG_PATH)
        if result != 0:
            return int(result)
        normalize_attempt03_outputs(config)
        return 0
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "status": "FAILED_CORRECTED_BOUNDED_ACTION_ONLY_MOVEMENT_ATTEMPT_03",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "attempts_01_and_02_preserved": True,
        }
        if not FAILURE_PATH.exists():
            attempt02.write_json(FAILURE_PATH, failure)
        print(json.dumps(failure, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
