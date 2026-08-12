"""Blender-only components for a hash-bound profiled adult candidate.

This module deliberately contains no CLI and no top-level scene mutation.  It
reconstructs the licensed MakeHuman body/rig from their documented formats,
adds review components, and exposes an optional hash-bound dynamic-hair
provider interface.  It never imports a prior Kira/Robert/BlackProject body
builder and it contains no hard-coded anatomy vertex map.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import bpy
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree


POSTERIOR_WORLD_AXIS = "+Y"
ANATOMICAL_FORWARD_AXIS = "-Y"
HELPER_EYE_FIT_SCALE = 0.855
HELPER_EYE_POSTERIOR_INSET_M = 0.0022
SKIN_SUBSURFACE_SCALE_M = 0.00125
EYE_SOCKET_MINIMUM_CLEARANCE_M = 0.00004
EYE_OPTICAL_MINIMUM_LAYER_SEPARATION_M = 0.00018
EYE_OPTICAL_FIT_SCALE_PER_ITERATION = 0.98
EYE_OPTICAL_FIT_MAX_ITERATIONS = 8
EYE_OPTICAL_MINIMUM_CUMULATIVE_SCALE = 0.85
EYE_CORNEA_RIM_FORWARD_OFFSET_M = 0.00034
EYE_CORNEA_DOME_DEPTH_M = 0.00040
NAIL_MINIMUM_SURFACE_CLEARANCE_M = 0.000025
NAIL_MAXIMUM_SURFACE_CLEARANCE_M = 0.00040
NAIL_PROJECTION_GRID_SIZE = 9
NAIL_PROJECTION_CENTER_FRACTION_CANDIDATES = (0.52, 0.58, 0.64, 0.70, 0.76, 0.82)
NAIL_FOOTPRINT_SCALE_CANDIDATES = (1.0, 0.95, 0.90, 0.85)
NAIL_MINIMUM_FOOTPRINT_SCALE = 0.85
NAIL_MINIMUM_OUTWARD_NORMAL_ALIGNMENT = 0.12
NAIL_ADAPTIVE_NORMAL_LIFT_STEP_M = 0.000025
NAIL_ADAPTIVE_NORMAL_LIFT_MAX_ITERATIONS = 10
KNEE_REVIEW_FLEXION_DEGREES = 55
KNEE_DEFORMATION_GATE_ANGLES_DEGREES = (30, 55, 80)
FORBIDDEN_PROVIDER_TOKENS = (
    "blackproject",
    "blender_build_kira_temporary_functional_body",
    "blender_build_robert_temporary_functional_body",
)


class ProfiledAdultBlenderComponentError(RuntimeError):
    """Raised before a component can violate the private build contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ProfiledAdultBlenderComponentError(f"JSON root is not an object: {path}")
    return payload


def _converted_makehuman(point: Vector) -> Vector:
    """Convert MakeHuman Y-up/+Z-forward to Blender Z-up/-Y-forward."""

    return Vector((float(point.x), -float(point.z), float(point.y)))


def _parse_obj_vertices_and_group_faces(
    path: Path,
    requested_groups: Iterable[str],
) -> tuple[list[Vector], dict[str, list[tuple[int, ...]]]]:
    wanted = set(requested_groups)
    groups = {name: [] for name in wanted}
    vertices: list[Vector] = []
    active_groups: set[str] = set()
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if fields[0] == "v" and len(fields) >= 4:
                vertices.append(Vector(tuple(float(value) for value in fields[1:4])))
            elif fields[0] == "g":
                active_groups = wanted.intersection(fields[1:])
            elif fields[0] == "f" and active_groups:
                face: list[int] = []
                for token in fields[1:]:
                    raw_index = int(token.split("/", 1)[0])
                    index = raw_index - 1 if raw_index > 0 else len(vertices) + raw_index
                    if not 0 <= index < len(vertices):
                        raise ProfiledAdultBlenderComponentError(
                            f"OBJ face index out of range at line {line_number}"
                        )
                    face.append(index)
                if len(face) < 3:
                    raise ProfiledAdultBlenderComponentError(
                        f"OBJ face has fewer than three vertices at line {line_number}"
                    )
                packed = tuple(face)
                for name in active_groups:
                    groups[name].append(packed)
    if not vertices:
        raise ProfiledAdultBlenderComponentError("official base OBJ has no vertices")
    missing = sorted(name for name, faces in groups.items() if not faces)
    if missing:
        raise ProfiledAdultBlenderComponentError(
            "official base OBJ groups missing: " + ",".join(missing)
        )
    return vertices, groups


def _apply_target(
    vertices: list[Vector],
    path: Path,
    weight: float,
) -> int:
    if not 0.0 <= float(weight) <= 1.0:
        raise ProfiledAdultBlenderComponentError(f"target weight out of range: {path}")
    changed = 0
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, start=1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            fields = line.split()
            if len(fields) != 4:
                raise ProfiledAdultBlenderComponentError(
                    f"invalid target row at {path}:{line_number}"
                )
            index = int(fields[0])
            if not 0 <= index < len(vertices):
                raise ProfiledAdultBlenderComponentError(
                    f"target vertex out of range at {path}:{line_number}"
                )
            delta = Vector(tuple(float(value) for value in fields[1:4]))
            if delta.length_squared > 0.0 and weight > 0.0:
                vertices[index] += delta * float(weight)
                changed += 1
    return changed


def prepare_profiled_body_source(
    *,
    base_path: Path,
    female_macros: Sequence[Mapping[str, Any]],
    resolved_style_targets: Sequence[Mapping[str, Any]],
    project_root: Path,
    target_height_m: float,
) -> dict[str, Any]:
    """Apply macros and exact validated style targets before uniform scaling."""

    root = Path(project_root).resolve(strict=True)
    vertices, grouped = _parse_obj_vertices_and_group_faces(base_path, {"body"})
    applied: list[dict[str, Any]] = []
    ordered = [("female_macro", row) for row in female_macros]
    ordered.extend(("style_target", row) for row in resolved_style_targets)
    style_ids: list[str] = []
    for kind, record in ordered:
        relative = Path(str(record.get("path") or ""))
        if relative.is_absolute() or ".." in relative.parts:
            raise ProfiledAdultBlenderComponentError(f"unsafe {kind} path")
        path = (root / relative).resolve(strict=True)
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ProfiledAdultBlenderComponentError(f"escaped {kind} path") from exc
        expected = str(record.get("sha256") or "").lower()
        actual = sha256_file(path)
        if actual != expected:
            raise ProfiledAdultBlenderComponentError(f"{kind} hash mismatch: {relative}")
        weight = float(record.get("weight") or 0.0)
        changed = _apply_target(vertices, path, weight)
        target_id = str(record.get("target_id") or "")
        if kind == "style_target":
            if not target_id or record.get("verified") is not True:
                raise ProfiledAdultBlenderComponentError(
                    f"unverified style target supplied: {relative}"
                )
            style_ids.append(target_id)
        applied.append(
            {
                "kind": kind,
                "target_id": target_id or None,
                "path": relative.as_posix(),
                "sha256": actual,
                "weight": weight,
                "changed_source_vertices": changed,
            }
        )
    body_faces = grouped["body"]
    used = sorted({index for face in body_faces for index in face})
    source_to_body = {source: compact for compact, source in enumerate(used)}
    converted = [_converted_makehuman(vertices[index]) for index in used]
    low_z = min(point.z for point in converted)
    high_z = max(point.z for point in converted)
    source_height = float(high_z - low_z)
    target = float(target_height_m)
    if source_height <= 0.0 or not 1.35 <= target <= 2.05:
        raise ProfiledAdultBlenderComponentError("invalid source or target body height")
    scale = target / source_height
    body_vertices = [
        Vector((point.x * scale, point.y * scale, (point.z - low_z) * scale))
        for point in converted
    ]
    compact_faces = [tuple(source_to_body[index] for index in face) for face in body_faces]
    return {
        "source_vertices_after_all_targets": vertices,
        "body_vertices": body_vertices,
        "body_faces": compact_faces,
        "source_to_body": source_to_body,
        "source_floor_z": float(low_z),
        "uniform_scale": float(scale),
        "source_height_units": source_height,
        "target_height_m": target,
        "applied_targets": applied,
        "style_target_ids_in_application_order": style_ids,
        "style_target_count": len(style_ids),
        "body_face_group_only": True,
        "male_helper_groups_used": False,
        "copied_anatomy_geometry_used": False,
    }


def transformed_source_point(source: Mapping[str, Any], source_index: int) -> Vector:
    point = _converted_makehuman(source["source_vertices_after_all_targets"][source_index])
    scale = float(source["uniform_scale"])
    return Vector(
        (
            point.x * scale,
            point.y * scale,
            (point.z - float(source["source_floor_z"])) * scale,
        )
    )


def srgb_channel_to_linear(value: float) -> float:
    channel = max(0.0, min(1.0, float(value)))
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def srgb_hex_to_linear_rgba(value: str) -> tuple[float, float, float, float]:
    if len(value) != 7 or not value.startswith("#"):
        raise ProfiledAdultBlenderComponentError("sRGB color must be #RRGGBB")
    try:
        channels = tuple(int(value[index : index + 2], 16) / 255.0 for index in (1, 3, 5))
    except ValueError as exc:
        raise ProfiledAdultBlenderComponentError("invalid sRGB color") from exc
    return tuple(srgb_channel_to_linear(channel) for channel in channels) + (1.0,)


def _principled_input(node: Any, *names: str) -> Any:
    for name in names:
        found = node.inputs.get(name)
        if found is not None:
            return found
    return None


def build_warm_skin_material(profile: Mapping[str, Any]) -> tuple[Any, dict[str, Any]]:
    skin = profile["material_profile"]["skin"]
    base_hex = str(skin["base_srgb_hex"])
    if base_hex.upper() != "#C7A08E" or skin.get("microvariation_required") is not True:
        raise ProfiledAdultBlenderComponentError("exact warm skin profile not supplied")
    base = srgb_hex_to_linear_rgba(base_hex)
    roughness = sum(float(value) for value in skin["roughness_range"]) * 0.5
    subsurface = sum(float(value) for value in skin["subsurface_weight_range"]) * 0.5
    material = bpy.data.materials.new("Kira_Profiled_Warm_C7A08E_Skin")
    material.use_nodes = True
    material.diffuse_color = base
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = nodes.get("Principled BSDF")
    if principled is None:
        raise ProfiledAdultBlenderComponentError("Principled BSDF unavailable")
    coordinates = nodes.new("ShaderNodeTexCoord")
    coordinates.name = "Kira_Skin_Generated_Coordinates"
    noise = nodes.new("ShaderNodeTexNoise")
    noise.name = "Kira_Subtle_Skin_Microvariation"
    noise.inputs["Scale"].default_value = 34.0
    noise.inputs["Detail"].default_value = 2.25
    noise.inputs["Roughness"].default_value = 0.48
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.name = "Kira_Bounded_Warm_Microvariation"
    darker = tuple(max(0.0, channel * 0.965) for channel in base[:3]) + (1.0,)
    lighter = tuple(min(1.0, channel * 1.035) for channel in base[:3]) + (1.0,)
    ramp.color_ramp.elements[0].position = 0.32
    ramp.color_ramp.elements[0].color = darker
    ramp.color_ramp.elements[1].position = 0.68
    ramp.color_ramp.elements[1].color = lighter
    links.new(coordinates.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    base_input = _principled_input(principled, "Base Color")
    if base_input is None:
        raise ProfiledAdultBlenderComponentError("Principled base color unavailable")
    links.new(ramp.outputs["Color"], base_input)
    roughness_input = _principled_input(principled, "Roughness")
    subsurface_input = _principled_input(principled, "Subsurface Weight", "Subsurface")
    if roughness_input is not None:
        roughness_input.default_value = roughness
    if subsurface_input is not None:
        subsurface_input.default_value = subsurface
    radius = _principled_input(principled, "Subsurface Radius")
    if radius is not None:
        radius.default_value = (1.0, 0.42, 0.24)
    subsurface_scale = _principled_input(principled, "Subsurface Scale")
    if subsurface_scale is None:
        raise ProfiledAdultBlenderComponentError(
            "Principled subsurface scale unavailable; refusing unbounded wax-like skin"
        )
    subsurface_scale.default_value = SKIN_SUBSURFACE_SCALE_M
    specular = _principled_input(principled, "Specular IOR Level", "Specular")
    if specular is not None:
        specular.default_value = 0.34
    bump = nodes.new("ShaderNodeBump")
    bump.name = "Kira_Subtle_Skin_Micro_Bump"
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.00016
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    normal = _principled_input(principled, "Normal")
    if normal is not None:
        links.new(bump.outputs["Normal"], normal)
    return material, {
        "base_srgb_hex": base_hex,
        "base_linear_rgba": [float(value) for value in base],
        "conversion": "IEC_61966_2_1_srgb_piecewise_to_scene_linear",
        "roughness": roughness,
        "subsurface_weight": subsurface,
        "subsurface_scale_m": SKIN_SUBSURFACE_SCALE_M,
        "subsurface_scale_source": "bounded_real_skin_component_constant_v1",
        "microvariation": "Noise_Texture_to_bounded_Color_Ramp",
        "microvariation_amplitude_fraction": 0.035,
        "micro_bump_distance_m": 0.00016,
        "micro_bump_strength": 0.12,
        "pale_r13_direction_used": False,
    }


def _simple_material(
    name: str,
    srgb_hex: str,
    *,
    roughness: float,
    transmission_weight: float = 0.0,
    alpha: float = 1.0,
) -> Any:
    color = srgb_hex_to_linear_rgba(srgb_hex)
    color = color[:3] + (float(alpha),)
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Roughness"].default_value = float(roughness)
        transmission = _principled_input(principled, "Transmission Weight", "Transmission")
        if transmission is not None:
            transmission.default_value = float(transmission_weight)
        alpha_input = _principled_input(principled, "Alpha")
        if alpha_input is not None:
            alpha_input.default_value = float(alpha)
        ior = _principled_input(principled, "IOR")
        if ior is not None and transmission_weight:
            ior.default_value = 1.376
    if alpha < 1.0:
        if hasattr(material, "surface_render_method"):
            material.surface_render_method = "DITHERED"
        elif hasattr(material, "blend_method"):
            material.blend_method = "BLEND"
    return material


def _natural_iris_material(name: str, srgb_hex: str) -> Any:
    """Create deterministic radial iris fibres without overlapping geometry."""

    base = srgb_hex_to_linear_rgba(srgb_hex)
    material = _simple_material(name, srgb_hex, roughness=0.31)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = nodes.get("Principled BSDF")
    if principled is None:
        raise ProfiledAdultBlenderComponentError("iris Principled BSDF unavailable")
    coordinates = nodes.new("ShaderNodeTexCoord")
    coordinates.name = "Kira_Iris_Generated_Coordinates"
    separate = nodes.new("ShaderNodeSeparateXYZ")
    separate.name = "Kira_Iris_Coordinate_Components"
    centered_x = nodes.new("ShaderNodeMath")
    centered_x.name = "Kira_Iris_Centered_X"
    centered_x.operation = "SUBTRACT"
    centered_x.inputs[1].default_value = 0.5
    centered_z = nodes.new("ShaderNodeMath")
    centered_z.name = "Kira_Iris_Centered_Z"
    centered_z.operation = "SUBTRACT"
    centered_z.inputs[1].default_value = 0.5
    angle = nodes.new("ShaderNodeMath")
    angle.name = "Kira_Iris_Radial_Angle"
    angle.operation = "ARCTAN2"
    spoke_scale = nodes.new("ShaderNodeMath")
    spoke_scale.name = "Kira_Iris_Fibre_Frequency"
    spoke_scale.operation = "MULTIPLY"
    spoke_scale.inputs[1].default_value = 53.0
    spokes = nodes.new("ShaderNodeMath")
    spokes.name = "Kira_Iris_Radial_Fibres"
    spokes.operation = "SINE"
    half = nodes.new("ShaderNodeMath")
    half.operation = "MULTIPLY"
    half.inputs[1].default_value = 0.5
    mapped_spokes = nodes.new("ShaderNodeMath")
    mapped_spokes.operation = "ADD"
    mapped_spokes.inputs[1].default_value = 0.5
    noise = nodes.new("ShaderNodeTexNoise")
    noise.name = "Kira_Natural_Iris_Variation"
    noise.inputs["Scale"].default_value = 6.0
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.62
    noise.inputs["Distortion"].default_value = 0.08
    variation = nodes.new("ShaderNodeMath")
    variation.name = "Kira_Iris_Radial_Noise_Product"
    variation.operation = "MULTIPLY"
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.name = "Kira_Bounded_Brown_Iris_Ramp"
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = tuple(channel * 0.68 for channel in base[:3]) + (1.0,)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = tuple(
        min(1.0, channel * 1.24) for channel in base[:3]
    ) + (1.0,)
    links.new(coordinates.outputs["Generated"], separate.inputs[0])
    links.new(separate.outputs["X"], centered_x.inputs[0])
    links.new(separate.outputs["Z"], centered_z.inputs[0])
    links.new(centered_z.outputs[0], angle.inputs[0])
    links.new(centered_x.outputs[0], angle.inputs[1])
    links.new(angle.outputs[0], spoke_scale.inputs[0])
    links.new(spoke_scale.outputs[0], spokes.inputs[0])
    links.new(spokes.outputs[0], half.inputs[0])
    links.new(half.outputs[0], mapped_spokes.inputs[0])
    links.new(coordinates.outputs["Generated"], noise.inputs["Vector"])
    links.new(mapped_spokes.outputs[0], variation.inputs[0])
    links.new(noise.outputs["Fac"], variation.inputs[1])
    links.new(variation.outputs[0], ramp.inputs["Fac"])
    base_input = principled.inputs.get("Base Color")
    if base_input is None:
        raise ProfiledAdultBlenderComponentError("iris base color unavailable")
    links.new(ramp.outputs["Color"], base_input)
    return material


def build_body_object(source: Mapping[str, Any], candidate_id: str, material: Any) -> Any:
    mesh = bpy.data.meshes.new(f"{candidate_id}_primary_adult_surface")
    mesh.from_pydata(
        [tuple(point) for point in source["body_vertices"]],
        [],
        source["body_faces"],
    )
    mesh.update(calc_edges=True)
    body = bpy.data.objects.new(f"{candidate_id}_primary_adult_surface", mesh)
    bpy.context.collection.objects.link(body)
    body.data.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    body["candidate_id"] = candidate_id
    body["candidate_author_id"] = (
        "profiled_confirmed_adult_female_candidate_builder_v1"
    )
    body["primary_surface"] = True
    body["body_class"] = "adult_female"
    body["confirmed_adult"] = True
    body["generic_identity_neutral_foundation"] = False
    body["kira_styling_applied"] = True
    body["source_geometry_copied"] = False
    body["wrong_sex_helper_present"] = False
    body["private_owner_review_only"] = True
    body["inactive_candidate"] = True
    body["runtime_activation_allowed"] = False
    body["roster_registration_allowed"] = False
    body["clothing_included"] = False
    body["publication_allowed"] = False
    body["anatomical_forward_axis"] = ANATOMICAL_FORWARD_AXIS
    return body


def _joint_positions(rig: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Vector]:
    result: dict[str, Vector] = {}
    source_count = len(source["source_vertices_after_all_targets"])
    for name, raw_indices in rig["joints"].items():
        indices = [int(value) for value in raw_indices]
        if not indices or any(not 0 <= index < source_count for index in indices):
            raise ProfiledAdultBlenderComponentError(f"invalid rig joint indices: {name}")
        point = sum(
            (transformed_source_point(source, index) for index in indices),
            Vector((0.0, 0.0, 0.0)),
        ) / len(indices)
        result[str(name)] = point
    return result


def _plane_normal(
    plane_name: str,
    rig: Mapping[str, Any],
    joints: Mapping[str, Vector],
) -> Vector | None:
    names = rig.get("planes", {}).get(plane_name)
    if not isinstance(names, list) or len(names) != 3 or any(name not in joints for name in names):
        return None
    first = (joints[names[1]] - joints[names[0]]).normalized()
    second = (joints[names[2]] - joints[names[1]]).normalized()
    normal = second.cross(first)
    return normal.normalized() if normal.length > 1.0e-8 else None


def build_official_rig_and_normalized_weights(
    *,
    body: Any,
    source: Mapping[str, Any],
    skeleton_path: Path,
    weights_path: Path,
    candidate_id: str,
    maximum_influences: int = 4,
) -> tuple[Any, dict[str, Any]]:
    if maximum_influences != 4:
        raise ProfiledAdultBlenderComponentError("exact four-influence policy required")
    rig = _read_json(skeleton_path)
    weight_payload = _read_json(weights_path)
    joints = _joint_positions(rig, source)
    armature_data = bpy.data.armatures.new(f"{candidate_id}_official_skeleton")
    armature = bpy.data.objects.new(f"{candidate_id}_official_rig", armature_data)
    bpy.context.collection.objects.link(armature)
    armature.show_in_front = True
    for key, value in {
        "candidate_id": candidate_id,
        "private_owner_review_only": True,
        "inactive_candidate": True,
        "runtime_activation_allowed": False,
        "roster_registration_allowed": False,
    }.items():
        armature[key] = value
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    remaining = dict(rig["bones"])
    built: set[str] = set()
    while remaining:
        progressed = False
        for name, definition in list(remaining.items()):
            parent = definition.get("parent")
            if parent and parent not in built:
                continue
            head = joints[definition["head"]]
            tail = joints[definition["tail"]]
            if (tail - head).length < 1.0e-5:
                tail = head + Vector((0.0, 0.0, 0.01))
            bone = armature_data.edit_bones.new(name)
            bone.head = head
            bone.tail = tail
            bone.use_deform = name in weight_payload["weights"]
            if parent:
                bone.parent = armature_data.edit_bones[parent]
                bone.use_connect = (bone.head - bone.parent.tail).length < 0.0005
            raw_planes = definition.get("rotation_plane")
            plane_names = raw_planes if isinstance(raw_planes, list) else [raw_planes]
            normals = [
                normal
                for plane_name in plane_names
                if isinstance(plane_name, str)
                for normal in [_plane_normal(plane_name, rig, joints)]
                if normal is not None
            ]
            if normals:
                try:
                    bone.align_roll(sum(normals, Vector((0.0, 0.0, 0.0))).normalized())
                except ValueError:
                    pass
            built.add(name)
            del remaining[name]
            progressed = True
        if not progressed:
            bpy.ops.object.mode_set(mode="OBJECT")
            raise ProfiledAdultBlenderComponentError(
                "unresolved rig parents: " + ",".join(sorted(remaining))
            )
    bpy.ops.object.mode_set(mode="OBJECT")

    source_to_body = source["source_to_body"]
    per_vertex: list[dict[str, float]] = [defaultdict(float) for _ in body.data.vertices]
    for bone_name, assignments in weight_payload["weights"].items():
        for raw_index, raw_weight in assignments:
            compact = source_to_body.get(int(raw_index))
            weight = float(raw_weight)
            if compact is not None and weight > 1.0e-10:
                per_vertex[int(compact)][str(bone_name)] += weight
    root_name = "root"
    normalized: list[list[tuple[str, float]]] = []
    fallback_count = 0
    for row in per_vertex:
        top = sorted(row.items(), key=lambda item: (-item[1], item[0]))[:maximum_influences]
        total = sum(weight for _name, weight in top)
        if total <= 1.0e-10:
            top = [(root_name, 1.0)]
            fallback_count += 1
        else:
            top = [(name, weight / total) for name, weight in top]
        normalized.append(top)
    group_names = sorted({name for row in normalized for name, _weight in row})
    groups = {name: body.vertex_groups.new(name=name) for name in group_names}
    assignment_count = 0
    for vertex_index, row in enumerate(normalized):
        for name, weight in row:
            groups[name].add([vertex_index], weight, "REPLACE")
            assignment_count += 1
    modifier = body.modifiers.new("Official_MakeHuman_Normalized_Rig", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True
    sums = [sum(weight for _name, weight in row) for row in normalized]
    counts = [len(row) for row in normalized]
    if not sums or min(sums) < 0.999999 or max(sums) > 1.000001 or max(counts) > 4:
        raise ProfiledAdultBlenderComponentError("normalized skin-weight invariant failed")
    return armature, {
        "skeleton_path": str(Path(skeleton_path)),
        "skeleton_sha256": sha256_file(skeleton_path),
        "weights_path": str(Path(weights_path)),
        "weights_sha256": sha256_file(weights_path),
        "bone_count": len(armature.data.bones),
        "deform_bone_count": sum(1 for bone in armature.data.bones if bone.use_deform),
        "weighted_vertex_count": len(normalized),
        "unweighted_vertex_count": 0,
        "fallback_root_vertex_count": fallback_count,
        "maximum_influences": max(counts),
        "weight_sum_minimum": min(sums),
        "weight_sum_maximum": max(sums),
        "weight_assignment_count": assignment_count,
        "normalization_required_and_applied": True,
        "armature_preserve_volume_enabled": True,
    }


def assign_rigid_bone(obj: Any, armature: Any, bone_name: str) -> None:
    if armature.data.bones.get(bone_name) is None:
        raise ProfiledAdultBlenderComponentError(f"required rigid bone missing: {bone_name}")
    group = obj.vertex_groups.new(name=bone_name)
    group.add([vertex.index for vertex in obj.data.vertices], 1.0, "REPLACE")
    modifier = obj.modifiers.new("Official_Rigid_Bone_Attachment", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.matrix_parent_inverse = armature.matrix_world.inverted()
    obj.matrix_world = world


def _build_group_mesh(
    *,
    name: str,
    faces: Sequence[Sequence[int]],
    source: Mapping[str, Any],
    material: Any,
) -> tuple[Any, dict[str, Any]]:
    used = sorted({int(index) for face in faces for index in face})
    mapping = {source_index: local for local, source_index in enumerate(used)}
    points = [transformed_source_point(source, index) for index in used]
    compact_faces = [tuple(mapping[int(index)] for index in face) for face in faces]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(point) for point in points], [], compact_faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj, {"source_vertex_count": len(used), "source_face_count": len(faces)}


def _object_bounds(obj: Any) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def _uv_sphere(
    name: str,
    location: Vector,
    scale: Sequence[float],
    material: Any,
    *,
    segments: int = 24,
    ring_count: int = 12,
) -> Any:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=ring_count,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(float(value) for value in scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def _world_surface_bvh(obj: Any) -> BVHTree:
    mesh = obj.data
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
    triangles = [tuple(int(value) for value in triangle.vertices) for triangle in mesh.loop_triangles]
    if not points or not triangles:
        raise ProfiledAdultBlenderComponentError("body surface BVH input is empty")
    return BVHTree.FromPolygons(points, triangles, all_triangles=True)


def _body_clearance_record(tree: BVHTree, objects: Sequence[Any]) -> dict[str, Any]:
    distances: list[float] = []
    for obj in objects:
        for vertex in obj.data.vertices:
            nearest = tree.find_nearest(obj.matrix_world @ vertex.co)
            if nearest[0] is None:
                raise ProfiledAdultBlenderComponentError(
                    f"body clearance query failed: {obj.name}"
                )
            distances.append(float(nearest[3]))
    if not distances:
        raise ProfiledAdultBlenderComponentError("body clearance record has no samples")
    distances.sort()
    percentile_05 = distances[max(0, int(len(distances) * 0.05) - 1)]
    return {
        "sample_count": len(distances),
        "minimum_unsigned_body_surface_clearance_m": distances[0],
        "percentile_05_unsigned_body_surface_clearance_m": percentile_05,
        "median_unsigned_body_surface_clearance_m": distances[len(distances) // 2],
        "maximum_unsigned_body_surface_clearance_m": distances[-1],
    }


def _radial_iris_disc(
    *,
    name: str,
    center: Vector,
    radius_x: float,
    radius_z: float,
    limbal_material: Any,
    iris_material: Any,
    pupil_material: Any,
    segments: int = 64,
) -> Any:
    """Build one continuous optical disc; pupil, iris, and limbal faces never overlap."""

    if segments < 32 or radius_x <= 0.0 or radius_z <= 0.0:
        raise ProfiledAdultBlenderComponentError("invalid radial iris-disc dimensions")
    ring_fractions = (0.34, 0.88, 1.0)
    points = [Vector((center.x, center.y - 0.00010, center.z))]
    for fraction in ring_fractions:
        bulge = 0.00010 * (1.0 - fraction * fraction)
        for index in range(segments):
            angle = math.tau * (index / segments)
            points.append(
                Vector(
                    (
                        center.x + math.cos(angle) * radius_x * fraction,
                        center.y - bulge,
                        center.z + math.sin(angle) * radius_z * fraction,
                    )
                )
            )
    first_ring = 1
    second_ring = first_ring + segments
    third_ring = second_ring + segments
    faces: list[tuple[int, ...]] = []
    material_indices: list[int] = []
    for index in range(segments):
        following = (index + 1) % segments
        faces.append((0, first_ring + index, first_ring + following))
        material_indices.append(2)
        faces.append(
            (
                first_ring + index,
                second_ring + index,
                second_ring + following,
                first_ring + following,
            )
        )
        material_indices.append(1)
        faces.append(
            (
                second_ring + index,
                third_ring + index,
                third_ring + following,
                second_ring + following,
            )
        )
        material_indices.append(0)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(point) for point in points], [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for material in (limbal_material, iris_material, pupil_material):
        mesh.materials.append(material)
    for polygon, material_index in zip(mesh.polygons, material_indices):
        polygon.material_index = material_index
        polygon.use_smooth = True
    obj["single_continuous_nonoverlapping_optical_disc"] = True
    obj["pupil_iris_coplanar_overlap_face_count"] = 0
    obj["radial_iris_fibre_shader"] = True
    return obj


def _shallow_cornea_dome(
    *,
    name: str,
    center: Vector,
    radius_x: float,
    radius_z: float,
    rim_y: float,
    depth_m: float,
    material: Any,
    segments: int = 64,
    ring_count: int = 8,
) -> Any:
    """Build only the visible anterior cornea, never a socket-crossing full sphere."""

    if (
        segments < 32
        or ring_count < 4
        or radius_x <= 0.0
        or radius_z <= 0.0
        or depth_m <= 0.0
    ):
        raise ProfiledAdultBlenderComponentError("invalid shallow cornea-dome dimensions")
    points = [Vector((center.x, rim_y - depth_m, center.z))]
    for ring_index in range(1, ring_count + 1):
        fraction = ring_index / ring_count
        y = rim_y - depth_m * (1.0 - fraction * fraction)
        for segment_index in range(segments):
            angle = math.tau * (segment_index / segments)
            points.append(
                Vector(
                    (
                        center.x + math.cos(angle) * radius_x * fraction,
                        y,
                        center.z + math.sin(angle) * radius_z * fraction,
                    )
                )
            )
    faces: list[tuple[int, ...]] = []
    for segment_index in range(segments):
        following = (segment_index + 1) % segments
        faces.append((0, 1 + segment_index, 1 + following))
    for ring_index in range(1, ring_count):
        inner_start = 1 + (ring_index - 1) * segments
        outer_start = 1 + ring_index * segments
        for segment_index in range(segments):
            following = (segment_index + 1) % segments
            faces.append(
                (
                    inner_start + segment_index,
                    outer_start + segment_index,
                    outer_start + following,
                    inner_start + following,
                )
            )
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(point) for point in points], [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj["transparent_open_anterior_cornea_dome"] = True
    obj["full_socket_crossing_cornea_sphere_used"] = False
    return obj


def _adapt_eye_component_to_socket(tree: BVHTree, obj: Any) -> dict[str, Any]:
    """Boundedly reduce only X/Z aperture span until the exact body gate passes."""

    initial_clearance = _body_clearance_record(tree, [obj])
    initial_overlap_count = len(tree.overlap(_world_surface_bvh(obj)))
    final_clearance = initial_clearance
    final_overlap_count = initial_overlap_count
    fit_iterations = 0
    cumulative_scale = 1.0
    while (
        final_overlap_count != 0
        or final_clearance["minimum_unsigned_body_surface_clearance_m"]
        < EYE_SOCKET_MINIMUM_CLEARANCE_M
    ) and fit_iterations < EYE_OPTICAL_FIT_MAX_ITERATIONS:
        points = [vertex.co.copy() for vertex in obj.data.vertices]
        low_x = min(point.x for point in points)
        high_x = max(point.x for point in points)
        low_z = min(point.z for point in points)
        high_z = max(point.z for point in points)
        center_x = (low_x + high_x) * 0.5
        center_z = (low_z + high_z) * 0.5
        for vertex in obj.data.vertices:
            vertex.co.x = center_x + (
                vertex.co.x - center_x
            ) * EYE_OPTICAL_FIT_SCALE_PER_ITERATION
            vertex.co.z = center_z + (
                vertex.co.z - center_z
            ) * EYE_OPTICAL_FIT_SCALE_PER_ITERATION
        obj.data.update()
        fit_iterations += 1
        cumulative_scale *= EYE_OPTICAL_FIT_SCALE_PER_ITERATION
        final_clearance = _body_clearance_record(tree, [obj])
        final_overlap_count = len(tree.overlap(_world_surface_bvh(obj)))
    fit_passed = (
        final_overlap_count == 0
        and final_clearance["minimum_unsigned_body_surface_clearance_m"]
        >= EYE_SOCKET_MINIMUM_CLEARANCE_M
        and cumulative_scale >= EYE_OPTICAL_MINIMUM_CUMULATIVE_SCALE
    )
    if not fit_passed:
        raise ProfiledAdultBlenderComponentError(
            "bounded eye optical-component socket fit failed: "
            f"{obj.name};overlaps={final_overlap_count};"
            f"iterations={fit_iterations};scale={cumulative_scale:.9f}"
        )
    return {
        "initial_body_surface_triangle_overlap_count": initial_overlap_count,
        "final_body_surface_triangle_overlap_count": final_overlap_count,
        "initial_socket_clearance": initial_clearance,
        "final_socket_clearance": final_clearance,
        "adaptive_fit_iteration_count": fit_iterations,
        "cumulative_xz_fit_scale": cumulative_scale,
        "minimum_allowed_cumulative_xz_fit_scale": (
            EYE_OPTICAL_MINIMUM_CUMULATIVE_SCALE
        ),
        "bounded_socket_fit_passed": True,
    }


def add_natural_helper_eyes(
    *,
    base_path: Path,
    source: Mapping[str, Any],
    body: Any,
    armature: Any,
    eye_profile: Mapping[str, Any],
    candidate_id: str,
) -> tuple[list[Any], dict[str, Any]]:
    if eye_profile.get("iris_color_family") != "brown":
        raise ProfiledAdultBlenderComponentError("natural brown eye profile required")
    if eye_profile.get("black_band_artifact_forbidden") is not True:
        raise ProfiledAdultBlenderComponentError("black-band prohibition missing")
    _vertices, groups = _parse_obj_vertices_and_group_faces(
        base_path, {"helper-l-eye", "helper-r-eye"}
    )
    if body is None or body.type != "MESH":
        raise ProfiledAdultBlenderComponentError("eye socket fit requires the exact body mesh")
    body_tree = _world_surface_bvh(body)
    sclera_material = _simple_material(
        "Kira_Profiled_Natural_Sclera", "#C8BAB0", roughness=0.42
    )
    limbal_material = _simple_material(
        "Kira_Profiled_Brown_Limbal", str(eye_profile["limbal_srgb_hex"]), roughness=0.34
    )
    iris_material = _natural_iris_material(
        "Kira_Profiled_Natural_Brown_Iris", str(eye_profile["iris_srgb_hex"])
    )
    pupil_material = _simple_material(
        "Kira_Profiled_Pupil", "#090604", roughness=0.2
    )
    cornea_material = _simple_material(
        "Kira_Profiled_Transparent_Cornea",
        "#FFFFFF",
        roughness=0.08,
        transmission_weight=1.0,
        alpha=0.12,
    )
    objects: list[Any] = []
    records: dict[str, Any] = {}
    for side, group_name in (("L", "helper-l-eye"), ("R", "helper-r-eye")):
        sclera, record = _build_group_mesh(
            name=f"{candidate_id}_official_helper_eye_sclera_{side}",
            faces=groups[group_name],
            source=source,
            material=sclera_material,
        )
        low, high = _object_bounds(sclera)
        center = (low + high) * 0.5
        for vertex in sclera.data.vertices:
            vertex.co = center + (vertex.co - center) * HELPER_EYE_FIT_SCALE
            vertex.co.y += HELPER_EYE_POSTERIOR_INSET_M
        sclera.data.update()
        sclera_clearance = _body_clearance_record(body_tree, [sclera])
        fit_iterations = 0
        while (
            sclera_clearance["minimum_unsigned_body_surface_clearance_m"]
            < EYE_SOCKET_MINIMUM_CLEARANCE_M
            and fit_iterations < 8
        ):
            low, high = _object_bounds(sclera)
            center = (low + high) * 0.5
            for vertex in sclera.data.vertices:
                vertex.co = center + (vertex.co - center) * 0.992
                vertex.co.y += 0.00006
            sclera.data.update()
            fit_iterations += 1
            sclera_clearance = _body_clearance_record(body_tree, [sclera])
        if (
            sclera_clearance["minimum_unsigned_body_surface_clearance_m"]
            < EYE_SOCKET_MINIMUM_CLEARANCE_M
        ):
            raise ProfiledAdultBlenderComponentError(
                f"measured eye socket clearance failed: {side}"
            )
        low, high = _object_bounds(sclera)
        center = (low + high) * 0.5
        radii = (high - low) * 0.5
        front_y = float(low.y)
        iris = _radial_iris_disc(
            name=f"{candidate_id}_brown_iris_radial_disc_{side}",
            center=Vector((center.x, front_y - 0.00042, center.z)),
            radius_x=float(radii.x * 0.39),
            radius_z=float(radii.z * 0.39),
            limbal_material=limbal_material,
            iris_material=iris_material,
            pupil_material=pupil_material,
            segments=64,
        )
        iris_fit = _adapt_eye_component_to_socket(body_tree, iris)
        cornea = _shallow_cornea_dome(
            name=f"{candidate_id}_transparent_cornea_cap_{side}",
            center=center,
            radius_x=float(radii.x * 0.42),
            radius_z=float(radii.z * 0.42),
            rim_y=front_y - EYE_CORNEA_RIM_FORWARD_OFFSET_M,
            depth_m=EYE_CORNEA_DOME_DEPTH_M,
            material=cornea_material,
            segments=40,
            ring_count=20,
        )
        cornea_fit = _adapt_eye_component_to_socket(body_tree, cornea)
        iris_low, _iris_high = _object_bounds(iris)
        cornea_low, _cornea_high = _object_bounds(cornea)
        optical_separation = float(iris_low.y - cornea_low.y)
        if optical_separation < EYE_OPTICAL_MINIMUM_LAYER_SEPARATION_M:
            raise ProfiledAdultBlenderComponentError(
                f"eye optical layer separation failed: {side}"
            )
        component_clearance = _body_clearance_record(body_tree, [sclera, iris, cornea])
        overlap_count = sum(
            len(body_tree.overlap(_world_surface_bvh(obj)))
            for obj in (sclera, iris, cornea)
        )
        if (
            component_clearance["minimum_unsigned_body_surface_clearance_m"]
            < EYE_SOCKET_MINIMUM_CLEARANCE_M
            or overlap_count != 0
        ):
            raise ProfiledAdultBlenderComponentError(
                f"eye socket/component clearance failed: {side};overlaps={overlap_count}"
            )
        for obj in (sclera, iris, cornea):
            obj["candidate_id"] = candidate_id
            obj["private_owner_review_only"] = True
            obj["inactive_candidate"] = True
            obj["runtime_activation_allowed"] = False
            obj["eye_component"] = True
            obj["intentionally_authored_black_band_object"] = False
            obj["measured_body_surface_clearance_m"] = float(
                component_clearance["minimum_unsigned_body_surface_clearance_m"]
            )
            obj["body_surface_triangle_overlap_count"] = overlap_count
            obj["visual_black_band_absence_proven"] = False
            assign_rigid_bone(obj, armature, f"eye.{side}")
            objects.append(obj)
        records[side] = {
            **record,
            "source_group": group_name,
            "fit_scale_initial": HELPER_EYE_FIT_SCALE,
            "posterior_inset_m": HELPER_EYE_POSTERIOR_INSET_M,
            "adaptive_fit_iteration_count": fit_iterations,
            "component_names": [obj.name for obj in (sclera, iris, cornea)],
            "single_continuous_nonoverlapping_optical_disc": True,
            "pupil_iris_coplanar_overlap_face_count": 0,
            "radial_iris_fibre_shader": True,
            "limbal_ring_present": True,
            "pupil_face_region_present": True,
            "transparent_cornea_cap_present": True,
            "transparent_open_anterior_cornea_dome": True,
            "full_socket_crossing_cornea_sphere_used": False,
            "optical_component_fit": {
                "iris": iris_fit,
                "cornea": cornea_fit,
            },
            "minimum_optical_layer_separation_m": optical_separation,
            "minimum_required_optical_layer_separation_m": (
                EYE_OPTICAL_MINIMUM_LAYER_SEPARATION_M
            ),
            "socket_clearance": component_clearance,
            "minimum_required_socket_clearance_m": EYE_SOCKET_MINIMUM_CLEARANCE_M,
            "body_surface_triangle_overlap_count": overlap_count,
            "measured_socket_fit_passed": True,
            "intentionally_authored_black_band_object_present": False,
            "visual_black_band_absence_proven": False,
            "visual_black_band_review_required": True,
        }
    return objects, {
        "method": "official_helper_socket_fit_single_radial_optical_disc_v3",
        "iris_color_family": "brown",
        "object_count": len(objects),
        "helper_eye_count": 2,
        "limbal_ring_count": 2,
        "pupil_face_region_count": 2,
        "transparent_cornea_count": 2,
        "natural_iris_procedural_variation": True,
        "radial_iris_fibre_shader": True,
        "single_continuous_nonoverlapping_optical_disc_per_eye": True,
        "pupil_iris_coplanar_overlap_face_count": 0,
        "measured_socket_fit_passed": True,
        "minimum_required_socket_clearance_m": EYE_SOCKET_MINIMUM_CLEARANCE_M,
        "minimum_required_optical_layer_separation_m": (
            EYE_OPTICAL_MINIMUM_LAYER_SEPARATION_M
        ),
        "intentionally_authored_black_band_object_count": 0,
        "visual_black_band_absence_proven": False,
        "visual_black_band_review_required": True,
        "records": records,
        "visual_socket_fit_review_required": True,
    }


def _projected_nail_plate(
    *,
    name: str,
    body_tree: BVHTree,
    armature: Any,
    bone_name: str,
    outward_hint: Vector,
    length_m: float,
    width_m: float,
    material: Any,
) -> tuple[Any, dict[str, Any]]:
    bone = armature.data.bones.get(bone_name)
    if bone is None:
        raise ProfiledAdultBlenderComponentError(f"nail terminal bone missing: {bone_name}")
    direction = (
        armature.matrix_world.to_3x3() @ (bone.tail_local - bone.head_local)
    ).normalized()
    outward = outward_hint.normalized()
    longitudinal = direction - outward * direction.dot(outward)
    if longitudinal.length <= 1.0e-8:
        raise ProfiledAdultBlenderComponentError(f"nail tangent degenerate: {bone_name}")
    longitudinal.normalize()
    lateral = outward.cross(longitudinal).normalized()
    terminal = armature.matrix_world @ bone.tail_local
    grid = NAIL_PROJECTION_GRID_SIZE
    faces = [
        (
            row * grid + column,
            row * grid + column + 1,
            (row + 1) * grid + column + 1,
            (row + 1) * grid + column,
        )
        for row in range(grid - 1)
        for column in range(grid - 1)
    ]
    projection_attempts: list[dict[str, Any]] = []
    total_raycast_count = 0
    accepted: dict[str, Any] | None = None
    for footprint_scale in NAIL_FOOTPRINT_SCALE_CANDIDATES:
        if accepted is not None:
            break
        for center_fraction in NAIL_PROJECTION_CENTER_FRACTION_CANDIDATES:
            nominal_center = terminal - longitudinal * (length_m * center_fraction)
            hits: list[Vector] = []
            normals: list[Vector] = []
            base_clearances: list[float] = []
            projection_complete = True
            failure_reason = ""
            minimum_normal_alignment = 1.0
            for row in range(grid):
                along = (
                    ((row / (grid - 1)) - 0.5)
                    * length_m
                    * footprint_scale
                )
                for column in range(grid):
                    across_fraction = (column / (grid - 1)) - 0.5
                    across = across_fraction * width_m * footprint_scale
                    expected = (
                        nominal_center + longitudinal * along + lateral * across
                    )
                    origin = expected + outward * 0.025
                    total_raycast_count += 1
                    hit, normal, _face, _distance = body_tree.ray_cast(
                        origin,
                        -outward,
                        0.050,
                    )
                    if hit is None or normal is None:
                        projection_complete = False
                        failure_reason = (
                            f"surface_projection_miss_row_{row}_column_{column}"
                        )
                        break
                    if normal.dot(outward) < 0.0:
                        normal = -normal
                    normal.normalize()
                    alignment = float(normal.dot(outward))
                    minimum_normal_alignment = min(
                        minimum_normal_alignment, alignment
                    )
                    if alignment < NAIL_MINIMUM_OUTWARD_NORMAL_ALIGNMENT:
                        projection_complete = False
                        failure_reason = (
                            f"outward_normal_alignment_failed_row_{row}_column_{column}"
                        )
                        break
                    arch = 1.0 - min(1.0, abs(across_fraction) * 2.0) ** 2
                    hits.append(hit.copy())
                    normals.append(normal.copy())
                    base_clearances.append(0.000055 + 0.000075 * arch)
                if not projection_complete:
                    break
            attempt: dict[str, Any] = {
                "footprint_scale": footprint_scale,
                "center_fraction_from_terminal": center_fraction,
                "projection_complete": projection_complete,
                "projected_sample_count": len(hits),
                "minimum_outward_normal_alignment": minimum_normal_alignment,
                "failure_reason": failure_reason,
            }
            if not projection_complete:
                projection_attempts.append(attempt)
                continue

            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(
                [
                    tuple(hit + normal * clearance)
                    for hit, normal, clearance in zip(
                        hits, normals, base_clearances
                    )
                ],
                [],
                faces,
            )
            mesh.update(calc_edges=True)
            nail = bpy.data.objects.new(name, mesh)
            bpy.context.collection.objects.link(nail)
            mesh.materials.append(material)
            for polygon in mesh.polygons:
                polygon.use_smooth = True

            initial_clearance: dict[str, Any] | None = None
            initial_overlap_count = -1
            clearance_record: dict[str, Any] | None = None
            overlap_count = -1
            accepted_lift_iteration = -1
            for lift_iteration in range(
                NAIL_ADAPTIVE_NORMAL_LIFT_MAX_ITERATIONS + 1
            ):
                additional_lift = (
                    lift_iteration * NAIL_ADAPTIVE_NORMAL_LIFT_STEP_M
                )
                for vertex, hit, normal, base_clearance in zip(
                    nail.data.vertices, hits, normals, base_clearances
                ):
                    vertex.co = hit + normal * (base_clearance + additional_lift)
                nail.data.update()
                clearance_record = _body_clearance_record(body_tree, [nail])
                overlap_count = len(body_tree.overlap(_world_surface_bvh(nail)))
                if lift_iteration == 0:
                    initial_clearance = clearance_record
                    initial_overlap_count = overlap_count
                minimum = float(
                    clearance_record[
                        "minimum_unsigned_body_surface_clearance_m"
                    ]
                )
                maximum = float(
                    clearance_record[
                        "maximum_unsigned_body_surface_clearance_m"
                    ]
                )
                if (
                    minimum >= NAIL_MINIMUM_SURFACE_CLEARANCE_M
                    and maximum <= NAIL_MAXIMUM_SURFACE_CLEARANCE_M
                    and overlap_count == 0
                    and footprint_scale >= NAIL_MINIMUM_FOOTPRINT_SCALE
                ):
                    accepted_lift_iteration = lift_iteration
                    break
                if maximum > NAIL_MAXIMUM_SURFACE_CLEARANCE_M:
                    break

            attempt.update(
                {
                    "initial_clearance": initial_clearance,
                    "initial_body_surface_triangle_overlap_count": (
                        initial_overlap_count
                    ),
                    "final_clearance": clearance_record,
                    "final_body_surface_triangle_overlap_count": overlap_count,
                    "adaptive_normal_lift_iteration_count": max(
                        0, accepted_lift_iteration
                    ),
                    "additional_normal_lift_m": max(
                        0, accepted_lift_iteration
                    )
                    * NAIL_ADAPTIVE_NORMAL_LIFT_STEP_M,
                    "fit_passed": accepted_lift_iteration >= 0,
                }
            )
            projection_attempts.append(attempt)
            if accepted_lift_iteration >= 0:
                accepted = {
                    "nail": nail,
                    "clearance": clearance_record,
                    "initial_clearance": initial_clearance,
                    "initial_overlap_count": initial_overlap_count,
                    "overlap_count": overlap_count,
                    "footprint_scale": footprint_scale,
                    "center_fraction": center_fraction,
                    "minimum_normal_alignment": minimum_normal_alignment,
                    "lift_iteration": accepted_lift_iteration,
                }
                break
            failed_mesh = nail.data
            bpy.data.objects.remove(nail, do_unlink=True)
            if failed_mesh.users == 0:
                bpy.data.meshes.remove(failed_mesh)

    if accepted is None:
        last_attempt = projection_attempts[-1] if projection_attempts else {}
        raise ProfiledAdultBlenderComponentError(
            f"bounded conformal nail fit failed: {bone_name};"
            f"attempts={len(projection_attempts)};last={last_attempt}"
        )
    nail = accepted["nail"]
    clearance_record = accepted["clearance"]
    overlap_count = int(accepted["overlap_count"])
    footprint_scale = float(accepted["footprint_scale"])
    center_fraction = float(accepted["center_fraction"])
    lift_iteration = int(accepted["lift_iteration"])
    additional_normal_lift = (
        lift_iteration * NAIL_ADAPTIVE_NORMAL_LIFT_STEP_M
    )
    nail["review_surface_normal"] = [float(value) for value in outward]
    nail["surface_fit_measured"] = True
    nail["floating_or_intersection_absence_proven"] = True
    nail["body_surface_triangle_overlap_count"] = overlap_count
    nail["projection_grid_size"] = grid
    nail["retained_footprint_scale"] = footprint_scale
    nail["projection_center_fraction_from_terminal"] = center_fraction
    nail["additional_normal_lift_m"] = additional_normal_lift
    nail["bounded_adaptive_conformal_fit_passed"] = True
    assign_rigid_bone(nail, armature, bone_name)
    return nail, {
        "object": nail.name,
        "bone": bone_name,
        "projection_raycast_count": total_raycast_count,
        "accepted_projection_raycast_count": grid * grid,
        "projection_attempt_count": len(projection_attempts),
        "projection_attempts": projection_attempts,
        "grid_dimensions": [grid, grid],
        "nominal_plate_length_m": length_m,
        "nominal_plate_width_m": width_m,
        "plate_length_m": length_m * footprint_scale,
        "plate_width_m": width_m * footprint_scale,
        "retained_footprint_scale": footprint_scale,
        "minimum_allowed_footprint_scale": NAIL_MINIMUM_FOOTPRINT_SCALE,
        "projection_center_fraction_from_terminal": center_fraction,
        "minimum_outward_normal_alignment": accepted[
            "minimum_normal_alignment"
        ],
        "minimum_required_outward_normal_alignment": (
            NAIL_MINIMUM_OUTWARD_NORMAL_ALIGNMENT
        ),
        "initial_clearance": accepted["initial_clearance"],
        "initial_body_surface_triangle_overlap_count": accepted[
            "initial_overlap_count"
        ],
        "adaptive_normal_lift_iteration_count": lift_iteration,
        "additional_normal_lift_m": additional_normal_lift,
        "maximum_allowed_additional_normal_lift_m": (
            NAIL_ADAPTIVE_NORMAL_LIFT_STEP_M
            * NAIL_ADAPTIVE_NORMAL_LIFT_MAX_ITERATIONS
        ),
        "review_surface_normal": [float(value) for value in outward],
        "clearance": clearance_record,
        "body_surface_triangle_overlap_count": overlap_count,
        "surface_fit_measured": True,
        "floating_or_intersection_absence_proven": True,
        "bounded_adaptive_conformal_fit_passed": True,
    }


def add_natural_nails(
    *,
    body: Any,
    armature: Any,
    target_height_m: float,
    candidate_id: str,
) -> tuple[list[Any], dict[str, Any]]:
    height = float(target_height_m)
    if body is None or body.type != "MESH":
        raise ProfiledAdultBlenderComponentError("conformal nails require the exact body mesh")
    body_tree = _world_surface_bvh(body)
    material = _simple_material(
        "Kira_Profiled_Natural_Nails", "#C9958C", roughness=0.38
    )
    objects: list[Any] = []
    records: list[dict[str, Any]] = []
    for side in ("L", "R"):
        for digit in range(1, 6):
            bone_name = f"finger{digit}-3.{side}"
            nail, record = _projected_nail_plate(
                name=f"{candidate_id}_fingernail_{digit}_{side}",
                body_tree=body_tree,
                armature=armature,
                bone_name=bone_name,
                outward_hint=Vector((0.0, -1.0, 0.0)),
                length_m=height * (0.0046 if digit == 1 else 0.0038),
                width_m=height * (0.0030 if digit == 1 else 0.0023),
                material=material,
            )
            objects.append(nail)
            records.append({**record, "kind": "fingernail", "digit": digit, "side": side})
        for digit in range(1, 6):
            bone_name = f"toe{digit}-{'2' if digit == 1 else '3'}.{side}"
            nail, record = _projected_nail_plate(
                name=f"{candidate_id}_toenail_{digit}_{side}",
                body_tree=body_tree,
                armature=armature,
                bone_name=bone_name,
                outward_hint=Vector((0.0, -0.12, 1.0)),
                length_m=height * (0.0048 if digit == 1 else 0.0031),
                width_m=height * (0.0041 if digit == 1 else 0.0024),
                material=material,
            )
            objects.append(nail)
            records.append({**record, "kind": "toenail", "digit": digit, "side": side})
    for nail in objects:
        nail["candidate_id"] = candidate_id
        nail["private_owner_review_only"] = True
        nail["inactive_candidate"] = True
        nail["runtime_activation_allowed"] = False
        nail["nail_component"] = True
        nail["natural_nail_material"] = True
        nail["visual_surface_fit_review_required"] = True
    clearances = [
        float(row["clearance"]["minimum_unsigned_body_surface_clearance_m"])
        for row in records
    ]
    maximums = [
        float(row["clearance"]["maximum_unsigned_body_surface_clearance_m"])
        for row in records
    ]
    return objects, {
        "method": "body_raycast_conformal_oriented_nail_plates_v3",
        "component_count": len(objects),
        "fingernail_count": sum(row["kind"] == "fingernail" for row in records),
        "toenail_count": sum(row["kind"] == "toenail" for row in records),
        "records": records,
        "surface_projection_raycast_count": sum(
            int(row["projection_raycast_count"]) for row in records
        ),
        "minimum_measured_surface_clearance_m": min(clearances),
        "maximum_measured_surface_clearance_m": max(maximums),
        "minimum_required_surface_clearance_m": NAIL_MINIMUM_SURFACE_CLEARANCE_M,
        "maximum_allowed_surface_clearance_m": NAIL_MAXIMUM_SURFACE_CLEARANCE_M,
        "body_surface_triangle_overlap_count": sum(
            int(row["body_surface_triangle_overlap_count"]) for row in records
        ),
        "minimum_retained_footprint_scale": min(
            float(row["retained_footprint_scale"]) for row in records
        ),
        "maximum_additional_normal_lift_m": max(
            float(row["additional_normal_lift_m"]) for row in records
        ),
        "all_bounded_adaptive_conformal_fits_passed": all(
            row["bounded_adaptive_conformal_fit_passed"] is True
            for row in records
        ),
        "surface_fit_measured": True,
        "floating_or_intersection_absence_proven": True,
        "toe_plate_orientation_derived_from_surface_projection": True,
        "visual_surface_fit_review_required": True,
    }


def reset_pose(armature: Any) -> None:
    for bone in armature.pose.bones:
        mode = bone.rotation_mode
        bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
        bone.rotation_mode = mode
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def apply_relaxed_hand_pose(
    armature: Any,
    side: str,
    *,
    target_height_m: float,
) -> dict[str, Any]:
    """Apply a small measured palmward curl without assuming a fixed bone-roll axis."""

    if side not in {"L", "R"}:
        raise ProfiledAdultBlenderComponentError("relaxed hand side must be L or R")
    palmward = armature.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))
    palmward.normalize()
    records: list[dict[str, Any]] = []
    maximum_displacement = 0.0
    for digit in range(1, 6):
        distal_name = f"finger{digit}-3.{side}"
        distal = armature.pose.bones.get(distal_name)
        if distal is None:
            raise ProfiledAdultBlenderComponentError(
                f"relaxed hand distal bone missing: {distal_name}"
            )
        start_tip = armature.matrix_world @ distal.tail
        digit_steps: list[dict[str, Any]] = []
        for segment, degrees in ((1, 5.0 if digit == 1 else 7.0), (2, 7.0 if digit == 1 else 10.0)):
            name = f"finger{digit}-{segment}.{side}"
            bone = armature.pose.bones.get(name)
            if bone is None:
                raise ProfiledAdultBlenderComponentError(
                    f"relaxed hand bone missing: {name}"
                )
            original_mode = bone.rotation_mode
            original = bone.rotation_quaternion.copy()
            before = armature.matrix_world @ distal.tail
            candidates: list[dict[str, Any]] = []
            for axis_name, axis in (
                ("LOCAL_X", Vector((1.0, 0.0, 0.0))),
                ("LOCAL_Y", Vector((0.0, 1.0, 0.0))),
                ("LOCAL_Z", Vector((0.0, 0.0, 1.0))),
            ):
                for sign in (-1, 1):
                    bone.rotation_mode = "QUATERNION"
                    bone.rotation_quaternion = Quaternion(axis, math.radians(sign * degrees))
                    bpy.context.view_layer.update()
                    after = armature.matrix_world @ distal.tail
                    displacement = after - before
                    palmward_motion = float(displacement.dot(palmward))
                    lateral_motion = abs(float(displacement.x))
                    vertical_motion = abs(float(displacement.z))
                    candidates.append(
                        {
                            "axis_name": axis_name,
                            "axis_vector": [float(value) for value in axis],
                            "sign": sign,
                            "degrees": degrees,
                            "palmward_motion_m": palmward_motion,
                            "lateral_motion_m": lateral_motion,
                            "vertical_motion_m": vertical_motion,
                            "score": (
                                palmward_motion
                                - lateral_motion * 0.30
                                - vertical_motion * 0.08
                            ),
                        }
                    )
                    bone.rotation_quaternion = original
                    bone.rotation_mode = original_mode
                    bpy.context.view_layer.update()
            selected = max(candidates, key=lambda row: float(row["score"]))
            if float(selected["palmward_motion_m"]) <= 0.0:
                raise ProfiledAdultBlenderComponentError(
                    f"no measured palmward relaxed-hand solution: {name}"
                )
            bone.rotation_mode = "QUATERNION"
            bone.rotation_quaternion = Quaternion(
                Vector(tuple(selected["axis_vector"])),
                math.radians(float(selected["sign"]) * degrees),
            )
            bpy.context.view_layer.update()
            digit_steps.append({"bone": name, **selected})
        end_tip = armature.matrix_world @ distal.tail
        displacement = end_tip - start_tip
        maximum_displacement = max(maximum_displacement, float(displacement.length))
        records.append(
            {
                "digit": digit,
                "side": side,
                "steps": digit_steps,
                "tip_displacement_m": [float(value) for value in displacement],
                "tip_displacement_length_m": float(displacement.length),
                "net_palmward_tip_motion_m": float(displacement.dot(palmward)),
            }
        )
    maximum_allowed = float(target_height_m) * 0.035
    if maximum_displacement > maximum_allowed:
        raise ProfiledAdultBlenderComponentError(
            "relaxed hand pose exceeded conservative fingertip displacement"
        )
    return {
        "method": "measured_local_axis_small_palmward_curl_v1",
        "side": side,
        "digit_count": len(records),
        "maximum_tip_displacement_m": maximum_displacement,
        "maximum_allowed_tip_displacement_m": maximum_allowed,
        "all_digits_moved_palmward": all(
            float(row["net_palmward_tip_motion_m"]) > 0.0 for row in records
        ),
        "records": records,
    }


def _leg_points(armature: Any, side: str) -> dict[str, Vector]:
    required = (f"upperleg02.{side}", f"lowerleg01.{side}", f"lowerleg02.{side}")
    if any(armature.pose.bones.get(name) is None for name in required):
        raise ProfiledAdultBlenderComponentError(f"knee chain missing for {side}")
    upper, lower, ankle = (armature.pose.bones[name] for name in required)
    return {
        "upper_head": armature.matrix_world @ upper.head,
        "knee_upper_tail": armature.matrix_world @ upper.tail,
        "knee_lower_head": armature.matrix_world @ lower.head,
        "ankle": armature.matrix_world @ ankle.tail,
    }


def _flexion_degrees(points: Mapping[str, Vector]) -> float:
    upper = points["knee_upper_tail"] - points["upper_head"]
    lower = points["ankle"] - points["knee_lower_head"]
    if upper.length <= 1.0e-8 or lower.length <= 1.0e-8:
        return 0.0
    cosine = max(-1.0, min(1.0, upper.normalized().dot(lower.normalized())))
    return math.degrees(math.acos(cosine))


def _evaluated_body_points(body: Any) -> list[Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        if len(mesh.vertices) != len(body.data.vertices):
            raise ProfiledAdultBlenderComponentError(
                "knee evaluated mesh topology differs from authored primary surface"
            )
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def _polygon_area(points: Sequence[Vector], indices: Sequence[int]) -> float:
    if len(indices) < 3:
        return 0.0
    anchor = points[int(indices[0])]
    return sum(
        float(
            (points[int(indices[index])] - anchor)
            .cross(points[int(indices[index + 1])] - anchor)
            .length
            * 0.5
        )
        for index in range(1, len(indices) - 1)
    )


def _bounded_percentile(sorted_values: Sequence[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    index = max(0, min(len(sorted_values) - 1, int((len(sorted_values) - 1) * fraction)))
    return float(sorted_values[index])


def _knee_deformation_record(
    body: Any,
    rest_points: Sequence[Vector],
    posed_points: Sequence[Vector],
    knee_center: Vector,
    body_height: float,
) -> dict[str, Any]:
    half_height = body_height * 0.055
    radial_limit = body_height * 0.060
    selected = {
        index
        for index, point in enumerate(rest_points)
        if abs(float(point.z - knee_center.z)) <= half_height
        and Vector((point.x - knee_center.x, point.y - knee_center.y, 0.0)).length
        <= radial_limit
    }
    faces = [
        tuple(int(value) for value in polygon.vertices)
        for polygon in body.data.polygons
        if all(int(value) in selected for value in polygon.vertices)
    ]
    edges = [
        (int(edge.vertices[0]), int(edge.vertices[1]))
        for edge in body.data.edges
        if int(edge.vertices[0]) in selected and int(edge.vertices[1]) in selected
    ]
    if len(selected) < 80 or len(faces) < 40 or len(edges) < 80:
        raise ProfiledAdultBlenderComponentError(
            "knee deformation region is too sparse for a conservative gate"
        )
    area_ratios = sorted(
        posed_area / rest_area
        for indices in faces
        for rest_area, posed_area in [
            (_polygon_area(rest_points, indices), _polygon_area(posed_points, indices))
        ]
        if rest_area > 1.0e-12
    )
    edge_ratios = sorted(
        (posed_points[second] - posed_points[first]).length
        / (rest_points[second] - rest_points[first]).length
        for first, second in edges
        if (rest_points[second] - rest_points[first]).length > 1.0e-9
    )
    rest_width = max(rest_points[index].x for index in selected) - min(
        rest_points[index].x for index in selected
    )
    posed_width = max(posed_points[index].x for index in selected) - min(
        posed_points[index].x for index in selected
    )
    if rest_width <= 1.0e-8 or not area_ratios or not edge_ratios:
        raise ProfiledAdultBlenderComponentError("knee deformation metrics are degenerate")
    width_ratio = float(posed_width / rest_width)
    area_p05 = _bounded_percentile(area_ratios, 0.05)
    area_p95 = _bounded_percentile(area_ratios, 0.95)
    edge_p05 = _bounded_percentile(edge_ratios, 0.05)
    edge_p95 = _bounded_percentile(edge_ratios, 0.95)
    passed = (
        0.68 <= width_ratio <= 1.45
        and area_p05 >= 0.25
        and area_p95 <= 3.50
        and edge_p05 >= 0.35
        and edge_p95 <= 2.20
    )
    return {
        "selected_rest_vertex_count": len(selected),
        "selected_rest_face_count": len(faces),
        "selected_rest_edge_count": len(edges),
        "lateral_width_ratio": width_ratio,
        "face_area_ratio_percentile_05": area_p05,
        "face_area_ratio_percentile_95": area_p95,
        "edge_length_ratio_percentile_05": edge_p05,
        "edge_length_ratio_percentile_95": edge_p95,
        "required_lateral_width_ratio_range": [0.68, 1.45],
        "required_face_area_ratio_percentile_05_minimum": 0.25,
        "required_face_area_ratio_percentile_95_maximum": 3.50,
        "required_edge_length_ratio_percentile_05_minimum": 0.35,
        "required_edge_length_ratio_percentile_95_maximum": 2.20,
        "evaluated_mesh_deformation_passed": passed,
    }


def solve_bilateral_knee_axes_and_actions(armature: Any, body: Any) -> dict[str, Any]:
    """Solve a conservative bend and prove evaluated-mesh quality at three angles."""

    modifier = next(
        (item for item in body.modifiers if item.type == "ARMATURE" and item.object == armature),
        None,
    )
    if modifier is None or modifier.use_deform_preserve_volume is not True:
        raise ProfiledAdultBlenderComponentError(
            "knee deformation proof requires preserve-volume armature skinning"
        )
    reset_pose(armature)
    rest_body_points = _evaluated_body_points(body)
    body_height = max(point.z for point in rest_body_points) - min(
        point.z for point in rest_body_points
    )
    solutions: dict[str, Any] = {}
    axes = {
        "LOCAL_X": Vector((1.0, 0.0, 0.0)),
        "LOCAL_Y": Vector((0.0, 1.0, 0.0)),
        "LOCAL_Z": Vector((0.0, 0.0, 1.0)),
    }
    for side in ("L", "R"):
        reset_pose(armature)
        rest = _leg_points(armature, side)
        candidates: list[dict[str, Any]] = []
        lower_name = f"lowerleg01.{side}"
        for axis_name, axis in axes.items():
            for sign in (-1, 1):
                for degrees in range(20, 91, 5):
                    reset_pose(armature)
                    lower = armature.pose.bones[lower_name]
                    lower.rotation_mode = "QUATERNION"
                    lower.rotation_quaternion = Quaternion(axis, math.radians(sign * degrees))
                    bpy.context.view_layer.update()
                    posed = _leg_points(armature, side)
                    displacement = posed["ankle"] - rest["ankle"]
                    posterior = float(displacement.y)
                    lateral = abs(float(displacement.x))
                    flexion = _flexion_degrees(posed)
                    valid = (
                        posterior > 0.015
                        and lateral <= max(0.018, posterior * 0.45)
                        and 25.0 <= flexion <= 90.0
                    )
                    candidates.append(
                        {
                            "axis_name": axis_name,
                            "axis_vector": [float(value) for value in axis],
                            "sign": sign,
                            "signed_angle_degrees": sign * degrees,
                            "posterior_displacement_m": posterior,
                            "lateral_displacement_m": lateral,
                            "flexion_degrees": flexion,
                            "valid": valid,
                            "target_flexion_error_degrees": abs(
                                flexion - KNEE_REVIEW_FLEXION_DEGREES
                            ),
                        }
                    )
        valid = [row for row in candidates if row["valid"]]
        if not valid:
            raise ProfiledAdultBlenderComponentError(f"no measured posterior knee solution: {side}")
        selected = min(
            valid,
            key=lambda row: (
                float(row["target_flexion_error_degrees"]),
                float(row["lateral_displacement_m"]),
                -float(row["posterior_displacement_m"]),
            ),
        )
        angle_gates: list[dict[str, Any]] = []
        for gate_angle in KNEE_DEFORMATION_GATE_ANGLES_DEGREES:
            reset_pose(armature)
            lower = armature.pose.bones[lower_name]
            lower.rotation_mode = "QUATERNION"
            signed_gate_angle = int(selected["sign"]) * gate_angle
            lower.rotation_quaternion = Quaternion(
                Vector(tuple(selected["axis_vector"])),
                math.radians(signed_gate_angle),
            )
            bpy.context.view_layer.update()
            posed = _leg_points(armature, side)
            displacement = posed["ankle"] - rest["ankle"]
            posterior = float(displacement.y)
            lateral = abs(float(displacement.x))
            flexion = _flexion_degrees(posed)
            deformation = _knee_deformation_record(
                body,
                rest_body_points,
                _evaluated_body_points(body),
                rest["knee_lower_head"],
                body_height,
            )
            skeleton_passed = (
                posterior > 0.010
                and lateral <= max(0.018, posterior * 0.50)
                and 20.0 <= flexion <= 95.0
            )
            passed = skeleton_passed and deformation["evaluated_mesh_deformation_passed"]
            angle_gates.append(
                {
                    "requested_rotation_degrees": gate_angle,
                    "signed_rotation_degrees": signed_gate_angle,
                    "measured_flexion_degrees": flexion,
                    "posterior_displacement_m": posterior,
                    "lateral_displacement_m": lateral,
                    "skeleton_direction_passed": skeleton_passed,
                    "deformation": deformation,
                    "passed": passed,
                }
            )
        if not all(row["passed"] for row in angle_gates):
            raise ProfiledAdultBlenderComponentError(
                f"multi-angle evaluated knee deformation gate failed: {side}"
            )
        solutions["left" if side == "L" else "right"] = {
            **selected,
            "upper_bone": f"upperleg02.{side}",
            "lower_bone": lower_name,
            "ankle_bone": f"lowerleg02.{side}",
            "posterior_world_axis": POSTERIOR_WORLD_AXIS,
            "anatomical_forward_axis": ANATOMICAL_FORWARD_AXIS,
            "search_candidate_count": len(candidates),
            "valid_candidate_count": len(valid),
            "multi_angle_deformation_gates": angle_gates,
            "skeleton_kinematic_objective_pass": True,
            "evaluated_mesh_deformation_objective_pass": True,
        }
    armature.animation_data_create()
    action_names: list[str] = []
    for side_name, solution in solutions.items():
        action = bpy.data.actions.new(
            f"kira_profiled_private_knee_flex_{side_name}_axis_solved"
        )
        action.use_fake_user = True
        armature.animation_data.action = action
        reset_pose(armature)
        lower = armature.pose.bones[solution["lower_bone"]]
        lower.rotation_mode = "QUATERNION"
        lower.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        lower.keyframe_insert("rotation_quaternion", frame=1, group=lower.name)
        lower.rotation_quaternion = Quaternion(
            Vector(tuple(solution["axis_vector"])),
            math.radians(float(solution["signed_angle_degrees"])),
        )
        lower.keyframe_insert("rotation_quaternion", frame=30, group=lower.name)
        action_names.append(action.name)
    armature.animation_data.action = None
    reset_pose(armature)
    return {
        "method": "preserve_volume_multi_angle_evaluated_knee_gate_v2",
        "posterior_world_axis": POSTERIOR_WORLD_AXIS,
        "solutions": solutions,
        "quaternion_actions": action_names,
        "deformation_gate_angles_degrees": list(KNEE_DEFORMATION_GATE_ANGLES_DEGREES),
        "armature_preserve_volume_verified": True,
        "skeleton_kinematic_objective_pass": all(
            row["skeleton_kinematic_objective_pass"] for row in solutions.values()
        ),
        "knee_mesh_deformation_quality_proven": all(
            row["evaluated_mesh_deformation_objective_pass"]
            for row in solutions.values()
        ),
        "knee_mesh_visual_review_required": True,
        "pose_space_pelvic_patch_audit_status": "NOT_PERFORMED_BY_KNEE_AXIS_SOLVER",
    }


def apply_knee_solution(armature: Any, solution: Mapping[str, Any]) -> None:
    reset_pose(armature)
    lower = armature.pose.bones[str(solution["lower_bone"])]
    lower.rotation_mode = "QUATERNION"
    lower.rotation_quaternion = Quaternion(
        Vector(tuple(solution["axis_vector"])),
        math.radians(float(solution["signed_angle_degrees"])),
    )
    bpy.context.view_layer.update()


def invoke_hash_bound_hair_provider(
    *,
    project_root: Path,
    provider_path: str | None,
    provider_sha256: str | None,
    body: Any,
    armature: Any,
    context: Mapping[str, Any],
) -> tuple[list[Any], dict[str, Any]]:
    """Inject root-owned dynamic hair, or record an explicit hairless build."""

    if not provider_path and not provider_sha256:
        return [], {
            "status": "HAIRLESS_ENGINEERING_CANDIDATE_PROVIDER_NOT_SUPPLIED",
            "provider_invoked": False,
            "runtime_hair_complete": False,
            "wind_runtime_proof_complete": False,
            "wet_runtime_proof_complete": False,
            "owner_groom_integration_required": True,
        }
    if not provider_path or not provider_sha256:
        raise ProfiledAdultBlenderComponentError("hair provider path and hash must be supplied together")
    root = Path(project_root).resolve(strict=True)
    relative = Path(provider_path)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() != ".py":
        raise ProfiledAdultBlenderComponentError("hair provider path unsafe")
    path = (root / relative).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ProfiledAdultBlenderComponentError("hair provider escaped project") from exc
    actual = sha256_file(path)
    if actual != str(provider_sha256).lower():
        raise ProfiledAdultBlenderComponentError("hair provider hash mismatch")
    source_text = path.read_text(encoding="utf-8-sig").lower()
    forbidden = [token for token in FORBIDDEN_PROVIDER_TOKENS if token in source_text]
    if forbidden:
        raise ProfiledAdultBlenderComponentError(
            "hair provider contains forbidden legacy dependency: " + ",".join(forbidden)
        )
    existing_object_pointers = {int(obj.as_pointer()) for obj in bpy.data.objects}
    existing_data_pointers = {
        int(obj.data.as_pointer())
        for obj in bpy.data.objects
        if getattr(obj, "data", None) is not None
    }
    spec = importlib.util.spec_from_file_location(
        f"kira_dynamic_hair_provider_{actual[:12]}", path
    )
    if spec is None or spec.loader is None:
        raise ProfiledAdultBlenderComponentError("hair provider could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    callable_value = getattr(module, "build_dynamic_hair", None)
    if not callable(callable_value):
        raise ProfiledAdultBlenderComponentError("build_dynamic_hair callable missing")
    result = callable_value(body=body, armature=armature, context=dict(context))
    if not isinstance(result, Mapping):
        raise ProfiledAdultBlenderComponentError("hair provider result must be a mapping")
    raw_objects = result.get("objects")
    evidence = result.get("evidence")
    if not isinstance(raw_objects, list) or not isinstance(evidence, Mapping):
        raise ProfiledAdultBlenderComponentError("hair provider objects/evidence missing")
    objects = list(raw_objects)
    if not objects:
        raise ProfiledAdultBlenderComponentError(
            "full hair provider returned no groom objects"
        )
    if len(objects) != 1:
        raise ProfiledAdultBlenderComponentError(
            "reviewed responsive provider must return exactly one groom"
        )
    if len({int(obj.as_pointer()) for obj in objects if obj is not None}) != len(objects):
        raise ProfiledAdultBlenderComponentError("hair provider returned duplicate objects")
    if any(
        obj is None or bpy.data.objects.get(getattr(obj, "name", "")) is not obj
        for obj in objects
    ):
        raise ProfiledAdultBlenderComponentError("hair provider returned an unlinked object")
    if evidence.get("source_geometry_copied") is not False:
        raise ProfiledAdultBlenderComponentError("hair provider geometry provenance not safe")
    if evidence.get("representation") not in {
        "guide_curves_with_render_children",
        "validated_dynamic_equivalent",
    }:
        raise ProfiledAdultBlenderComponentError("hair provider representation invalid")
    if any(obj.type != "CURVE" for obj in objects):
        raise ProfiledAdultBlenderComponentError(
            "hair provider must return actual legacy CURVE groom objects"
        )
    if any(int(obj.as_pointer()) in existing_object_pointers for obj in objects):
        raise ProfiledAdultBlenderComponentError(
            "hair provider returned a pre-existing object"
        )
    if any(
        getattr(obj, "data", None) is None
        or int(obj.data.as_pointer()) in existing_data_pointers
        for obj in objects
    ):
        raise ProfiledAdultBlenderComponentError(
            "hair provider returned pre-existing or missing curve data"
        )
    spline_control_counts = [
        len(spline.points) + len(spline.bezier_points)
        for obj in objects
        for spline in obj.data.splines
    ]
    measured_strands = len(spline_control_counts)
    measured_controls = sum(spline_control_counts)
    if measured_strands <= 0 or measured_controls <= 0 or min(spline_control_counts) < 2:
        raise ProfiledAdultBlenderComponentError(
            "hair provider returned no measurable strand geometry"
        )
    requested_strands = int(context.get("strand_count") or 0)
    requested_controls = int(context.get("controls_per_strand") or 0)
    if measured_strands != requested_strands:
        raise ProfiledAdultBlenderComponentError(
            "hair provider measured strand count differs from requested count"
        )
    measured_minimum = min(spline_control_counts)
    measured_maximum = max(spline_control_counts)
    if requested_controls < 2 or any(
        count < requested_controls or count > requested_controls * 16
        for count in spline_control_counts
    ):
        raise ProfiledAdultBlenderComponentError(
            "hair provider adaptive controls escaped bounded requested topology"
        )
    if int(evidence.get("strand_count") or -1) != measured_strands:
        raise ProfiledAdultBlenderComponentError(
            "hair provider evidence strand count differs from geometry"
        )
    if int(evidence.get("requested_controls_per_strand") or -1) != requested_controls:
        raise ProfiledAdultBlenderComponentError(
            "hair provider evidence initial controls differ from request"
        )
    if int(evidence.get("minimum_actual_controls_per_strand") or -1) != measured_minimum:
        raise ProfiledAdultBlenderComponentError(
            "hair provider evidence minimum controls differs from geometry"
        )
    if int(evidence.get("maximum_actual_controls_per_strand") or -1) != measured_maximum:
        raise ProfiledAdultBlenderComponentError(
            "hair provider evidence maximum controls differs from geometry"
        )
    if int(evidence.get("curve_control_point_count") or -1) != measured_controls:
        raise ProfiledAdultBlenderComponentError(
            "hair provider evidence control-point count differs from geometry"
        )
    expected_shape_keys = [
        "Basis",
        "hair_wind_left_dry",
        "hair_wind_right_dry",
        "hair_wet_neutral",
        "hair_wet_wind_left",
        "hair_wet_wind_right",
    ]
    groom = objects[0]
    shape_keys = getattr(groom.data, "shape_keys", None)
    actual_shape_keys = (
        list(shape_keys.key_blocks.keys()) if shape_keys is not None else []
    )
    if actual_shape_keys != expected_shape_keys:
        raise ProfiledAdultBlenderComponentError(
            "hair provider response shape-key set differs from reviewed contract"
        )
    if any(
        len(shape_keys.key_blocks[name].data) != measured_controls
        for name in expected_shape_keys
    ):
        raise ProfiledAdultBlenderComponentError(
            "hair provider response shape-key topology differs from groom geometry"
        )
    if (
        "hair_wind_direction_minus1_1" not in groom
        or "hair_wetness_0_1" not in groom
    ):
        raise ProfiledAdultBlenderComponentError(
            "hair provider signed-wind or wetness control missing"
        )
    adaptive = evidence.get("adaptive_tube_clearance_proof")
    if not isinstance(adaptive, Mapping):
        raise ProfiledAdultBlenderComponentError(
            "hair provider adaptive clearance proof missing"
        )
    if adaptive.get("state_labels") != expected_shape_keys:
        raise ProfiledAdultBlenderComponentError(
            "hair provider adaptive state topology differs from shape keys"
        )
    adaptive_exact = {
        "initial_basis_control_point_count": requested_strands * requested_controls,
        "actual_basis_control_point_count": measured_controls,
        "minimum_controls_per_strand": measured_minimum,
        "maximum_controls_per_strand": measured_maximum,
    }
    if any(adaptive.get(name) != expected for name, expected in adaptive_exact.items()):
        raise ProfiledAdultBlenderComponentError(
            "hair provider adaptive proof differs from measured geometry"
        )
    maximum_depth = int(adaptive.get("maximum_adaptive_depth_used") or -1)
    allowed_depth = int(adaptive.get("maximum_adaptive_depth_allowed") or -1)
    tolerance = float(adaptive.get("clearance_tolerance_m") or -1.0)
    corner_margin = float(adaptive.get("minimum_sampled_clearance_margin_m") or -1.0)
    bilinear_margin = float(
        adaptive.get("bilinear_minimum_sampled_clearance_margin_m") or -1.0
    )
    if not (
        0 <= maximum_depth <= allowed_depth <= 8
        and 0.0 < tolerance <= 0.0001
        and corner_margin >= -tolerance
        and bilinear_margin >= -tolerance
        and adaptive.get("all_state_sampled_tube_clearance_passed") is True
        and adaptive.get("all_bilinear_grid_tube_clearance_passed") is True
        and int(adaptive.get("validation_sample_count") or 0) > 0
        and int(adaptive.get("bilinear_validation_sample_count") or 0) > 0
        and len(adaptive.get("bilinear_grid") or []) == 15
    ):
        raise ProfiledAdultBlenderComponentError(
            "hair provider adaptive tube/bilinear clearance gate failed"
        )
    collision_surface = evidence.get("collision_surface_proof")
    if not isinstance(collision_surface, Mapping) or not (
        collision_surface.get("closed_contiguous_outward_winding_proven") is True
        and collision_surface.get("connected_component_count") == 1
        and collision_surface.get("boundary_edge_count") == 0
        and collision_surface.get("nonmanifold_edge_count") == 0
        and collision_surface.get("winding_discontinuity_count") == 0
    ):
        raise ProfiledAdultBlenderComponentError(
            "hair provider collision-surface proof failed"
        )
    parent_binding = evidence.get("head_parent_binding")
    if not isinstance(parent_binding, Mapping) or not (
        parent_binding.get("head_bone_parented") is True
        and parent_binding.get("bind_world_transform_preserved") is True
        and parent_binding.get("pose_follow_runtime_proven") is False
    ):
        raise ProfiledAdultBlenderComponentError(
            "hair provider head-bone private bind proof failed"
        )
    if not (
        evidence.get("private_blend_response_states_proven") is True
        and evidence.get("proof_scope")
        == "PRIVATE_BLEND_AUTHORED_STATES_NOT_WORLD_RUNTIME"
    ):
        raise ProfiledAdultBlenderComponentError(
            "hair provider private response proof scope invalid"
        )
    runtime_fields = (
        "runtime_hair_complete",
        "wind_runtime_proof_complete",
        "wet_runtime_proof_complete",
    )
    if any(evidence.get(name) is not False for name in runtime_fields):
        raise ProfiledAdultBlenderComponentError(
            "candidate builder accepts no provider-asserted World runtime proof"
        )
    evidence_record = dict(evidence)
    evidence_record.update({name: False for name in runtime_fields})
    evidence_record["provider_geometry_provenance_independent_review_required"] = True
    for obj in objects:
        obj["private_owner_review_only"] = True
        obj["inactive_candidate"] = True
        obj["runtime_activation_allowed"] = False
        obj["dynamic_hair_provider_sha256"] = actual
    return objects, {
        "status": "HASH_BOUND_DYNAMIC_HAIR_PROVIDER_INVOKED",
        "provider_invoked": True,
        "provider_path": relative.as_posix(),
        "provider_sha256": actual,
        "object_count": len(objects),
        "object_types": [obj.type for obj in objects],
        "measured_strand_count": measured_strands,
        "measured_curve_control_point_count": measured_controls,
        "requested_initial_controls_per_strand": requested_controls,
        "measured_controls_per_strand_minimum": measured_minimum,
        "measured_controls_per_strand_maximum": measured_maximum,
        "adaptive_shared_topology_verified": True,
        "sampled_corner_and_bilinear_clearance_verified": True,
        "returned_objects_and_data_new_in_scene": True,
        "provider_geometry_provenance_independent_review_required": True,
        "evidence": evidence_record,
        "runtime_hair_complete": False,
        "wind_runtime_proof_complete": False,
        "wet_runtime_proof_complete": False,
    }


__all__ = [
    "ANATOMICAL_FORWARD_AXIS",
    "HELPER_EYE_FIT_SCALE",
    "HELPER_EYE_POSTERIOR_INSET_M",
    "KNEE_DEFORMATION_GATE_ANGLES_DEGREES",
    "SKIN_SUBSURFACE_SCALE_M",
    "POSTERIOR_WORLD_AXIS",
    "ProfiledAdultBlenderComponentError",
    "add_natural_helper_eyes",
    "add_natural_nails",
    "apply_relaxed_hand_pose",
    "apply_knee_solution",
    "build_body_object",
    "build_official_rig_and_normalized_weights",
    "build_warm_skin_material",
    "invoke_hash_bound_hair_provider",
    "prepare_profiled_body_source",
    "reset_pose",
    "sha256_file",
    "solve_bilateral_knee_axes_and_actions",
    "srgb_hex_to_linear_rgba",
]
