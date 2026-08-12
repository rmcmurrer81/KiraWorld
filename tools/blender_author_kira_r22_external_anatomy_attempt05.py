#!/usr/bin/env python3
"""Attempt 05: restrained, body-integrated R22 external-anatomy correction.

This append-only attempt preserves the existing R22 body, face, eyes, brows,
nails, rig, weights, actions, and nonpelvic materials.  It changes only the
detachable external-anatomy module and the already-authorized rejected central
pelvic insert relaxation.  It is a private visual candidate, not evidence of
internal anatomy, physiology, sensation, continence, reproduction, or owner
acceptance.
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

import blender_author_kira_r22_external_anatomy_attempt04 as previous  # noqa: E402


base = previous.base
ray_surface_y_fixed = previous.ray_surface_y_fixed
bind_to_rig_preserving_world = previous.bind_to_rig_preserving_world
run_attempt = previous.run_attempt


def add_subdivision(obj: bpy.types.Object, level: int = 2) -> None:
    modifier = obj.modifiers.new("R22_ATTEMPT05_TISSUE_SUBDIVISION", "SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = level
    modifier.render_levels = level


def small_partial_hood(
    body: bpy.types.Object,
    material: bpy.types.Material,
) -> bpy.types.Object:
    """Create a shallow superior arch; the glans remains mostly covered."""

    rows = 30
    columns = 5
    vertices: list[Vector] = []
    center_z = 0.8847
    radius_x = 0.00205
    radius_z = 0.00155
    for row in range(rows):
        angle = math.radians(24.0 + (132.0 * row / (rows - 1)))
        taper = math.sin(math.pi * row / (rows - 1)) ** 0.65
        center_x = radius_x * math.cos(angle)
        z = center_z + radius_z * math.sin(angle)
        tangent = Vector(
            (-radius_x * math.sin(angle), 0.0, radius_z * math.cos(angle))
        ).normalized()
        across = Vector((tangent.z, 0.0, -tangent.x))
        for column in range(columns):
            u = -1.0 + 2.0 * column / (columns - 1)
            x = center_x + across.x * 0.00042 * u * taper
            point_z = z + across.z * 0.00042 * u * taper
            surface_y = ray_surface_y_fixed(body, x, point_z, front=True)
            relief = 0.00048 * taper * max(0.0, 1.0 - u * u)
            vertices.append(Vector((x, surface_y - relief, point_z)))
    faces: list[tuple[int, ...]] = []
    for row in range(rows - 1):
        for column in range(columns - 1):
            first = row * columns + column
            faces.append((first, first + 1, first + 1 + columns, first + columns))
    return base.mesh_object(
        base.MODULE_PREFIX + "Clitoral_Hood_Mostly_Covering",
        vertices,
        faces,
        material,
        body,
    )


def create_module_restrained(
    body: bpy.types.Object,
    rig: bpy.types.Object,
) -> tuple[list[bpy.types.Object], dict[str, Any]]:
    """Build lower-relief external relationships without a diagram-like stack."""

    outer = body.data.materials[base.PATCH_SLOT]
    inner = base.make_material(
        "R22_Attempt05_Natural_Inner_Tissue",
        (0.39, 0.135, 0.120, 1.0),
        0.54,
        0.055,
    )
    vestibule = base.make_material(
        "R22_Attempt05_Subtle_Vestibular_Tissue",
        (0.30, 0.080, 0.082, 1.0),
        0.57,
        0.060,
    )
    recess = base.make_material(
        "R22_Attempt05_Opening_Shadow",
        (0.105, 0.018, 0.024, 1.0),
        0.64,
        0.035,
    )

    objects: list[bpy.types.Object] = []

    # Broad, shallow outer folds merge into the existing body material.  Their
    # inner edges meet closely enough to conceal most of the vestibule in a
    # neutral standing view.
    objects.append(
        base.ribbon(
            name=base.MODULE_PREFIX + "Left_Labium_Majus_Integrated",
            body=body,
            material=outer,
            z_top=0.8920,
            z_bottom=0.8468,
            center_x=lambda t: -0.00610 - 0.00055 * math.sin(math.pi * t),
            half_width=lambda t: 0.00470 - 0.00070 * t,
            height=lambda t: 0.00118 - 0.00024 * t,
            samples=42,
            cross_samples=10,
        )
    )
    objects.append(
        base.ribbon(
            name=base.MODULE_PREFIX + "Right_Labium_Majus_Integrated",
            body=body,
            material=outer,
            z_top=0.8911,
            z_bottom=0.8475,
            center_x=lambda t: 0.00585 + 0.00045 * math.sin(math.pi * t),
            half_width=lambda t: 0.00455 - 0.00062 * t,
            height=lambda t: 0.00110 - 0.00022 * t,
            samples=40,
            cross_samples=10,
        )
    )

    # A very shallow, narrow vestibular field prevents a dark exposed tube.
    objects.append(
        base.elliptical_cap(
            name=base.MODULE_PREFIX + "Vestibule_Subtle",
            body=body,
            material=vestibule,
            center_x=0.00005,
            center_z=0.8692,
            radius_x=0.00265,
            radius_z=0.0112,
            outward=0.00010,
            segments=56,
        )
    )

    # Inner folds are intentionally asymmetric and mostly covered by the
    # outer folds.  Relief is sub-millimetre at model scale.
    objects.append(
        base.ribbon(
            name=base.MODULE_PREFIX + "Left_Labium_Minus_Mostly_Covered",
            body=body,
            material=inner,
            z_top=0.8834,
            z_bottom=0.8538,
            center_x=lambda t: -0.00172 - 0.00020 * math.sin(math.pi * t),
            half_width=lambda t: 0.00092 - 0.00016 * t,
            height=lambda t: 0.00058 - 0.00012 * t,
            samples=34,
            cross_samples=7,
        )
    )
    objects.append(
        base.ribbon(
            name=base.MODULE_PREFIX + "Right_Labium_Minus_Mostly_Covered",
            body=body,
            material=inner,
            z_top=0.8821,
            z_bottom=0.8550,
            center_x=lambda t: 0.00158 + 0.00016 * math.sin(math.pi * t),
            half_width=lambda t: 0.00082 - 0.00013 * t,
            height=lambda t: 0.00050 - 0.00010 * t,
            samples=32,
            cross_samples=7,
        )
    )

    # Openings are restrained surface cues rather than protruding rims.  They
    # remain separate exact objects for later replacement with functional
    # internal modules; this visual attempt does not claim an internal canal.
    objects.append(
        base.elliptical_cap(
            name=base.MODULE_PREFIX + "Vaginal_Introitus_Subtle_Slit",
            body=body,
            material=recess,
            center_x=0.00010,
            center_z=0.8597,
            radius_x=0.00072,
            radius_z=0.00310,
            outward=0.00020,
            segments=56,
        )
    )
    objects.append(
        base.elliptical_cap(
            name=base.MODULE_PREFIX + "Urethral_Meatus_Subtle",
            body=body,
            material=vestibule,
            center_x=-0.00005,
            center_z=0.8742,
            radius_x=0.00022,
            radius_z=0.00018,
            outward=0.00016,
            segments=32,
        )
    )
    objects.append(small_partial_hood(body, inner))
    objects.append(
        base.elliptical_cap(
            name=base.MODULE_PREFIX + "Clitoral_Glans_Partially_Visible",
            body=body,
            material=inner,
            center_x=0.00008,
            center_z=0.88455,
            radius_x=0.00031,
            radius_z=0.00038,
            outward=0.00030,
            segments=36,
        )
    )
    objects.append(
        base.ribbon(
            name=base.MODULE_PREFIX + "Posterior_Fourchette_Subtle",
            body=body,
            material=outer,
            z_top=0.8534,
            z_bottom=0.8485,
            center_x=lambda _t: 0.0,
            half_width=lambda _t: 0.00245,
            height=lambda _t: 0.00034,
            samples=10,
            cross_samples=7,
        )
    )

    # The posterior feature is smaller and uses a body-toned rim.  It is not
    # visible from the protected front views and remains anatomically separate.
    objects.append(
        base.elliptical_cap(
            name=base.MODULE_PREFIX + "Anal_Opening_Subtle",
            body=body,
            material=recess,
            center_x=0.0,
            center_z=0.8420,
            radius_x=0.00118,
            radius_z=0.00092,
            outward=0.00020,
            front=False,
            segments=48,
        )
    )
    objects.append(
        base.ellipse_rim(
            name=base.MODULE_PREFIX + "Anal_External_Rim_Subtle",
            body=body,
            material=outer,
            center_x=0.0,
            center_z=0.8420,
            radius_x=0.00152,
            radius_z=0.00120,
            thickness=0.14,
            height=0.00030,
            front=False,
            segments=56,
        )
    )

    for obj in objects:
        add_subdivision(obj, 2 if "Opening" not in obj.name and "Meatus" not in obj.name else 1)

    bindings = {
        obj.name: bind_to_rig_preserving_world(obj, body, rig) for obj in objects
    }
    return objects, {
        "component_order_anterior_to_posterior": [
            "mostly_covered_clitoral_hood_and_partially_visible_glans",
            "subtle_external_urethral_meatus",
            "narrow_vaginal_introitus_surface_cue",
            "posterior_fourchette",
            "continuous_perineal_body_surface",
            "separate_subtle_anal_region",
        ],
        "component_count": len(objects),
        "objects": [obj.name for obj in objects],
        "bindings": bindings,
        "deliberate_normal_variation": "minor left/right fold asymmetry",
        "visual_corrections": [
            "skin-integrated low-relief outer folds",
            "inner folds reduced and mostly covered",
            "no complete diagram-like clitoral ring",
            "glans largely covered",
            "urethral cue reduced below one half millimetre radius",
            "vaginal opening represented as a narrow subtle slit",
            "posterior feature reduced and kept separate",
            "dark exposed tubular vestibule removed",
        ],
        "truth_boundary": (
            "external private visual candidate only; no internal canal, pelvic-floor, "
            "continence, reproductive, sensation, or physiological function is claimed"
        ),
    }


base.ray_surface_y = ray_surface_y_fixed
base.bind_to_rig = bind_to_rig_preserving_world
base.relax_rejected_center = previous.relax_rejected_center_v2
base.create_module = create_module_restrained


if __name__ == "__main__":
    output_dir = ROOT / "Avatar/private_owner_review/kira_r22_external_anatomy_attempt_05"
    evidence_dir = ROOT / (
        "RecoverySprint/continuation_20260802/kira_r22_external_anatomy/attempt_05"
    )
    output_blend = output_dir / (
        "KIRA_R22_BALD_PRIVATE_INACTIVE_EXTERNAL_ANATOMY_ATTEMPT05.blend"
    )
    raise SystemExit(
        run_attempt(
            base,
            root=ROOT,
            attempt_number=5,
            output_dir=output_dir,
            evidence_dir=evidence_dir,
            output_blend=output_blend,
            prior_attempt_truth={
                "attempt_01": "failed before save because the ray bound used the wrong coordinate scale",
                "attempt_02": "saved but the module transform was displaced by rig parenting",
                "attempt_03": "aligned and anatomically ordered but visually rejected as diagram-like",
                "attempt_04": "naturalized topology but remained too protruding, dark, open, and tube-like",
            },
            repair_summary=(
                "single bounded external visual correction: shallower body-matched outer folds, "
                "mostly covered inner structures, a small hood and partially visible glans, "
                "subtle urethral cue, narrow introital slit, and a smaller separate posterior feature"
            ),
        )
    )
