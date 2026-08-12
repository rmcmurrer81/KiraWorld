"""Pure contract and mask for the bounded rear-scalp custom-normal repair."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from Core.avatar_shading_normal_repair_v1 import smoothstep


METHOD_ID = "avatar_shading_normal_repair_v2"
CONFIG_PATH = Path(
    "Avatar/avatar_builder/tooling/avatar_shading_normal_repair_v2.json"
)


class AvatarShadingNormalRepairV2Error(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rear_scalp_mask_weight_v2(
    *,
    normalized_body_height: float,
    normalized_head_rearwardness: float,
    normalized_head_lateral: float,
    existing_head_neck_membership: float,
) -> float:
    height = float(normalized_body_height)
    rear = float(normalized_head_rearwardness)
    lateral = abs(float(normalized_head_lateral))
    membership = max(0.0, min(1.0, float(existing_head_neck_membership) / 0.32))
    return max(
        0.0,
        min(
            1.0,
            smoothstep(0.865, 0.885, height)
            * (1.0 - smoothstep(0.925, 0.945, height))
            * smoothstep(0.62, 0.78, rear)
            * (1.0 - smoothstep(0.80, 1.05, lateral))
            * membership,
        ),
    )


def load_validated_avatar_shading_normal_repair_v2(
    project_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(project_root).resolve(strict=True)
    path = (root / CONFIG_PATH).resolve(strict=True)
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise AvatarShadingNormalRepairV2Error("v2 normal schema drifted")
    if config.get("config_id") != METHOD_ID or config.get("method_id") != METHOD_ID:
        raise AvatarShadingNormalRepairV2Error("v2 normal method identity drifted")
    if config.get("supersedes_visual_rejected_method") != "avatar_shading_normal_repair_v1":
        raise AvatarShadingNormalRepairV2Error("rejected v1 provenance missing")
    smoothing = config.get("normal_smoothing", {})
    if (
        smoothing.get("representation") != "localized_custom_split_vertex_normals"
        or not 4 <= int(smoothing.get("laplacian_iterations", 0)) <= 16
        or not 0.1 <= float(smoothing.get("per_iteration_strength", 0.0)) <= 0.8
        or not 5.0 <= float(smoothing.get("maximum_normal_change_degrees", 0.0)) <= 35.0
    ):
        raise AvatarShadingNormalRepairV2Error("custom-normal smoothing bounds drifted")
    if config.get("diagnosis", {}).get("bilateral_knees") != (
        "separate flexed-geometry and self-shadow defect; not repaired or concealed here"
    ):
        raise AvatarShadingNormalRepairV2Error("knee truth boundary drifted")
    gates = config.get("hard_gates", {})
    if not gates or any(value is not True and value != 0 for value in gates.values()):
        raise AvatarShadingNormalRepairV2Error("v2 normal hard gates drifted")
    forbidden = config.get("forbidden", {})
    if not forbidden or any(value is not True for value in forbidden.values()):
        raise AvatarShadingNormalRepairV2Error("v2 normal forbidden boundary drifted")
    return config, {
        "method_id": METHOD_ID,
        "config_path": CONFIG_PATH.as_posix(),
        "config_sha256": sha256_file(path),
        "geometry_or_weight_edits_allowed": False,
        "knee_repair_claimed": False,
        "scalp_hair_dependencies_allowed": False,
        "owner_visual_review_required": True,
    }


__all__ = [
    "AvatarShadingNormalRepairV2Error",
    "CONFIG_PATH",
    "METHOD_ID",
    "load_validated_avatar_shading_normal_repair_v2",
    "rear_scalp_mask_weight_v2",
    "sha256_file",
]
