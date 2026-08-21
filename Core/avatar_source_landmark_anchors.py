"""Pure-Python, read-only pelvic orientation-landmark derivation.

This module derives four orientation points from the exact HRA female pelvis
GLB.  The points are deterministic axis-aligned-bounds centers.  They are not
authored meshes, organs, tissue, or evidence that an anatomy component exists.
No Blender API is imported and no source artifact is modified.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
from typing import Any, Mapping, Sequence


RECEIPT_SCHEMA = "kira.avatar.source_derived_pelvic_landmark_receipt.v1"
RECEIPT_STATUS = "SOURCE_DERIVED_ORIENTATION_LANDMARKS_VERIFIED_NOT_COMPONENTS"
ALGORITHM_ID = "glb_binary_position_aabb_center_v1"
SOURCE_FILE = "VH_F_Pelvis.glb"
SOURCE_SHA256 = "155603d0c44a8ed1e0ca307f1ec3037941304f29f4187631135a9a150fab048d"
SOURCE_BYTES = 1_593_336
SOURCE_UNITS = "meters"
SOURCE_AXES = {"up": "+Y", "forward": "+Z", "handedness": "right"}
TARGET_UNITS = "meters"
TARGET_AXES = {"up": "+Z", "forward": "-Y", "handedness": "right"}
NORMALIZATION_TRANSFORM = (
    1.0, 0.0, 0.0, 0.0,
    0.0, 0.0, -1.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 1.0,
)

# ``landmark_id`` names match existing contract inventory entries only so the
# receipt can explain which orientation blocker it informs.  The receipt never
# maps these IDs as components.
LANDMARK_SPECS: tuple[dict[str, Any], ...] = (
    {
        "landmark_id": "pubic_landmark_empty",
        "anchor_id": "pubic_reference",
        "source_node": "VH_F_pubis",
        "node_mode": "exact_descendant_mesh_union",
        "mesh_nodes": (
            "VH_F_pubis_compact_bone_L",
            "VH_F_pubis_compact_bone_R",
            "VH_F_pubis_spongy_bone_L",
            "VH_F_pubis_spongy_bone_R",
        ),
    },
    {
        "landmark_id": "sacral_landmark_empty",
        "anchor_id": "sacral_reference",
        "source_node": "VH_F_sacrum",
        "node_mode": "exact_direct_mesh",
        "mesh_nodes": ("VH_F_sacrum",),
    },
    {
        "landmark_id": "pelvic_side_anchor_left",
        "anchor_id": "pelvic_side_left",
        "source_node": "VH_F_ilium_compact_bone_L",
        "node_mode": "exact_direct_mesh",
        "mesh_nodes": ("VH_F_ilium_compact_bone_L",),
    },
    {
        "landmark_id": "pelvic_side_anchor_right",
        "anchor_id": "pelvic_side_right",
        "source_node": "VH_F_ilium_compact_bone_R",
        "node_mode": "exact_direct_mesh",
        "mesh_nodes": ("VH_F_ilium_compact_bone_R",),
    },
)


class SourceLandmarkAnchorError(ValueError):
    """Fail-closed source, geometry, frame, or receipt validation error."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise SourceLandmarkAnchorError("cannot read landmark source GLB") from exc
    return digest.hexdigest()


def _clean_float(value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise SourceLandmarkAnchorError("landmark geometry contains a non-finite value")
    return 0.0 if abs(number) < 1.0e-15 else number


def _read_glb(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise SourceLandmarkAnchorError("cannot read landmark source GLB") from exc
    if len(payload) < 28:
        raise SourceLandmarkAnchorError("landmark source GLB is truncated")
    magic, version, declared_length = struct.unpack_from("<4sII", payload, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(payload):
        raise SourceLandmarkAnchorError("landmark source is not an exact-length GLB 2 artifact")
    json_length, json_type = struct.unpack_from("<II", payload, 12)
    if json_type != 0x4E4F534A or json_length % 4:
        raise SourceLandmarkAnchorError("landmark source GLB JSON chunk is invalid")
    json_end = 20 + json_length
    if json_end + 8 > len(payload):
        raise SourceLandmarkAnchorError("landmark source GLB binary chunk is missing")
    binary_length, binary_type = struct.unpack_from("<II", payload, json_end)
    binary_start = json_end + 8
    binary_end = binary_start + binary_length
    if binary_type != 0x004E4942 or binary_length % 4 or binary_end != len(payload):
        raise SourceLandmarkAnchorError("landmark source GLB must contain one final binary chunk")
    try:
        document = json.loads(payload[20:json_end].rstrip(b" \t\r\n\x00"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceLandmarkAnchorError("landmark source GLB JSON is invalid") from exc
    if not isinstance(document, dict):
        raise SourceLandmarkAnchorError("landmark source GLB JSON must be an object")
    asset = document.get("asset")
    if not isinstance(asset, Mapping) or asset.get("version") != "2.0":
        raise SourceLandmarkAnchorError("landmark source GLB asset version is unsupported")
    return document, payload[binary_start:binary_end]


def _strict_frame(
    *,
    source_units: str,
    source_axes: Mapping[str, Any],
    target_units: str,
    target_axes: Mapping[str, Any],
    normalization_transform: Sequence[float],
) -> list[float]:
    if source_units != SOURCE_UNITS or dict(source_axes) != SOURCE_AXES:
        raise SourceLandmarkAnchorError("pelvic landmark source units/axes mismatch")
    if target_units != TARGET_UNITS or dict(target_axes) != TARGET_AXES:
        raise SourceLandmarkAnchorError("pelvic landmark target units/axes mismatch")
    if isinstance(normalization_transform, (str, bytes)) or len(normalization_transform) != 16:
        raise SourceLandmarkAnchorError("pelvic landmark normalization transform is invalid")
    matrix: list[float] = []
    for entry in normalization_transform:
        if isinstance(entry, bool) or not isinstance(entry, (int, float)):
            raise SourceLandmarkAnchorError("pelvic landmark normalization must be numeric")
        matrix.append(_clean_float(float(entry)))
    if matrix != list(NORMALIZATION_TRANSFORM):
        raise SourceLandmarkAnchorError("pelvic landmark normalization transform mismatch")
    return matrix


def _node_tables(document: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], dict[str, int]]:
    raw_nodes = document.get("nodes")
    raw_meshes = document.get("meshes")
    if not isinstance(raw_nodes, list) or not isinstance(raw_meshes, list):
        raise SourceLandmarkAnchorError("landmark source nodes/meshes are missing")
    nodes: list[Mapping[str, Any]] = []
    names: dict[str, int] = {}
    parents: dict[int, int] = {}
    for node_index, raw_node in enumerate(raw_nodes):
        if not isinstance(raw_node, Mapping):
            raise SourceLandmarkAnchorError("landmark source node is invalid")
        node = raw_node
        nodes.append(node)
        name = node.get("name")
        if isinstance(name, str) and name.strip():
            if name in names:
                raise SourceLandmarkAnchorError(f"duplicate landmark source node name: {name}")
            names[name] = node_index
        children = node.get("children", [])
        if not isinstance(children, list) or len(children) != len(set(children)):
            raise SourceLandmarkAnchorError("landmark source child list is invalid")
        for child in children:
            if not isinstance(child, int) or isinstance(child, bool) or not 0 <= child < len(raw_nodes):
                raise SourceLandmarkAnchorError("landmark source child index is invalid")
            if child in parents:
                raise SourceLandmarkAnchorError("landmark source node has multiple parents")
            parents[child] = node_index
    if not names:
        raise SourceLandmarkAnchorError("landmark source has no named nodes")

    visiting: set[int] = set()
    visited: set[int] = set()

    def visit(index: int) -> None:
        if index in visiting:
            raise SourceLandmarkAnchorError("landmark source node hierarchy contains a cycle")
        if index in visited:
            return
        visiting.add(index)
        for child in nodes[index].get("children", []):
            visit(child)
        visiting.remove(index)
        visited.add(index)

    for index in range(len(nodes)):
        visit(index)
    return nodes, names


def _descendant_mesh_nodes(
    nodes: Sequence[Mapping[str, Any]],
    names: Mapping[str, int],
    source_node: str,
) -> list[tuple[str, int]]:
    if source_node not in names:
        raise SourceLandmarkAnchorError(f"required landmark source node is missing: {source_node}")
    result: list[tuple[str, int]] = []

    def collect(index: int) -> None:
        node = nodes[index]
        if any(key in node for key in ("matrix", "translation", "rotation", "scale")):
            raise SourceLandmarkAnchorError("landmark source node transforms are not supported")
        mesh = node.get("mesh")
        if mesh is not None:
            name = node.get("name")
            if not isinstance(name, str) or not name:
                raise SourceLandmarkAnchorError("selected landmark mesh node is unnamed")
            if not isinstance(mesh, int) or isinstance(mesh, bool):
                raise SourceLandmarkAnchorError("selected landmark mesh index is invalid")
            result.append((name, mesh))
        for child in node.get("children", []):
            collect(child)

    collect(names[source_node])
    if not result:
        raise SourceLandmarkAnchorError(f"landmark node has no mesh geometry: {source_node}")
    return sorted(result)


def _accessor_positions(
    document: Mapping[str, Any],
    binary: bytes,
    accessor_index: int,
) -> list[tuple[float, float, float]]:
    accessors = document.get("accessors")
    views = document.get("bufferViews")
    buffers = document.get("buffers")
    if not isinstance(accessors, list) or not isinstance(views, list) or not isinstance(buffers, list):
        raise SourceLandmarkAnchorError("landmark source geometry tables are missing")
    if len(buffers) != 1 or not isinstance(buffers[0], Mapping) or "uri" in buffers[0]:
        raise SourceLandmarkAnchorError("landmark source must use one embedded binary buffer")
    if buffers[0].get("byteLength") != len(binary):
        raise SourceLandmarkAnchorError("landmark source binary buffer length mismatch")
    if not 0 <= accessor_index < len(accessors) or not isinstance(accessors[accessor_index], Mapping):
        raise SourceLandmarkAnchorError("landmark POSITION accessor index is invalid")
    accessor = accessors[accessor_index]
    if (
        accessor.get("componentType") != 5126
        or accessor.get("type") != "VEC3"
        or accessor.get("normalized", False) is not False
        or "sparse" in accessor
    ):
        raise SourceLandmarkAnchorError("landmark POSITION accessor must be nonsparse FLOAT VEC3")
    count = accessor.get("count")
    view_index = accessor.get("bufferView")
    accessor_offset = accessor.get("byteOffset", 0)
    if (
        not isinstance(count, int)
        or isinstance(count, bool)
        or count <= 0
        or not isinstance(view_index, int)
        or isinstance(view_index, bool)
        or not 0 <= view_index < len(views)
        or not isinstance(accessor_offset, int)
        or isinstance(accessor_offset, bool)
        or accessor_offset < 0
    ):
        raise SourceLandmarkAnchorError("landmark POSITION accessor layout is invalid")
    view = views[view_index]
    if not isinstance(view, Mapping) or view.get("buffer") != 0:
        raise SourceLandmarkAnchorError("landmark POSITION buffer view is invalid")
    view_offset = view.get("byteOffset", 0)
    view_length = view.get("byteLength")
    stride = view.get("byteStride", 12)
    if (
        not isinstance(view_offset, int)
        or isinstance(view_offset, bool)
        or view_offset < 0
        or not isinstance(view_length, int)
        or isinstance(view_length, bool)
        or view_length <= 0
        or not isinstance(stride, int)
        or isinstance(stride, bool)
        or stride < 12
        or stride % 4
        or view_offset + view_length > len(binary)
        or accessor_offset + (count - 1) * stride + 12 > view_length
    ):
        raise SourceLandmarkAnchorError("landmark POSITION byte range is invalid")
    positions: list[tuple[float, float, float]] = []
    for index in range(count):
        offset = view_offset + accessor_offset + index * stride
        positions.append(tuple(_clean_float(item) for item in struct.unpack_from("<3f", binary, offset)))
    declared_min = accessor.get("min")
    declared_max = accessor.get("max")
    if (
        not isinstance(declared_min, list)
        or not isinstance(declared_max, list)
        or len(declared_min) != 3
        or len(declared_max) != 3
    ):
        raise SourceLandmarkAnchorError("landmark POSITION accessor lacks declared bounds")
    actual_min = [min(point[axis] for point in positions) for axis in range(3)]
    actual_max = [max(point[axis] for point in positions) for axis in range(3)]
    for declared, actual in zip(declared_min + declared_max, actual_min + actual_max):
        if isinstance(declared, bool) or not isinstance(declared, (int, float)):
            raise SourceLandmarkAnchorError("landmark POSITION declared bounds are invalid")
        if not math.isclose(float(declared), actual, rel_tol=1.0e-6, abs_tol=1.0e-7):
            raise SourceLandmarkAnchorError("landmark POSITION declared bounds mismatch binary geometry")
    return positions


def _mesh_positions(
    document: Mapping[str, Any],
    binary: bytes,
    mesh_index: int,
    expected_name: str,
) -> tuple[list[tuple[float, float, float]], list[int]]:
    meshes = document.get("meshes")
    if not isinstance(meshes, list) or not 0 <= mesh_index < len(meshes):
        raise SourceLandmarkAnchorError("selected landmark mesh index is out of range")
    mesh = meshes[mesh_index]
    if not isinstance(mesh, Mapping) or mesh.get("name") != expected_name:
        raise SourceLandmarkAnchorError("selected landmark node/mesh name binding mismatch")
    primitives = mesh.get("primitives")
    if not isinstance(primitives, list) or not primitives:
        raise SourceLandmarkAnchorError("selected landmark mesh has no primitives")
    positions: list[tuple[float, float, float]] = []
    accessor_indices: list[int] = []
    for primitive in primitives:
        attributes = primitive.get("attributes") if isinstance(primitive, Mapping) else None
        accessor_index = attributes.get("POSITION") if isinstance(attributes, Mapping) else None
        if not isinstance(accessor_index, int) or isinstance(accessor_index, bool):
            raise SourceLandmarkAnchorError("selected landmark primitive has no POSITION accessor")
        if accessor_index in accessor_indices:
            raise SourceLandmarkAnchorError("selected landmark reuses a POSITION accessor")
        accessor_indices.append(accessor_index)
        positions.extend(_accessor_positions(document, binary, accessor_index))
    return positions, accessor_indices


def _bounds(points: Sequence[Sequence[float]]) -> tuple[list[float], list[float], list[float]]:
    if not points:
        raise SourceLandmarkAnchorError("landmark point set is empty")
    minimum = [_clean_float(min(point[axis] for point in points)) for axis in range(3)]
    maximum = [_clean_float(max(point[axis] for point in points)) for axis in range(3)]
    extents = [maximum[axis] - minimum[axis] for axis in range(3)]
    if any(not math.isfinite(extent) or extent <= 1.0e-8 for extent in extents):
        raise SourceLandmarkAnchorError("landmark geometry bounds are degenerate")
    center = [_clean_float((minimum[axis] + maximum[axis]) / 2.0) for axis in range(3)]
    return minimum, maximum, center


def _transform_point(matrix: Sequence[float], point: Sequence[float]) -> list[float]:
    return [
        _clean_float(sum(matrix[row * 4 + column] * point[column] for column in range(3)) + matrix[row * 4 + 3])
        for row in range(3)
    ]


def _transform_bounds(
    matrix: Sequence[float],
    minimum: Sequence[float],
    maximum: Sequence[float],
) -> tuple[list[float], list[float]]:
    corners = [
        _transform_point(matrix, point)
        for point in itertools.product(*zip(minimum, maximum))
    ]
    transformed_min = [min(point[axis] for point in corners) for axis in range(3)]
    transformed_max = [max(point[axis] for point in corners) for axis in range(3)]
    return [_clean_float(item) for item in transformed_min], [_clean_float(item) for item in transformed_max]


def derive_pelvic_landmark_anchor_receipt(
    source_path: Path | str,
    *,
    expected_source_file: str,
    expected_bytes: int,
    expected_sha256: str,
    source_units: str,
    source_axes: Mapping[str, Any],
    target_units: str,
    target_axes: Mapping[str, Any],
    normalization_transform: Sequence[float],
) -> dict[str, Any]:
    """Derive an immutable orientation-only receipt from exact GLB positions."""

    path = Path(source_path)
    if expected_source_file != SOURCE_FILE or path.name != expected_source_file:
        raise SourceLandmarkAnchorError("pelvic landmark source file binding mismatch")
    if (
        isinstance(expected_bytes, bool)
        or not isinstance(expected_bytes, int)
        or expected_bytes <= 0
        or expected_bytes != SOURCE_BYTES
        or path.stat().st_size != expected_bytes
    ):
        raise SourceLandmarkAnchorError("pelvic landmark source byte count mismatch")
    if expected_sha256 != SOURCE_SHA256 or _sha256_file(path) != expected_sha256:
        raise SourceLandmarkAnchorError("pelvic landmark source SHA-256 mismatch")
    matrix = _strict_frame(
        source_units=source_units,
        source_axes=source_axes,
        target_units=target_units,
        target_axes=target_axes,
        normalization_transform=normalization_transform,
    )
    document, binary = _read_glb(path)
    nodes, names = _node_tables(document)
    landmarks: list[dict[str, Any]] = []
    used_accessors: set[int] = set()
    for spec in LANDMARK_SPECS:
        source_node = spec["source_node"]
        selected = _descendant_mesh_nodes(nodes, names, source_node)
        selected_names = tuple(sorted(name for name, _ in selected))
        if selected_names != tuple(sorted(spec["mesh_nodes"])):
            raise SourceLandmarkAnchorError(
                f"landmark source-node membership mismatch: {source_node}"
            )
        if spec["node_mode"] == "exact_direct_mesh" and selected_names != (source_node,):
            raise SourceLandmarkAnchorError(f"direct landmark node is not exact: {source_node}")
        points: list[tuple[float, float, float]] = []
        accessor_indices: list[int] = []
        mesh_indices: list[int] = []
        for mesh_node, mesh_index in selected:
            mesh_points, mesh_accessors = _mesh_positions(
                document,
                binary,
                mesh_index,
                mesh_node,
            )
            overlap = used_accessors.intersection(mesh_accessors)
            if overlap:
                raise SourceLandmarkAnchorError(
                    "orientation landmarks cannot reuse POSITION geometry: "
                    + ",".join(str(item) for item in sorted(overlap))
                )
            used_accessors.update(mesh_accessors)
            points.extend(mesh_points)
            accessor_indices.extend(mesh_accessors)
            mesh_indices.append(mesh_index)
        source_min, source_max, source_center = _bounds(points)
        normalized_min, normalized_max = _transform_bounds(matrix, source_min, source_max)
        normalized_center = _transform_point(matrix, source_center)
        landmark = {
            "landmark_id": spec["landmark_id"],
            "anchor_id": spec["anchor_id"],
            "source_file": SOURCE_FILE,
            "source_file_sha256": expected_sha256,
            "source_node": source_node,
            "source_node_mode": spec["node_mode"],
            "source_mesh_nodes": list(selected_names),
            "source_mesh_indices": sorted(mesh_indices),
            "position_accessor_indices": sorted(accessor_indices),
            "source_vertex_count": len(points),
            "source_bounds_meters": {"min": source_min, "max": source_max},
            "source_aabb_center_meters": source_center,
            "normalized_bounds_meters": {"min": normalized_min, "max": normalized_max},
            "normalized_aabb_center_meters": normalized_center,
            "algorithm_id": ALGORITHM_ID,
            "source_bound": True,
            "authored": False,
            "counts_as_anatomy_component": False,
            "tissue_or_organ_claim": False,
            "function_implemented": False,
        }
        landmark["landmark_receipt_sha256"] = _canonical_sha256(landmark)
        landmarks.append(landmark)
    by_id = {item["landmark_id"]: item for item in landmarks}
    left = by_id["pelvic_side_anchor_left"]["source_bounds_meters"]
    right = by_id["pelvic_side_anchor_right"]["source_bounds_meters"]
    left_center = by_id["pelvic_side_anchor_left"]["source_aabb_center_meters"]
    right_center = by_id["pelvic_side_anchor_right"]["source_aabb_center_meters"]
    if not (left["min"][0] > right["max"][0] and left_center[0] > 0.0 > right_center[0]):
        raise SourceLandmarkAnchorError("pelvic left/right source geometry is swapped or overlapping")
    pubic = by_id["pubic_landmark_empty"]
    sacral = by_id["sacral_landmark_empty"]
    if not (
        pubic["source_aabb_center_meters"][2] > sacral["source_aabb_center_meters"][2]
        and pubic["normalized_aabb_center_meters"][1]
        < sacral["normalized_aabb_center_meters"][1]
    ):
        raise SourceLandmarkAnchorError("pubic/sacral anterior-posterior relation is invalid")
    landmarks.sort(key=lambda item: item["landmark_id"])
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "schema_version": 1,
        "status": RECEIPT_STATUS,
        "source": {
            "file": SOURCE_FILE,
            "bytes": expected_bytes,
            "sha256": expected_sha256,
            "glb_version": 2,
            "binary_positions_decoded": True,
        },
        "normalization": {
            "source_units": source_units,
            "source_axes": dict(source_axes),
            "target_units": target_units,
            "target_axes": dict(target_axes),
            "transform": matrix,
            "transform_sha256": _canonical_sha256(matrix),
        },
        "algorithm": {
            "algorithm_id": ALGORITHM_ID,
            "parameters_sha256": _canonical_sha256(LANDMARK_SPECS),
            "uses_binary_position_values": True,
            "uses_declared_accessor_bounds_as_verification_only": True,
            "point_rule": "center_of_exact_selected_source_geometry_axis_aligned_bounds",
            "mutates_source": False,
        },
        "landmarks": landmarks,
        "truth_limits": {
            "counts_as_anatomy_components": False,
            "authored_geometry": False,
            "tissue_or_organ_claim": False,
            "normalization_or_carrier_fit_completed": False,
            "internal_anatomy_complete": False,
            "whole_body_complete": False,
            "function_implemented": False,
            "blender_invoked": False,
            "runtime_activation_allowed": False,
        },
    }
    receipt["receipt_sha256"] = _canonical_sha256(receipt)
    return receipt


def validate_pelvic_landmark_anchor_receipt(
    receipt: Mapping[str, Any],
    source_path: Path | str,
    **derivation_arguments: Any,
) -> dict[str, Any]:
    """Re-derive and require byte-canonical receipt equality; reject spoofing."""

    if not isinstance(receipt, Mapping):
        raise SourceLandmarkAnchorError("pelvic landmark receipt must be an object")
    expected = derive_pelvic_landmark_anchor_receipt(
        source_path,
        **derivation_arguments,
    )
    if _canonical_bytes(dict(receipt)) != _canonical_bytes(expected):
        raise SourceLandmarkAnchorError("pelvic landmark receipt differs from exact re-derivation")
    return expected


__all__ = [
    "ALGORITHM_ID",
    "LANDMARK_SPECS",
    "NORMALIZATION_TRANSFORM",
    "RECEIPT_SCHEMA",
    "RECEIPT_STATUS",
    "SOURCE_AXES",
    "SOURCE_BYTES",
    "SOURCE_FILE",
    "SOURCE_SHA256",
    "SourceLandmarkAnchorError",
    "TARGET_AXES",
    "derive_pelvic_landmark_anchor_receipt",
    "validate_pelvic_landmark_anchor_receipt",
]
