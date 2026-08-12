"""Second and final bounded Kira R21 eyebrow-only visual repair.

Attempt 01 proved exact component isolation and skin attachment, but its
ordered strand layout looked too evenly combed. This append-only worker reuses
the same hash-locked source and accepted anchors while creating a softer,
irregular two-dimensional field of thinner overlapping hairs.
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import blender_author_kira_r21_brow_only_attempt01 as base  # noqa: E402


base.OUTPUT_DIR = base.PROJECT / "Avatar" / "private_owner_review" / "kira_r21_brow_only_correction_attempt_02"
base.OUTPUT_BLEND = base.OUTPUT_DIR / "KIRA_R21_BALD_PRIVATE_INACTIVE_BROW_ATTEMPT02_REVIEW.blend"
base.EVIDENCE_DIR = base.PROJECT / "RecoverySprint" / "continuation_20260802" / "kira_r21_brow_only_correction" / "author_attempt_02"
base.EVIDENCE_PATH = base.EVIDENCE_DIR / "BUILD_EVIDENCE.json"
base.README_PATH = base.OUTPUT_DIR / "OWNER_REVIEW_README.md"
base.NEW_BROW_PREFIX = "Kira_R21_Natural_Overlapping_Brow_Attempt02"
base.CANDIDATE_ID = "kira_r21_brow_only_correction_attempt_02"
base.STRANDS_PER_SIDE = 336
base.SAMPLES_PER_STRAND = 5
base.SURFACE_CLEARANCE_LOCAL = 0.026
base.RNG_SEED = 21023367
base.__file__ = __file__


def create_side_brow_attempt02(
    *,
    body: bpy.types.Object,
    rig: bpy.types.Object,
    tree: BVHTree,
    y_min: float,
    y_max: float,
    anchor: dict[str, float],
    sign: float,
    label: str,
    materials: list[bpy.types.Material],
    rng: random.Random,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    face_materials: list[int] = []
    strand_vertex_ranges: list[tuple[list[int], float]] = []
    inner = anchor["inner_abs_x"]
    outer = anchor["outer_abs_x"]
    median_z = anchor["median_z"]
    span = outer - inner
    if not 3.5 <= span <= 6.5:
        raise base.BrowAuthoringError(f"implausible inherited brow span for {label}: {span}")

    accepted = 0
    candidate_index = 0
    while accepted < base.STRANDS_PER_SIDE:
        # Two irrational progressions make an irregular but deterministic
        # two-dimensional root field without the ordered-comb alignment from
        # Attempt 01.
        u = (candidate_index * 0.6180339887498949 + (0.071 if sign < 0.0 else 0.391)) % 1.0
        q_raw = (candidate_index * 0.7548776662466927 + (0.283 if sign < 0.0 else 0.617)) % 1.0
        candidate_index += 1
        edge_density = min(1.0, u / 0.105, (1.0 - u) / 0.145)
        if rng.random() > 0.34 + 0.66 * max(0.0, edge_density):
            continue
        u = min(0.998, max(0.002, u + (rng.random() - 0.5) * 0.010))
        q = q_raw - 0.5
        q = math.copysign((abs(q) * 2.0) ** 1.32, q) * 0.5

        x_root = sign * (inner + span * u)
        arch = math.sin(math.pi * (u ** 0.92))
        center_z = median_z - 0.12 + 0.55 * arch - 0.07 * u
        half_band = max(0.11, 0.28 + 0.15 * (arch ** 0.75) - 0.16 * u)
        z_root = center_z + q * 2.0 * half_band + (rng.random() - 0.5) * 0.060

        flow_degrees = 51.0 - 56.0 * u + (rng.random() - 0.5) * 21.0
        flow = math.radians(flow_degrees)
        center_density = 0.74 + 0.26 * math.sin(math.pi * u)
        edge_length = 0.58 + 0.42 * min(1.0, u / 0.10, (1.0 - u) / 0.15)
        length = (0.29 + 0.18 * rng.random()) * center_density * edge_length
        dx = sign * math.cos(flow) * length
        dz = math.sin(flow) * length
        curvature = (rng.random() - 0.36) * (0.085 + 0.025 * arch)
        half_width = (0.0062 + 0.0033 * rng.random()) * (0.82 + 0.18 * arch)
        clearance = base.SURFACE_CLEARANCE_LOCAL + (rng.random() - 0.5) * 0.0035

        centerline = []
        for sample in range(base.SAMPLES_PER_STRAND):
            t = sample / (base.SAMPLES_PER_STRAND - 1)
            ease = t * (0.90 + 0.10 * t)
            lateral_wander = sign * (rng.random() - 0.5) * 0.007 * math.sin(math.pi * t)
            centerline.append(
                Vector(
                    (
                        x_root + dx * ease + lateral_wander,
                        0.0,
                        z_root + dz * ease + curvature * math.sin(math.pi * t),
                    )
                )
            )
        indices: list[int] = []
        for sample, center in enumerate(centerline):
            if sample == 0:
                tangent = centerline[1] - centerline[0]
            elif sample == len(centerline) - 1:
                tangent = centerline[-1] - centerline[-2]
            else:
                tangent = centerline[sample + 1] - centerline[sample - 1]
            tangent.y = 0.0
            tangent.normalize()
            cross = Vector((-tangent.z, 0.0, tangent.x))
            taper = (0.78, 1.00, 0.76, 0.38, 0.035)[sample]
            width = half_width * taper
            for point in (center - cross * width, center + cross * width):
                projected = base.projected_front_point(tree, y_min, y_max, point.x, point.z, clearance)
                indices.append(len(vertices))
                vertices.append(tuple(projected))
            if sample:
                current = len(vertices) - 2
                previous = current - 2
                faces.append((previous, current, current + 1, previous + 1))
                shade_offset = 2 if u < 0.08 or u > 0.88 else 0
                face_materials.append((accepted * 5 + shade_offset + (1 if sign > 0 else 0)) % len(materials))
        strand_vertex_ranges.append((indices, u))
        accepted += 1

    mesh = bpy.data.meshes.new(f"{base.NEW_BROW_PREFIX}_{label}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    for material in materials:
        mesh.materials.append(material)
    for polygon, material_index in zip(mesh.polygons, face_materials):
        polygon.material_index = int(material_index)
        polygon.use_smooth = True

    obj = bpy.data.objects.new(f"{base.NEW_BROW_PREFIX}_{label}", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = body.matrix_world.copy()
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted()
    obj.matrix_world = world

    if sign < 0.0:
        bone_names = ("rBrowInner_0119", "rBrowMid_0120", "rBrowOuter_0122")
    else:
        bone_names = ("lBrowInner_0123", "lBrowMid_0124", "lBrowOuter_0125")
    for bone_name in bone_names:
        if rig.pose.bones.get(bone_name) is None:
            raise base.BrowAuthoringError(f"native brow expression bone missing: {bone_name}")
    groups = [obj.vertex_groups.new(name=bone_name) for bone_name in bone_names]
    for indices, u in strand_vertex_ranges:
        for group, weight in zip(groups, base.gaussian_weights(u)):
            if weight > 1.0e-6:
                group.add(indices, float(weight), "REPLACE")
    modifier = obj.modifiers.new("R21_Native_Brow_Expression_Attachment", "ARMATURE")
    modifier.object = rig
    obj["candidate_id"] = base.CANDIDATE_ID
    obj["component_role"] = "eyebrow"
    obj["inactive_candidate"] = True
    obj["private_owner_review_only"] = True
    obj["runtime_activation_allowed"] = False
    obj["scalp_hair"] = False
    obj["strand_count"] = base.STRANDS_PER_SIDE
    obj["strand_style"] = "irregular_overlapping_curved_tapered_skin_conforming_mesh_ribbons"
    return obj, {
        "object": obj.name,
        "side": label,
        "strand_count": base.STRANDS_PER_SIDE,
        "samples_per_strand": base.SAMPLES_PER_STRAND,
        "vertex_count": len(vertices),
        "polygon_count": len(faces),
        "geometry_uv_sha256": base.mesh_geometry_digest(obj),
        "positive_weight_assignment_sha256": base.weight_digest(obj),
        "native_expression_bones": list(bone_names),
        "source_anchor": anchor,
        "skin_projection_clearance_local_units": base.SURFACE_CLEARANCE_LOCAL,
        "root_distribution": "deterministic_two_dimensional_low_discrepancy_with_bounded_jitter",
        "edge_density_taper": True,
        "flow_variation_degrees": 21.0,
    }


base.create_side_brow = create_side_brow_attempt02


if __name__ == "__main__":
    base.main()
