#!/usr/bin/env python3
"""Attempt 06: one-piece, shallow R22 external-surface integration.

Attempt 05 proved that reducing individual components was insufficient: the
separate ribbons still read as a vertical diagram stack.  This append-only
attempt keeps the exact inherited body outside the rejected pelvic mask and
replaces the front stack with one broad, shallow surface field whose boundary
returns to the body.  Regional material cues are assigned on that one field.

This remains an external visual candidate.  It does not create or claim an
internal vagina, urethra, bladder, bowel, pelvic floor, reproductive organs,
continence, sensation, fertility, pregnancy, or other physiology.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys
from typing import Any

import bpy
from mathutils import Vector


ROOT = Path(r"C:\Users\robmc\Kira")
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import blender_author_kira_r22_external_anatomy_attempt05 as previous  # noqa: E402


base = previous.base
ray_surface_y_fixed = previous.ray_surface_y_fixed
bind_to_rig_preserving_world = previous.bind_to_rig_preserving_world
run_attempt = previous.run_attempt


def smoothstep(value: float) -> float:
    t = max(0.0, min(1.0, float(value)))
    return t * t * (3.0 - 2.0 * t)


def relax_and_recess_center(
    body: bpy.types.Object,
    topology: dict[str, Any],
) -> dict[str, Any]:
    """Smooth the rejected insert and recess only its deep interior.

    The small recess prevents the preserved failed surface from occluding the
    new one-piece field.  Interface vertices and the first two interior rings
    are never moved.
    """

    relaxation = previous.relax_rejected_center_v2(body, topology)
    mesh = body.data
    before_recess = {
        index: mesh.vertices[index].co.copy() for index in topology["vertices"]
    }
    moved: set[int] = set()
    maximum_world_recess = 0.0
    inverse = body.matrix_world.inverted()
    for index in topology["vertices"]:
        if int(topology["distance"].get(index, 0)) <= 2:
            continue
        world = body.matrix_world @ mesh.vertices[index].co
        x_weight = smoothstep((0.038 - abs(world.x)) / 0.018)
        z_weight = smoothstep((world.z - 0.842) / 0.012) * smoothstep(
            (0.898 - world.z) / 0.014
        )
        front_weight = smoothstep((0.075 - world.y) / 0.050)
        weight = x_weight * z_weight * front_weight
        if weight <= 1.0e-8:
            continue
        recess = 0.00135 * weight
        target_world = world + Vector((0.0, recess, 0.0))
        mesh.vertices[index].co = inverse @ target_world
        moved.add(index)
        maximum_world_recess = max(maximum_world_recess, recess)
    mesh.update()
    seam_delta = max(
        (
            (mesh.vertices[index].co - before_recess[index]).length
            for index in topology["seam"]
        ),
        default=0.0,
    )
    return {
        "method": "bounded_relaxation_plus_deep_interior_recess_for_one_piece_field",
        "relaxation": relaxation,
        "recessed_vertex_count": len(moved),
        "maximum_world_recess": float(maximum_world_recess),
        "seam_maximum_delta": float(seam_delta),
    }


def gaussian(value: float, center: float, sigma: float) -> float:
    return math.exp(-0.5 * ((value - center) / sigma) ** 2)


def one_piece_external_field(
    body: bpy.types.Object,
    outer: bpy.types.Material,
    inner: bpy.types.Material,
    recess: bpy.types.Material,
) -> bpy.types.Object:
    columns = 49
    rows = 73
    x_min = -0.0155
    x_max = 0.0155
    z_min = 0.8425
    z_max = 0.8950
    vertices: list[Vector] = []

    for row in range(rows):
        v = row / (rows - 1)
        z = z_min + (z_max - z_min) * v
        z_taper = math.sin(math.pi * v) ** 0.72
        for column in range(columns):
            u = column / (columns - 1)
            x = x_min + (x_max - x_min) * u
            x_taper = math.sin(math.pi * u) ** 0.78
            boundary = x_taper * z_taper

            # Broad outer folds; both return continuously to the body.
            left_outer = gaussian(x, -0.0054, 0.0030) * gaussian(z, 0.8695, 0.0195)
            right_outer = gaussian(x, 0.0052, 0.0029) * gaussian(z, 0.8690, 0.0190)

            # Small natural asymmetry and low-relief inner folds.
            left_center = -0.00145 - 0.00016 * math.sin(
                math.pi * (z - z_min) / (z_max - z_min)
            )
            right_center = 0.00134 + 0.00011 * math.sin(
                math.pi * (z - z_min) / (z_max - z_min)
            )
            left_inner = gaussian(x, left_center, 0.00072) * gaussian(
                z, 0.8688, 0.0118
            )
            right_inner = gaussian(x, right_center, 0.00066) * gaussian(
                z, 0.8694, 0.0112
            )

            # A shallow midline depression keeps the field from reading as a
            # solid central ridge.  The underlying failed insert was recessed
            # first, so this depression remains visible without z-fighting.
            midline = gaussian(x, 0.0, 0.00125) * gaussian(z, 0.8675, 0.0145)
            hood = gaussian(x, 0.0, 0.0020) * gaussian(z, 0.8842, 0.0019)
            relief = boundary * (
                0.00078 * left_outer
                + 0.00074 * right_outer
                + 0.00020 * left_inner
                + 0.00017 * right_inner
                + 0.00020 * hood
                - 0.00030 * midline
            )
            surface_y = ray_surface_y_fixed(body, x, z, front=True)
            vertices.append(Vector((x, surface_y - relief - 0.00006 * boundary, z)))

    faces: list[tuple[int, ...]] = []
    for row in range(rows - 1):
        for column in range(columns - 1):
            first = row * columns + column
            faces.append((first, first + 1, first + 1 + columns, first + columns))

    obj = base.mesh_object(
        base.MODULE_PREFIX + "One_Piece_Integrated_External_Field",
        vertices,
        faces,
        outer,
        body,
    )
    obj.data.materials.append(inner)
    obj.data.materials.append(recess)

    # Assign restrained regional colour to faces on the same continuous field.
    # This avoids twelve independently protruding objects.
    for polygon in obj.data.polygons:
        center = obj.matrix_world @ polygon.center
        x = float(center.x)
        z = float(center.z)
        introital = (x / 0.00066) ** 2 + ((z - 0.8593) / 0.00255) ** 2
        urethral = (x / 0.00020) ** 2 + ((z - 0.8740) / 0.00017) ** 2
        left_path = -0.00145 - 0.00016 * math.sin(
            math.pi * (z - z_min) / (z_max - z_min)
        )
        right_path = 0.00134 + 0.00011 * math.sin(
            math.pi * (z - z_min) / (z_max - z_min)
        )
        inner_band = (
            0.8535 <= z <= 0.8825
            and (abs(x - left_path) < 0.00052 or abs(x - right_path) < 0.00048)
        )
        hood_region = (
            ((x / 0.00175) ** 2 + ((z - 0.8840) / 0.00135) ** 2) < 1.0
            and z >= 0.8836
        )
        if introital < 1.0:
            polygon.material_index = 2
        elif urethral < 1.0 or inner_band or hood_region:
            polygon.material_index = 1
        else:
            polygon.material_index = 0

    modifier = obj.modifiers.new("R22_ATTEMPT06_FIELD_SUBDIVISION", "SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = 1
    modifier.render_levels = 1
    return obj


def create_module_one_piece(
    body: bpy.types.Object,
    rig: bpy.types.Object,
) -> tuple[list[bpy.types.Object], dict[str, Any]]:
    outer = body.data.materials[base.PATCH_SLOT]
    inner = base.make_material(
        "R22_Attempt06_Subtle_Inner_Tissue",
        (0.355, 0.120, 0.112, 1.0),
        0.57,
        0.050,
    )
    opening = base.make_material(
        "R22_Attempt06_Opening_Shadow",
        (0.118, 0.025, 0.030, 1.0),
        0.66,
        0.025,
    )

    objects: list[bpy.types.Object] = [
        one_piece_external_field(body, outer, inner, opening)
    ]

    # One small posterior cue remains separate because it is on the opposite
    # surface and must never be conflated with the anterior field.
    objects.append(
        base.elliptical_cap(
            name=base.MODULE_PREFIX + "Posterior_Opening_Subtle",
            body=body,
            material=opening,
            center_x=0.0,
            center_z=0.8420,
            radius_x=0.00105,
            radius_z=0.00078,
            outward=0.00016,
            front=False,
            segments=48,
        )
    )
    objects.append(
        base.ellipse_rim(
            name=base.MODULE_PREFIX + "Posterior_External_Rim_Subtle",
            body=body,
            material=outer,
            center_x=0.0,
            center_z=0.8420,
            radius_x=0.00138,
            radius_z=0.00105,
            thickness=0.13,
            height=0.00024,
            front=False,
            segments=56,
        )
    )
    for obj in objects[1:]:
        modifier = obj.modifiers.new("R22_ATTEMPT06_POSTERIOR_SUBDIVISION", "SUBSURF")
        modifier.levels = 1
        modifier.render_levels = 1

    bindings = {
        obj.name: bind_to_rig_preserving_world(obj, body, rig) for obj in objects
    }
    return objects, {
        "component_order_anterior_to_posterior": [
            "one_piece_anterior_external_surface_field_with_subtle_region_cues",
            "continuous_inherited_perineal_body_surface",
            "separate_small_posterior_region",
        ],
        "component_count": len(objects),
        "objects": [obj.name for obj in objects],
        "bindings": bindings,
        "topology_change_from_attempt05": (
            "twelve-object anterior stack replaced by one broad continuous field"
        ),
        "visual_corrections": [
            "outer boundary returns to exact inherited body surface",
            "broad sub-millimetre outer relief",
            "low-relief asymmetric inner contours on the same field",
            "shallow central groove",
            "small superior hood cue with no exposed separate glans object",
            "narrow introital colour/depth cue without a protruding rim",
            "tiny urethral colour cue without a ring",
            "separate reduced posterior cue",
        ],
        "truth_boundary": (
            "external private visual candidate only; regional shading is not a hole or "
            "internal canal and no physiological function is claimed"
        ),
    }


base.ray_surface_y = ray_surface_y_fixed
base.bind_to_rig = bind_to_rig_preserving_world
base.relax_rejected_center = relax_and_recess_center
base.create_module = create_module_one_piece


if __name__ == "__main__":
    output_dir = ROOT / "Avatar/private_owner_review/kira_r22_external_anatomy_attempt_06"
    evidence_dir = ROOT / (
        "RecoverySprint/continuation_20260802/kira_r22_external_anatomy/attempt_06"
    )
    output_blend = output_dir / (
        "KIRA_R22_BALD_PRIVATE_INACTIVE_EXTERNAL_ANATOMY_ATTEMPT06.blend"
    )
    raise SystemExit(
        run_attempt(
            base,
            root=ROOT,
            attempt_number=6,
            output_dir=output_dir,
            evidence_dir=evidence_dir,
            output_blend=output_blend,
            prior_attempt_truth={
                "attempt_04": "aligned but still visually protruding and diagram-like",
                "attempt_05": "smaller components still read as a narrow vertical stack",
            },
            repair_summary=(
                "replace the anterior multi-object stack with one broad shallow body-integrated "
                "surface field carrying only restrained regional contour and colour cues"
            ),
        )
    )
