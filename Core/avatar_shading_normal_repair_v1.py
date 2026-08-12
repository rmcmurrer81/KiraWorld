"""Pure helpers for a localized, geometry-preserving avatar normal repair."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


METHOD_ID = "avatar_shading_normal_repair_v1"
CONFIG_PATH = Path(
    "Avatar/avatar_builder/tooling/avatar_shading_normal_repair_v1.json"
)


class AvatarShadingNormalRepairV1Error(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    if float(edge1) <= float(edge0):
        raise ValueError("smoothstep edges must increase")
    amount = max(
        0.0,
        min(1.0, (float(value) - float(edge0)) / (float(edge1) - float(edge0))),
    )
    return amount * amount * (3.0 - 2.0 * amount)


def rear_scalp_mask_weight(
    *,
    normalized_body_height: float,
    normalized_head_rearwardness: float,
    normalized_head_lateral: float,
    existing_head_neck_membership: float,
) -> float:
    """Return a soft mask for the rear scalp/head-neck shading band only."""

    height = float(normalized_body_height)
    rear = float(normalized_head_rearwardness)
    lateral = abs(float(normalized_head_lateral))
    membership = max(0.0, min(1.0, float(existing_head_neck_membership) / 0.32))
    lower = smoothstep(0.84, 0.875, height)
    upper = 1.0 - smoothstep(0.925, 0.955, height)
    rear_weight = smoothstep(0.62, 0.78, rear)
    lateral_weight = 1.0 - smoothstep(0.80, 1.05, lateral)
    return max(
        0.0,
        min(1.0, lower * upper * rear_weight * lateral_weight * membership),
    )


def combined_shading_mask_weight(
    *, scalp_weight: float, left_knee_weight: float, right_knee_weight: float
) -> float:
    return max(
        0.0,
        min(
            1.0,
            max(
                float(scalp_weight),
                float(left_knee_weight),
                float(right_knee_weight),
            ),
        ),
    )


def load_validated_avatar_shading_normal_repair_v1(
    project_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(project_root).resolve(strict=True)
    path = (root / CONFIG_PATH).resolve(strict=True)
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise AvatarShadingNormalRepairV1Error("normal-repair schema drifted")
    if config.get("config_id") != METHOD_ID or config.get("method_id") != METHOD_ID:
        raise AvatarShadingNormalRepairV1Error("normal-repair method identity drifted")
    modifier = config.get("normal_modifier", {})
    if (
        modifier.get("type") != "WEIGHTED_NORMAL"
        or modifier.get("mode") != "FACE_AREA_WITH_ANGLE"
        or not 1 <= int(modifier.get("weight", 0)) <= 50
        or not 0.0 < float(modifier.get("threshold_radians", 0.0)) <= 0.05
        or modifier.get("must_be_last_modifier") is not True
    ):
        raise AvatarShadingNormalRepairV1Error("weighted-normal contract drifted")
    gates = config.get("hard_gates", {})
    required_gates = {
        "primary_mesh_coordinates_unchanged",
        "evaluated_vertex_positions_unchanged",
        "topology_unchanged",
        "existing_deform_weight_hash_unchanged",
        "existing_vertex_groups_unchanged",
        "only_new_vertex_group_is_non_deform_shading_mask",
        "material_slots_and_polygon_indices_unchanged",
        "regional_skin_attribute_unchanged",
        "clean_bald_scalp_material_unchanged",
    }
    if any(gates.get(key) is not True for key in required_gates):
        raise AvatarShadingNormalRepairV1Error("normal-repair hard gates drifted")
    forbidden = config.get("forbidden", {})
    if not forbidden or any(value is not True for value in forbidden.values()):
        raise AvatarShadingNormalRepairV1Error("normal-repair forbidden boundary drifted")
    return config, {
        "method_id": METHOD_ID,
        "config_path": CONFIG_PATH.as_posix(),
        "config_sha256": sha256_file(path),
        "geometry_edits_allowed": False,
        "existing_rig_weight_edits_allowed": False,
        "material_edits_allowed": False,
        "scalp_hair_dependencies_allowed": False,
        "owner_visual_review_required": True,
    }


__all__ = [
    "AvatarShadingNormalRepairV1Error",
    "CONFIG_PATH",
    "METHOD_ID",
    "combined_shading_mask_weight",
    "load_validated_avatar_shading_normal_repair_v1",
    "rear_scalp_mask_weight",
    "sha256_file",
    "smoothstep",
]
