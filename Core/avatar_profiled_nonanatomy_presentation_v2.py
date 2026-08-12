"""Versioned, identity-honest presentation targets for profiled adult avatars.

This module contains no Blender dependency.  It is the fail-closed contract used by
the Blender adapter and its tests.  The target set is an owner-directed qualitative
face direction built only from the repository's official MakeHuman CC0 targets; it
is not a biometric fit or an identity-match claim.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


METHOD_ID = "profiled_adult_nonanatomy_presentation_v2"
FACE_DIRECTION_ID = "kira_qualitative_feminine_adult_face_direction_v2"

# Each weight stays at or below the existing Avatar Builder 0.25 ceiling.
FACE_TARGETS: tuple[dict[str, Any], ...] = (
    {
        "target_id": "face_v2_chin_width_decrease",
        "feature": "chin",
        "direction": "width_decrease",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/chin/chin-width-decr.target",
        "sha256": "599e978ca38cfc5eddb95f412242f24028ecffc98a2d45a9f6ce91247110beeb",
        "weight": 0.22,
    },
    {
        "target_id": "face_v2_chin_triangle",
        "feature": "chin",
        "direction": "adult_feminine_taper",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/chin/chin-triangle.target",
        "sha256": "c596652e08266093309d4996c6c5c71a4d184ca5adceeeab80d4202b0938a3fc",
        "weight": 0.10,
    },
    {
        "target_id": "face_v2_nose_horizontal_decrease",
        "feature": "nose",
        "direction": "width_decrease",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/nose/nose-scale-horiz-decr.target",
        "sha256": "5cf77aa83f1ab83d019e3ba965521c88364ec729b68104fc802a95a9bff8dd76",
        "weight": 0.14,
    },
    {
        "target_id": "face_v2_nose_volume_decrease",
        "feature": "nose",
        "direction": "volume_decrease",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/nose/nose-volume-decr.target",
        "sha256": "89ea9041438729527aa9daa526b6b0233477cafb308dd1b2e1df4172830aa383",
        "weight": 0.08,
    },
    {
        "target_id": "face_v2_mouth_horizontal_increase",
        "feature": "mouth",
        "direction": "width_increase",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/mouth/mouth-scale-horiz-incr.target",
        "sha256": "04b91799a42ffdd7c377b9ae180d861e250b5f5790161eb4659700e587e836ba",
        "weight": 0.10,
    },
    {
        "target_id": "face_v2_upper_lip_volume_increase",
        "feature": "upper_lip",
        "direction": "volume_increase",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/mouth/mouth-upperlip-volume-incr.target",
        "sha256": "73916c93fbeeedcefd4279c2153a1d7ccb6b2c394fbfb6d50e0bf4d2bb365af2",
        "weight": 0.20,
    },
    {
        "target_id": "face_v2_lower_lip_volume_increase",
        "feature": "lower_lip",
        "direction": "volume_increase",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/mouth/mouth-lowerlip-volume-incr.target",
        "sha256": "082e7a91b2d8c930eb4b3c027407a0e94d16dfdc710cc161bd0bc87191435213",
        "weight": 0.12,
    },
    {
        "target_id": "face_v2_cupids_bow_increase",
        "feature": "upper_lip",
        "direction": "cupids_bow_definition",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/mouth/mouth-cupidsbow-incr.target",
        "sha256": "5729d370a5139ca3d299851dae11eefa35c9fa22b1fe8ad4eec13a7c47ad8211",
        "weight": 0.15,
    },
    {
        "target_id": "face_v2_left_cheekbone_increase",
        "feature": "cheekbone",
        "direction": "paired_definition",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/cheek/l-cheek-bones-incr.target",
        "sha256": "b0316f8ec8b656c7a3a9c18c6f92503461e675ab89cf55e35f6c9e9423bf2cb2",
        "weight": 0.08,
        "pair_id": "cheekbone_definition",
        "side": "left",
    },
    {
        "target_id": "face_v2_right_cheekbone_increase",
        "feature": "cheekbone",
        "direction": "paired_definition",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/cheek/r-cheek-bones-incr.target",
        "sha256": "cc4b1623f47de2f705739019e8ceb820c90c2c5f5688dc8791924c78a2714222",
        "weight": 0.08,
        "pair_id": "cheekbone_definition",
        "side": "right",
    },
)

SKIN_CALIBRATION = {
    "source_profile_srgb_hex": "#C7A08E",
    "calibrated_warm_non_pale_srgb_hex": "#AF806D",
    "maximum_channel_delta_from_source": 33,
    "roughness": 0.52,
    "subsurface_weight": 0.10,
    "subsurface_scale_m": 0.00105,
    "specular_ior_level": 0.27,
    "microvariation_fraction": 0.028,
    "truth_boundary": "owner-directed appearance calibration, not measured skin tone",
}

REVIEW_RIG = {
    "world_linear_rgba": (0.028, 0.038, 0.055, 1.0),
    "world_strength": 0.82,
    "exposure": -1.0,
    "gamma": 1.0,
    "key": {"energy_w": 300.0, "size_m": 3.2, "casts_shadows": True},
    "fill": {"energy_w": 155.0, "size_m": 3.8, "casts_shadows": False},
    "rim": {"energy_w": 120.0, "size_m": 3.4, "casts_shadows": False},
}


def sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def face_target_manifest() -> list[dict[str, Any]]:
    return deepcopy(list(FACE_TARGETS))


def validate_face_target_manifest(project_root: Path) -> dict[str, Any]:
    root = Path(project_root).resolve(strict=True)
    records: list[dict[str, Any]] = []
    ids: set[str] = set()
    pair_members: dict[str, set[str]] = {}
    for row in FACE_TARGETS:
        target_id = str(row["target_id"])
        if target_id in ids:
            raise ValueError(f"duplicate face target id: {target_id}")
        ids.add(target_id)
        weight = float(row["weight"])
        if not 0.0 < weight <= 0.25:
            raise ValueError(f"face target weight outside (0, 0.25]: {target_id}")
        relative = Path(str(row["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe face target path: {target_id}")
        resolved = (root / relative).resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"face target escaped project: {target_id}") from exc
        actual = sha256_file(resolved)
        if actual != str(row["sha256"]).lower():
            raise ValueError(f"face target hash mismatch: {target_id}")
        if row.get("pair_id"):
            pair_members.setdefault(str(row["pair_id"]), set()).add(str(row["side"]))
        records.append(
            {
                "target_id": target_id,
                "path": relative.as_posix(),
                "sha256": actual,
                "weight": weight,
                "feature": str(row["feature"]),
                "direction": str(row["direction"]),
            }
        )
    if pair_members != {"cheekbone_definition": {"left", "right"}}:
        raise ValueError("face target symmetric pair contract failed")
    required_features = {"chin", "nose", "mouth", "upper_lip", "lower_lip", "cheekbone"}
    actual_features = {str(row["feature"]) for row in FACE_TARGETS}
    if not required_features.issubset(actual_features):
        raise ValueError("face target feature coverage incomplete")
    return {
        "method_id": METHOD_ID,
        "face_direction_id": FACE_DIRECTION_ID,
        "target_count": len(records),
        "targets": records,
        "exact_hashes_verified": True,
        "maximum_target_weight": max(float(row["weight"]) for row in FACE_TARGETS),
        "paired_targets_complete": True,
        "biometric_fit_performed": False,
        "identity_match_claim_allowed": False,
        "qualitative_owner_direction_only": True,
    }


def rounded_nail_row_scale(row_index: int, grid_size: int) -> float:
    """Return a deterministic tapered width for a projected nail grid row."""

    if grid_size < 5 or grid_size % 2 == 0:
        raise ValueError("rounded nail grid must be odd and at least five")
    if not 0 <= row_index < grid_size:
        raise ValueError("rounded nail row index out of range")
    t = row_index / (grid_size - 1)
    # Proximal cuticle is gently rounded; the distal free edge is more oval.
    proximal = 0.72 + 0.28 * min(1.0, t / 0.34)
    distal = 0.56 + 0.44 * min(1.0, (1.0 - t) / 0.38)
    return min(proximal, distal, 1.0)


def component_frame_scale(
    projected_points: Iterable[Sequence[float]],
    *,
    minimum_scale_m: float,
    margin: float = 1.32,
) -> dict[str, Any]:
    points = [tuple(float(value) for value in point) for point in projected_points]
    if not points or any(len(point) != 2 for point in points):
        raise ValueError("component frame requires 2D projected points")
    if not 1.05 <= float(margin) <= 2.0 or minimum_scale_m <= 0.0:
        raise ValueError("invalid component frame bounds")
    low = tuple(min(point[axis] for point in points) for axis in range(2))
    high = tuple(max(point[axis] for point in points) for axis in range(2))
    center = tuple((low[axis] + high[axis]) * 0.5 for axis in range(2))
    extent = max(high[axis] - low[axis] for axis in range(2))
    scale = max(float(minimum_scale_m), extent * float(margin))
    return {
        "center_2d": list(center),
        "extent_2d_m": float(extent),
        "ortho_scale_m": float(scale),
        "margin": float(margin),
        "all_points_inside_frame": all(
            abs(point[axis] - center[axis]) <= scale * 0.5 / margin
            for point in points
            for axis in range(2)
        ),
    }


def silhouette_roughness(values: Sequence[float]) -> dict[str, float]:
    samples = [float(value) for value in values]
    if len(samples) < 7:
        raise ValueError("silhouette roughness requires at least seven samples")
    first = [samples[index + 1] - samples[index] for index in range(len(samples) - 1)]
    second = [first[index + 1] - first[index] for index in range(len(first) - 1)]
    return {
        "maximum_absolute_second_difference": max(abs(value) for value in second),
        "mean_absolute_second_difference": sum(abs(value) for value in second) / len(second),
        "range": max(samples) - min(samples),
    }


__all__ = [
    "FACE_DIRECTION_ID",
    "FACE_TARGETS",
    "METHOD_ID",
    "REVIEW_RIG",
    "SKIN_CALIBRATION",
    "component_frame_scale",
    "face_target_manifest",
    "rounded_nail_row_scale",
    "sha256_file",
    "silhouette_roughness",
    "validate_face_target_manifest",
]
