"""Bounded, identity-honest Kira face direction for private adult-body review.

This contract combines official MakeHuman CC0 targets into a qualitative face
direction.  It is not a biometric reconstruction and makes no identity-match
claim.  The Blender adapter applies it only above a measured head boundary and
preserves mesh topology, vertex order, rig source correspondence, and body
height.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping


METHOD_ID = "kira_qualitative_face_delivery_v3"
HEAD_REGION_MINIMUM_HEIGHT_FRACTION = 0.76
MAXIMUM_VERTEX_DELTA_M = 0.012


TARGETS: tuple[dict[str, Any], ...] = (
    {
        "target_id": "head_oval_soft",
        "feature": "head",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/head/head-oval.target",
        "sha256": "f873122d889a9ba0f730b76e43fbd16b955ffb9f7cfe08c2752347d5f774b48f",
        "weight": 0.15,
    },
    {
        "target_id": "chin_width_soft_decrease",
        "feature": "chin",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/chin/chin-width-decr.target",
        "sha256": "599e978ca38cfc5eddb95f412242f24028ecffc98a2d45a9f6ce91247110beeb",
        "weight": 0.25,
    },
    {
        "target_id": "chin_soft_triangle",
        "feature": "chin",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/chin/chin-triangle.target",
        "sha256": "c596652e08266093309d4996c6c5c71a4d184ca5adceeeab80d4202b0938a3fc",
        "weight": 0.15,
    },
    {
        "target_id": "nose_horizontal_soft_decrease",
        "feature": "nose",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/nose/nose-scale-horiz-decr.target",
        "sha256": "5cf77aa83f1ab83d019e3ba965521c88364ec729b68104fc802a95a9bff8dd76",
        "weight": 0.18,
    },
    {
        "target_id": "nose_volume_soft_decrease",
        "feature": "nose",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/nose/nose-volume-decr.target",
        "sha256": "89ea9041438729527aa9daa526b6b0233477cafb308dd1b2e1df4172830aa383",
        "weight": 0.10,
    },
    {
        "target_id": "mouth_width_soft_increase",
        "feature": "mouth",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/mouth/mouth-scale-horiz-incr.target",
        "sha256": "04b91799a42ffdd7c377b9ae180d861e250b5f5790161eb4659700e587e836ba",
        "weight": 0.20,
    },
    {
        "target_id": "upper_lip_natural_volume",
        "feature": "upper_lip",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/mouth/mouth-upperlip-volume-incr.target",
        "sha256": "73916c93fbeeedcefd4279c2153a1d7ccb6b2c394fbfb6d50e0bf4d2bb365af2",
        "weight": 0.25,
    },
    {
        "target_id": "lower_lip_natural_volume",
        "feature": "lower_lip",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/mouth/mouth-lowerlip-volume-incr.target",
        "sha256": "082e7a91b2d8c930eb4b3c027407a0e94d16dfdc710cc161bd0bc87191435213",
        "weight": 0.20,
    },
    {
        "target_id": "cupids_bow_soft_definition",
        "feature": "upper_lip",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/mouth/mouth-cupidsbow-incr.target",
        "sha256": "5729d370a5139ca3d299851dae11eefa35c9fa22b1fe8ad4eec13a7c47ad8211",
        "weight": 0.15,
    },
    {
        "target_id": "left_cheekbone_soft_definition",
        "feature": "cheekbone",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/cheek/l-cheek-bones-incr.target",
        "sha256": "b0316f8ec8b656c7a3a9c18c6f92503461e675ab89cf55e35f6c9e9423bf2cb2",
        "weight": 0.18,
        "pair_id": "cheekbone_definition",
        "side": "left",
    },
    {
        "target_id": "right_cheekbone_soft_definition",
        "feature": "cheekbone",
        "path": "Avatar/avatar_builder/tooling/makehuman_official/makehuman/data/targets/cheek/r-cheek-bones-incr.target",
        "sha256": "cc4b1623f47de2f705739019e8ceb820c90c2c5f5688dc8791924c78a2714222",
        "weight": 0.18,
        "pair_id": "cheekbone_definition",
        "side": "right",
    },
)


def sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_contract(project_root: Path) -> dict[str, Any]:
    root = Path(project_root).resolve(strict=True)
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    pairs: dict[str, set[str]] = {}
    for target in TARGETS:
        target_id = str(target["target_id"])
        if target_id in ids:
            raise ValueError(f"duplicate face target: {target_id}")
        ids.add(target_id)
        weight = float(target["weight"])
        if not 0.0 < weight <= 0.25:
            raise ValueError(f"face target weight out of bounds: {target_id}")
        relative = Path(str(target["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe face target path: {target_id}")
        path = (root / relative).resolve(strict=True)
        path.relative_to(root)
        actual = sha256_file(path)
        if actual != str(target["sha256"]).lower():
            raise ValueError(f"face target hash mismatch: {target_id}")
        if target.get("pair_id"):
            pairs.setdefault(str(target["pair_id"]), set()).add(str(target["side"]))
        rows.append(
            {
                "target_id": target_id,
                "feature": str(target["feature"]),
                "path": relative.as_posix(),
                "sha256": actual,
                "weight": weight,
            }
        )
    if pairs != {"cheekbone_definition": {"left", "right"}}:
        raise ValueError("paired cheek target contract is incomplete")
    return {
        "method_id": METHOD_ID,
        "target_count": len(rows),
        "targets": rows,
        "head_region_minimum_height_fraction": HEAD_REGION_MINIMUM_HEIGHT_FRACTION,
        "maximum_vertex_delta_m": MAXIMUM_VERTEX_DELTA_M,
        "topology_change_allowed": False,
        "identity_match_claim_allowed": False,
        "biometric_fit_performed": False,
        "qualitative_owner_direction_only": True,
    }


def contract_summary() -> Mapping[str, Any]:
    return {
        "method_id": METHOD_ID,
        "target_count": len(TARGETS),
        "features": sorted({str(row["feature"]) for row in TARGETS}),
    }


__all__ = [
    "HEAD_REGION_MINIMUM_HEIGHT_FRACTION",
    "MAXIMUM_VERTEX_DELTA_M",
    "METHOD_ID",
    "TARGETS",
    "contract_summary",
    "validate_contract",
]
