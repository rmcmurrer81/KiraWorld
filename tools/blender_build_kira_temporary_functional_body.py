#!/usr/bin/env python3
"""Author one private Kira Hart temporary functional-body candidate.

This worker consumes a validated rapid-body request and derives a new surface
from the enrolled 3ec62 adult-female cage.  It never reads a Robert-specific
reference, never changes a runtime selector, and never treats the output as an
approved or active body.

The build is deliberately useful but bounded:

* exact compatible duplicate seams are welded;
* a reversible natural-athletic proportion key and an integrated adult
  external-form key are authored on the body mesh;
* the existing 79-joint skin is retained and exercised in four poses;
* light regional skin, brown review eyes, a removable straight black review
  groom, and ordinary nail plates are authored as separate components;
* neutral, close-review, and deformation renders are retained locally; and
* a private GLB and Blender review scene are exported.

Hair dynamics, cloth simulation, long-duration locomotion, expressive face
animation, and owner acceptance remain later gates.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
import statistics
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helper module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOLS = Path(__file__).resolve().parent
r5 = _load_module(
    "kira_temporary_functional_r5_helpers",
    TOOLS / "blender_build_kira_provisional_body_r5.py",
)
r6 = _load_module(
    "kira_temporary_functional_r6_helpers",
    TOOLS / "blender_build_kira_provisional_body_r6.py",
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def gaussian(value: float, center: float, sigma: float) -> float:
    return math.exp(-0.5 * ((value - center) / sigma) ** 2)


def group_index(body: bpy.types.Object, name: str) -> int:
    group = body.vertex_groups.get(name)
    if group is None:
        raise ValueError(f"missing required body group {name}")
    return int(group.index)


def vertex_weight(vertex: bpy.types.MeshVertex, indices: set[int]) -> float:
    return max(
        (float(item.weight) for item in vertex.groups if int(item.group) in indices),
        default=0.0,
    )


def position_hash(points: list[Vector], indices: list[int]) -> str:
    digest = hashlib.sha256()
    for index in indices:
        point = points[index]
        digest.update(
            struct.pack(
                "<Ifff",
                index,
                float(point.x),
                float(point.y),
                float(point.z),
            )
        )
    return digest.hexdigest()


def top_ancestor(obj: bpy.types.Object) -> bpy.types.Object:
    current = obj
    while current.parent is not None:
        current = current.parent
    return current


def normalize_height(
    body: bpy.types.Object,
    armature: bpy.types.Object,
    target_height_m: float,
) -> dict[str, object]:
    body_root = top_ancestor(body)
    armature_root = top_ancestor(armature)
    if body_root is not armature_root:
        raise ValueError("body and armature do not share one imported root")
    low_before, high_before = r5.bounds_for_body(body, evaluated=True)
    height_before = float(high_before.z - low_before.z)
    if height_before <= 0.1:
        raise ValueError("source body height is invalid")
    scale_factor = target_height_m / height_before
    body_root.scale = tuple(float(value) * scale_factor for value in body_root.scale)
    bpy.context.view_layer.update()
    low_scaled, high_scaled = r5.bounds_for_body(body, evaluated=True)
    body_root.location.z += -float(low_scaled.z)
    bpy.context.view_layer.update()
    low_after, high_after = r5.bounds_for_body(body, evaluated=True)
    height_after = float(high_after.z - low_after.z)
    if abs(height_after - target_height_m) > 0.002:
        raise ValueError(
            f"target height missed: expected {target_height_m:.4f}, got {height_after:.4f}"
        )
    return {
        "source_height_m": round(height_before, 9),
        "target_height_m": round(target_height_m, 9),
        "uniform_root_scale_factor": round(scale_factor, 9),
        "result_height_m": round(height_after, 9),
        "floor_z_m": round(float(low_after.z), 9),
        "top_z_m": round(float(high_after.z), 9),
        "shared_import_root": body_root.name,
    }


def author_parametric_surface(
    body: bpy.types.Object,
    parameters: dict[str, object],
) -> dict[str, object]:
    """Add bounded proportions and a refined external adult-form key.

    The source coordinates are the exact enrolled 3ec62 cage.  All form
    changes stay on that one body mesh.  No donor surface or private-person
    coordinate is read.
    """

    if body.data.shape_keys is None:
        raise ValueError("R6 external-form key must be authored first")
    basis = body.data.shape_keys.key_blocks.get("Basis")
    if basis is None:
        raise ValueError("shape-key basis is missing")
    key = body.shape_key_add(
        name="Kira_Hart_Natural_Athletic_Temporary_Functional",
        from_mix=False,
    )
    key.value = 1.0
    key.slider_min = 0.0
    key.slider_max = 1.0

    hips = {group_index(body, r5.HIPS)}
    torso = {group_index(body, name) for name in (r5.SPINE, r5.SPINE1, r5.SPINE2)}
    thighs = {
        group_index(body, r5.LEFT_THIGH),
        group_index(body, r5.RIGHT_THIGH),
    }
    upper_arms = {
        group_index(body, r5.LEFT_ARM),
        group_index(body, r5.RIGHT_ARM),
    }

    waist_amount = float(parameters.get("waist_abdomen", -0.04))
    hip_amount = float(parameters.get("hips_pelvis", 0.02))
    leg_amount = float(parameters.get("legs", 0.02))
    muscularity = float(parameters.get("muscularity", 0.18))
    if not (-0.12 <= waist_amount <= 0.08):
        raise ValueError("waist parameter is outside the bounded rapid-body lane")
    if not (-0.08 <= hip_amount <= 0.10):
        raise ValueError("hip parameter is outside the bounded rapid-body lane")
    if not (-0.08 <= leg_amount <= 0.10):
        raise ValueError("leg parameter is outside the bounded rapid-body lane")
    if not (0.0 <= muscularity <= 0.45):
        raise ValueError("muscularity is outside the natural rapid-body lane")

    source_points = [basis.data[index].co.copy() for index in range(len(body.data.vertices))]
    protected_head = [
        index for index, point in enumerate(source_points) if float(point.z) >= 6.0
    ]
    head_hash_before = position_hash(source_points, protected_head)
    moved = 0
    displacement_sum = 0.0
    maximum_displacement = 0.0
    region_counts: collections.Counter[str] = collections.Counter()
    region_max: collections.defaultdict[str, float] = collections.defaultdict(float)

    for vertex in body.data.vertices:
        original = basis.data[vertex.index].co.copy()
        target = original.copy()
        hip_weight = vertex_weight(vertex, hips)
        torso_weight = vertex_weight(vertex, torso)
        thigh_weight = vertex_weight(vertex, thighs)
        arm_weight = vertex_weight(vertex, upper_arms)

        # Request-driven but deliberately bounded body fitting.  These bands
        # are smooth and weight-gated; they do not globally scale limbs or
        # overwrite the exact source head/hand/foot topology.
        waist_band = gaussian(float(original.z), 4.72, 0.34)
        pelvis_band = gaussian(float(original.z), 4.08, 0.36)
        thigh_band = gaussian(float(original.z), 3.25, 0.58)
        upper_arm_band = gaussian(float(original.z), 5.05, 0.72)
        torso_scale_x = 1.0 + waist_amount * 0.72 * waist_band * torso_weight
        torso_scale_y = 1.0 + waist_amount * 0.34 * waist_band * torso_weight
        target.x *= torso_scale_x
        target.y *= torso_scale_y
        if torso_weight > 1e-5 and waist_band > 0.03:
            region_counts["request_waist_abdomen"] += 1

        target.x *= 1.0 + hip_amount * pelvis_band * hip_weight
        target.y *= 1.0 + hip_amount * 0.60 * pelvis_band * hip_weight
        if hip_weight > 1e-5 and pelvis_band > 0.03:
            region_counts["request_hips_pelvis"] += 1

        # Natural athletic is intentionally modest: slightly firmer thigh and
        # upper-arm depth, without a bodybuilder silhouette.
        target.y *= 1.0 + leg_amount * 0.45 * thigh_band * thigh_weight
        target.y *= 1.0 + muscularity * 0.010 * upper_arm_band * arm_weight
        if thigh_weight > 1e-5 and thigh_band > 0.03:
            region_counts["request_legs"] += 1
        if arm_weight > 1e-5 and upper_arm_band > 0.03:
            region_counts["request_natural_athletic_arms"] += 1

        # Refine the integrated external adult-female surface already added by
        # the R6 helper.  Every cue is a displacement of the same skinned body
        # surface; there is no floating anatomical insert.
        if (
            float(original.y) <= -0.10
            and 3.30 <= float(original.z) <= 4.03
            and abs(float(original.x)) <= 0.29
        ):
            front_gate = clamp((-0.10 - float(original.y)) / 0.27)
            x_value = float(original.x)
            z_value = float(original.z)
            mons = gaussian(x_value, 0.0, 0.17) * gaussian(z_value, 3.88, 0.16)
            outer_left = gaussian(x_value, 0.058, 0.035) * gaussian(z_value, 3.57, 0.16)
            outer_right = gaussian(x_value, -0.058, 0.035) * gaussian(z_value, 3.57, 0.16)
            inner_left = gaussian(x_value, 0.024, 0.018) * gaussian(z_value, 3.58, 0.13)
            inner_right = gaussian(x_value, -0.024, 0.018) * gaussian(z_value, 3.58, 0.13)
            vestibule = gaussian(x_value, 0.0, 0.016) * gaussian(z_value, 3.54, 0.11)
            hood = gaussian(x_value, 0.0, 0.030) * gaussian(z_value, 3.72, 0.045)
            perineal = gaussian(x_value, 0.0, 0.065) * gaussian(z_value, 3.36, 0.055)
            delta_y = (
                -0.0045 * mons
                -0.0075 * (outer_left + outer_right)
                -0.0030 * (inner_left + inner_right)
                +0.0050 * vestibule
                -0.0034 * hood
                +0.0020 * perineal
            ) * front_gate
            target.y += delta_y
            if abs(delta_y) > 1e-7:
                for name, field in (
                    ("mons_transition", mons),
                    ("outer_labial_transition", outer_left + outer_right),
                    ("inner_labial_transition", inner_left + inner_right),
                    ("vestibular_cleft", vestibule),
                    ("clitoral_hood_transition", hood),
                    ("perineal_transition", perineal),
                ):
                    if field > 0.02:
                        region_counts[name] += 1
                        region_max[name] = max(region_max[name], abs(delta_y))

        # The enrolled generic face/head is outside this body-proportion pass.
        # Some high head vertices retain tiny spine weights in the source, so
        # the coordinate boundary—not skin weights—is the final guard.
        if float(original.z) >= 6.0:
            target = original.copy()

        displacement = (target - original).length
        if displacement > 1e-9:
            moved += 1
            displacement_sum += displacement
            maximum_displacement = max(maximum_displacement, displacement)
        key.data[vertex.index].co = target

    target_points = [key.data[index].co.copy() for index in range(len(body.data.vertices))]
    head_hash_after = position_hash(target_points, protected_head)
    if head_hash_after != head_hash_before:
        raise ValueError("rapid body proportions changed the protected generic head")

    required_external_regions = (
        "mons_transition",
        "outer_labial_transition",
        "inner_labial_transition",
        "vestibular_cleft",
        "clitoral_hood_transition",
        "perineal_transition",
    )
    region_gate = all(region_counts[name] > 0 for name in required_external_regions)
    world_scale = sum(abs(float(body.matrix_world[index][index])) for index in range(3)) / 3.0
    return {
        "shape_key": key.name,
        "default_value": 1.0,
        "reversible_to_enrolled_basis": True,
        "request_parameters": {
            "build_preset": parameters.get("build_preset"),
            "muscularity": muscularity,
            "waist_abdomen": waist_amount,
            "hips_pelvis": hip_amount,
            "legs": leg_amount,
        },
        "moved_vertex_count": moved,
        "mean_local_displacement": round(displacement_sum / max(moved, 1), 9),
        "maximum_local_displacement": round(maximum_displacement, 9),
        "mean_world_displacement_m": round(
            displacement_sum / max(moved, 1) * world_scale,
            9,
        ),
        "maximum_world_displacement_m": round(maximum_displacement * world_scale, 9),
        "region_vertex_visits": dict(region_counts),
        "region_maximum_local_displacement": {
            name: round(value, 9) for name, value in region_max.items()
        },
        "integrated_external_adult_form": {
            "authored_on_primary_body_surface": True,
            "separate_or_floating_anatomy_mesh_created": False,
            "required_named_regions": list(required_external_regions),
            "all_named_regions_received_surface_displacement": region_gate,
            "visual_owner_review_required": True,
            "functional_soft_tissue_behavior_proven": False,
            "internal_organ_model_claimed": False,
        },
        "protected_generic_head": {
            "vertex_count": len(protected_head),
            "position_sha256_before": head_hash_before,
            "position_sha256_after": head_hash_after,
            "exactly_preserved": head_hash_before == head_hash_after,
        },
        "private_person_reference_coordinates_used": False,
        "identifiable_person_likeness_claimed": False,
    }


def author_light_skin_material(output_dir: Path) -> tuple[bpy.types.Material, dict[str, object]]:
    import numpy as np

    texture_dir = output_dir / "textures"
    texture_dir.mkdir(parents=True, exist_ok=True)
    size = 512
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    u = xx / float(size - 1)
    v = yy / float(size - 1)
    grain = (
        0.52 * np.sin(u * 43.0 + v * 19.0)
        + 0.31 * np.sin(u * 97.0 - v * 61.0)
        + 0.17 * np.sin(u * 211.0 + v * 179.0)
    )
    base = np.array([230.0, 192.0, 169.0], dtype=np.float32) / 255.0
    variation = 0.014 * grain + 0.006 * np.sin(v * math.tau * 2.0)
    albedo = np.zeros((size, size, 4), dtype=np.float32)
    albedo[..., 0] = np.clip(base[0] + variation, 0.0, 1.0)
    albedo[..., 1] = np.clip(base[1] + variation * 0.82, 0.0, 1.0)
    albedo[..., 2] = np.clip(base[2] + variation * 0.66, 0.0, 1.0)
    albedo[..., 3] = 1.0
    rough_value = np.clip(0.51 + 0.035 * grain, 0.42, 0.66)
    roughness = np.stack(
        (rough_value, rough_value, rough_value, np.ones_like(rough_value)),
        axis=-1,
    ).astype(np.float32)
    grad_y, grad_x = np.gradient(0.35 * grain)
    nx = -grad_x * 0.13
    ny = -grad_y * 0.13
    nz = np.ones_like(nx)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.stack(
        (
            nx / length * 0.5 + 0.5,
            ny / length * 0.5 + 0.5,
            nz / length * 0.5 + 0.5,
            np.ones_like(nx),
        ),
        axis=-1,
    ).astype(np.float32)
    paths = {
        "albedo": texture_dir / "kira_hart_light_skin_albedo.png",
        "roughness": texture_dir / "kira_hart_light_skin_roughness.png",
        "normal": texture_dir / "kira_hart_light_skin_normal.png",
    }
    images = {
        "albedo": r5.save_texture(
            paths["albedo"],
            "Kira_Hart_Light_Skin_Albedo",
            albedo,
            colorspace="sRGB",
        ),
        "roughness": r5.save_texture(
            paths["roughness"],
            "Kira_Hart_Light_Skin_Roughness",
            roughness,
            colorspace="Non-Color",
        ),
        "normal": r5.save_texture(
            paths["normal"],
            "Kira_Hart_Light_Skin_Normal",
            normal,
            colorspace="Non-Color",
        ),
    }
    material = bpy.data.materials.new("Kira_Hart_Light_Natural_Skin")
    material.use_nodes = True
    material.diffuse_color = (0.7913, 0.5271, 0.3971, 1.0)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (620, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    bsdf.inputs["Roughness"].default_value = 0.51
    bsdf.inputs["Metallic"].default_value = 0.0
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.41
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.30
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.055
    albedo_node = nodes.new("ShaderNodeTexImage")
    albedo_node.image = images["albedo"]
    albedo_node.location = (-380, 150)
    rough_node = nodes.new("ShaderNodeTexImage")
    rough_node.image = images["roughness"]
    rough_node.location = (-380, -30)
    normal_node = nodes.new("ShaderNodeTexImage")
    normal_node.image = images["normal"]
    normal_node.location = (-380, -220)
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = 0.07
    normal_map.location = (0, -210)
    links.new(albedo_node.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(rough_node.outputs["Color"], bsdf.inputs["Roughness"])
    links.new(normal_node.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material, {
        "template_id": "caucasian_light_neutral_adult",
        "template_hex": "#e6c0a9",
        "workflow": "deterministic UV albedo/roughness/normal plus separate subtle regional materials",
        "textures": {
            name: {
                "path": str(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for name, path in paths.items()
        },
        "texture_resolution": [size, size],
        "subsurface_weight": 0.055,
    }


def add_regional_body_materials(
    body: bpy.types.Object,
    skin: bpy.types.Material,
) -> dict[str, object]:
    lip = r5.make_material("Kira_Hart_Subtle_Lip", (0.54, 0.22, 0.19, 1.0), 0.46)
    areola = r5.make_material(
        "Kira_Hart_Subtle_Areola",
        (0.49, 0.255, 0.215, 1.0),
        0.54,
    )
    intimate = r5.make_material(
        "Kira_Hart_Natural_Adult_Regional_Skin",
        (0.56, 0.285, 0.25, 1.0),
        0.56,
    )
    body.data.materials.clear()
    for material in (skin, lip, areola, intimate):
        body.data.materials.append(material)
    counts: collections.Counter[str] = collections.Counter()
    for polygon in body.data.polygons:
        center = polygon.center
        polygon.use_smooth = True
        material_index = 0
        if (
            6.46 <= float(center.z) <= 6.61
            and abs(float(center.x)) <= 0.16
            and float(center.y) <= -0.15
        ):
            material_index = 1
            counts["lips"] += 1
        if (
            5.28 <= float(center.z) <= 5.52
            and min(
                abs(float(center.x) - 0.31),
                abs(float(center.x) + 0.31),
            )
            <= 0.075
            and float(center.y) <= -0.27
        ):
            material_index = 2
            counts["areolae"] += 1
        if (
            3.30 <= float(center.z) <= 3.83
            and abs(float(center.x)) <= 0.13
            and float(center.y) <= -0.08
        ):
            material_index = 3
            counts["adult_external_region"] += 1
        polygon.material_index = material_index
    return {
        "material_slots": [material.name for material in body.data.materials],
        "regional_polygon_counts": dict(counts),
        "single_flat_body_color_avoided": all(
            counts[name] > 0 for name in ("lips", "areolae", "adult_external_region")
        ),
    }


def make_simple_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float,
    metallic: float = 0.0,
) -> bpy.types.Material:
    material = r5.make_material(name, color, roughness)
    bsdf = material.node_tree.nodes.get("Principled BSDF") if material.use_nodes else None
    if bsdf:
        bsdf.inputs["Metallic"].default_value = metallic
    return material


def parent_to_bone(
    obj: bpy.types.Object,
    armature: bpy.types.Object,
    bone_name: str,
) -> None:
    if bone_name not in armature.data.bones:
        raise ValueError(f"cannot parent {obj.name}; missing bone {bone_name}")
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = world


def make_eye_component(
    name: str,
    location: Vector,
    scale: tuple[float, float, float],
    material: bpy.types.Material,
    armature: bpy.types.Object,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=20,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj["private_review_component"] = True
    obj["runtime_approved"] = False
    parent_to_bone(obj, armature, r5.HEAD)
    return obj


def add_brown_review_eyes(
    body: bpy.types.Object,
    armature: bpy.types.Object,
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    low, high = r5.bounds_for_body(body, evaluated=True)
    height = float(high.z - low.z)
    center_x = float((low.x + high.x) * 0.5)
    center_y = float((low.y + high.y) * 0.5)
    eye_z = float(low.z + height * 0.935)
    eye_x = height * 0.0190
    eye_y = center_y - height * 0.0336
    sclera = make_simple_material(
        "Kira_Hart_Eye_Sclera",
        (0.89, 0.88, 0.83, 1.0),
        0.28,
    )
    iris = make_simple_material(
        "Kira_Hart_Natural_Brown_Iris",
        (0.19, 0.070, 0.026, 1.0),
        0.34,
    )
    pupil = make_simple_material(
        "Kira_Hart_Eye_Pupil",
        (0.005, 0.004, 0.003, 1.0),
        0.25,
    )
    catchlight = make_simple_material(
        "Kira_Hart_Eye_Catchlight",
        (0.95, 0.97, 1.0, 1.0),
        0.10,
    )
    objects: list[bpy.types.Object] = []
    centers: dict[str, list[float]] = {}
    for side, sign in (("Left", 1.0), ("Right", -1.0)):
        center = Vector((center_x + sign * eye_x, eye_y, eye_z))
        centers[side.lower()] = r5.vector_list(center)
        objects.append(
            make_eye_component(
                f"Kira_Hart_{side}_Sclera",
                center,
                (height * 0.0107, height * 0.0042, height * 0.0062),
                sclera,
                armature,
            )
        )
        iris_center = center + Vector((0.0, -height * 0.0041, 0.0))
        objects.append(
            make_eye_component(
                f"Kira_Hart_{side}_Brown_Iris",
                iris_center,
                (height * 0.0052, height * 0.0009, height * 0.0052),
                iris,
                armature,
            )
        )
        pupil_center = center + Vector((0.0, -height * 0.0050, 0.0))
        objects.append(
            make_eye_component(
                f"Kira_Hart_{side}_Pupil",
                pupil_center,
                (height * 0.0023, height * 0.00065, height * 0.0023),
                pupil,
                armature,
            )
        )
        highlight_center = center + Vector(
            (
                sign * height * 0.0012,
                -height * 0.0056,
                height * 0.0016,
            )
        )
        objects.append(
            make_eye_component(
                f"Kira_Hart_{side}_Eye_Catchlight",
                highlight_center,
                (height * 0.0008, height * 0.00035, height * 0.0008),
                catchlight,
                armature,
            )
        )
    return objects, {
        "color": "natural brown",
        "centers_world_m": centers,
        "component_count": len(objects),
        "head_bone_binding": r5.HEAD,
        "bilateral_symmetry_authored": True,
        "socket_overlay_method": "bounded flattened review assemblies fitted to the enrolled generic face",
        "blink_control_proven": False,
        "gaze_control_proven": False,
        "owner_visual_fit_approved": False,
    }


def create_cap_mesh(
    center: Vector,
    height: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    rx, ry, rz = height * 0.061, height * 0.056, height * 0.083
    segments = 48
    rings = 11
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    for ring in range(rings + 1):
        phi = (math.pi * 0.47) * ring / rings
        for segment in range(segments):
            theta = math.tau * segment / segments
            vertices.append(
                (
                    float(center.x + rx * math.sin(phi) * math.cos(theta)),
                    float(center.y + ry * math.sin(phi) * math.sin(theta)),
                    float(center.z + rz * math.cos(phi)),
                )
            )
    for ring in range(rings):
        for segment in range(segments):
            nxt = (segment + 1) % segments
            a = ring * segments + segment
            b = ring * segments + nxt
            c = (ring + 1) * segments + nxt
            d = (ring + 1) * segments + segment
            faces.append((a, b, c, d))
    mesh = bpy.data.meshes.new("Kira_Hart_Black_Hair_Scalp_Cap_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new("Kira_Hart_Black_Straight_Review_Hair_Cap", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj["removable_review_hair"] = True
    obj["runtime_hair_system_complete"] = False
    return obj


def create_straight_strand_groom(
    center: Vector,
    height: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(
        "Kira_Hart_Black_Straight_Review_Hair_Strands_Curve",
        type="CURVE",
    )
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = height * 0.00155
    curve.bevel_resolution = 2
    curve.resolution_u = 2
    rx, ry, rz = height * 0.060, height * 0.055, height * 0.081
    strand_count = 64
    authored = 0
    for index in range(strand_count):
        theta = math.tau * index / strand_count
        # Leave the central face clear.  Side locks begin outside the eye
        # envelope and descend vertically to a shoulder-clear bob.
        frontness = math.sin(theta)
        sideness = abs(math.cos(theta))
        if frontness < -0.48 and sideness < 0.60:
            continue
        root = Vector(
            (
                center.x + rx * 0.90 * math.cos(theta),
                center.y + ry * 0.90 * math.sin(theta),
                center.z + rz * 0.30,
            )
        )
        side_factor = 0.84 + 0.16 * sideness
        end_z = center.z - height * (0.130 + 0.018 * side_factor)
        outward = Vector(
            (
                height * 0.006 * math.cos(theta),
                height * 0.005 * math.sin(theta),
                0.0,
            )
        )
        end = Vector((root.x, root.y, end_z)) + outward
        mid = root.lerp(end, 0.54)
        mid += outward * 0.55
        spline = curve.splines.new("POLY")
        spline.points.add(2)
        for point, value in zip(spline.points, (root, mid, end)):
            point.co = (*value, 1.0)
        authored += 1

    # A restrained center-part fringe follows the forehead but stops above the
    # eyes.  It is geometry, not a painted cap.
    for sign in (-1.0, 1.0):
        for index in range(7):
            offset = (index + 1) / 8.0
            root = Vector(
                (
                    center.x + sign * height * 0.008 * offset,
                    center.y - ry * 0.68,
                    center.z + rz * (0.84 - 0.04 * offset),
                )
            )
            end = Vector(
                (
                    center.x + sign * height * (0.019 + 0.016 * offset),
                    center.y - ry * (0.93 + 0.03 * offset),
                    center.z + height * (0.012 - 0.024 * offset),
                )
            )
            mid = root.lerp(end, 0.52)
            spline = curve.splines.new("POLY")
            spline.points.add(2)
            for point, value in zip(spline.points, (root, mid, end)):
                point.co = (*value, 1.0)
            authored += 1

    obj = bpy.data.objects.new(
        "Kira_Hart_Black_Straight_Review_Hair_Strands",
        curve,
    )
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj.name = "Kira_Hart_Black_Straight_Review_Hair_Strands"
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj["strand_spline_count"] = authored
    obj["removable_review_hair"] = True
    obj["runtime_hair_system_complete"] = False
    return obj


def add_straight_black_review_hair(
    body: bpy.types.Object,
    armature: bpy.types.Object,
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    low, high = r5.bounds_for_body(body, evaluated=True)
    height = float(high.z - low.z)
    center = Vector(
        (
            float((low.x + high.x) * 0.5),
            float((low.y + high.y) * 0.5 + height * 0.006),
            float(high.z - height * 0.084),
        )
    )
    material = make_simple_material(
        "Kira_Hart_Natural_Black_Hair",
        (0.008, 0.009, 0.012, 1.0),
        0.31,
    )
    cap = create_cap_mesh(center, height, material)
    strands = create_straight_strand_groom(center, height, material)
    for obj in (cap, strands):
        parent_to_bone(obj, armature, r5.HEAD)
    return [cap, strands], {
        "color": "black",
        "texture": "straight",
        "review_style": "simple removable shoulder-clear bob",
        "component_names": [cap.name, strands.name],
        "head_bone_binding": r5.HEAD,
        "removable": True,
        "procedurally_authored_from_request": True,
        "external_hair_asset_copied": False,
        "runtime_grooming_growth_wetness_or_dynamics_complete": False,
        "truth_note": "Static removable review groom only; later production hair remains a separate stage.",
    }


def make_nail_plate(
    name: str,
    location: Vector,
    direction: Vector,
    length: float,
    width: float,
    material: bpy.types.Material,
    armature: bpy.types.Object,
    bone_name: str,
) -> bpy.types.Object:
    direction = direction.normalized()
    up = Vector((0.0, 0.0, 1.0))
    if abs(direction.dot(up)) > 0.92:
        up = Vector((0.0, 1.0, 0.0))
    dorsal = direction.cross(up).cross(direction).normalized()
    position = location + dorsal * width * 0.32
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=20,
        ring_count=10,
        location=position,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = (width, length, max(width * 0.14, 0.00045))
    obj.rotation_euler = direction.to_track_quat("Y", "Z").to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj["ordinary_nail_plate"] = True
    parent_to_bone(obj, armature, bone_name)
    return obj


def rest_bone_points(
    armature: bpy.types.Object,
    bone_name: str,
) -> tuple[Vector, Vector]:
    bone = armature.data.bones.get(bone_name)
    if bone is None:
        raise ValueError(f"missing nail anchor bone {bone_name}")
    return (
        armature.matrix_world @ bone.head_local,
        armature.matrix_world @ bone.tail_local,
    )


def add_ordinary_nails(
    armature: bpy.types.Object,
    body_height: float,
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    material = make_simple_material(
        "Kira_Hart_Natural_Nail",
        (0.74, 0.47, 0.42, 1.0),
        0.34,
    )
    objects: list[bpy.types.Object] = []
    finger_bones = [
        name
        for name in (bone.name for bone in armature.data.bones)
        if "Hand" in name
        and any(token in name for token in ("Thumb4_", "Index4_", "Middle4_", "Ring4_", "Pinky4_"))
        and "_end_" not in name
    ]
    for bone_name in sorted(finger_bones):
        head, tail = rest_bone_points(armature, bone_name)
        direction = tail - head
        if direction.length < 1e-6:
            continue
        objects.append(
            make_nail_plate(
                f"Kira_Hart_Fingernail_{len(objects) + 1:02d}",
                head.lerp(tail, 0.72),
                direction,
                body_height * 0.0048,
                body_height * 0.0023,
                material,
                armature,
                bone_name,
            )
        )
    # The enrolled rig has one toe chain per foot.  Five separate plates are
    # placed across each authored forefoot and all follow the appropriate toe
    # bone.  Their placement is inspection evidence, not final podiatry.
    toe_bones = (
        "mixamorig:LeftToeBase_058",
        "mixamorig:RightToeBase_063",
    )
    for bone_name in toe_bones:
        head, tail = rest_bone_points(armature, bone_name)
        direction = tail - head
        if direction.length < 1e-6:
            continue
        for index, offset in enumerate((-2, -1, 0, 1, 2), start=1):
            location = head.lerp(tail, 0.72) + Vector(
                (offset * body_height * 0.0052, 0.0, 0.0)
            )
            objects.append(
                make_nail_plate(
                    f"Kira_Hart_Toenail_{bone_name.split(':')[-1]}_{index}",
                    location,
                    direction,
                    body_height * (0.0054 if index == 3 else 0.0045),
                    body_height * (0.0034 if index == 3 else 0.0028),
                    material,
                    armature,
                    bone_name,
                )
            )
    return objects, {
        "finger_nail_count": len(finger_bones),
        "toe_nail_count": max(0, len(objects) - len(finger_bones)),
        "separate_keratin_review_plates": True,
        "bone_parented": True,
        "owner_visual_placement_approved": False,
    }


def boundary_loop_record(body: bpy.types.Object) -> dict[str, object]:
    edge_use: collections.Counter[tuple[int, int]] = collections.Counter()
    for polygon in body.data.polygons:
        vertices = [int(index) for index in polygon.vertices]
        for position, first in enumerate(vertices):
            edge_use[
                tuple(sorted((first, vertices[(position + 1) % len(vertices)])))
            ] += 1
    boundary = [edge for edge, count in edge_use.items() if count == 1]
    adjacency: dict[int, set[int]] = {}
    for left, right in boundary:
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)
    seen: set[int] = set()
    components: list[dict[str, object]] = []
    for seed in adjacency:
        if seed in seen:
            continue
        stack = [seed]
        component: set[int] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(adjacency.get(current, ()))
        seen.update(component)
        local_points = [body.data.vertices[index].co for index in component]
        world_points = [body.matrix_world @ point for point in local_points]
        local_center = sum(local_points, Vector()) / max(len(local_points), 1)
        world_center = sum(world_points, Vector()) / max(len(world_points), 1)
        components.append(
            {
                "vertex_count": len(component),
                "all_degree_two_closed_cycle": all(
                    len(adjacency.get(index, ())) == 2 for index in component
                ),
                "local_centroid": r5.vector_list(local_center),
                "world_centroid_m": r5.vector_list(world_center),
            }
        )
    return {
        "boundary_edge_count": len(boundary),
        "component_count": len(components),
        "components": components,
        "all_components_closed_cycles": bool(components)
        and all(item["all_degree_two_closed_cycle"] for item in components),
        "truth_note": "Boundary cycles are preserved and reported; watertightness is not inferred from one connected surface.",
    }


def quantile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * ratio
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return float(ordered[low])
    blend = position - low
    return float(ordered[low] * (1.0 - blend) + ordered[high] * blend)


def evaluated_points(body: bpy.types.Object) -> list[Vector]:
    return r5.mesh_world_points(body, evaluated=True)


def deformation_metrics(
    body: bpy.types.Object,
    rest: list[Vector],
) -> dict[str, object]:
    current = evaluated_points(body)
    if len(current) != len(rest):
        raise ValueError("evaluated vertex domain changed during deformation test")
    finite = all(
        math.isfinite(float(component))
        for point in current
        for component in point
    )
    edge_indices = list(body.data.edges)
    stride = max(1, len(edge_indices) // 25000)
    ratios: list[float] = []
    for edge in edge_indices[::stride]:
        left, right = (int(value) for value in edge.vertices)
        before = (rest[left] - rest[right]).length
        after = (current[left] - current[right]).length
        if before > 1e-8:
            ratios.append(after / before)
    displacements = [(after - before).length for before, after in zip(rest, current)]
    return {
        "all_coordinates_finite": finite,
        "sampled_edge_count": len(ratios),
        "edge_stretch_ratio": {
            "minimum": round(min(ratios, default=0.0), 7),
            "p01": round(quantile(ratios, 0.01), 7),
            "median": round(quantile(ratios, 0.50), 7),
            "p99": round(quantile(ratios, 0.99), 7),
            "maximum": round(max(ratios, default=0.0), 7),
        },
        "vertex_displacement_m": {
            "mean": round(statistics.fmean(displacements), 7),
            "p95": round(quantile(displacements, 0.95), 7),
            "maximum": round(max(displacements, default=0.0), 7),
        },
    }


def render_target(
    output: Path,
    camera: bpy.types.Object,
    location: Vector,
    target: Vector,
    ortho_scale: float,
) -> dict[str, object]:
    camera.location = location
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale
    r5.look_at(camera, target)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    return {
        "path": str(output),
        "sha256": sha256_file(output),
        "size_bytes": output.stat().st_size,
        "target_world_m": r5.vector_list(target),
        "camera_world_m": r5.vector_list(location),
        "orthographic_scale": round(float(ortho_scale), 7),
    }


def setup_review_scene(
    body: bpy.types.Object,
) -> tuple[bpy.types.Object, bpy.types.Object, bpy.types.Object]:
    low, high = r5.bounds_for_body(body, evaluated=True)
    height = float(high.z - low.z)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.035, 0.039, 0.048)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.15
    ground = r5.add_ground(low, high)
    seat = r5.add_seat_helper(height)
    r5.add_lighting((low + high) * 0.5, height)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "Kira_Hart_Private_Inspection_Camera_Not_Exported"
    camera["private_diagnostic_helper"] = True
    scene.camera = camera
    return camera, ground, seat


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    project_root = Path(config["project_root"]).resolve(strict=True)
    source = Path(config["source_model"]).resolve(strict=True)
    request_path = Path(config["request_path"]).resolve(strict=True)
    output_dir = Path(config["output_dir"]).resolve()
    allowed_root = (
        project_root
        / "Avatar"
        / "private_owner_review"
        / "kira_temporary_functional_body_20260730"
    ).resolve()
    output_dir.relative_to(allowed_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    if sha256_file(source) != config["source_sha256"]:
        raise ValueError("enrolled adult-female source hash changed")
    if sha256_file(request_path) != config["request_sha256"]:
        raise ValueError("rapid-body request hash changed")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    parameters = request["parameters"]
    if request["privacy"]["robert_private_data_allowed"] is not False:
        raise ValueError("worker refuses any Robert-private-data request")
    if bool(request["output"]["runtime_assignment_allowed"]):
        raise ValueError("worker refuses runtime assignment")

    r5.clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    body, armature = r5.primary_body_and_armature()
    removed_helpers = r5.remove_source_helpers(body)
    original_bones = [bone.name for bone in armature.data.bones]
    original_group_names = [group.name for group in body.vertex_groups]
    original_topology = r5.topology_counts(body.data)
    original_weights = r5.weight_health(body.data)
    original_uv = r5.uv_multiset_hash(body.data)
    if len(original_bones) != 79 or not set(r5.REQUIRED_BONES).issubset(original_bones):
        raise ValueError("source is not the enrolled 79-joint adult-female cage")

    body.name = "Kira_Hart_Temporary_Functional_Body"
    body.data.name = "Kira_Hart_Temporary_Functional_Body_Surface"
    armature.name = "Kira_Hart_79_Joint_Functional_Rig"
    armature.data.name = "Kira_Hart_79_Joint_Functional_Skeleton"
    for owner in (body, armature):
        owner["candidate_id"] = "kira_temporary_functional_body_20260730"
        owner["body_purpose"] = "TEMPORARY_FUNCTIONAL_BODY"
        owner["adult_status"] = "adult"
        owner["private_inspection_only"] = True
        owner["runtime_assignment_allowed"] = False
        owner["owner_approved"] = False
        owner["robert_private_data_used"] = False

    seam_audit = r5.weld_exact_safe_seams(body)
    r6_external = r6.author_private_adult_external_form(body)
    parametric = author_parametric_surface(body, parameters)
    height_audit = normalize_height(
        body,
        armature,
        float(parameters["height_m"]),
    )

    skin, skin_audit = author_light_skin_material(output_dir)
    regional_materials = add_regional_body_materials(body, skin)
    eye_objects, eye_audit = add_brown_review_eyes(body, armature)
    hair_objects, hair_audit = add_straight_black_review_hair(body, armature)
    neutral_low, neutral_high = r5.bounds_for_body(body, evaluated=True)
    body_height = float(neutral_high.z - neutral_low.z)
    nail_objects, nail_audit = add_ordinary_nails(armature, body_height)
    exportable_components = [body, *eye_objects, *hair_objects, *nail_objects]
    for obj in exportable_components:
        obj["private_inspection_component"] = True
        obj["runtime_assignment_allowed"] = False

    topology_after = r5.topology_counts(body.data)
    weights_after = r5.weight_health(body.data)
    uv_after = r5.uv_multiset_hash(body.data)
    boundary_audit = boundary_loop_record(body)
    if topology_after["surface_island_count"] != 1:
        raise ValueError("welded Kira body is not one connected indexed surface")
    if topology_after["non_manifold_edge_count"] != 0:
        raise ValueError("welded Kira body contains nonmanifold edges")
    if weights_after["unweighted_vertex_count"] != 0:
        raise ValueError("Kira body contains unweighted vertices")

    camera, _ground, seat = setup_review_scene(body)
    renders: dict[str, dict[str, object]] = {}
    r5.reset_pose(armature)
    full_views = (
        ("neutral_front", Vector((0.0, -1.0, 0.03))),
        ("neutral_back", Vector((0.0, 1.0, 0.03))),
        ("neutral_left_profile", Vector((1.0, 0.0, 0.02))),
        ("neutral_right_profile", Vector((-1.0, 0.0, 0.02))),
        ("neutral_left_three_quarter", Vector((0.70, -1.0, 0.05))),
        ("neutral_right_three_quarter", Vector((-0.70, -1.0, 0.05))),
    )
    for label, direction in full_views:
        renders[label] = r5.render_view(
            output_dir / "renders" / f"{label}.png",
            body=body,
            camera=camera,
            direction=direction,
        )

    center_y = float((neutral_low.y + neutral_high.y) * 0.5)
    face_target = Vector(
        (
            0.0,
            center_y,
            float(neutral_low.z + body_height * 0.925),
        )
    )
    renders["face_close_front"] = render_target(
        output_dir / "renders" / "face_close_front.png",
        camera,
        face_target + Vector((0.0, -2.0, 0.0)),
        face_target,
        body_height * 0.27,
    )
    pelvis_target = Vector(
        (
            0.0,
            center_y,
            float(neutral_low.z + body_height * 0.50),
        )
    )
    renders["protected_adult_surface_front"] = render_target(
        output_dir / "renders" / "protected_adult_surface_front.png",
        camera,
        pelvis_target + Vector((0.0, -2.0, 0.0)),
        pelvis_target,
        body_height * 0.31,
    )
    renders["protected_adult_surface_side"] = render_target(
        output_dir / "renders" / "protected_adult_surface_side.png",
        camera,
        pelvis_target + Vector((2.0, -0.25, 0.0)),
        pelvis_target,
        body_height * 0.31,
    )
    left_hand_head, left_hand_tail = rest_bone_points(armature, r5.LEFT_HAND)
    hand_target = left_hand_head.lerp(left_hand_tail, 0.50)
    renders["left_hand_nail_close"] = render_target(
        output_dir / "renders" / "left_hand_nail_close.png",
        camera,
        hand_target + Vector((0.0, -1.2, body_height * 0.04)),
        hand_target,
        body_height * 0.22,
    )
    left_foot_head, left_foot_tail = rest_bone_points(armature, r5.LEFT_FOOT)
    foot_target = left_foot_head.lerp(left_foot_tail, 0.72)
    renders["left_foot_nail_close"] = render_target(
        output_dir / "renders" / "left_foot_nail_close.png",
        camera,
        foot_target + Vector((0.25, -1.15, body_height * 0.08)),
        foot_target,
        body_height * 0.24,
    )

    rest = evaluated_points(body)
    pose_metrics: dict[str, object] = {}
    deformation: dict[str, object] = {}
    for pose, direction, show_seat in (
        ("reach", Vector((0.68, -1.0, 0.075)), False),
        ("stride", Vector((0.68, -1.0, 0.075)), False),
        ("seated", Vector((0.68, -1.0, 0.070)), True),
    ):
        pose_metrics[pose] = r5.apply_pose(
            armature,
            body,
            pose,
            neutral_low,
            neutral_high,
        )
        deformation[pose] = deformation_metrics(body, rest)
        seat.hide_render = not show_seat
        if show_seat:
            pose_metrics[pose]["seat_support"] = r5.seat_support_metrics(body, seat)
        renders[f"pose_{pose}"] = r5.render_view(
            output_dir / "renders" / f"pose_{pose}.png",
            body=body,
            camera=camera,
            direction=direction,
        )
        r5.reset_pose(armature)
    seat.hide_render = True
    reset_points = evaluated_points(body)
    reset_maximum = max(
        ((after - before).length for before, after in zip(rest, reset_points)),
        default=0.0,
    )
    deformation["restoration"] = {
        "maximum_vertex_delta_after_reset_m": round(reset_maximum, 9),
        "restored_within_1e_6_m": reset_maximum <= 1e-6,
    }

    actions = [
        r5.create_action(
            armature,
            body,
            name=f"Kira_Hart_Temporary_{pose.title()}_Evidence",
            pose=pose,
            low=neutral_low,
            high=neutral_high,
        )
        for pose in ("neutral", "reach", "stride", "seated")
    ]
    r5.reset_pose(armature)

    pose_gate = all(
        bool(record["all_coordinates_finite"])
        and float(record["edge_stretch_ratio"]["p01"]) >= 0.42
        and float(record["edge_stretch_ratio"]["p99"]) <= 1.85
        and float(record["vertex_displacement_m"]["maximum"]) > 0.01
        for pose, record in deformation.items()
        if pose != "restoration"
    ) and bool(deformation["restoration"]["restored_within_1e_6_m"])

    model_path = output_dir / "kira_hart_temporary_functional_body.glb"
    review_blend = output_dir / "kira_hart_temporary_functional_body_private_review.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(review_blend))

    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    for obj in exportable_components:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(
        filepath=str(model_path),
        export_format="GLB",
        use_selection=True,
        export_apply=False,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_def_bones=True,
        export_yup=True,
        export_morph=True,
        export_extras=True,
    )
    if not model_path.is_file():
        raise RuntimeError("Blender did not export the Kira temporary body GLB")

    final_bones = [bone.name for bone in armature.data.bones]
    final_group_names = [group.name for group in body.vertex_groups]
    if final_bones != original_bones:
        raise ValueError("rapid build changed bone names or order")
    if final_group_names != original_group_names:
        raise ValueError("rapid build changed body vertex-group names or order")

    integrated_form_gate = bool(
        parametric["integrated_external_adult_form"][
            "all_named_regions_received_surface_displacement"
        ]
        and topology_after["surface_island_count"] == 1
        and topology_after["non_manifold_edge_count"] == 0
        and not parametric["integrated_external_adult_form"][
            "separate_or_floating_anatomy_mesh_created"
        ]
    )
    structural_rig_gate = bool(
        len(final_bones) == 79
        and weights_after["unweighted_vertex_count"] == 0
        and weights_after["weight_sum_out_of_tolerance_count"] == 0
        and pose_gate
    )
    # The enrolled 3ec62 asset is a useful high-density cage-fit source, but
    # its authority record explicitly does not prove complete adult topology.
    # Surface displacement cannot silently promote that source limitation.
    complete_integrated_adult_anatomy_proven = False
    evidence = {
        "schema_version": 1,
        "created_at": now_iso(),
        "candidate_id": "kira_temporary_functional_body_20260730",
        "display_name": "Kira Hart Temporary Functional Body",
        "status": "BLOCKED_PRIVATE_INSPECTION_CANDIDATE_COMPLETE_ADULT_ANATOMY_NOT_PROVEN",
        "request": {
            "path": str(request_path),
            "sha256": config["request_sha256"],
            "body_purpose": request["body_purpose"],
            "parameters": parameters,
        },
        "source": {
            "path": str(source),
            "sha256": config["source_sha256"],
            "role": "enrolled_cage_fit_engineering_source_only",
            "anatomical_completeness_proven": False,
            "stable_working_rig_proven_at_source": False,
            "copy_as_unmodified_candidate_allowed": False,
            "removed_helpers": removed_helpers,
            "topology_before": original_topology,
            "weights_before": original_weights,
            "uv_before": original_uv,
        },
        "surface_authoring": {
            "exact_seam_weld": seam_audit,
            "existing_r6_external_form_helper": r6_external,
            "request_parametric_key": parametric,
            "height": height_audit,
            "body_topology_after": topology_after,
            "body_weights_after": weights_after,
            "body_uv_after": uv_after,
            "boundary_cycles": boundary_audit,
        },
        "appearance_components": {
            "skin": skin_audit,
            "regional_materials": regional_materials,
            "eyes": eye_audit,
            "hair": hair_audit,
            "nails": nail_audit,
        },
        "rig_and_deformation": {
            "armature": armature.name,
            "bone_count": len(final_bones),
            "bone_names_and_order_preserved": final_bones == original_bones,
            "body_vertex_groups_preserved": final_group_names == original_group_names,
            "actions": [action.name for action in actions],
            "pose_metrics": pose_metrics,
            "deformation_metrics": deformation,
            "bounded_pose_gate_passed": pose_gate,
            "long_duration_runtime_locomotion_proven": False,
        },
        "renders": renders,
        "artifacts": {
            "candidate_glb": {
                "path": str(model_path),
                "sha256": sha256_file(model_path),
                "size_bytes": model_path.stat().st_size,
            },
            "private_review_blend": {
                "path": str(review_blend),
                "sha256": sha256_file(review_blend),
                "size_bytes": review_blend.stat().st_size,
            },
        },
        "gates": {
            "new_transformed_surface_not_unmodified_copy": sha256_file(model_path)
            != config["source_sha256"],
            "one_connected_primary_body_surface": topology_after["surface_island_count"]
            == 1,
            "zero_primary_body_nonmanifold_edges": topology_after[
                "non_manifold_edge_count"
            ]
            == 0,
            "known_boundary_cycles_reported": boundary_audit["component_count"]
            == topology_after["boundary_loop_count"],
            "integrated_external_adult_form_engineering_gate": integrated_form_gate,
            "complete_integrated_adult_anatomy_requirement_passed": complete_integrated_adult_anatomy_proven,
            "movement_ready_structural_and_bounded_pose_gate": structural_rig_gate,
            "brown_review_eyes_present": len(eye_objects) == 8,
            "straight_black_removable_review_hair_present": len(hair_objects) == 2,
            "ordinary_finger_and_toe_nail_review_components_present": (
                nail_audit["finger_nail_count"] == 10
                and nail_audit["toe_nail_count"] == 10
            ),
            "future_clothing_structural_compatibility": (
                topology_after["surface_island_count"] == 1
                and len(final_bones) == 79
                and not any("clothing" in obj.name.lower() for obj in exportable_components)
            ),
            "future_hair_structural_compatibility": hair_audit["removable"],
            "owner_approved": False,
            "runtime_assignment_allowed": False,
            "public_export_allowed": False,
            "overall_request_gate_passed": False,
        },
        "privacy": {
            "private_local_review_only": True,
            "robert_private_data_allowed": False,
            "robert_private_data_read_or_used_by_worker": False,
            "identifiable_person_likeness_used": False,
            "copy_existing_person_body_used": False,
            "runtime_files_read_or_written_by_worker": False,
        },
        "truthful_limits": [
            "The face is a bounded generic adult-female foundation, not an approved Kira likeness.",
            "The external adult form is integrated on one body mesh and is pending owner visual review; internal organs and dynamic soft-tissue behavior are not claimed.",
            "The enrolled cage does not independently prove complete adult topology. This build therefore fails the request's complete-integrated-anatomy gate even when its local external-form displacement gate passes.",
            "The three retained source boundary cycles are explicitly reported; watertightness is not claimed.",
            "The 79-joint rig passed bounded reach, stride, and seated deformation checks; long-duration natural locomotion remains unproven.",
            "The black straight hair is a removable static review groom with no wetness, growth, combing, or secondary-motion system.",
            "The brown eyes are static review assemblies; final socket fit, blinking, gaze, and expressive facial animation are not approved.",
            "Clothing collision and cloth simulation remain later gates.",
            "Nothing in this build assigns, activates, or replaces Kira's current runtime body.",
        ],
    }
    evidence_path = output_dir / "blender_build_evidence.json"
    evidence_path.write_text(
        json.dumps(evidence, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "candidate": str(model_path),
                "candidate_sha256": evidence["artifacts"]["candidate_glb"]["sha256"],
                "review_blend": str(review_blend),
                "evidence": str(evidence_path),
                "render_count": len(renders),
                "integrated_external_adult_form_engineering_gate": integrated_form_gate,
                "movement_ready_structural_and_bounded_pose_gate": structural_rig_gate,
                "owner_approved": False,
                "runtime_assignment_allowed": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
