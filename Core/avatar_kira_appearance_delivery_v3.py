"""Pure contract helpers for Kira's third bounded appearance delivery pass.

This module deliberately contains no Blender dependency.  It validates the
hash-bound qualitative reference contract and supplies deterministic, bounded
profiles used by the Blender adapter.  It makes no identity-match, measured
pigmentation, anatomy-geometry, or runtime-activation claim.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Iterable


METHOD_ID = "kira_appearance_delivery_v3"
CONFIG_PATH = Path("Avatar/avatar_builder/tooling/kira_appearance_delivery_v3.json")
REGIONAL_SKIN_TINT_ATTRIBUTE = "Kira_Regional_Skin_Tint_V3"
REGIONAL_SKIN_MULTIPLY_NODE = "Kira_Regional_Skin_Multiply_V3"


class KiraAppearanceDeliveryV3Error(RuntimeError):
    """Raised when the bounded appearance contract or a pure gate fails."""


def sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounded(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(float(minimum), min(float(maximum), float(value)))


def _gaussian(value: float, center: float, sigma: float) -> float:
    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    return math.exp(-0.5 * ((float(value) - float(center)) / float(sigma)) ** 2)


def _blend_multiplier(
    current: tuple[float, float, float],
    target: tuple[float, float, float],
    weight: float,
) -> tuple[float, float, float]:
    amount = _bounded(weight)
    return tuple(
        float(source) + (float(destination) - float(source)) * amount
        for source, destination in zip(current, target)
    )


def regional_skin_multiplier(
    *,
    normalized_lateral: float,
    normalized_height: float,
    frontness: float,
) -> tuple[float, float, float]:
    """Return a bilateral, low-amplitude skin-albedo multiplier.

    ``normalized_lateral`` is -1..1 over the complete body width,
    ``normalized_height`` is 0..1 from sole to crown, and ``frontness`` is 0..1.
    The result is intentionally qualitative and bounded; it is not a sampled
    color or a claim about a photographed person's pigmentation.
    """

    lateral = _bounded(normalized_lateral, -1.0, 1.0)
    height = _bounded(normalized_height)
    forward = _bounded(frontness)
    absolute_lateral = abs(lateral)
    result = (1.0, 1.0, 1.0)

    craniofacial = (
        _gaussian(height, 0.885, 0.065)
        * _gaussian(absolute_lateral, 0.0, 0.19)
        * (0.35 + 0.65 * forward)
    )
    result = _blend_multiplier(result, (1.020, 0.982, 0.970), 0.48 * craniofacial)

    central_face = (
        _gaussian(height, 0.895, 0.035)
        * _gaussian(absolute_lateral, 0.075, 0.07)
        * forward
    )
    result = _blend_multiplier(result, (1.035, 0.950, 0.930), 0.30 * central_face)

    knees = _gaussian(height, 0.305, 0.047) * _gaussian(
        absolute_lateral, 0.20, 0.13
    )
    result = _blend_multiplier(result, (0.990, 0.945, 0.930), 0.42 * knees)

    elbows = _gaussian(height, 0.755, 0.055) * _gaussian(
        absolute_lateral, 0.66, 0.13
    )
    result = _blend_multiplier(result, (0.992, 0.952, 0.940), 0.32 * elbows)

    hands = _gaussian(height, 0.735, 0.075) * _gaussian(
        absolute_lateral, 0.92, 0.09
    )
    result = _blend_multiplier(result, (0.985, 0.950, 0.938), 0.28 * hands)

    feet = _gaussian(height, 0.035, 0.045) * _gaussian(
        absolute_lateral, 0.17, 0.15
    )
    result = _blend_multiplier(result, (0.988, 0.950, 0.936), 0.34 * feet)

    bounded = tuple(_bounded(channel, 0.90, 1.04) for channel in result)
    if any(abs(channel - 1.0) > 0.10 + 1.0e-9 for channel in bounded):
        raise KiraAppearanceDeliveryV3Error("regional tint escaped bounded contract")
    return bounded


def brow_profile(*, u: float, side_sign: float) -> dict[str, float]:
    """Return a shallow, tapered continuous brow profile in eye-height units."""

    parameter = _bounded(u, -1.0, 1.0)
    sign = 1.0 if float(side_sign) >= 0.0 else -1.0
    outward_u = sign * parameter
    arch = 0.082 * (1.0 - parameter * parameter)
    tail_drop = 0.095 * max(0.0, outward_u) ** 2
    inner_lift = 0.012 * max(0.0, -outward_u)
    center_offset = 0.285 + arch - tail_drop + inner_lift
    endpoint_floor = 0.42 if outward_u < 0.0 else 0.14
    endpoint_taper = endpoint_floor + (1.0 - endpoint_floor) * (
        1.0 - abs(parameter) ** 1.65
    )
    half_thickness = (0.054 + 0.017 * (1.0 - parameter * parameter)) * endpoint_taper
    return {
        "center_offset_eye_heights": center_offset,
        "half_thickness_eye_heights": half_thickness,
        "endpoint_taper": endpoint_taper,
        "outward_u": outward_u,
    }


def tapered_line_radius(*, u: float, minimum_fraction: float = 0.18) -> float:
    """Smoothly taper a continuous lash/lid curve without segmenting it."""

    parameter = abs(_bounded(u, -1.0, 1.0))
    floor = _bounded(minimum_fraction, 0.05, 1.0)
    return floor + (1.0 - floor) * (1.0 - parameter**2)


def continuous_strip_topology(sample_count: int) -> dict[str, int | bool]:
    count = int(sample_count)
    if count < 9 or count % 2 == 0:
        raise ValueError("continuous brow strip requires an odd sample count >= 9")
    return {
        "sample_count": count,
        "vertex_count": count * 2,
        "quad_count": count - 1,
        "single_connected_strip": True,
        "separate_stroke_count": 0,
    }


def required_face_vertex_count(face_size: int) -> int:
    size = int(face_size)
    if size < 3:
        raise ValueError("mesh faces require at least three vertices")
    return max(3, size - 1)


def validate_exact_reference_rows(
    project_root: Path, rows: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    root = Path(project_root).resolve(strict=True)
    validated: list[dict[str, Any]] = []
    for row in rows:
        relative = Path(str(row["path"]))
        path = (root / relative).resolve(strict=True)
        if root not in path.parents:
            raise KiraAppearanceDeliveryV3Error(f"reference escaped project: {relative}")
        actual = sha256_file(path)
        expected = str(row["sha256"]).lower()
        if actual != expected:
            raise KiraAppearanceDeliveryV3Error(
                f"reference hash mismatch: {relative.as_posix()}"
            )
        validated.append(
            {
                "path": relative.as_posix(),
                "sha256": actual,
                "size_bytes": path.stat().st_size,
            }
        )
    if len(validated) < 6:
        raise KiraAppearanceDeliveryV3Error("qualitative reference set is incomplete")
    return validated


def load_validated_kira_appearance_delivery_v3(project_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(project_root).resolve(strict=True)
    path = (root / CONFIG_PATH).resolve(strict=True)
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise KiraAppearanceDeliveryV3Error("appearance schema version drifted")
    if config.get("config_id") != METHOD_ID or config.get("method_id") != METHOD_ID:
        raise KiraAppearanceDeliveryV3Error("appearance method identity drifted")
    reference = config.get("reference_policy", {})
    if (
        reference.get("identity_match_claim_allowed") is not False
        or reference.get("measured_color_claim_allowed") is not False
        or reference.get("texture_or_geometry_copy_allowed") is not False
    ):
        raise KiraAppearanceDeliveryV3Error("qualitative reference truth boundary drifted")
    bald = config.get("bald_low_resource_boundary", {})
    prohibited_bald_values = (
        "separate_scalp_material_allowed",
        "scalp_hair_provider_allowed",
        "scalp_hair_object_allowed",
        "scalp_hair_material_allowed",
        "scalp_hair_texture_allowed",
        "scalp_hair_controller_allowed",
    )
    if any(bald.get(key) is not False for key in prohibited_bald_values):
        raise KiraAppearanceDeliveryV3Error("bald low-resource boundary drifted")
    if bald.get("natural_scalp_is_primary_skin_surface") is not True:
        raise KiraAppearanceDeliveryV3Error("natural scalp continuity is not required")
    skin = config.get("skin", {})
    if (
        skin.get("regional_tint_attribute") != REGIONAL_SKIN_TINT_ATTRIBUTE
        or skin.get("shader_multiply_node") != REGIONAL_SKIN_MULTIPLY_NODE
        or float(skin.get("minimum_channel_multiplier", 0.0)) < 0.90
        or float(skin.get("maximum_channel_multiplier", 2.0)) > 1.04
        or skin.get("image_textures_added") is not False
    ):
        raise KiraAppearanceDeliveryV3Error("regional skin bounds drifted")
    eye = config.get("eye_surrounds", {})
    brow = eye.get("brow", {})
    topology = continuous_strip_topology(int(brow.get("sample_count", 0)))
    if brow.get("representation") != "single_continuous_tapered_conformal_mesh_per_side":
        raise KiraAppearanceDeliveryV3Error("continuous brow representation drifted")
    forbidden = config.get("forbidden", {})
    required_forbidden = {
        "body_geometry_change",
        "rig_or_weight_change",
        "separate_lip_mesh",
        "separate_nipple_or_areola_mesh",
        "scalp_cap_or_dome",
        "scalp_hair_instantiation",
        "runtime_activation",
        "glb_export",
        "clothing",
        "publication_or_upload",
    }
    if any(forbidden.get(key) is not True for key in required_forbidden):
        raise KiraAppearanceDeliveryV3Error("forbidden operation boundary drifted")
    exact_references = validate_exact_reference_rows(
        root, reference.get("reviewed_exact_files", ())
    )
    return config, {
        "config_path": CONFIG_PATH.as_posix(),
        "config_sha256": sha256_file(path),
        "method_id": METHOD_ID,
        "exact_qualitative_references": exact_references,
        "qualitative_reference_count": len(exact_references),
        "identity_match_claim_allowed": False,
        "measured_color_claim_allowed": False,
        "texture_or_geometry_copy_allowed": False,
        "continuous_brow_topology": topology,
        "natural_scalp_is_unchanged_primary_skin_surface": True,
    }


__all__ = [
    "CONFIG_PATH",
    "KiraAppearanceDeliveryV3Error",
    "METHOD_ID",
    "REGIONAL_SKIN_MULTIPLY_NODE",
    "REGIONAL_SKIN_TINT_ATTRIBUTE",
    "brow_profile",
    "continuous_strip_topology",
    "load_validated_kira_appearance_delivery_v3",
    "regional_skin_multiplier",
    "required_face_vertex_count",
    "sha256_file",
    "tapered_line_radius",
    "validate_exact_reference_rows",
]
