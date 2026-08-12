"""Blender adapter for the bounded qualitative Kira face direction v3."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

from mathutils import Vector

from Core.avatar_kira_face_delivery_v3 import (
    HEAD_REGION_MINIMUM_HEIGHT_FRACTION,
    MAXIMUM_VERTEX_DELTA_M,
    METHOD_ID,
    TARGETS,
    validate_contract,
)
import tools.blender_profiled_adult_candidate_components as components


class KiraFaceDeliveryV3Error(RuntimeError):
    pass


def _read_target(path: Path) -> dict[int, Vector]:
    rows: dict[int, Vector] = {}
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, start=1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            fields = line.split()
            if len(fields) != 4:
                raise KiraFaceDeliveryV3Error(
                    f"invalid target row at {path}:{line_number}"
                )
            index = int(fields[0])
            if index in rows:
                raise KiraFaceDeliveryV3Error(
                    f"duplicate target index at {path}:{line_number}"
                )
            rows[index] = Vector(tuple(float(value) for value in fields[1:4]))
    if not rows:
        raise KiraFaceDeliveryV3Error(f"empty target: {path}")
    return rows


def apply_kira_face_direction_to_source_v3(
    source: dict[str, Any], *, project_root: Path, target_height_m: float,
) -> dict[str, Any]:
    """Mutate only compatible head vertices in a prepared source dictionary."""

    contract = validate_contract(project_root)
    body_vertices = source.get("body_vertices")
    source_to_body = source.get("source_to_body")
    if not isinstance(body_vertices, list) or not isinstance(source_to_body, dict):
        raise KiraFaceDeliveryV3Error("prepared source mapping is incomplete")
    before_count = len(body_vertices)
    minimum_z = float(target_height_m) * HEAD_REGION_MINIMUM_HEIGHT_FRACTION
    scale = float(source["uniform_scale"])
    accumulated: dict[int, Vector] = {}
    feature_vertices: dict[str, set[int]] = {}
    target_reports: list[dict[str, Any]] = []
    excluded_rows = 0
    root = Path(project_root).resolve(strict=True)

    for record in TARGETS:
        rows = _read_target(root / str(record["path"]))
        mapped = 0
        excluded = 0
        feature = str(record["feature"])
        feature_set = feature_vertices.setdefault(feature, set())
        for source_index, raw_delta in rows.items():
            compact = source_to_body.get(source_index)
            if compact is None:
                continue
            if float(body_vertices[compact].z) < minimum_z:
                excluded += 1
                continue
            delta = components._converted_makehuman(raw_delta) * scale * float(record["weight"])  # noqa: SLF001
            if not all(math.isfinite(float(value)) for value in delta):
                raise KiraFaceDeliveryV3Error(
                    f"non-finite target delta: {record['target_id']}"
                )
            accumulated[compact] = accumulated.get(compact, Vector()) + delta
            feature_set.add(int(compact))
            mapped += 1
        if mapped == 0:
            raise KiraFaceDeliveryV3Error(
                f"target has no compatible head vertices: {record['target_id']}"
            )
        excluded_rows += excluded
        target_reports.append(
            {
                "target_id": str(record["target_id"]),
                "feature": feature,
                "mapped_head_vertex_count": mapped,
                "excluded_below_head_vertex_count": excluded,
                "weight": float(record["weight"]),
            }
        )

    maximum_delta = max((float(delta.length) for delta in accumulated.values()), default=0.0)
    if not accumulated or maximum_delta > MAXIMUM_VERTEX_DELTA_M:
        raise KiraFaceDeliveryV3Error(
            f"bounded face delta failed: changed={len(accumulated)} max={maximum_delta:.9f}"
        )
    minimum_touched_z = min(float(body_vertices[index].z) for index in accumulated)
    if minimum_touched_z < minimum_z:
        raise KiraFaceDeliveryV3Error("face delta escaped measured head region")
    for compact, delta in accumulated.items():
        body_vertices[compact] = body_vertices[compact] + delta
    if len(body_vertices) != before_count:
        raise KiraFaceDeliveryV3Error("face direction changed vertex count")

    source["kira_face_delivery_v3"] = {
        "method_id": METHOD_ID,
        "changed_vertex_count": len(accumulated),
        "minimum_touched_z_m": minimum_touched_z,
        "minimum_allowed_z_m": minimum_z,
        "maximum_accumulated_vertex_delta_m": maximum_delta,
        "excluded_below_head_target_rows": excluded_rows,
        "target_reports": target_reports,
        "feature_vertex_counts": {
            key: len(values) for key, values in sorted(feature_vertices.items())
        },
        "topology_changed": False,
        "vertex_order_changed": False,
        "body_height_changed": False,
        "identity_match_claim_allowed": False,
        "owner_visual_review_required": True,
        "contract": contract,
    }
    return source["kira_face_delivery_v3"]


__all__ = ["KiraFaceDeliveryV3Error", "apply_kira_face_direction_to_source_v3"]
