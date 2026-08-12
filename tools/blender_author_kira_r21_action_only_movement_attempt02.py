#!/usr/bin/env python3
"""Attempt 02 wrapper: correct only Attempt 01's false signature gate.

Attempt 01 compared R21 brow-worker evidence hashes with older R19 serializer
implementations and therefore stopped before mutation.  This wrapper preserves
the full Attempt-01 action/contact/render/postflight implementation, but binds
the configured body, weight and rest-rig hashes through the exact serializers
that produced the R21 eyebrow Attempt-02 evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
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

import blender_author_kira_r21_action_only_movement_attempt01 as base  # noqa: E402
import blender_author_kira_r21_brow_only_attempt01 as brow_serializers  # noqa: E402


OVERLAY_PATH = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_action_only_movement_correction/"
    "MOVEMENT_CONFIG_ATTEMPT_02_OVERLAY.json"
)
EXPANDED_CONFIG_PATH = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_action_only_movement_correction/"
    "MOVEMENT_CONFIG_ATTEMPT_02_EXPANDED.json"
)
FAILURE_PATH = PROJECT_ROOT / (
    "RecoverySprint/continuation_20260802/kira_r21_action_only_movement_correction/"
    "attempt_02_failure.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def expanded_config() -> dict[str, Any]:
    overlay = json.loads(OVERLAY_PATH.read_text(encoding="utf-8"))
    inherited_path = PROJECT_ROOT / str(overlay["inherits"])
    if sha256_file(inherited_path) != str(overlay["inherits_sha256"]):
        raise RuntimeError("Attempt-01 config changed; refusing Attempt-02 expansion")
    config = json.loads(inherited_path.read_text(encoding="utf-8"))
    config.update(dict(overlay["overrides"]))
    config["signature_serializer_contract"] = dict(overlay["only_gate_correction"])
    write_json(EXPANDED_CONFIG_PATH, config)
    return config


def corrected_find_components(
    config: dict[str, Any],
) -> tuple[bpy.types.Object, bpy.types.Object, list[bpy.types.Object]]:
    body = bpy.data.objects.get(str(config["body_object"]))
    rig = bpy.data.objects.get(str(config["rig_object"]))
    if body is None or body.type != "MESH":
        raise RuntimeError("exact configured R21 body object is missing")
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError("exact configured native rig is missing")
    if len(rig.data.bones) != int(config["expected_rig_joint_count"]):
        raise RuntimeError("native rig joint count drifted")
    geometry = brow_serializers.mesh_geometry_digest(body)
    if geometry != str(config["body_geometry_uv_sha256"]):
        raise RuntimeError(
            "approved body geometry/UV signature drifted under the exact R21 brow serializer: "
            f"{geometry}"
        )
    weights = brow_serializers.weight_digest(body)
    if weights != str(config["body_positive_weight_assignment_sha256"]):
        raise RuntimeError(
            "approved body weight signature drifted under the exact R21 brow serializer: "
            f"{weights}"
        )
    rig_digest = brow_serializers.armature_digest(rig)
    if rig_digest != str(config["rig_rest_sha256"]):
        raise RuntimeError(
            "approved native rest-rig signature drifted under the exact R21 brow serializer: "
            f"{rig_digest}"
        )
    nails = sorted(
        [obj for obj in bpy.data.objects if obj.type == "MESH" and bool(obj.get("nail_component"))],
        key=lambda item: item.name,
    )
    if len(nails) != 20:
        raise RuntimeError(f"expected inherited 20-nail inventory, found {len(nails)}")
    return body, rig, nails


def refresh_manifest(recovery_dir: Path, owner_dir: Path) -> None:
    manifest_path = recovery_dir / "PACKAGE_MANIFEST.json"
    files = [
        path
        for root in (recovery_dir, owner_dir)
        for path in root.rglob("*")
        if path.is_file() and path.resolve() != manifest_path.resolve()
    ]
    base.make_manifest(files, manifest_path)


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def normalize_attempt02_outputs(config: dict[str, Any]) -> None:
    recovery_dir = PROJECT_ROOT / str(config["recovery_output_dir"])
    owner_dir = PROJECT_ROOT / str(config["owner_review_output_dir"])
    old_blend = owner_dir / "KIRA_R21_BALD_PRIVATE_INACTIVE_ACTION_ONLY_MOVEMENT_ATTEMPT01.blend"
    new_blend = owner_dir / "KIRA_R21_BALD_PRIVATE_INACTIVE_ACTION_ONLY_MOVEMENT_ATTEMPT02.blend"
    if not old_blend.is_file() or new_blend.exists():
        raise RuntimeError("Attempt-02 output normalization found an unexpected Blend inventory")
    old_blend.replace(new_blend)

    evidence_path = recovery_dir / "BUILD_EVIDENCE.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["artifact_kind"] = "KIRA_R21_ACTION_ONLY_MOVEMENT_CORRECTION_ATTEMPT02_BUILD_EVIDENCE"
    evidence["status"] = (
        "PRIVATE_INACTIVE_ONE_CORRECTED_BOUNDED_ACTION_ONLY_MOVEMENT_ATTEMPT_PENDING_VISUAL_REVIEW"
    )
    evidence["attempt"] = "attempt_02"
    evidence["preflight"]["signature_serializer_contract"] = {
        "geometry_uv": "R21 brow mesh_geometry_digest",
        "weights": "R21 brow weight_digest",
        "rig_rest": "R21 brow armature_digest",
        "false_attempt01_gate_only_corrected": True,
        "invariants_weakened": False,
    }
    evidence["preflight"]["body_geometry_uv_sha256_r21_brow_serializer"] = (
        str(config["body_geometry_uv_sha256"])
    )
    evidence["preflight"]["body_positive_weight_assignment_sha256_r21_brow_serializer"] = (
        str(config["body_positive_weight_assignment_sha256"])
    )
    evidence["preflight"]["rig_rest_sha256_r21_brow_serializer"] = str(config["rig_rest_sha256"])
    evidence["output"]["blend"] = rel(new_blend)
    evidence["output"]["blend_sha256"] = sha256_file(new_blend)
    evidence["output"]["blend_bytes"] = new_blend.stat().st_size
    evidence["output"]["worker"] = rel(Path(__file__))
    evidence["output"]["worker_sha256"] = sha256_file(Path(__file__))
    evidence["output"]["expanded_config"] = rel(EXPANDED_CONFIG_PATH)
    evidence["output"]["expanded_config_sha256"] = sha256_file(EXPANDED_CONFIG_PATH)
    write_json(evidence_path, evidence)

    readme = owner_dir / "OWNER_REVIEW_README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        .replace("Attempt 01", "Attempt 02")
        .replace("Attempt-01", "Attempt-02"),
        encoding="utf-8",
    )
    refresh_manifest(recovery_dir, owner_dir)


class PersistentActionProxy:
    """Retain an action name across Blender's save/reopen pointer invalidation."""

    def __init__(self, action: bpy.types.Action):
        self.raw = action
        self.name = str(action.name)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.raw, name)


def install_reopen_safe_transition_adapter() -> None:
    original_author = base.author_transition_action
    original_audit = base.transition_audit
    original_render = base.render_pose_suite

    def author_adapter(*args: Any, **kwargs: Any) -> PersistentActionProxy:
        return PersistentActionProxy(original_author(*args, **kwargs))

    def audit_adapter(action: Any, *args: Any, **kwargs: Any) -> Any:
        raw = action.raw if isinstance(action, PersistentActionProxy) else action
        return original_audit(raw, *args, **kwargs)

    def render_adapter(*args: Any, **kwargs: Any) -> Any:
        values = list(args)
        if len(values) >= 9 and isinstance(values[8], PersistentActionProxy):
            values[8] = values[8].raw
        elif isinstance(kwargs.get("transition"), PersistentActionProxy):
            kwargs["transition"] = kwargs["transition"].raw
        return original_render(*values, **kwargs)

    base.author_transition_action = author_adapter
    base.transition_audit = audit_adapter
    base.render_pose_suite = render_adapter


def main() -> int:
    try:
        config = expanded_config()
        base.find_components = corrected_find_components
        base.ACTION_PREFIX = "KIRA_R21_MOVEMENT_ATTEMPT02_"
        base.TEMP_COLLECTION = "KIRA_R21_MOVEMENT_ATTEMPT02_TEMP_RENDER_ONLY"
        install_reopen_safe_transition_adapter()
        result = base.run(EXPANDED_CONFIG_PATH)
        if result != 0:
            return int(result)
        normalize_attempt02_outputs(config)
        return 0
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "status": "FAILED_CORRECTED_BOUNDED_ACTION_ONLY_MOVEMENT_ATTEMPT_02",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "attempt_01_preserved": True,
        }
        if not FAILURE_PATH.exists():
            write_json(FAILURE_PATH, failure)
        print(json.dumps(failure, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
