"""Isolated v2 non-anatomy presentation adapter for profiled adult candidates.

The accepted R15-bound v1 component and builder modules are intentionally not
modified.  This module can be called by a later append-only builder revision after
its own hash/config binding is added.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import bpy
from mathutils import Vector

import tools.blender_profiled_adult_candidate_components as v1
from Core.avatar_profiled_nonanatomy_presentation_v2 import (
    FACE_DIRECTION_ID,
    FACE_TARGETS,
    METHOD_ID,
    REVIEW_RIG,
    SKIN_CALIBRATION,
    rounded_nail_row_scale,
    silhouette_roughness,
    validate_face_target_manifest,
)


class ProfiledPresentationV2Error(RuntimeError):
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
                raise ProfiledPresentationV2Error(
                    f"invalid target row at {path}:{line_number}"
                )
            index = int(fields[0])
            if index in rows:
                raise ProfiledPresentationV2Error(
                    f"duplicate target vertex at {path}:{line_number}"
                )
            rows[index] = Vector(tuple(float(value) for value in fields[1:4]))
    if not rows:
        raise ProfiledPresentationV2Error(f"empty target: {path}")
    return rows


def _width(points: Sequence[Vector]) -> float:
    return float(max(point.x for point in points) - min(point.x for point in points))


def apply_qualitative_face_geometry_v2(
    *,
    body: Any,
    project_root: Path,
    base_body_path: Path,
    baseline_source: Mapping[str, Any],
    target_height_m: float,
) -> dict[str, Any]:
    """Apply the hash-bound qualitative face direction to a compatible body mesh.

    ``baseline_source`` must be the exact pre-face result returned by the preserved
    v1 source preparer.  Compatibility is proven on every touched compact vertex
    before a delta is written, so post-build diagnostic use cannot silently apply
    a source index to a reordered mesh.
    """

    if body is None or body.type != "MESH":
        raise ProfiledPresentationV2Error("face geometry requires a mesh body")
    manifest = validate_face_target_manifest(project_root)
    _vertices, groups = v1._parse_obj_vertices_and_group_faces(  # noqa: SLF001
        Path(base_body_path), {"body"}
    )
    used = sorted({index for face in groups["body"] for index in face})
    source_to_body = {source: compact for compact, source in enumerate(used)}
    if source_to_body != dict(baseline_source["source_to_body"]):
        raise ProfiledPresentationV2Error("baseline source-to-body map mismatch")
    if len(body.data.vertices) < len(used):
        raise ProfiledPresentationV2Error("body lost original compact source vertices")

    root = Path(project_root).resolve(strict=True)
    scale = float(baseline_source["uniform_scale"])
    accumulated: dict[int, Vector] = {}
    per_target: list[dict[str, Any]] = []
    lip_source_indices: set[int] = set()
    compatibility_errors: list[float] = []
    feature_width_deltas: dict[str, float] = {}
    lip_forward_deltas: list[float] = []
    cheek_mean_lateral: dict[str, float] = {}
    minimum_face_z = float(target_height_m) * 0.76
    excluded_below_face_region: list[dict[str, Any]] = []

    for record in FACE_TARGETS:
        path = (root / str(record["path"])).resolve(strict=True)
        rows = _read_target(path)
        weight = float(record["weight"])
        mapped_all = sorted(index for index in rows if index in source_to_body)
        if not mapped_all:
            raise ProfiledPresentationV2Error(
                f"face target has no body vertices: {record['target_id']}"
            )
        mapped = [
            index
            for index in mapped_all
            if float(body.data.vertices[source_to_body[index]].co.z) >= minimum_face_z
        ]
        excluded = sorted(set(mapped_all).difference(mapped))
        if not mapped:
            raise ProfiledPresentationV2Error(
                f"face target has no vertices inside face region: {record['target_id']}"
            )
        excluded_below_face_region.extend(
            {
                "target_id": str(record["target_id"]),
                "source_index": int(index),
                "body_z_m": float(body.data.vertices[source_to_body[index]].co.z),
            }
            for index in excluded
        )
        before = [body.data.vertices[source_to_body[index]].co.copy() for index in mapped]
        expected = [
            Vector(baseline_source["body_vertices"][source_to_body[index]])
            for index in mapped
        ]
        compatibility_errors.extend(
            float((current - baseline).length)
            for current, baseline in zip(before, expected)
        )
        deltas = [v1._converted_makehuman(rows[index]) * scale * weight for index in mapped]  # noqa: SLF001
        after = [point + delta for point, delta in zip(before, deltas)]
        direction = str(record["direction"])
        if direction == "width_decrease" or direction == "width_increase":
            feature_width_deltas[str(record["feature"])] = _width(after) - _width(before)
        if record["feature"] in {"upper_lip", "lower_lip"}:
            lip_source_indices.update(mapped)
            lip_forward_deltas.extend(float(delta.y) for delta in deltas)
        if record.get("pair_id") == "cheekbone_definition":
            cheek_mean_lateral[str(record["side"])] = sum(
                float(delta.x) for delta in deltas
            ) / len(deltas)
        for source_index, delta in zip(mapped, deltas):
            compact = source_to_body[source_index]
            accumulated[compact] = accumulated.get(compact, Vector()) + delta
        per_target.append(
            {
                "target_id": str(record["target_id"]),
                "feature": str(record["feature"]),
                "direction": direction,
                "mapped_source_vertex_count_before_region_filter": len(mapped_all),
                "mapped_body_vertex_count": len(mapped),
                "excluded_below_face_region_vertex_count": len(excluded),
                "maximum_delta_m": max(float(delta.length) for delta in deltas),
            }
        )

    maximum_compatibility_error = max(compatibility_errors, default=math.inf)
    if maximum_compatibility_error > 2.0e-6:
        raise ProfiledPresentationV2Error(
            "face source-index compatibility failed: "
            f"maximum_error_m={maximum_compatibility_error:.9f}"
        )
    before_coords = {index: body.data.vertices[index].co.copy() for index in accumulated}
    minimum_touched_z = min(float(point.z) for point in before_coords.values())
    if minimum_touched_z < minimum_face_z:
        raise ProfiledPresentationV2Error(
            f"face target escaped head region: minimum_z={minimum_touched_z:.6f}"
        )
    for compact, delta in accumulated.items():
        body.data.vertices[compact].co += delta
    body.data.update()

    chin_delta = float(feature_width_deltas.get("chin", 0.0))
    nose_delta = float(feature_width_deltas.get("nose", 0.0))
    mouth_delta = float(feature_width_deltas.get("mouth", 0.0))
    mean_lip_forward = sum(lip_forward_deltas) / len(lip_forward_deltas)
    cheek_balance = abs(
        float(cheek_mean_lateral.get("left", 0.0))
        + float(cheek_mean_lateral.get("right", 0.0))
    )
    geometry_gates = {
        "source_index_compatibility": maximum_compatibility_error <= 2.0e-6,
        "head_region_only": minimum_touched_z >= minimum_face_z,
        "changed_vertex_count": len(accumulated) >= 700,
        "chin_width_decreased": chin_delta <= -0.00035,
        "nose_width_decreased": nose_delta <= -0.00025,
        "mouth_width_increased": mouth_delta >= 0.00045,
        "lip_volume_projects_anteriorly": mean_lip_forward <= -0.000025,
        "paired_cheek_lateral_balance": cheek_balance <= 1.0e-7,
    }
    if not all(geometry_gates.values()):
        for index, point in before_coords.items():
            body.data.vertices[index].co = point
        body.data.update()
        raise ProfiledPresentationV2Error(
            "hard face geometry gate failed: "
            + json.dumps(geometry_gates, sort_keys=True)
        )
    body["profiled_nonanatomy_face_direction"] = FACE_DIRECTION_ID
    body["profiled_nonanatomy_face_identity_match_claim"] = False
    return {
        "method": "hash_bound_official_makehuman_qualitative_face_geometry_v2",
        "contract": manifest,
        "changed_body_vertex_count": len(accumulated),
        "minimum_touched_z_m": minimum_touched_z,
        "minimum_face_application_z_m": minimum_face_z,
        "below_face_region_rows_excluded_before_application": len(
            excluded_below_face_region
        ),
        "below_face_region_exclusion_examples": excluded_below_face_region[:20],
        "region_filter_reason": (
            "official qualitative face target rows outside the upper 24 percent "
            "of the body are not allowed to alter the torso or limbs"
        ),
        "maximum_source_index_compatibility_error_m": maximum_compatibility_error,
        "feature_width_deltas_m": {
            "chin": chin_delta,
            "nose": nose_delta,
            "mouth": mouth_delta,
        },
        "mean_lip_anterior_delta_m": mean_lip_forward,
        "paired_cheek_mean_lateral_balance_m": cheek_balance,
        "geometry_gates": geometry_gates,
        "hard_face_geometry_gate_passed": True,
        "lip_compact_vertex_indices": sorted(
            source_to_body[index] for index in lip_source_indices
        ),
        "targets": per_target,
        "identity_match_claim_allowed": False,
        "qualitative_target_direction_only": True,
    }


def _material_input(node: Any, *names: str) -> Any:
    return v1._principled_input(node, *names)  # noqa: SLF001


def calibrate_warm_non_pale_skin_v2(body: Any) -> dict[str, Any]:
    if body is None or body.type != "MESH" or not body.data.materials:
        raise ProfiledPresentationV2Error("skin calibration requires body material")
    material = body.data.materials[0]
    if not material.use_nodes or material.node_tree is None:
        raise ProfiledPresentationV2Error("skin calibration requires node material")
    base = v1.srgb_hex_to_linear_rgba(
        str(SKIN_CALIBRATION["calibrated_warm_non_pale_srgb_hex"])
    )
    material.diffuse_color = base
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is None:
        raise ProfiledPresentationV2Error("skin Principled BSDF missing")
    ramp = material.node_tree.nodes.get("Kira_Bounded_Warm_Microvariation")
    if ramp is None:
        raise ProfiledPresentationV2Error("bounded skin microvariation ramp missing")
    amplitude = float(SKIN_CALIBRATION["microvariation_fraction"])
    ramp.color_ramp.elements[0].color = tuple(
        max(0.0, channel * (1.0 - amplitude)) for channel in base[:3]
    ) + (1.0,)
    ramp.color_ramp.elements[1].color = tuple(
        min(1.0, channel * (1.0 + amplitude)) for channel in base[:3]
    ) + (1.0,)
    for names, value in (
        (("Roughness",), SKIN_CALIBRATION["roughness"]),
        (("Subsurface Weight", "Subsurface"), SKIN_CALIBRATION["subsurface_weight"]),
        (("Subsurface Scale",), SKIN_CALIBRATION["subsurface_scale_m"]),
        (("Specular IOR Level", "Specular"), SKIN_CALIBRATION["specular_ior_level"]),
    ):
        socket = _material_input(principled, *names)
        if socket is not None:
            socket.default_value = float(value)
    material["warm_non_pale_calibration_v2"] = True
    return {
        "method": "owner_reference_appearance_calibrated_warm_skin_v2",
        **dict(SKIN_CALIBRATION),
        "material": material.name,
        "profile_source_color_preserved_as_provenance": True,
        "visual_requalification_required": True,
    }


def add_subtle_lip_material_v2(body: Any, lip_vertex_indices: Sequence[int]) -> dict[str, Any]:
    lip_set = {int(index) for index in lip_vertex_indices}
    if not lip_set:
        raise ProfiledPresentationV2Error("lip material requires target-derived vertices")
    material = v1._simple_material(  # noqa: SLF001
        "Kira_Profiled_Subtle_Natural_Lip_V2", "#9B6258", roughness=0.48
    )
    body.data.materials.append(material)
    material_index = len(body.data.materials) - 1
    selected = []
    for polygon in body.data.polygons:
        count = sum(int(index) in lip_set for index in polygon.vertices)
        if count >= max(3, len(polygon.vertices) - 1):
            polygon.material_index = material_index
            selected.append(int(polygon.index))
    if len(selected) < 20:
        raise ProfiledPresentationV2Error(
            f"target-derived lip face coverage too sparse: {len(selected)}"
        )
    body.data.update()
    return {
        "method": "target_derived_subtle_natural_lip_material_v2",
        "material": material.name,
        "lip_polygon_count": len(selected),
        "minimum_required_lip_polygon_count": 20,
        "lipstick_or_makeup_claim": False,
        "natural_lip_readability_only": True,
    }


def _object_bounds(obj: Any) -> tuple[Vector, Vector]:
    return v1._object_bounds(obj)  # noqa: SLF001


def _curve_object(
    name: str,
    splines: Sequence[Sequence[Vector]],
    material: Any,
    bevel_depth: float,
) -> Any:
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 2
    data.bevel_depth = float(bevel_depth)
    data.bevel_resolution = 2
    for points in splines:
        spline = data.splines.new("POLY")
        spline.points.add(len(points) - 1)
        for target, point in zip(spline.points, points):
            target.co = (*point, 1.0)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(material)
    return obj


def _project_face_point(tree: Any, x: float, z: float) -> Vector:
    origin = Vector((float(x), -0.45, float(z)))
    hit, normal, _face, _distance = tree.ray_cast(origin, Vector((0.0, 1.0, 0.0)), 1.0)
    if hit is None or normal is None:
        raise ProfiledPresentationV2Error(
            f"face adornment projection missed at x={x:.6f},z={z:.6f}"
        )
    if normal.dot(Vector((0.0, -1.0, 0.0))) < 0.0:
        normal = -normal
    return hit + normal.normalized() * 0.00042


def _parent_curve_to_bone(obj: Any, armature: Any, bone_name: str) -> None:
    """Rigidly attach a presentation curve without mesh-only vertex groups."""

    if obj is None or obj.type != "CURVE":
        raise ProfiledPresentationV2Error("facial curve attachment requires a curve")
    if armature is None or armature.type != "ARMATURE":
        raise ProfiledPresentationV2Error("facial curve attachment requires an armature")
    if armature.pose.bones.get(bone_name) is None:
        raise ProfiledPresentationV2Error(f"facial attachment bone missing: {bone_name}")
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = world


def add_feminine_eye_surrounds_v2(
    *, body: Any, armature: Any, eye_objects: Sequence[Any], candidate_id: str,
) -> tuple[list[Any], dict[str, Any]]:
    body_tree = v1._world_surface_bvh(body)  # noqa: SLF001
    brow_material = v1._simple_material(  # noqa: SLF001
        "Kira_Profiled_Natural_Brow_V2", "#2B1C18", roughness=0.72
    )
    lash_material = v1._simple_material(  # noqa: SLF001
        "Kira_Profiled_Natural_Lash_V2", "#171113", roughness=0.66
    )
    lid_material = v1._simple_material(  # noqa: SLF001
        "Kira_Profiled_Lid_Definition_V2", "#68443C", roughness=0.76
    )
    objects: list[Any] = []
    records: dict[str, Any] = {}
    for side in ("L", "R"):
        sclera = next(
            (obj for obj in eye_objects if f"sclera_{side}".lower() in obj.name.lower()),
            None,
        )
        iris = next(
            (obj for obj in eye_objects if f"disc_{side}".lower() in obj.name.lower()),
            None,
        )
        if sclera is None or iris is None:
            raise ProfiledPresentationV2Error(f"eye component inventory missing for {side}")
        low, high = _object_bounds(sclera)
        center = (low + high) * 0.5
        width = float(high.x - low.x)
        height = float(high.z - low.z)
        iris_low, iris_high = _object_bounds(iris)
        iris_center = (iris_low + iris_high) * 0.5
        for vertex in iris.data.vertices:
            vertex.co = iris_center + (vertex.co - iris_center) * 0.84
        iris.data.update()

        brow_splines: list[list[Vector]] = []
        sign = 1.0 if center.x >= 0.0 else -1.0
        for strand_index in range(13):
            u = -1.0 + 2.0 * strand_index / 12.0
            x = float(center.x + u * width * 0.53)
            arch = (1.0 - u * u) * height * 0.42
            z = float(high.z + height * 0.32 + arch + sign * u * height * 0.05)
            base = _project_face_point(body_tree, x, z)
            tip = _project_face_point(
                body_tree,
                x + sign * width * 0.025,
                z + height * (0.13 + 0.06 * (1.0 - abs(u))),
            )
            brow_splines.append([base, tip])
        brow = _curve_object(
            f"{candidate_id}_natural_brow_hairs_v2_{side}",
            brow_splines,
            brow_material,
            max(0.00026, height * 0.012),
        )

        upper: list[Vector] = []
        lower: list[Vector] = []
        for sample in range(13):
            u = -1.0 + 2.0 * sample / 12.0
            x = float(center.x + u * width * 0.46)
            upper_z = float(center.z + height * (0.18 + 0.15 * (1.0 - u * u)))
            lower_z = float(center.z - height * (0.15 + 0.09 * (1.0 - u * u)))
            upper.append(_project_face_point(body_tree, x, upper_z))
            lower.append(_project_face_point(body_tree, x, lower_z))
        lash = _curve_object(
            f"{candidate_id}_upper_lash_line_v2_{side}", [upper], lash_material, 0.00034
        )
        lid = _curve_object(
            f"{candidate_id}_lower_lid_definition_v2_{side}", [lower], lid_material, 0.00022
        )
        for obj, role in ((brow, "brow"), (lash, "upper_lash"), (lid, "lower_lid")):
            obj["candidate_id"] = candidate_id
            obj["profiled_nonanatomy_presentation_v2"] = True
            obj["facial_presentation_role"] = role
            obj["private_owner_review_only"] = True
            obj["runtime_activation_allowed"] = False
            _parent_curve_to_bone(obj, armature, "head")
            objects.append(obj)
        records[side] = {
            "sclera_width_m": width,
            "sclera_height_m": height,
            "iris_xz_scale_multiplier": 0.84,
            "brow_hair_strand_count": len(brow_splines),
            "upper_lash_sample_count": len(upper),
            "lower_lid_sample_count": len(lower),
            "components": [brow.name, lash.name, lid.name],
        }
    return objects, {
        "method": "source_eye_proportional_projected_brows_lashes_lids_v2",
        "object_count": len(objects),
        "brow_count": 2,
        "upper_lash_count": 2,
        "lower_lid_definition_count": 2,
        "iris_scale_reduced_from_r15": True,
        "facial_curve_attachment_method": "direct_head_bone_parent_preserve_world_matrix",
        "identity_geometry_substitute": False,
        "records": records,
        "visual_requalification_required": True,
    }


def round_existing_nail_silhouettes_v2(body: Any, nail_objects: Sequence[Any]) -> dict[str, Any]:
    body_tree = v1._world_surface_bvh(body)  # noqa: SLF001
    records: list[dict[str, Any]] = []
    for nail in nail_objects:
        grid = int(nail.get("projection_grid_size", 0))
        if grid < 5 or len(nail.data.vertices) != grid * grid:
            raise ProfiledPresentationV2Error(f"unexpected nail grid: {nail.name}")
        before = [vertex.co.copy() for vertex in nail.data.vertices]
        evaluations: list[dict[str, Any]] = []
        selected_strength: float | None = None
        clearance: dict[str, Any] = {}
        overlap_count = -1
        for strength in (1.0, 0.65, 0.40, 0.20):
            for vertex, point in zip(nail.data.vertices, before):
                vertex.co = point
            for row in range(grid):
                indices = [row * grid + column for column in range(grid)]
                center = sum((before[index] for index in indices), Vector()) / grid
                full_scale = rounded_nail_row_scale(row, grid)
                scale = 1.0 - float(strength) * (1.0 - full_scale)
                for index in indices:
                    nail.data.vertices[index].co = (
                        center + (before[index] - center) * scale
                    )
            nail.data.update()
            clearance = v1._body_clearance_record(body_tree, [nail])  # noqa: SLF001
            overlap_count = len(  # noqa: SLF001
                body_tree.overlap(v1._world_surface_bvh(nail))
            )
            minimum_clearance = float(
                clearance["minimum_unsigned_body_surface_clearance_m"]
            )
            passed = overlap_count == 0 and minimum_clearance >= 0.000045
            evaluations.append(
                {
                    "rounding_strength": float(strength),
                    "body_surface_triangle_overlap_count": overlap_count,
                    "minimum_clearance_m": minimum_clearance,
                    "fit_gate_passed": passed,
                }
            )
            if passed:
                selected_strength = float(strength)
                break
        if selected_strength is None:
            for vertex, point in zip(nail.data.vertices, before):
                vertex.co = point
            nail.data.update()
            raise ProfiledPresentationV2Error(f"rounded nail fit gate failed: {nail.name}")
        nail["rounded_natural_silhouette_v2"] = True
        records.append(
            {
                "object": nail.name,
                "grid": grid,
                "selected_rounding_strength": selected_strength,
                "proximal_width_scale": 1.0
                - selected_strength * (1.0 - rounded_nail_row_scale(0, grid)),
                "distal_width_scale": 1.0
                - selected_strength
                * (1.0 - rounded_nail_row_scale(grid - 1, grid)),
                "body_surface_triangle_overlap_count": overlap_count,
                "minimum_clearance_m": float(
                    clearance["minimum_unsigned_body_surface_clearance_m"]
                ),
                "bounded_fit_evaluations": evaluations,
            }
        )
    return {
        "method": "conformal_grid_rounded_cuticle_and_free_edge_v2",
        "nail_count": len(records),
        "all_twenty_nails_processed": len(records) == 20,
        "all_overlap_counts_zero": all(
            row["body_surface_triangle_overlap_count"] == 0 for row in records
        ),
        "records": records,
        "visual_requalification_required": True,
    }


def install_knee_corrective_smoothing_v2(
    body: Any, armature: Any, target_height_m: float,
) -> dict[str, Any]:
    height = float(target_height_m)
    records: dict[str, Any] = {}
    for side in ("L", "R"):
        bone = armature.data.bones.get(f"lowerleg01.{side}")
        if bone is None:
            raise ProfiledPresentationV2Error(f"knee bone missing: {side}")
        center = armature.matrix_world @ bone.head_local
        group = body.vertex_groups.get(f"AVATAR_BUILDER_KNEE_CORRECTIVE_V2_{side}")
        if group is None:
            group = body.vertex_groups.new(name=f"AVATAR_BUILDER_KNEE_CORRECTIVE_V2_{side}")
        weights: list[tuple[int, float]] = []
        for vertex in body.data.vertices:
            point = body.matrix_world @ vertex.co
            radial = math.sqrt(
                ((point.x - center.x) / (height * 0.072)) ** 2
                + ((point.y - center.y) / (height * 0.075)) ** 2
                + ((point.z - center.z) / (height * 0.090)) ** 2
            )
            if radial < 1.0:
                weight = (1.0 - radial * radial) ** 2
                group.add([vertex.index], weight, "REPLACE")
                weights.append((int(vertex.index), float(weight)))
        if len(weights) < 120:
            raise ProfiledPresentationV2Error(
                f"knee corrective region too sparse: {side};{len(weights)}"
            )
        modifier = body.modifiers.new(
            f"AvatarBuilder_Knee_CorrectiveSmooth_V2_{side}", "CORRECTIVE_SMOOTH"
        )
        modifier.vertex_group = group.name
        modifier.factor = 0.55
        modifier.iterations = 10
        modifier.scale = 1.0
        if hasattr(modifier, "smooth_type"):
            modifier.smooth_type = "LENGTH_WEIGHTED"
        if hasattr(modifier, "rest_source"):
            modifier.rest_source = "ORCO"
        if hasattr(modifier, "use_pin_boundary"):
            modifier.use_pin_boundary = True
        records[side] = {
            "group": group.name,
            "modifier": modifier.name,
            "weighted_vertex_count": len(weights),
            "maximum_weight": max(weight for _index, weight in weights),
            "factor": 0.55,
            "iterations": 10,
            "rest_source": getattr(modifier, "rest_source", "UNAVAILABLE"),
        }
    return {
        "method": "localized_length_weighted_corrective_smooth_v2",
        "records": records,
        "topology_changed": False,
        "pose_space_visual_and_silhouette_requalification_required": True,
    }


def evaluated_knee_profile(
    body: Any, armature: Any, side: str, target_height_m: float, bins: int = 25,
) -> dict[str, Any]:
    bone = armature.data.bones.get(f"lowerleg01.{side}")
    if bone is None:
        raise ProfiledPresentationV2Error(f"knee profile bone missing: {side}")
    center = armature.matrix_world @ bone.head_local
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()
    height = float(target_height_m)
    half_z = height * 0.105
    lateral = height * 0.065
    rows: list[list[Vector]] = [[] for _ in range(bins)]
    for point in points:
        if abs(float(point.x - center.x)) > lateral:
            continue
        normalized = (float(point.z - center.z) + half_z) / (2.0 * half_z)
        index = min(bins - 1, max(0, int(normalized * bins)))
        if 0.0 <= normalized <= 1.0:
            rows[index].append(point)
    if any(not row for row in rows):
        raise ProfiledPresentationV2Error(f"knee profile bins incomplete: {side}")
    anterior = [min(float(point.y) for point in row) for row in rows]
    posterior = [max(float(point.y) for point in row) for row in rows]
    widths = [back - front for front, back in zip(anterior, posterior)]
    return {
        "side": side,
        "bin_count": bins,
        "anterior_profile_y": anterior,
        "posterior_profile_y": posterior,
        "anterior_roughness": silhouette_roughness(anterior),
        "posterior_roughness": silhouette_roughness(posterior),
        "minimum_depth_m": min(widths),
        "maximum_depth_m": max(widths),
    }


def component_bone_frame_v2(
    armature: Any,
    *,
    side: str,
    kind: str,
    view_direction: Vector,
    target_height_m: float,
) -> dict[str, Any]:
    if kind == "hand":
        names = [f"wrist.{side}"] + [
            f"finger{digit}-{segment}.{side}"
            for digit in range(1, 6)
            for segment in range(1, 4)
        ]
        minimum = float(target_height_m) * 0.17
    elif kind == "foot":
        names = [f"foot.{side}"] + [
            f"toe{digit}-{segment}.{side}"
            for digit in range(1, 6)
            for segment in range(1, 4)
            if armature.data.bones.get(f"toe{digit}-{segment}.{side}") is not None
        ]
        minimum = float(target_height_m) * 0.18
    else:
        raise ProfiledPresentationV2Error("component frame kind must be hand or foot")
    bones = [armature.data.bones.get(name) for name in names]
    if any(bone is None for bone in bones):
        raise ProfiledPresentationV2Error(f"component frame bone inventory missing: {kind}.{side}")
    points = [
        armature.matrix_world @ endpoint
        for bone in bones
        for endpoint in (bone.head_local, bone.tail_local)
    ]
    target = sum(points, Vector()) / len(points)
    direction = view_direction.normalized()
    up = Vector((0.0, 0.0, 1.0))
    if abs(direction.dot(up)) > 0.93:
        up = Vector((0.0, 1.0, 0.0))
    right = direction.cross(up).normalized()
    true_up = right.cross(direction).normalized()
    projected = [(float((point - target).dot(right)), float((point - target).dot(true_up))) for point in points]
    extent = max(
        max(value[axis] for value in projected) - min(value[axis] for value in projected)
        for axis in range(2)
    )
    scale = max(minimum, extent * 1.55)
    return {
        "kind": kind,
        "side": side,
        "target": [float(value) for value in target],
        "view_direction": [float(value) for value in direction],
        "ortho_scale_m": float(scale),
        "bone_count": len(bones),
        "projected_bone_extent_m": float(extent),
        "full_component_margin_multiplier": 1.55,
    }


def install_shadow_controlled_review_rig_v2(scene: Any, target_height_m: float) -> tuple[Any, dict[str, Any]]:
    for obj in list(bpy.data.objects):
        if obj.type in {"LIGHT", "CAMERA"} and (
            obj.name.startswith("Kira_Private_")
            or obj.name.startswith("Kira_Profiled_Private_Review_Camera")
            or obj.name.startswith("AvatarBuilder_PresentationV2_")
        ):
            bpy.data.objects.remove(obj, do_unlink=True)
    camera_data = bpy.data.cameras.new("AvatarBuilder_PresentationV2_Camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("AvatarBuilder_PresentationV2_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    world = bpy.data.worlds.new("AvatarBuilder_PresentationV2_World")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = tuple(REVIEW_RIG["world_linear_rgba"])
    background.inputs["Strength"].default_value = float(REVIEW_RIG["world_strength"])
    scene.world = world
    layout = (
        ("key", Vector((-2.2, -3.0, target_height_m * 1.45))),
        ("fill", Vector((2.5, -1.6, target_height_m * 1.12))),
        ("rim", Vector((0.0, 2.8, target_height_m * 1.52))),
    )
    records = []
    for role, location in layout:
        config = REVIEW_RIG[role]
        data = bpy.data.lights.new(f"AvatarBuilder_PresentationV2_{role}", "AREA")
        data.energy = float(config["energy_w"])
        data.shape = "DISK"
        data.size = float(config["size_m"])
        data.color = (1.0, 1.0, 1.0)
        if hasattr(data, "use_shadow"):
            data.use_shadow = bool(config["casts_shadows"])
        light = bpy.data.objects.new(data.name, data)
        bpy.context.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (
            Vector((0.0, 0.0, target_height_m * 0.75)) - light.location
        ).to_track_quat("-Z", "Y").to_euler()
        records.append(
            {
                "role": role,
                "energy_w": data.energy,
                "size_m": data.size,
                "casts_shadows": bool(config["casts_shadows"]),
            }
        )
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "None"):
        try:
            scene.view_settings.look = look
            break
        except TypeError:
            continue
    scene.view_settings.exposure = float(REVIEW_RIG["exposure"])
    scene.view_settings.gamma = float(REVIEW_RIG["gamma"])
    report = {
        "method": "shadow_controlled_neutral_review_rig_v2",
        "world_linear_rgba": list(REVIEW_RIG["world_linear_rgba"]),
        "world_strength": float(REVIEW_RIG["world_strength"]),
        "exposure": float(REVIEW_RIG["exposure"]),
        "lights": records,
        "single_large_soft_key_is_only_shadow_caster": sum(
            row["casts_shadows"] for row in records
        ) == 1,
        "hand_shaped_fill_and_rim_cast_shadows_disabled": True,
    }
    scene["profiled_nonanatomy_presentation_v2_report"] = json.dumps(report, sort_keys=True)
    return camera, report


__all__ = [
    "METHOD_ID",
    "ProfiledPresentationV2Error",
    "add_feminine_eye_surrounds_v2",
    "add_subtle_lip_material_v2",
    "apply_qualitative_face_geometry_v2",
    "calibrate_warm_non_pale_skin_v2",
    "component_bone_frame_v2",
    "evaluated_knee_profile",
    "install_knee_corrective_smoothing_v2",
    "install_shadow_controlled_review_rig_v2",
    "round_existing_nail_silhouettes_v2",
]
