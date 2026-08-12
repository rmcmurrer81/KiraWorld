"""Pure, reusable contract for natural conformal avatar nails (version 3).

The Blender adapter deliberately keeps nails separate from the primary body mesh.
That lets a failed presentation refinement be replaced without changing body
topology, skin weights, identity, or the rig.  This module has no Blender
dependency and owns the bounded inventory, silhouette, material, clearance, and
single-terminal-bone attachment rules used by the adapter.
"""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence


METHOD_ID = "avatar_natural_nail_delivery_v3"
SCHEMA_VERSION = 3
PROJECTION_GRID_SIZE = 9
EXPECTED_NAIL_COUNT = 20
EXPECTED_FINGERNAIL_COUNT = 10
EXPECTED_TOENAIL_COUNT = 10

# A close conformal helper must remain visibly attached without intersecting.
MINIMUM_SURFACE_CLEARANCE_M = 0.000040
MAXIMUM_SURFACE_CLEARANCE_M = 0.000450
NORMAL_LIFT_STEP_M = 0.000025
MAXIMUM_NORMAL_LIFT_ITERATIONS = 10
MINIMUM_OUTWARD_NORMAL_ALIGNMENT = 0.12
FOOTPRINT_SCALE_CANDIDATES = (1.00, 0.96, 0.92, 0.88)
MINIMUM_RETAINED_FOOTPRINT_SCALE = 0.88
CENTER_FRACTION_CANDIDATES = (0.52, 0.58, 0.64, 0.70, 0.76, 0.82)

# The mesh surface is the nail bed.  A small outward-only solidify modifier gives
# it a believable edge without changing or cutting the body mesh.
NAIL_PLATE_THICKNESS_M = 0.00018
FREE_EDGE_START_FACE_ROW = PROJECTION_GRID_SIZE - 2

NAIL_BED_MATERIAL: dict[str, Any] = {
    "srgb_hex": "#D5A5A2",
    "alpha": 0.965,
    "roughness": 0.34,
    "transmission_weight": 0.025,
    "subsurface_weight": 0.025,
    "coat_weight": 0.12,
    "description": "soft translucent natural pink nail bed",
}

FREE_EDGE_MATERIAL: dict[str, Any] = {
    "srgb_hex": "#E7CFCA",
    "alpha": 0.945,
    "roughness": 0.37,
    "transmission_weight": 0.035,
    "subsurface_weight": 0.018,
    "coat_weight": 0.08,
    "description": "softly paler translucent free edge, never opaque white polish",
}


def _smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


def oval_half_width_scale(row_index: int, grid_size: int = PROJECTION_GRID_SIZE) -> float:
    """Return a squoval/oval half-width for a proximal-to-distal grid row.

    The smaller proximal row rounds into the cuticle, the widest section sits
    slightly proximal to center, and the distal row remains broad enough to look
    like a short ordinary nail rather than a pointed cosmetic extension.
    """

    if grid_size < 7 or grid_size % 2 == 0:
        raise ValueError("nail projection grid must be odd and at least seven")
    if not 0 <= int(row_index) < grid_size:
        raise ValueError("nail row index out of range")
    t = int(row_index) / (grid_size - 1)
    widest_at = 0.42
    if t <= widest_at:
        return 0.62 + 0.38 * _smoothstep(t / widest_at)
    return 1.0 - 0.34 * _smoothstep((t - widest_at) / (1.0 - widest_at))


def is_free_edge_face_row(
    face_row: int,
    grid_size: int = PROJECTION_GRID_SIZE,
) -> bool:
    """Identify the narrow distal material band without painting a white tip."""

    if grid_size < 7 or grid_size % 2 == 0:
        raise ValueError("nail projection grid must be odd and at least seven")
    if not 0 <= int(face_row) < grid_size - 1:
        raise ValueError("nail face row out of range")
    return int(face_row) >= grid_size - 2


def expected_nail_inventory() -> tuple[dict[str, Any], ...]:
    """Return the exact bilateral MakeHuman terminal-bone nail inventory."""

    rows: list[dict[str, Any]] = []
    for side in ("L", "R"):
        for digit in range(1, 6):
            rows.append(
                {
                    "nail_id": f"fingernail_{digit}_{side}",
                    "kind": "fingernail",
                    "side": side,
                    "digit": digit,
                    "bone": f"finger{digit}-3.{side}",
                    "outward_hint": (0.0, -1.0, 0.0),
                    "length_height_fraction": 0.0046 if digit == 1 else 0.0038,
                    "width_height_fraction": 0.0030 if digit == 1 else 0.0023,
                }
            )
        for digit in range(1, 6):
            rows.append(
                {
                    "nail_id": f"toenail_{digit}_{side}",
                    "kind": "toenail",
                    "side": side,
                    "digit": digit,
                    "bone": f"toe{digit}-{'2' if digit == 1 else '3'}.{side}",
                    "outward_hint": (0.0, -0.12, 1.0),
                    "length_height_fraction": 0.0048 if digit == 1 else 0.0031,
                    "width_height_fraction": 0.0041 if digit == 1 else 0.0024,
                }
            )
    return tuple(deepcopy(rows))


def material_contract() -> dict[str, Any]:
    return {
        "nail_bed": deepcopy(NAIL_BED_MATERIAL),
        "free_edge": deepcopy(FREE_EDGE_MATERIAL),
        "free_edge_is_paler_than_bed": _relative_luminance(
            FREE_EDGE_MATERIAL["srgb_hex"]
        )
        > _relative_luminance(NAIL_BED_MATERIAL["srgb_hex"]),
        "opaque_white_polish_allowed": False,
        "cosmetic_extension_allowed": False,
    }


def _relative_luminance(srgb_hex: str) -> float:
    value = str(srgb_hex)
    if len(value) != 7 or not value.startswith("#"):
        raise ValueError("expected #RRGGBB color")
    channels = [int(value[index : index + 2], 16) / 255.0 for index in (1, 3, 5)]

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def validate_finite_points(points: Iterable[Sequence[float]]) -> dict[str, Any]:
    values = [tuple(float(value) for value in point) for point in points]
    if not values or any(len(point) != 3 for point in values):
        raise ValueError("nail geometry requires non-empty XYZ points")
    if any(not math.isfinite(value) for point in values for value in point):
        raise ValueError("nail geometry contains a non-finite coordinate")
    return {
        "finite_geometry": True,
        "vertex_count": len(values),
        "coordinate_magnitude_maximum_m": max(abs(value) for point in values for value in point),
    }


def validate_clearance_measurement(
    *,
    minimum_m: float,
    maximum_m: float,
    overlap_count: int,
) -> dict[str, Any]:
    minimum = float(minimum_m)
    maximum = float(maximum_m)
    overlaps = int(overlap_count)
    if not all(math.isfinite(value) for value in (minimum, maximum)):
        raise ValueError("nail clearance is not finite")
    if minimum > maximum:
        raise ValueError("nail clearance minimum exceeds maximum")
    if overlaps != 0:
        raise ValueError("nail intersects the primary body surface")
    if minimum < MINIMUM_SURFACE_CLEARANCE_M:
        raise ValueError("nail is too close to or inside the primary body surface")
    if maximum > MAXIMUM_SURFACE_CLEARANCE_M:
        raise ValueError("nail visibly floats above the primary body surface")
    return {
        "minimum_m": minimum,
        "maximum_m": maximum,
        "body_surface_triangle_overlap_count": overlaps,
        "conservative_clearance_passed": True,
    }


def validate_attachment_measurement(
    *,
    expected_bone: str,
    actual_bone: str,
    parent_is_exact_armature: bool,
    armature_modifier_targets_exact_rig: bool,
    every_vertex_has_unit_terminal_bone_weight: bool,
) -> dict[str, Any]:
    if str(actual_bone) != str(expected_bone):
        raise ValueError("nail is attached to the wrong terminal bone")
    gates = {
        "parent_is_exact_armature": bool(parent_is_exact_armature),
        "armature_modifier_targets_exact_rig": bool(
            armature_modifier_targets_exact_rig
        ),
        "every_vertex_has_unit_terminal_bone_weight": bool(
            every_vertex_has_unit_terminal_bone_weight
        ),
    }
    if not all(gates.values()):
        raise ValueError("nail rigid-follow attachment contract failed")
    return {
        "bone": str(actual_bone),
        **gates,
        "rigid_terminal_bone_follow_proven_by_construction": True,
    }


def validate_delivery_records(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Fail closed on inventory, geometry, fit, dimensions, and attachment."""

    rows = [dict(record) for record in records]
    expected = {row["nail_id"]: row for row in expected_nail_inventory()}
    actual_ids = [str(row.get("nail_id", "")) for row in rows]
    if len(rows) != EXPECTED_NAIL_COUNT or len(set(actual_ids)) != len(rows):
        raise ValueError("natural nail delivery must contain 20 unique records")
    if set(actual_ids) != set(expected):
        raise ValueError("natural nail delivery inventory drifted")
    for row in rows:
        definition = expected[str(row["nail_id"])]
        if any(row.get(key) != definition[key] for key in ("kind", "side", "digit", "bone")):
            raise ValueError(f"nail identity or terminal bone drifted: {row['nail_id']}")
        if row.get("finite_geometry") is not True:
            raise ValueError(f"nail geometry not proven finite: {row['nail_id']}")
        length = float(row.get("plate_length_m", math.nan))
        width = float(row.get("plate_width_m", math.nan))
        target_height = float(row.get("target_height_m", math.nan))
        if not all(math.isfinite(value) and value > 0.0 for value in (length, width, target_height)):
            raise ValueError(f"invalid nail dimensions: {row['nail_id']}")
        nominal_length = target_height * float(definition["length_height_fraction"])
        nominal_width = target_height * float(definition["width_height_fraction"])
        if not 0.82 * nominal_length <= length <= 1.08 * nominal_length:
            raise ValueError(f"nail length outside conservative bound: {row['nail_id']}")
        if not 0.72 * nominal_width <= width <= 1.08 * nominal_width:
            raise ValueError(f"nail width outside conservative bound: {row['nail_id']}")
        ratio = length / width
        if not 0.95 <= ratio <= 2.15:
            raise ValueError(f"nail aspect ratio is not ordinary: {row['nail_id']}")
        validate_clearance_measurement(
            minimum_m=float(row["minimum_clearance_m"]),
            maximum_m=float(row["maximum_clearance_m"]),
            overlap_count=int(row["body_surface_triangle_overlap_count"]),
        )
        validate_attachment_measurement(
            expected_bone=str(definition["bone"]),
            actual_bone=str(row["bone"]),
            parent_is_exact_armature=row.get("parent_is_exact_armature") is True,
            armature_modifier_targets_exact_rig=(
                row.get("armature_modifier_targets_exact_rig") is True
            ),
            every_vertex_has_unit_terminal_bone_weight=(
                row.get("every_vertex_has_unit_terminal_bone_weight") is True
            ),
        )
        if row.get("rounded_oval_silhouette") is not True:
            raise ValueError(f"rounded nail silhouette not proven: {row['nail_id']}")
        if int(row.get("free_edge_face_count", 0)) <= 0:
            raise ValueError(f"paler free edge not present: {row['nail_id']}")
    return {
        "method_id": METHOD_ID,
        "component_count": len(rows),
        "fingernail_count": sum(row["kind"] == "fingernail" for row in rows),
        "toenail_count": sum(row["kind"] == "toenail" for row in rows),
        "all_twenty_present": True,
        "all_geometry_finite": True,
        "all_rounded_oval": True,
        "all_clearances_and_overlap_gates_passed": True,
        "all_exact_terminal_bone_follow_gates_passed": True,
        "primary_body_mesh_or_rig_modified": False,
        "dynamic_pose_clearance_requalification_required": True,
    }


__all__ = [
    "CENTER_FRACTION_CANDIDATES",
    "EXPECTED_FINGERNAIL_COUNT",
    "EXPECTED_NAIL_COUNT",
    "EXPECTED_TOENAIL_COUNT",
    "FOOTPRINT_SCALE_CANDIDATES",
    "FREE_EDGE_MATERIAL",
    "FREE_EDGE_START_FACE_ROW",
    "MAXIMUM_NORMAL_LIFT_ITERATIONS",
    "MAXIMUM_SURFACE_CLEARANCE_M",
    "METHOD_ID",
    "MINIMUM_OUTWARD_NORMAL_ALIGNMENT",
    "MINIMUM_RETAINED_FOOTPRINT_SCALE",
    "MINIMUM_SURFACE_CLEARANCE_M",
    "NAIL_BED_MATERIAL",
    "NAIL_PLATE_THICKNESS_M",
    "NORMAL_LIFT_STEP_M",
    "PROJECTION_GRID_SIZE",
    "SCHEMA_VERSION",
    "expected_nail_inventory",
    "is_free_edge_face_row",
    "material_contract",
    "oval_half_width_scale",
    "validate_attachment_measurement",
    "validate_clearance_measurement",
    "validate_delivery_records",
    "validate_finite_points",
]
