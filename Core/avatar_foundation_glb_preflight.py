"""Deterministic read-only preflight for the two current foundation GLBs.

The preflight opens the exact Kira and Synthetic Robert candidate containers,
validates their binary layout, and records structural evidence for geometry,
rigging, animation, materials, and hair-named geometry.  It never edits an
asset and it deliberately keeps body acceptance, internal anatomy, physical
skin or hair behavior, visual approval, activation, and export false.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
from pathlib import Path
from typing import Any, Iterable, Mapping


POLICY_PATH = Path(
    "Avatar/avatar_builder/body_systems/avatar_foundation_glb_preflight_v1.json"
)
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
COMPONENT_FORMATS = {
    5120: ("b", 1),
    5121: ("B", 1),
    5122: ("h", 2),
    5123: ("H", 2),
    5125: ("I", 4),
    5126: ("f", 4),
}
TYPE_WIDTHS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}
ACCEPTANCE_AXES = {
    "external_geometry_accepted",
    "rig_and_movement_accepted",
    "skin_and_hair_behavior_accepted",
    "internal_anatomy_accepted",
    "owner_visual_acceptance",
    "runtime_activation_allowed",
    "public_export_allowed",
}


class FoundationGlbInvalid(RuntimeError):
    """Raised when a container or policy fails the closed preflight."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return _sha256_bytes(payload)


def _required_list(document: Mapping[str, Any], key: str) -> list[Any]:
    value = document.get(key, [])
    if not isinstance(value, list):
        raise FoundationGlbInvalid(f"{key} must be a list")
    return value


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise FoundationGlbInvalid(f"{label} must be an integer >= {minimum}")
    return value


def _index(value: Any, count: int, label: str) -> int:
    result = _integer(value, label)
    if result >= count:
        raise FoundationGlbInvalid(f"{label} is out of range")
    return result


def _finite(value: Any, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise FoundationGlbInvalid(f"{label} is not finite")
    return result


def _parse_glb(payload: bytes) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    if len(payload) < 20:
        raise FoundationGlbInvalid("GLB is shorter than its required header")
    magic, version, declared_length = struct.unpack_from("<4sII", payload, 0)
    if magic != b"glTF":
        raise FoundationGlbInvalid("GLB magic differs")
    if version != 2:
        raise FoundationGlbInvalid("GLB version differs")
    if declared_length != len(payload):
        raise FoundationGlbInvalid("GLB declared length differs")

    chunks: list[tuple[int, bytes]] = []
    offset = 12
    while offset < len(payload):
        if offset + 8 > len(payload):
            raise FoundationGlbInvalid("GLB chunk header is truncated")
        chunk_length, chunk_type = struct.unpack_from("<II", payload, offset)
        offset += 8
        if chunk_length % 4:
            raise FoundationGlbInvalid("GLB chunk length is not four-byte aligned")
        end = offset + chunk_length
        if end > len(payload):
            raise FoundationGlbInvalid("GLB chunk exceeds the container")
        chunks.append((chunk_type, payload[offset:end]))
        offset = end
    if offset != len(payload):
        raise FoundationGlbInvalid("GLB chunk walk did not end at container length")
    if not chunks or chunks[0][0] != JSON_CHUNK:
        raise FoundationGlbInvalid("GLB JSON chunk is not first")
    if [kind for kind, _ in chunks].count(JSON_CHUNK) != 1:
        raise FoundationGlbInvalid("GLB must contain exactly one JSON chunk")
    if [kind for kind, _ in chunks].count(BIN_CHUNK) != 1:
        raise FoundationGlbInvalid("GLB must contain exactly one BIN chunk")
    if any(kind not in {JSON_CHUNK, BIN_CHUNK} for kind, _ in chunks):
        raise FoundationGlbInvalid("GLB contains an unsupported chunk type")

    json_payload = chunks[0][1].rstrip(b" \x00")
    try:
        document = json.loads(json_payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FoundationGlbInvalid("GLB JSON chunk is invalid") from error
    if not isinstance(document, dict):
        raise FoundationGlbInvalid("GLB JSON root must be an object")
    binary = next(data for kind, data in chunks if kind == BIN_CHUNK)
    asset = document.get("asset")
    if not isinstance(asset, dict) or asset.get("version") != "2.0":
        raise FoundationGlbInvalid("glTF asset version differs")
    return document, binary, {
        "glb_version": version,
        "chunk_count": len(chunks),
        "json_chunk_bytes": len(chunks[0][1]),
        "binary_chunk_bytes": len(binary),
        "generator": str(asset.get("generator", "")),
    }


def _validate_layout(document: Mapping[str, Any], binary: bytes) -> None:
    buffers = _required_list(document, "buffers")
    if len(buffers) != 1 or not isinstance(buffers[0], dict):
        raise FoundationGlbInvalid("one embedded buffer is required")
    if "uri" in buffers[0]:
        raise FoundationGlbInvalid("external buffer URI is forbidden")
    declared = _integer(buffers[0].get("byteLength"), "buffer byteLength")
    if declared > len(binary) or len(binary) - declared > 3:
        raise FoundationGlbInvalid("embedded buffer length or padding differs")

    views = _required_list(document, "bufferViews")
    for view_index, view in enumerate(views):
        if not isinstance(view, dict):
            raise FoundationGlbInvalid(f"bufferView {view_index} is not an object")
        if _index(view.get("buffer"), len(buffers), f"bufferView {view_index} buffer") != 0:
            raise FoundationGlbInvalid("bufferView uses a nonembedded buffer")
        start = _integer(view.get("byteOffset", 0), f"bufferView {view_index} byteOffset")
        length = _integer(view.get("byteLength"), f"bufferView {view_index} byteLength")
        if start + length > declared:
            raise FoundationGlbInvalid(f"bufferView {view_index} exceeds the buffer")
        if "byteStride" in view:
            stride = _integer(view["byteStride"], f"bufferView {view_index} byteStride", 4)
            if stride > 252 or stride % 4:
                raise FoundationGlbInvalid(f"bufferView {view_index} byteStride differs")

    accessors = _required_list(document, "accessors")
    for accessor_index, accessor in enumerate(accessors):
        if not isinstance(accessor, dict):
            raise FoundationGlbInvalid(f"accessor {accessor_index} is not an object")
        component_type = accessor.get("componentType")
        accessor_type = accessor.get("type")
        if component_type not in COMPONENT_FORMATS or accessor_type not in TYPE_WIDTHS:
            raise FoundationGlbInvalid(f"accessor {accessor_index} format differs")
        count = _integer(accessor.get("count"), f"accessor {accessor_index} count")
        component_bytes = COMPONENT_FORMATS[component_type][1]
        element_bytes = component_bytes * TYPE_WIDTHS[accessor_type]
        if "bufferView" in accessor:
            view_index = _index(
                accessor.get("bufferView"), len(views), f"accessor {accessor_index} bufferView"
            )
            view = views[view_index]
            stride = _integer(view.get("byteStride", element_bytes), "effective byteStride", 1)
            if stride < element_bytes:
                raise FoundationGlbInvalid(f"accessor {accessor_index} stride is too small")
            local_offset = _integer(
                accessor.get("byteOffset", 0), f"accessor {accessor_index} byteOffset"
            )
            required = local_offset if count == 0 else local_offset + (count - 1) * stride + element_bytes
            if required > _integer(view.get("byteLength"), "bufferView byteLength"):
                raise FoundationGlbInvalid(f"accessor {accessor_index} exceeds its bufferView")
        elif "sparse" not in accessor:
            raise FoundationGlbInvalid(f"accessor {accessor_index} has no storage")

        if "sparse" in accessor:
            sparse = accessor["sparse"]
            if not isinstance(sparse, dict):
                raise FoundationGlbInvalid(f"accessor {accessor_index} sparse record differs")
            sparse_count = _integer(
                sparse.get("count"), f"accessor {accessor_index} sparse count", 1
            )
            if sparse_count > count:
                raise FoundationGlbInvalid(f"accessor {accessor_index} sparse count exceeds count")
            indices = sparse.get("indices")
            values = sparse.get("values")
            if not isinstance(indices, dict) or not isinstance(values, dict):
                raise FoundationGlbInvalid(f"accessor {accessor_index} sparse storage differs")
            index_component = indices.get("componentType")
            if index_component not in {5121, 5123, 5125}:
                raise FoundationGlbInvalid(f"accessor {accessor_index} sparse index type differs")
            index_view = views[
                _index(indices.get("bufferView"), len(views), "sparse index bufferView")
            ]
            value_view = views[
                _index(values.get("bufferView"), len(views), "sparse value bufferView")
            ]
            if "byteStride" in index_view or "byteStride" in value_view:
                raise FoundationGlbInvalid("sparse bufferViews may not be interleaved")
            index_offset = _integer(indices.get("byteOffset", 0), "sparse index byteOffset")
            value_offset = _integer(values.get("byteOffset", 0), "sparse value byteOffset")
            index_required = index_offset + sparse_count * COMPONENT_FORMATS[index_component][1]
            value_required = value_offset + sparse_count * element_bytes
            if index_required > int(index_view["byteLength"]):
                raise FoundationGlbInvalid(f"accessor {accessor_index} sparse indices exceed bufferView")
            if value_required > int(value_view["byteLength"]):
                raise FoundationGlbInvalid(f"accessor {accessor_index} sparse values exceed bufferView")
        for bound_name in ("min", "max"):
            if bound_name in accessor:
                bound = accessor[bound_name]
                if not isinstance(bound, list) or len(bound) != TYPE_WIDTHS[accessor_type]:
                    raise FoundationGlbInvalid(f"accessor {accessor_index} {bound_name} differs")
                for component in bound:
                    _finite(component, f"accessor {accessor_index} {bound_name}")


def _decode_accessor(
    document: Mapping[str, Any],
    binary: bytes,
    accessor_index: int,
) -> list[tuple[int | float, ...]]:
    accessors = _required_list(document, "accessors")
    views = _required_list(document, "bufferViews")
    accessor = accessors[_index(accessor_index, len(accessors), "accessor index")]
    component_type = int(accessor["componentType"])
    fmt, component_bytes = COMPONENT_FORMATS[component_type]
    width = TYPE_WIDTHS[str(accessor["type"])]
    element_bytes = component_bytes * width
    unpacker = struct.Struct("<" + fmt * width)
    count = int(accessor["count"])
    if "bufferView" in accessor:
        view = views[int(accessor["bufferView"])]
        stride = int(view.get("byteStride", element_bytes))
        start = int(view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
        result = [unpacker.unpack_from(binary, start + index * stride) for index in range(count)]
    else:
        result = [tuple(0 for _ in range(width)) for _ in range(count)]
    sparse = accessor.get("sparse")
    if sparse is not None:
        sparse_count = int(sparse["count"])
        indices = sparse["indices"]
        index_fmt, index_bytes = COMPONENT_FORMATS[int(indices["componentType"])]
        index_unpacker = struct.Struct("<" + index_fmt)
        index_view = views[int(indices["bufferView"])]
        index_start = int(index_view.get("byteOffset", 0)) + int(indices.get("byteOffset", 0))
        values_record = sparse["values"]
        value_view = views[int(values_record["bufferView"])]
        value_start = int(value_view.get("byteOffset", 0)) + int(values_record.get("byteOffset", 0))
        previous = -1
        for sparse_index in range(sparse_count):
            destination = int(index_unpacker.unpack_from(binary, index_start + sparse_index * index_bytes)[0])
            if destination <= previous or destination >= count:
                raise FoundationGlbInvalid("sparse indices are not strictly increasing or in range")
            previous = destination
            result[destination] = unpacker.unpack_from(binary, value_start + sparse_index * element_bytes)
    return result


def _normalized_weight(value: int | float, component_type: int) -> float:
    if component_type == 5126:
        return float(value)
    if component_type == 5121:
        return float(value) / 255.0
    if component_type == 5123:
        return float(value) / 65535.0
    raise FoundationGlbInvalid("weight accessor component type differs")


def _name_contains_hair(value: Any) -> bool:
    return isinstance(value, str) and "hair" in value.casefold()


def _analyze_document(document: Mapping[str, Any], binary: bytes) -> dict[str, Any]:
    accessors = _required_list(document, "accessors")
    meshes = _required_list(document, "meshes")
    nodes = _required_list(document, "nodes")
    skins = _required_list(document, "skins")
    animations = _required_list(document, "animations")
    materials = _required_list(document, "materials")
    textures = _required_list(document, "textures")
    images = _required_list(document, "images")
    decoded: dict[int, list[tuple[int | float, ...]]] = {}

    def values(index: int) -> list[tuple[int | float, ...]]:
        if index not in decoded:
            decoded[index] = _decode_accessor(document, binary, index)
        return decoded[index]

    mesh_skin_map: dict[int, set[int]] = {}
    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise FoundationGlbInvalid(f"node {node_index} is not an object")
        for child in node.get("children", []):
            _index(child, len(nodes), f"node {node_index} child")
        if "mesh" in node:
            mesh_index = _index(node["mesh"], len(meshes), f"node {node_index} mesh")
            if "skin" in node:
                skin_index = _index(node["skin"], len(skins), f"node {node_index} skin")
                mesh_skin_map.setdefault(mesh_index, set()).add(skin_index)

    total_vertices = 0
    total_triangles = 0
    primitive_count = 0
    indexed_primitive_count = 0
    normal_primitive_count = 0
    uv_primitive_count = 0
    weighted_primitive_count = 0
    morph_target_count = 0
    bounds_min = [math.inf, math.inf, math.inf]
    bounds_max = [-math.inf, -math.inf, -math.inf]
    weight_sum_min = math.inf
    weight_sum_max = -math.inf
    zero_weight_vertices = 0
    invalid_joint_indices = 0
    hair_named_mesh_count = 0

    for mesh_index, mesh in enumerate(meshes):
        if not isinstance(mesh, dict):
            raise FoundationGlbInvalid(f"mesh {mesh_index} is not an object")
        hair_named_mesh_count += int(_name_contains_hair(mesh.get("name")))
        primitives = mesh.get("primitives")
        if not isinstance(primitives, list) or not primitives:
            raise FoundationGlbInvalid(f"mesh {mesh_index} has no primitives")
        for primitive_index, primitive in enumerate(primitives):
            if not isinstance(primitive, dict):
                raise FoundationGlbInvalid("mesh primitive is not an object")
            primitive_count += 1
            mode = int(primitive.get("mode", 4))
            if mode != 4:
                raise FoundationGlbInvalid("non-triangle primitive is outside this preflight")
            attributes = primitive.get("attributes")
            if not isinstance(attributes, dict) or "POSITION" not in attributes:
                raise FoundationGlbInvalid("mesh primitive has no POSITION accessor")
            position_index = _index(
                attributes["POSITION"], len(accessors), "POSITION accessor"
            )
            positions = values(position_index)
            if not positions or any(len(point) != 3 for point in positions):
                raise FoundationGlbInvalid("POSITION accessor shape differs")
            total_vertices += len(positions)
            for point in positions:
                for axis in range(3):
                    coordinate = _finite(point[axis], "POSITION component")
                    bounds_min[axis] = min(bounds_min[axis], coordinate)
                    bounds_max[axis] = max(bounds_max[axis], coordinate)

            if "indices" in primitive:
                index_accessor = accessors[_index(primitive["indices"], len(accessors), "index accessor")]
                if index_accessor.get("type") != "SCALAR" or int(index_accessor["count"]) % 3:
                    raise FoundationGlbInvalid("triangle index accessor differs")
                total_triangles += int(index_accessor["count"]) // 3
                indexed_primitive_count += 1
            else:
                if len(positions) % 3:
                    raise FoundationGlbInvalid("nonindexed triangle count differs")
                total_triangles += len(positions) // 3

            if "NORMAL" in attributes:
                normal_accessor = accessors[_index(attributes["NORMAL"], len(accessors), "NORMAL accessor")]
                if int(normal_accessor["count"]) != len(positions):
                    raise FoundationGlbInvalid("NORMAL count differs from POSITION count")
                normal_primitive_count += 1
            if "TEXCOORD_0" in attributes:
                uv_accessor = accessors[_index(attributes["TEXCOORD_0"], len(accessors), "TEXCOORD_0 accessor")]
                if int(uv_accessor["count"]) != len(positions):
                    raise FoundationGlbInvalid("TEXCOORD_0 count differs from POSITION count")
                uv_primitive_count += 1

            has_joints = "JOINTS_0" in attributes
            has_weights = "WEIGHTS_0" in attributes
            if has_joints != has_weights:
                raise FoundationGlbInvalid("JOINTS_0 and WEIGHTS_0 must appear together")
            if has_joints:
                weighted_primitive_count += 1
                joint_index = _index(attributes["JOINTS_0"], len(accessors), "JOINTS_0 accessor")
                weight_index = _index(attributes["WEIGHTS_0"], len(accessors), "WEIGHTS_0 accessor")
                joint_accessor = accessors[joint_index]
                weight_accessor = accessors[weight_index]
                if int(joint_accessor["count"]) != len(positions) or int(weight_accessor["count"]) != len(positions):
                    raise FoundationGlbInvalid("joint or weight count differs from POSITION count")
                if int(joint_accessor["componentType"]) not in {5121, 5123}:
                    raise FoundationGlbInvalid("JOINTS_0 component type differs")
                if int(weight_accessor["componentType"]) not in {5121, 5123, 5126}:
                    raise FoundationGlbInvalid("WEIGHTS_0 component type differs")
                linked_skins = mesh_skin_map.get(mesh_index, set())
                if len(linked_skins) != 1:
                    raise FoundationGlbInvalid("weighted mesh must bind exactly one skin")
                joint_limit = len(skins[next(iter(linked_skins))].get("joints", []))
                joint_rows = values(joint_index)
                weight_rows = values(weight_index)
                for joint_row, weight_row in zip(joint_rows, weight_rows, strict=True):
                    invalid_joint_indices += sum(int(joint) >= joint_limit for joint in joint_row)
                    total = sum(
                        _normalized_weight(component, int(weight_accessor["componentType"]))
                        for component in weight_row
                    )
                    if not math.isfinite(total) or total < -1e-6:
                        raise FoundationGlbInvalid("vertex weight sum is invalid")
                    weight_sum_min = min(weight_sum_min, total)
                    weight_sum_max = max(weight_sum_max, total)
                    zero_weight_vertices += int(total <= 1e-8)
            morph_target_count += len(primitive.get("targets", []))

    total_joint_count = 0
    inverse_bind_count = 0
    for skin_index, skin in enumerate(skins):
        if not isinstance(skin, dict):
            raise FoundationGlbInvalid(f"skin {skin_index} is not an object")
        joints = skin.get("joints")
        if not isinstance(joints, list) or not joints:
            raise FoundationGlbInvalid(f"skin {skin_index} has no joints")
        for joint in joints:
            _index(joint, len(nodes), f"skin {skin_index} joint")
        total_joint_count += len(joints)
        if "inverseBindMatrices" in skin:
            accessor = accessors[_index(skin["inverseBindMatrices"], len(accessors), "inverse bind accessor")]
            if accessor.get("type") != "MAT4" or int(accessor["count"]) != len(joints):
                raise FoundationGlbInvalid("inverse bind matrix accessor differs")
            inverse_bind_count += int(accessor["count"])

    animation_summaries: list[dict[str, Any]] = []
    total_channels = 0
    for animation_index, animation in enumerate(animations):
        if not isinstance(animation, dict):
            raise FoundationGlbInvalid(f"animation {animation_index} is not an object")
        samplers = animation.get("samplers")
        channels = animation.get("channels")
        if not isinstance(samplers, list) or not samplers or not isinstance(channels, list) or not channels:
            raise FoundationGlbInvalid(f"animation {animation_index} structure differs")
        starts: list[float] = []
        ends: list[float] = []
        paths: dict[str, int] = {}
        for sampler_index, sampler in enumerate(samplers):
            input_index = _index(sampler.get("input"), len(accessors), "animation input accessor")
            _index(sampler.get("output"), len(accessors), "animation output accessor")
            input_accessor = accessors[input_index]
            if input_accessor.get("type") != "SCALAR" or int(input_accessor["componentType"]) != 5126:
                raise FoundationGlbInvalid("animation input accessor differs")
            times = [_finite(row[0], "animation time") for row in values(input_index)]
            if not times or any(right < left for left, right in zip(times, times[1:])):
                raise FoundationGlbInvalid("animation times are empty or decreasing")
            starts.append(times[0])
            ends.append(times[-1])
        for channel in channels:
            sampler_index = _index(channel.get("sampler"), len(samplers), "animation sampler")
            del sampler_index
            target = channel.get("target")
            if not isinstance(target, dict):
                raise FoundationGlbInvalid("animation target differs")
            _index(target.get("node"), len(nodes), "animation target node")
            path = str(target.get("path"))
            if path not in {"translation", "rotation", "scale", "weights"}:
                raise FoundationGlbInvalid("animation target path differs")
            paths[path] = paths.get(path, 0) + 1
        total_channels += len(channels)
        animation_summaries.append(
            {
                "animation_index": animation_index,
                "channel_count": len(channels),
                "duration_seconds": round(max(ends) - min(starts), 6),
                "target_path_counts": dict(sorted(paths.items())),
            }
        )

    if invalid_joint_indices:
        raise FoundationGlbInvalid("joint indices exceed the linked skin")
    bounds = {
        "minimum": [round(value, 9) for value in bounds_min],
        "maximum": [round(value, 9) for value in bounds_max],
        "extent": [round(bounds_max[axis] - bounds_min[axis], 9) for axis in range(3)],
    }
    return {
        "geometry": {
            "mesh_count": len(meshes),
            "primitive_count": primitive_count,
            "indexed_primitive_count": indexed_primitive_count,
            "vertex_count": total_vertices,
            "triangle_count": total_triangles,
            "normal_primitive_count": normal_primitive_count,
            "uv_primitive_count": uv_primitive_count,
            "morph_target_count": morph_target_count,
            "local_coordinate_bounds": bounds,
            "structural_geometry_present": total_vertices > 0 and total_triangles > 0,
            "external_geometry_accepted": False,
        },
        "rig": {
            "skin_count": len(skins),
            "joint_count": total_joint_count,
            "inverse_bind_matrix_count": inverse_bind_count,
            "weighted_primitive_count": weighted_primitive_count,
            "zero_weight_vertex_count": zero_weight_vertices,
            "weight_sum_min": None if math.isinf(weight_sum_min) else round(weight_sum_min, 9),
            "weight_sum_max": None if math.isinf(weight_sum_max) else round(weight_sum_max, 9),
            "structural_rig_present": len(skins) > 0 and weighted_primitive_count > 0,
            "rig_accepted": False,
        },
        "movement": {
            "animation_count": len(animations),
            "animation_channel_count": total_channels,
            "animations": animation_summaries,
            "structural_animation_present": len(animations) > 0,
            "deformation_and_movement_accepted": False,
        },
        "skin_hair": {
            "material_count": len(materials),
            "texture_count": len(textures),
            "image_count": len(images),
            "hair_named_mesh_count": hair_named_mesh_count,
            "surface_material_structure_present": len(materials) > 0,
            "skin_soft_tissue_behavior_accepted": False,
            "hair_physics_and_wet_behavior_accepted": False,
        },
        "internal_anatomy": {
            "machine_readable_internal_system_established": False,
            "internal_anatomy_accepted": False,
        },
        "owner_visual_acceptance": {
            "accepted": False,
            "turntable_review_completed": False,
        },
    }


def inspect_foundation_glb(path: Path, *, subject_id: str, project_path: str) -> dict[str, Any]:
    """Inspect one regular GLB without modifying it or any adjacent file."""

    if path.is_symlink() or not path.is_file() or path.suffix.casefold() != ".glb":
        raise FoundationGlbInvalid("source must be one regular non-link GLB")
    before = path.stat()
    payload = path.read_bytes()
    document, binary, container = _parse_glb(payload)
    _validate_layout(document, binary)
    analysis = _analyze_document(document, binary)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise FoundationGlbInvalid("source identity changed during preflight")
    return {
        "subject_id": subject_id,
        "source": {
            "project_path": project_path,
            "bytes": len(payload),
            "sha256": _sha256_bytes(payload),
            **container,
        },
        **analysis,
        "source_modified": False,
    }


def _resolve_project_path(project_root: Path, project_path: str) -> Path:
    relative = Path(project_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise FoundationGlbInvalid("policy source path must stay project-relative")
    root = project_root.resolve(strict=True)
    resolved = (root / relative).resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise FoundationGlbInvalid("policy source escapes the project root") from error
    return resolved


def _load_policy(project_root: Path, policy_path: Path) -> dict[str, Any]:
    resolved = policy_path if policy_path.is_absolute() else project_root / policy_path
    document = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise FoundationGlbInvalid("preflight policy root differs")
    if document.get("schema_version") != 1 or document.get("record_type") != "avatar_foundation_glb_preflight_policy":
        raise FoundationGlbInvalid("preflight policy identity differs")
    subjects = document.get("subjects")
    if not isinstance(subjects, list) or len(subjects) != 2:
        raise FoundationGlbInvalid("preflight policy requires exactly two subjects")
    if {entry.get("subject_id") for entry in subjects if isinstance(entry, dict)} != {"kira", "synthetic_robert"}:
        raise FoundationGlbInvalid("preflight policy subjects differ")
    axes = document.get("acceptance_axes")
    if not isinstance(axes, dict) or set(axes) != ACCEPTANCE_AXES or any(value is not False for value in axes.values()):
        raise FoundationGlbInvalid("preflight policy acceptance axes must remain false")
    requirements = document.get("requirements")
    expected_requirements = {
        "distinct_source_artifacts": True,
        "distinct_final_body_artifacts": True,
        "cross_identity_final_body_reuse_allowed": False,
        "glb_version": 2,
        "triangles_required": True,
        "skin_required": True,
        "weighted_geometry_required": True,
        "animation_structure_required": True,
    }
    if requirements != expected_requirements:
        raise FoundationGlbInvalid("preflight policy requirements differ")
    return document


def evaluate_foundation_sources(
    project_root: Path,
    policy_path: Path = POLICY_PATH,
) -> dict[str, Any]:
    """Evaluate the exact two configured sources and return a stable receipt."""

    root = project_root.resolve(strict=True)
    policy = _load_policy(root, policy_path)
    failures: list[str] = []
    results: list[dict[str, Any]] = []
    source_paths: list[str] = []
    source_hashes: list[str] = []
    requirements = policy["requirements"]
    for entry in sorted(policy["subjects"], key=lambda item: item["subject_id"]):
        subject_id = str(entry["subject_id"])
        project_path = str(entry.get("project_path", ""))
        try:
            path = _resolve_project_path(root, project_path)
            result = inspect_foundation_glb(path, subject_id=subject_id, project_path=project_path)
            source = result["source"]
            if source["bytes"] != entry.get("bytes"):
                failures.append(f"{subject_id}_source_byte_count_mismatch")
            if source["sha256"] != entry.get("sha256"):
                failures.append(f"{subject_id}_source_sha256_mismatch")
            if source["glb_version"] != requirements["glb_version"]:
                failures.append(f"{subject_id}_glb_version_mismatch")
            if requirements["triangles_required"] and not result["geometry"]["structural_geometry_present"]:
                failures.append(f"{subject_id}_triangle_geometry_missing")
            if requirements["skin_required"] and result["rig"]["skin_count"] < 1:
                failures.append(f"{subject_id}_skin_missing")
            if requirements["weighted_geometry_required"] and result["rig"]["weighted_primitive_count"] < 1:
                failures.append(f"{subject_id}_weighted_geometry_missing")
            if requirements["animation_structure_required"] and not result["movement"]["structural_animation_present"]:
                failures.append(f"{subject_id}_animation_structure_missing")
            results.append(result)
            source_paths.append(project_path.casefold())
            source_hashes.append(str(source["sha256"]))
        except (FoundationGlbInvalid, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            failures.append(f"{subject_id}_preflight_error:{type(error).__name__}:{error}")

    if len(set(source_paths)) != len(source_paths):
        failures.append("foundation_source_paths_must_be_distinct")
    if len(set(source_hashes)) != len(source_hashes):
        failures.append("foundation_source_hashes_must_be_distinct")
    passed = len(results) == 2 and not failures
    receipt = {
        "schema_version": 1,
        "record_type": "avatar_foundation_glb_preflight_result",
        "status": (
            "actual_sources_preflight_passed_body_acceptance_pending"
            if passed
            else "foundation_source_preflight_failed_closed"
        ),
        "policy_sha256": _sha256_bytes(
            (root / policy_path).read_bytes() if not policy_path.is_absolute() else policy_path.read_bytes()
        ),
        "preflight_passed": passed,
        "non_destructive_authoring_stage_ready": passed,
        "subjects": results,
        "pair_separation": {
            "source_paths_distinct": len(source_paths) == 2 and len(set(source_paths)) == 2,
            "source_hashes_distinct": len(source_hashes) == 2 and len(set(source_hashes)) == 2,
            "distinct_final_body_artifacts_required": True,
            "cross_identity_final_body_reuse_allowed": False,
        },
        "acceptance_axes": dict(policy["acceptance_axes"]),
        "body_authoring_performed": False,
        "blender_started": False,
        "source_files_modified": False,
        "failures": sorted(failures),
    }
    receipt["receipt_sha256"] = _sha256_json(receipt)
    return receipt


def write_receipt_exclusive(path: Path, receipt: Mapping[str, Any]) -> None:
    """Create one receipt without replacing any existing file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n"
    with path.open("x", encoding="ascii", newline="\n") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


__all__ = [
    "FoundationGlbInvalid",
    "POLICY_PATH",
    "evaluate_foundation_sources",
    "inspect_foundation_glb",
    "write_receipt_exclusive",
]
