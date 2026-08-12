#!/usr/bin/env python3
"""Attempt 04: bounded naturalization of the R22 external-anatomy module."""

from __future__ import annotations

from collections import deque
import math
from pathlib import Path
import sys
from typing import Any

import bpy
from mathutils import Vector


ROOT = Path(r"C:\Users\robmc\Kira")
TOOLS = ROOT / "Tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import blender_author_kira_r22_external_anatomy_attempt01 as base  # noqa: E402
from blender_author_kira_r22_external_anatomy_attempt02 import ray_surface_y_fixed  # noqa: E402
from blender_author_kira_r22_external_anatomy_attempt03 import bind_to_rig_preserving_world  # noqa: E402
from blender_author_kira_r22_external_anatomy_runner import run_attempt  # noqa: E402


def relax_rejected_center_v2(body: bpy.types.Object, topology: dict[str, Any]) -> dict[str, Any]:
    mesh = body.data
    original = {index: mesh.vertices[index].co.copy() for index in topology["vertices"]}
    moved: set[int] = set()
    iterations = 72
    relaxation = 0.44
    for _ in range(iterations):
        previous = {index: mesh.vertices[index].co.copy() for index in topology["vertices"]}
        pending: dict[int, Vector] = {}
        for index in topology["vertices"]:
            ring = topology["distance"].get(index, 0)
            if ring <= 2:
                continue
            world = body.matrix_world @ previous[index]
            z_gate = base.smoothstep((world.z - 0.832) / 0.015) * base.smoothstep((0.913 - world.z) / 0.013)
            x_gate = base.smoothstep((0.042 - abs(world.x)) / 0.020)
            front_gate = base.smoothstep((0.065 - world.y) / 0.045)
            weight = z_gate * x_gate * front_gate
            if weight <= 1.0e-6:
                continue
            adjacent = topology["neighbors"][index]
            target = sum((previous[value] for value in adjacent), Vector()) / len(adjacent)
            pending[index] = previous[index].lerp(target, relaxation * weight)
        for index, value in pending.items():
            mesh.vertices[index].co = value
            moved.add(index)
        mesh.update()
    maximum = max(
        ((mesh.vertices[index].co - original[index]).length for index in moved),
        default=0.0,
    )
    seam_delta = max(
        ((mesh.vertices[index].co - original[index]).length for index in topology["seam"]),
        default=0.0,
    )
    return {
        "method": "bounded_weighted_laplacian_relaxation_of_rejected_insert_v2",
        "iterations": iterations,
        "relaxation": relaxation,
        "moved_vertex_count": len(moved),
        "maximum_body_local_movement": float(maximum),
        "seam_maximum_delta": float(seam_delta),
    }


def partial_hood(
    body: bpy.types.Object,
    material: bpy.types.Material,
) -> bpy.types.Object:
    segments = 32
    cross = 5
    vertices: list[Vector] = []
    center_z = 0.8878
    for row in range(segments):
        angle = math.radians(18.0 + (144.0 * row / (segments - 1)))
        taper = math.sin(math.pi * row / (segments - 1)) ** 0.5
        cx = 0.00325 * math.cos(angle)
        z = center_z + 0.00255 * math.sin(angle)
        tangent = Vector((-0.00325 * math.sin(angle), 0.0, 0.00255 * math.cos(angle))).normalized()
        across = Vector((tangent.z, 0.0, -tangent.x))
        for column in range(cross):
            u = -1.0 + 2.0 * column / (cross - 1)
            point_x = cx + across.x * 0.00072 * u * taper
            point_z = z + across.z * 0.00072 * u * taper
            surface_y = ray_surface_y_fixed(body, point_x, point_z, front=True)
            relief = 0.00135 * taper * max(0.0, 1.0 - u * u)
            vertices.append(Vector((point_x, surface_y - relief, point_z)))
    faces = []
    for row in range(segments - 1):
        for column in range(cross - 1):
            first = row * cross + column
            faces.append((first, first + 1, first + 1 + cross, first + cross))
    return base.mesh_object(base.MODULE_PREFIX + "Clitoral_Hood_Partial", vertices, faces, material, body)


def add_subdivision(obj: bpy.types.Object, level: int = 2) -> None:
    modifier = obj.modifiers.new("R22_TISSUE_SUBDIVISION", "SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = level
    modifier.render_levels = level


def create_module_natural(body: bpy.types.Object, rig: bpy.types.Object) -> tuple[list[bpy.types.Object], dict[str, Any]]:
    outer = body.data.materials[base.PATCH_SLOT]
    inner = base.make_material("R22_Natural_Inner_Vulvar_Tissue", (0.285, 0.070, 0.065, 1.0), 0.48, 0.07)
    vestibule = base.make_material("R22_Natural_Vestibular_Tissue", (0.205, 0.038, 0.042, 1.0), 0.43, 0.08)
    opening = base.make_material("R22_Natural_Opening_Recess", (0.045, 0.006, 0.008, 1.0), 0.62, 0.02)
    objects: list[bpy.types.Object] = []
    objects.append(base.ribbon(
        name=base.MODULE_PREFIX + "Left_Labium_Majus", body=body, material=outer,
        z_top=0.891, z_bottom=0.847,
        center_x=lambda t: -0.0087 - 0.0012 * math.sin(math.pi * t),
        half_width=lambda t: 0.0058 - 0.0010 * t,
        height=lambda t: 0.00255 - 0.00045 * t,
        samples=36, cross_samples=9,
    ))
    objects.append(base.ribbon(
        name=base.MODULE_PREFIX + "Right_Labium_Majus", body=body, material=outer,
        z_top=0.890, z_bottom=0.848,
        center_x=lambda t: 0.0084 + 0.0010 * math.sin(math.pi * t),
        half_width=lambda t: 0.0055 - 0.0009 * t,
        height=lambda t: 0.0024 - 0.0004 * t,
        samples=36, cross_samples=9,
    ))
    objects.append(base.elliptical_cap(
        name=base.MODULE_PREFIX + "Vestibule", body=body, material=vestibule,
        center_x=0.0, center_z=0.8695, radius_x=0.0046, radius_z=0.0138,
        outward=0.00028,
    ))
    objects.append(base.ribbon(
        name=base.MODULE_PREFIX + "Left_Labium_Minus", body=body, material=inner,
        z_top=0.887, z_bottom=0.852,
        center_x=lambda t: -0.00315 - 0.00042 * math.sin(math.pi * t),
        half_width=lambda t: 0.00225 - 0.00045 * t,
        height=lambda t: 0.00170 - 0.00028 * t,
        samples=34, cross_samples=8,
    ))
    objects.append(base.ribbon(
        name=base.MODULE_PREFIX + "Right_Labium_Minus", body=body, material=inner,
        z_top=0.8855, z_bottom=0.8535,
        center_x=lambda t: 0.00295 + 0.00032 * math.sin(math.pi * t),
        half_width=lambda t: 0.00205 - 0.00040 * t,
        height=lambda t: 0.00155 - 0.00025 * t,
        samples=32, cross_samples=8,
    ))
    objects.append(base.elliptical_cap(
        name=base.MODULE_PREFIX + "Vaginal_Introitus_Cap", body=body, material=opening,
        center_x=0.00015, center_z=0.8602, radius_x=0.00245, radius_z=0.00455,
        outward=0.00068,
    ))
    objects.append(base.ellipse_rim(
        name=base.MODULE_PREFIX + "Vaginal_Introitus_Rim", body=body, material=inner,
        center_x=0.00015, center_z=0.8602, radius_x=0.00295, radius_z=0.00515,
        thickness=0.16, height=0.00115,
    ))
    objects.append(base.elliptical_cap(
        name=base.MODULE_PREFIX + "Urethral_Meatus_Cap", body=body, material=opening,
        center_x=-0.0001, center_z=0.8752, radius_x=0.00078, radius_z=0.00060,
        outward=0.00062,
    ))
    objects.append(base.ellipse_rim(
        name=base.MODULE_PREFIX + "Urethral_Meatus_Rim", body=body, material=inner,
        center_x=-0.0001, center_z=0.8752, radius_x=0.00102, radius_z=0.00082,
        thickness=0.20, height=0.00072,
    ))
    objects.append(partial_hood(body, inner))
    objects.append(base.elliptical_cap(
        name=base.MODULE_PREFIX + "Clitoral_Glans", body=body, material=inner,
        center_x=0.00015, center_z=0.8860, radius_x=0.00082, radius_z=0.0010,
        outward=0.0010,
    ))
    objects.append(base.ribbon(
        name=base.MODULE_PREFIX + "Posterior_Fourchette", body=body, material=outer,
        z_top=0.8520, z_bottom=0.8470,
        center_x=lambda _t: 0.0,
        half_width=lambda _t: 0.0041,
        height=lambda _t: 0.00085,
        samples=10, cross_samples=8,
    ))
    objects.append(base.elliptical_cap(
        name=base.MODULE_PREFIX + "Anal_Canal_External_Cap", body=body, material=opening,
        center_x=0.0, center_z=0.8420, radius_x=0.00325, radius_z=0.0027,
        outward=0.00058, front=False,
    ))
    objects.append(base.ellipse_rim(
        name=base.MODULE_PREFIX + "Anal_Sphincter_External_Rim", body=body, material=outer,
        center_x=0.0, center_z=0.8420, radius_x=0.0038, radius_z=0.00325,
        thickness=0.18, height=0.0009, front=False,
    ))
    for obj in objects:
        add_subdivision(obj, 2 if "Cap" not in obj.name else 1)
    bindings = {obj.name: bind_to_rig_preserving_world(obj, body, rig) for obj in objects}
    return objects, {
        "component_order_anterior_to_posterior": [
            "clitoral_hood_and_glans",
            "external_urethral_meatus",
            "vaginal_introitus",
            "posterior_fourchette",
            "continuous_perineum",
            "separate_anal_region",
        ],
        "component_count": len(objects),
        "objects": [obj.name for obj in objects],
        "bindings": bindings,
        "deliberate_normal_variation": "minor left/right fold asymmetry",
        "naturalization_changes": [
            "outer folds reuse exact body pelvic material",
            "reduced relief and fold width",
            "subtle asymmetric fold lengths",
            "smaller urethral and vaginal external openings",
            "partial clitoral hood rather than complete ellipse",
            "subdivision surface on soft-tissue components",
        ],
    }


base.ray_surface_y = ray_surface_y_fixed
base.bind_to_rig = bind_to_rig_preserving_world
base.relax_rejected_center = relax_rejected_center_v2
base.create_module = create_module_natural


if __name__ == "__main__":
    output_dir = ROOT / "Avatar/private_owner_review/kira_r22_external_anatomy_attempt_04"
    evidence_dir = ROOT / (
        "RecoverySprint/continuation_20260802/kira_r22_external_anatomy/attempt_04"
    )
    output_blend = output_dir / "KIRA_R22_BALD_PRIVATE_INACTIVE_EXTERNAL_ANATOMY_ATTEMPT04.blend"
    raise SystemExit(run_attempt(
        base,
        root=ROOT,
        attempt_number=4,
        output_dir=output_dir,
        evidence_dir=evidence_dir,
        output_blend=output_blend,
        prior_attempt_truth={
            "attempt_01": "failed before save because ray bound used the wrong coordinate scale",
            "attempt_02": "saved but module transform was displaced by rig parenting",
            "attempt_03": "aligned and anatomically ordered but visually rejected as diagram-like",
        },
        repair_summary=(
            "single bounded naturalization pass: body-matched outer tissue, smaller lower-relief "
            "folds/openings, partial hood, subtle asymmetry, soft subdivision, and stronger smoothing "
            "strictly inside the rejected pelvic mask"
        ),
    ))
