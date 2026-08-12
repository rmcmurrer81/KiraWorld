"""Author one append-only, inactive Kira R18 bald private-review candidate.

This Blender-only worker consumes the exact frozen R17 candidate and the R18
preflight plan.  It never edits R17, exports a runtime avatar, activates or
assigns Kira, creates clothing or scalp hair, or begins Robert.  The surface
repair is deliberately topology preserving: the rejected R17 front plate is
reprojected in the P1 chart from the independently qualified adult-female
foundation by named, restricted anatomical-subchart closest-point projection,
with front rays only as a bounded last fallback. No donor index is copied and
no global nearest-neighbour transfer is used.

``probe`` writes a small append-only staging Blend and four diagnostic renders.
``delivery`` writes the full private owner-review package after immutable-diff,
intersection, bald-package, inactive-state, source-integrity, and movement
evidence gates have run.  Neither mode makes an owner-acceptance claim.
"""

from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import time
import traceback
from typing import Any, Iterable, Mapping, Sequence

import bmesh
import bpy
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tools.blender_build_kira_r17_corrected_bald_candidate as r17
import tools.blender_build_profiled_kira_bald_delivery_candidate as r16
import tools.blender_kira_face_delivery_v3 as face_v3
import tools.blender_profiled_adult_candidate_components as components
import tools.blender_report_kira_r18_preflight_masks as masks
from Core.avatar_kira_face_delivery_v3 import TARGETS
from Core.avatar_profiled_adult_candidate_contract import capture_live_kira_state_hashes
from tools.blender_author_adult_female_external_surface import (
    _nonadjacent_intersection_face_pairs,
)
from tools.blender_avatar_human_pose_clearance_v1 import (
    apply_pose_foundation_v1,
    reset_pose_v1,
)
from tools.blender_profiled_adult_candidate_components_v2 import (
    install_shadow_controlled_review_rig_v2,
)
from tools.prepare_kira_r18_bounded_bald_authoring import (
    P1_BOUNDARY,
    P2_BOUNDARY,
    R17_BLEND_RELATIVE,
    R17_BLEND_SHA256,
    R17_CANDIDATE_ID,
    R17_PACKAGE_INVENTORY_SHA256,
    index_set_sha256,
    package_inventory,
    sha256_file,
    validate_sources,
)


TARGET_HEIGHT_M = 1.651
PLAN_RELATIVE = Path(
    "RecoverySprint/continuation_20260802/"
    "kira_r18_bounded_bald_authoring_preparation/AUTHORING_PLAN.json"
)
PLAN_SHA256 = "0cda2366af4a0c440be805dcb1045dadfd5912335c2efe704fae25d4a05a1453"
FOUNDATION_RELATIVE = Path(
    "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/"
    "generic_makehuman_adult_female_foundation_inactive_v1_20260801/"
    "generic_makehuman_adult_female_foundation_inactive_v1_20260801.blend"
)
FOUNDATION_SHA256 = "3911419c44681d25f33892122e61206f1f4651bb78b3e403e377d1ed099cde2f"
PROBE_PARENT = Path(
    "RecoverySprint/continuation_20260802/kira_r18_bounded_bald_authoring"
)
DELIVERY_PARENT = Path("Avatar/private_owner_review")
DELIVERY_PREFIX = "kira_profiled_adult_candidate_r18_bald_targeted_"

EXPECTED_MASKS = {
    # The controlling preflight binds P1 by unique count/bounds and binds its
    # boundary digest.  It intentionally does not invent a component digest.
    "P1": (5478, None),
    "S": (286, "6d26abaea72462d046ceb66958e3cede7fbc84163b3215ff6fd0e19997b45601"),
    "K_L": (230, "f304e16f178574aed15b95b545fad44e1916370e8822a342c1bcf8f05255f44f"),
    "K_R": (230, "77ca8bfbbe07ac56cd61e1b20296a5d1775273353dca8b629f5cf1f70a1fdfc5"),
    "F1": (1385, "0f3889475e7fd928a916032e069def76b71b843e0bb7588d1535bb6363d275d9"),
    "F2": (187, "2603edd3d96c8ab505402cffec03653dcf1040b03b8fa5b2cb09685c64eeb1d3"),
    "H_L": (1671, "b07c12953d3c8cbc4fb2667aa19455d4e6150fdbd7d406ad1177b24ece84b803"),
    "H_R": (1671, "b63861cefe99dbde33505c1972344399a6f443a60cf3730d229d4863ef329074"),
    "T_L": (1150, "ac9d8f5293fae8a7ef3031e76c148e89903d07cd63f33fc1dab98f96cc0f7b85"),
    "T_R": (1150, "f5e4e4cc059120e2f3a4839d59b151f3a6e62d3165e5cc688136088f29988a5d"),
}
P1_BOUNDARY_SHA256 = "507b50a612b8fbe4f8946b7b58d58904e643db8e007e23922f859260cfe07c5b"


class KiraR18AuthoringError(RuntimeError):
    """Raised before a result may be represented as an R18 candidate."""


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-blend", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mode", choices=("probe", "delivery"), required=True)
    parser.add_argument("--attempt-number", type=int, choices=(1, 2, 3, 4), required=True)
    parser.add_argument("--surface-transfer-strength", type=float, default=1.0)
    parser.add_argument("--acknowledge-inactive-private-candidate", action="store_true")
    parser.add_argument("--render-owner-review", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def _json_safe(value: Any) -> Any:
    return r16.r15._json_safe(value)  # noqa: SLF001


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if not args.acknowledge_inactive_private_candidate:
        raise KiraR18AuthoringError(
            "--acknowledge-inactive-private-candidate is required"
        )
    if args.mode == "delivery" and not args.render_owner_review:
        raise KiraR18AuthoringError("delivery requires --render-owner-review")
    if not 0.65 <= float(args.surface_transfer_strength) <= 1.0:
        raise KiraR18AuthoringError("surface transfer strength must be 0.65..1.0")
    source = (PROJECT_ROOT / Path(args.source_blend)).resolve(strict=True)
    expected_source = (PROJECT_ROOT / R17_BLEND_RELATIVE).resolve(strict=True)
    if source != expected_source or sha256_file(source) != R17_BLEND_SHA256:
        raise KiraR18AuthoringError("only the exact frozen R17 Blend is permitted")
    if sha256_file(PROJECT_ROOT / PLAN_RELATIVE) != PLAN_SHA256:
        raise KiraR18AuthoringError("R18 authoring plan hash drifted")
    foundation = (PROJECT_ROOT / FOUNDATION_RELATIVE).resolve(strict=True)
    if sha256_file(foundation) != FOUNDATION_SHA256:
        raise KiraR18AuthoringError("qualified foundation hash drifted")

    relative = Path(args.output_dir)
    output = (PROJECT_ROOT / relative).resolve()
    if args.mode == "probe":
        required = (PROJECT_ROOT / PROBE_PARENT / f"attempt_{args.attempt_number:02d}").resolve()
        if output != required:
            raise KiraR18AuthoringError(
                f"probe output must be {required.relative_to(PROJECT_ROOT).as_posix()}"
            )
    else:
        parent = (PROJECT_ROOT / DELIVERY_PARENT).resolve()
        if output.parent != parent or not output.name.startswith(DELIVERY_PREFIX):
            raise KiraR18AuthoringError(
                "delivery output must be an append-only R18 private-review child"
            )
    if output.exists():
        raise KiraR18AuthoringError("append-only output already exists")
    return source, output, foundation


def _coordinate_digest(body: Any, indices: Iterable[int] | None = None) -> str:
    rows = range(len(body.data.vertices)) if indices is None else sorted(set(indices))
    digest = hashlib.sha256()
    rows = list(rows)
    digest.update(struct.pack("<Q", len(rows)))
    for index in rows:
        co = body.data.vertices[int(index)].co
        digest.update(struct.pack("<I3d", int(index), *(float(v) for v in co)))
    return digest.hexdigest()


def _topology_digest(body: Any) -> str:
    digest = hashlib.sha256()
    digest.update(
        struct.pack(
            "<QQQ",
            len(body.data.vertices),
            len(body.data.edges),
            len(body.data.polygons),
        )
    )
    for edge in body.data.edges:
        digest.update(struct.pack("<II", *(int(v) for v in edge.vertices)))
    for face in body.data.polygons:
        values = [int(v) for v in face.vertices]
        digest.update(struct.pack("<II", int(face.index), len(values)))
        digest.update(struct.pack(f"<{len(values)}I", *values))
    return digest.hexdigest()


def _weight_digest(body: Any) -> str:
    names = {int(group.index): group.name for group in body.vertex_groups}
    digest = hashlib.sha256()
    for vertex in body.data.vertices:
        assignments = sorted(
            (names[int(item.group)], float(item.weight)) for item in vertex.groups
        )
        digest.update(struct.pack("<II", int(vertex.index), len(assignments)))
        for name, weight in assignments:
            encoded = name.encode("utf-8")
            digest.update(struct.pack("<I", len(encoded)))
            digest.update(encoded)
            digest.update(struct.pack("<d", weight))
    return digest.hexdigest()


def _material_index_digest(body: Any) -> str:
    digest = hashlib.sha256()
    for face in body.data.polygons:
        digest.update(struct.pack("<II", int(face.index), int(face.material_index)))
    return digest.hexdigest()


def _attribute_digest(body: Any) -> str:
    """Digest all primary-mesh attributes without depending on RNA byte casts."""

    def digest_value(value: Any) -> bytes:
        if isinstance(value, bool):
            return b"b" + struct.pack("<?", value)
        if isinstance(value, int):
            return b"i" + struct.pack("<q", value)
        if isinstance(value, float):
            return b"f" + struct.pack("<d", value)
        if isinstance(value, str):
            encoded = value.encode("utf-8")
            return b"s" + struct.pack("<Q", len(encoded)) + encoded
        try:
            values = tuple(value)
        except TypeError as exc:
            raise KiraR18AuthoringError(
                f"unsupported mesh attribute value type: {type(value).__name__}"
            ) from exc
        encoded_values = b"".join(digest_value(item) for item in values)
        return b"a" + struct.pack("<Q", len(values)) + encoded_values

    digest = hashlib.sha256()
    for attribute in sorted(body.data.attributes, key=lambda item: item.name):
        if attribute.name in {"position", ".position"}:
            # Authorized coordinate edits are digested separately.
            continue
        digest.update(attribute.name.encode("utf-8"))
        digest.update(str(attribute.domain).encode("utf-8"))
        digest.update(str(attribute.data_type).encode("utf-8"))
        digest.update(struct.pack("<Q", len(attribute.data)))
        for item in attribute.data:
            if hasattr(item, "color"):
                digest.update(digest_value(item.color))
            elif hasattr(item, "vector"):
                digest.update(digest_value(item.vector))
            elif hasattr(item, "value"):
                digest.update(digest_value(item.value))
            else:
                raise KiraR18AuthoringError(
                    f"unsupported mesh attribute data item: {attribute.name}"
                )
    return digest.hexdigest()


def _action_digest() -> str:
    """Digest legacy and Blender 5.1 layered actions without mutating either."""

    def curve_rows(curves: Iterable[Any]) -> list[dict[str, Any]]:
        rows = []
        for curve in sorted(
            curves,
            key=lambda value: (value.data_path, int(value.array_index)),
        ):
            rows.append(
                {
                    "path": str(curve.data_path),
                    "index": int(curve.array_index),
                    "extrapolation": str(curve.extrapolation),
                    "keys": [
                        {
                            "co": [float(point.co.x), float(point.co.y)],
                            "handle_left": [
                                float(point.handle_left.x),
                                float(point.handle_left.y),
                            ],
                            "handle_right": [
                                float(point.handle_right.x),
                                float(point.handle_right.y),
                            ],
                            "handle_left_type": str(point.handle_left_type),
                            "handle_right_type": str(point.handle_right_type),
                            "interpolation": str(point.interpolation),
                            "easing": str(point.easing),
                        }
                        for point in curve.keyframe_points
                    ],
                }
            )
        return rows

    rows = []
    for action in sorted(bpy.data.actions, key=lambda value: value.name):
        action_row: dict[str, Any] = {
            "name": action.name,
            "frame_range": [float(value) for value in action.frame_range],
        }
        if hasattr(action, "fcurves"):
            action_row["storage"] = "legacy"
            action_row["curves"] = curve_rows(action.fcurves)
        else:
            action_row["storage"] = "layered"
            action_row["slots"] = [
                {
                    "handle": int(slot.handle),
                    "identifier": str(slot.identifier),
                    "target_id_type": str(slot.target_id_type),
                }
                for slot in sorted(action.slots, key=lambda value: int(value.handle))
            ]
            action_row["layers"] = []
            for layer in action.layers:
                layer_row = {"name": str(layer.name), "strips": []}
                for strip in layer.strips:
                    strip_row = {"type": str(strip.type), "channelbags": []}
                    for channelbag in sorted(
                        strip.channelbags,
                        key=lambda value: int(value.slot_handle),
                    ):
                        strip_row["channelbags"].append(
                            {
                                "slot_handle": int(channelbag.slot_handle),
                                "curves": curve_rows(channelbag.fcurves),
                            }
                        )
                    layer_row["strips"].append(strip_row)
                action_row["layers"].append(layer_row)
        rows.append(action_row)
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _mesh_object_geometry_digest(obj: Any) -> str:
    if obj.type != "MESH":
        return ""
    digest = hashlib.sha256()
    digest.update(_topology_digest(obj).encode("ascii"))
    digest.update(_coordinate_digest(obj).encode("ascii"))
    for slot in obj.material_slots:
        digest.update((slot.material.name if slot.material else "").encode("utf-8"))
    return digest.hexdigest()


def _protected_object_geometry() -> list[str]:
    selected = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and any(
            token in obj.name.casefold()
            for token in ("sclera", "iris", "cornea", "lid", "lash", "crease")
        )
    ]
    # Object/candidate metadata is retagged for the append-only package.  The
    # protected invariant is geometry/material content, not an R17 name prefix.
    return sorted(_mesh_object_geometry_digest(obj) for obj in selected)


def _adjacency(body: Any) -> list[set[int]]:
    result = [set() for _ in body.data.vertices]
    for edge in body.data.edges:
        left, right = (int(v) for v in edge.vertices)
        result[left].add(right)
        result[right].add(left)
    return result


def _p1_component(body: Any, adjacency: Sequence[set[int]]) -> set[int]:
    remaining = set(range(13380, len(body.data.vertices)))
    components_found: list[set[int]] = []
    while remaining:
        seed = min(remaining)
        queue = [seed]
        component: set[int] = set()
        remaining.remove(seed)
        while queue:
            current = queue.pop()
            component.add(current)
            for neighbor in adjacency[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
        components_found.append(component)
    matches = []
    for component in components_found:
        if len(component) != EXPECTED_MASKS["P1"][0]:
            continue
        points = [body.data.vertices[index].co for index in component]
        low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
        high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
        if (
            abs(low.x + 0.0629142) < 2.0e-5
            and abs(high.x - 0.0629142) < 2.0e-5
            and abs(low.z - 0.6568492) < 2.0e-5
            and abs(high.z - 0.8720571) < 2.0e-5
        ):
            matches.append(component)
    if len(matches) != 1:
        raise KiraR18AuthoringError(f"exact P1 component not unique: {len(matches)}")
    return matches[0]


def _target_sets(body: Any) -> tuple[set[int], set[int], dict[str, set[int]], dict[str, Any]]:
    source = masks._prepared_source()  # noqa: SLF001
    source_to_body = source["source_to_body"]
    baseline = source["body_vertices"]
    minimum_z = TARGET_HEIGHT_M * 0.76
    target_sets: dict[str, set[int]] = {}
    for record in TARGETS:
        indices = {
            int(source_to_body[source_index])
            for source_index in face_v3._read_target(  # noqa: SLF001
                PROJECT_ROOT / str(record["path"])
            )
            if source_index in source_to_body
            and float(baseline[source_to_body[source_index]].z) >= minimum_z
        }
        target_sets[str(record["target_id"])] = indices
    f1 = set().union(
        *(value for key, value in target_sets.items() if key != "head_oval_soft")
    )
    f2 = target_sets["lower_lip_natural_volume"]
    return f1, f2, target_sets, source


def _verify_mask(name: str, indices: Iterable[int]) -> None:
    rows = set(int(v) for v in indices)
    expected_count, expected_hash = EXPECTED_MASKS[name]
    actual = index_set_sha256(rows)
    if len(rows) != expected_count or (
        expected_hash is not None and actual != expected_hash
    ):
        raise KiraR18AuthoringError(
            f"{name} mask drifted: count={len(rows)} sha256={actual}"
        )


def _derive_masks(body: Any) -> dict[str, set[int]]:
    adjacency = _adjacency(body)
    p1 = _p1_component(body, adjacency)
    scalp, _ = masks._scalp_mask(body)  # noqa: SLF001
    _knees_union, knees = masks._knee_masks(body)  # noqa: SLF001
    f1, f2, _targets, _source = _target_sets(body)
    result = {"P1": p1, "S": scalp, "F1": f1, "F2": f2}
    for side in ("L", "R"):
        knee_group = body.vertex_groups[f"AVATAR_BUILDER_KNEE_CORRECTIVE_V2_{side}"]
        result[f"K_{side}"] = {
            int(vertex.index)
            for vertex in body.data.vertices
            if any(
                int(item.group) == int(knee_group.index) and float(item.weight) > 0.0
                for item in vertex.groups
            )
        }
        for kind, prefix in (("hand", "H"), ("foot", "T")):
            values, _record = masks._limb_mask(body, side=side, kind=kind)  # noqa: SLF001
            result[f"{prefix}_{side}"] = values
    for name, indices in result.items():
        _verify_mask(name, indices)
    if index_set_sha256(P1_BOUNDARY) != P1_BOUNDARY_SHA256:
        raise KiraR18AuthoringError("P1 boundary constant drifted")
    return result


def _boundary_distance(
    editable: set[int], boundary: set[int], adjacency: Sequence[set[int]]
) -> dict[int, int]:
    distance: dict[int, int] = {}
    queue: deque[int] = deque()
    allowed = editable.union(boundary)
    for index in boundary:
        distance[index] = 0
        queue.append(index)
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current]:
            if neighbor in allowed and neighbor not in distance:
                distance[neighbor] = distance[current] + 1
                queue.append(neighbor)
    missing = editable.difference(distance)
    if missing:
        raise KiraR18AuthoringError(
            f"editable chart disconnected from pinned boundary: {len(missing)}"
        )
    return distance


def _append_foundation_objects(path: Path) -> tuple[Any, list[Any]]:
    with bpy.data.libraries.load(str(path), link=False) as (available, requested):
        requested.objects = list(available.objects)
    objects = [obj for obj in requested.objects if obj is not None]
    collection = bpy.data.collections.new("R18_TEMP_QUALIFIED_FOUNDATION_REFERENCE")
    bpy.context.scene.collection.children.link(collection)
    for obj in objects:
        collection.objects.link(obj)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    if not meshes:
        raise KiraR18AuthoringError("qualified foundation contains no mesh")
    primary = max(meshes, key=lambda obj: len(obj.data.vertices))
    return primary, objects


def _remove_foundation_objects(objects: Sequence[Any]) -> None:
    meshes = [obj.data for obj in objects if obj.type == "MESH"]
    for obj in list(objects):
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    collection = bpy.data.collections.get("R18_TEMP_QUALIFIED_FOUNDATION_REFERENCE")
    if collection is not None:
        bpy.data.collections.remove(collection)


def _foundation_reference_bvhs(
    foundation: Any, body: Any
) -> tuple[BVHTree, dict[str, BVHTree], dict[int, str], dict[str, Any]]:
    prefix = "AFES_LANDMARK__"
    foundation_group_names = {
        int(group.index): group.name
        for group in foundation.vertex_groups
        if group.name.startswith(prefix)
    }
    group_indices = set(foundation_group_names)
    landmark_vertices = {
        int(vertex.index)
        for vertex in foundation.data.vertices
        if any(int(item.group) in group_indices and float(item.weight) > 0.0 for item in vertex.groups)
    }
    if len(landmark_vertices) < 500:
        raise KiraR18AuthoringError(
            f"qualified foundation landmark chart unexpectedly small: {len(landmark_vertices)}"
        )
    body_inverse = body.matrix_world.inverted()
    coordinates = [
        body_inverse @ (foundation.matrix_world @ vertex.co)
        for vertex in foundation.data.vertices
    ]
    faces = []
    for face in foundation.data.polygons:
        values = [int(index) for index in face.vertices]
        if not any(index in landmark_vertices for index in values):
            continue
        center_z = sum(float(coordinates[index].z) for index in values) / len(values)
        if 0.62 <= center_z <= 0.91:
            faces.append(values)
    if len(faces) < 1500:
        raise KiraR18AuthoringError(
            f"qualified foundation restricted chart unexpectedly small: {len(faces)}"
        )
    global_tree = BVHTree.FromPolygons(coordinates, faces, all_triangles=False)
    group_members: dict[str, set[int]] = {
        name: set() for name in foundation_group_names.values()
    }
    for vertex in foundation.data.vertices:
        for item in vertex.groups:
            name = foundation_group_names.get(int(item.group))
            if name is not None and float(item.weight) > 0.05:
                group_members[name].add(int(vertex.index))
    group_trees: dict[str, BVHTree] = {}
    group_face_counts: dict[str, int] = {}
    for name, members in group_members.items():
        local_faces = [
            values for values in faces if any(index in members for index in values)
        ]
        if len(local_faces) >= 8:
            group_trees[name] = BVHTree.FromPolygons(
                coordinates, local_faces, all_triangles=False
            )
            group_face_counts[name] = len(local_faces)

    body_group_names = {
        int(group.index): group.name
        for group in body.vertex_groups
        if group.name in group_trees
    }
    body_dominant: dict[int, str] = {}
    for vertex in body.data.vertices:
        choices = [
            (float(item.weight), body_group_names[int(item.group)])
            for item in vertex.groups
            if int(item.group) in body_group_names and float(item.weight) > 0.05
        ]
        if choices:
            body_dominant[int(vertex.index)] = max(choices)[1]
    return global_tree, group_trees, body_dominant, {
        "foundation_object": foundation.name,
        "landmark_vertex_count": len(landmark_vertices),
        "restricted_face_count": len(faces),
        "anatomical_subchart_count": len(group_trees),
        "anatomical_subchart_face_counts": group_face_counts,
        "selection": (
            "AFES landmark incident faces restricted to pelvic/perineal z chart, "
            "then divided by dominant named anatomical landmark for local transfer"
        ),
    }


def _apply_p1_reference_transfer(
    body: Any,
    p1: set[int],
    adjacency: Sequence[set[int]],
    foundation_path: Path,
    strength: float,
    permitted_intersections: set[tuple[int, int]],
) -> dict[str, Any]:
    foundation, temp_objects = _append_foundation_objects(foundation_path)
    try:
        tree, group_trees, body_dominant, reference = _foundation_reference_bvhs(
            foundation, body
        )
        distances = _boundary_distance(p1, set(P1_BOUNDARY), adjacency)
        before = {index: body.data.vertices[index].co.copy() for index in p1}
        boundary_before = {
            index: body.data.vertices[index].co.copy() for index in P1_BOUNDARY
        }
        anatomical_local_hits = 0
        chart_local_hits = 0
        ray_fallbacks = 0
        displacements: list[float] = []
        capped = 0
        for index in sorted(p1):
            point = before[index]
            group_name = body_dominant.get(index)
            local_tree = group_trees.get(group_name, tree)
            hit, _normal, _face, _distance = local_tree.find_nearest(point, 0.045)
            if hit is None:
                hit, _normal, _face, _distance = tree.find_nearest(point, 0.045)
                if hit is not None:
                    chart_local_hits += 1
            else:
                anatomical_local_hits += 1
            if hit is None:
                origin = Vector((point.x, -0.35, point.z))
                hit, _normal, _face, _distance = tree.ray_cast(
                    origin, Vector((0.0, 1.0, 0.0)), 0.55
                )
                if hit is None:
                    continue
                ray_fallbacks += 1
            ring = int(distances[index])
            fade = min(1.0, max(0.0, ring / 7.0))
            fade = fade * fade * (3.0 - 2.0 * fade)
            proposed_delta = (float(hit.y) - float(point.y)) * fade * float(strength)
            maximum = 0.030
            if abs(proposed_delta) > maximum:
                proposed_delta = math.copysign(maximum, proposed_delta)
                capped += 1
            # A sub-millimetre lateral asymmetry avoids a perfectly mirrored
            # mannequin read while remaining far below the transferred relief.
            asymmetry = (
                0.00016
                * math.sin((float(point.z) - 0.72) * 95.0)
                * math.tanh(float(point.x) / 0.010)
                * fade
            )
            body.data.vertices[index].co.y = float(point.y) + proposed_delta + asymmetry
            displacements.append(abs(proposed_delta + asymmetry))
        body.data.update()
        bpy.context.view_layer.update()
        boundary_exact = all(
            (body.data.vertices[index].co - boundary_before[index]).length <= 1.0e-12
            for index in P1_BOUNDARY
        )
        if anatomical_local_hits + chart_local_hits + ray_fallbacks < int(len(p1) * 0.93):
            raise KiraR18AuthoringError(
                "too few local qualified-chart transfer hits: "
                f"{anatomical_local_hits + chart_local_hits + ray_fallbacks}/{len(p1)}"
            )
        proposed = {index: body.data.vertices[index].co.copy() for index in p1}
        initial_pairs = _rest_intersections(body)
        initial_new_pairs = initial_pairs.difference(permitted_intersections)
        protected_core: set[int] = set()
        backoff_vertices: set[int] = set()
        backoff_iterations = []
        remaining_new_pairs = set(initial_new_pairs)
        for iteration, margin in enumerate((5, 7, 9, 11), start=1):
            if not remaining_new_pairs:
                break
            for left, right in remaining_new_pairs:
                for face_index in (left, right):
                    protected_core.update(
                        int(index)
                        for index in body.data.polygons[face_index].vertices
                        if int(index) in p1
                    )
            if not protected_core:
                raise KiraR18AuthoringError(
                    "P1 transfer created an intersection with no P1 vertex to back off"
                )
            distances: dict[int, int] = {index: 0 for index in protected_core}
            queue: deque[int] = deque(sorted(protected_core))
            while queue:
                current = queue.popleft()
                if distances[current] >= margin:
                    continue
                for neighbor in adjacency[current]:
                    if neighbor in p1 and neighbor not in distances:
                        distances[neighbor] = distances[current] + 1
                        queue.append(neighbor)
            for index in p1:
                distance = distances.get(index)
                if distance is None or distance >= margin:
                    body.data.vertices[index].co = proposed[index]
                    continue
                ratio = max(0.0, min(1.0, float(distance) / float(margin)))
                blend = ratio * ratio * (3.0 - 2.0 * ratio)
                body.data.vertices[index].co = before[index].lerp(proposed[index], blend)
                backoff_vertices.add(index)
            body.data.update()
            bpy.context.view_layer.update()
            iteration_pairs = _rest_intersections(body)
            remaining_new_pairs = iteration_pairs.difference(permitted_intersections)
            backoff_iterations.append(
                {
                    "iteration": iteration,
                    "margin_edge_rings": margin,
                    "protected_core_vertex_count": len(protected_core),
                    "backoff_vertex_count": len(backoff_vertices),
                    "remaining_new_pair_count": len(remaining_new_pairs),
                }
            )
        if remaining_new_pairs:
            raise KiraR18AuthoringError(
                "P1 collision-aware backoff did not reach zero new pairs: "
                f"remaining={len(remaining_new_pairs)}"
            )
        final_displacements = [
            abs(float(body.data.vertices[index].co.y) - float(before[index].y))
            for index in p1
        ]
        return {
            "method": "restricted_named_anatomical_subchart_barycentric_transfer_v1",
            "direct_index_graft_used": False,
            "global_nearest_neighbor_used": False,
            "donor_vertex_indices_copied": False,
            "topology_changed": False,
            "p1_vertex_count": len(p1),
            "p1_index_set_sha256": index_set_sha256(p1),
            "pinned_boundary_vertex_count": len(P1_BOUNDARY),
            "pinned_boundary_sha256": index_set_sha256(P1_BOUNDARY),
            "pinned_boundary_exact": boundary_exact,
            "named_anatomical_subchart_closest_point_hits": anatomical_local_hits,
            "restricted_chart_closest_point_hits": chart_local_hits,
            "restricted_front_ray_fallbacks": ray_fallbacks,
            "displacement_count": len(final_displacements),
            "maximum_abs_displacement_m": max(final_displacements, default=0.0),
            "mean_abs_displacement_m": (
                sum(final_displacements) / len(final_displacements)
                if final_displacements
                else 0.0
            ),
            "initial_pre_backoff_maximum_abs_displacement_m": max(
                displacements, default=0.0
            ),
            "maximum_delta_cap_count": capped,
            "surface_transfer_strength": float(strength),
            "collision_safe_backoff": {
                "required": bool(initial_new_pairs),
                "initial_new_pair_count": len(initial_new_pairs),
                "final_new_pair_count": len(remaining_new_pairs),
                "protected_core_vertex_count": len(protected_core),
                "backoff_vertex_count": len(backoff_vertices),
                "iterations": backoff_iterations,
                "policy": (
                    "retain the qualified P1 transfer outside the exact local "
                    "self-contact neighborhood; blend that neighborhood back "
                    "toward its already non-intersecting post-face coordinates"
                ),
            },
            "reference": reference,
            "qualified_foundation_path": FOUNDATION_RELATIVE.as_posix(),
            "qualified_foundation_sha256": FOUNDATION_SHA256,
            "owner_visual_review_required": True,
        }
    finally:
        _remove_foundation_objects(temp_objects)


def _apply_face_targets(
    body: Any,
    source: Mapping[str, Any],
    target_sets: Mapping[str, set[int]],
) -> dict[str, Any]:
    source_to_body = source["source_to_body"]
    scale = float(source["uniform_scale"])
    weight_adjustments = {
        "lower_lip_natural_volume": -0.08,  # exact 0.20 -> 0.12
        "chin_width_soft_decrease": +0.035,
        "chin_soft_triangle": +0.025,
        "nose_horizontal_soft_decrease": +0.025,
        "nose_volume_soft_decrease": +0.015,
        "left_cheekbone_soft_definition": +0.028,
        "right_cheekbone_soft_definition": +0.022,
    }
    reports = []
    maximum = 0.0
    changed: set[int] = set()
    records = {str(row["target_id"]): row for row in TARGETS}
    for target_id, delta_weight in weight_adjustments.items():
        record = records[target_id]
        rows = face_v3._read_target(PROJECT_ROOT / str(record["path"]))  # noqa: SLF001
        local_changed = 0
        local_max = 0.0
        for source_index, raw_delta in rows.items():
            compact = source_to_body.get(source_index)
            if compact is None or int(compact) not in target_sets[target_id]:
                continue
            delta = components._converted_makehuman(raw_delta) * scale * float(delta_weight)  # noqa: SLF001
            body.data.vertices[int(compact)].co += delta
            changed.add(int(compact))
            local_changed += 1
            local_max = max(local_max, float(delta.length))
            maximum = max(maximum, float(delta.length))
        reports.append(
            {
                "target_id": target_id,
                "weight_adjustment": float(delta_weight),
                "changed_vertex_count": local_changed,
                "maximum_vertex_delta_m": local_max,
            }
        )
    body.data.update()
    bpy.context.view_layer.update()
    return {
        "method": "bounded_kira_face_r18_target_weight_refinement",
        "lower_lip_weight_before": 0.20,
        "lower_lip_weight_after": 0.12,
        "changed_vertex_count": len(changed),
        "changed_index_set_sha256": index_set_sha256(changed),
        "maximum_single_target_delta_m": maximum,
        "target_adjustments": reports,
        "head_oval_or_cranium_changed": False,
        "eyes_lids_lashes_changed": False,
        "identity_match_claim_allowed": False,
        "owner_visual_review_required": True,
    }


def _smooth_mask(
    body: Any,
    indices: set[int],
    adjacency: Sequence[set[int]],
    *,
    iterations: int,
    alpha: float,
    maximum_total_m: float,
    axes: tuple[bool, bool, bool] = (True, True, True),
) -> dict[str, Any]:
    boundary = {
        index for index in indices if any(neighbor not in indices for neighbor in adjacency[index])
    }
    interior = indices.difference(boundary)
    initial = {index: body.data.vertices[index].co.copy() for index in indices}
    for _iteration in range(iterations):
        proposed: dict[int, Vector] = {}
        for index in interior:
            neighbors = adjacency[index].intersection(indices)
            if not neighbors:
                continue
            average = sum(
                (body.data.vertices[neighbor].co for neighbor in neighbors),
                Vector(),
            ) / len(neighbors)
            current = body.data.vertices[index].co.copy()
            delta = (average - current) * float(alpha)
            for axis, allowed in enumerate(axes):
                if not allowed:
                    delta[axis] = 0.0
            candidate = current + delta
            total = candidate - initial[index]
            if total.length > maximum_total_m:
                candidate = initial[index] + total.normalized() * maximum_total_m
            proposed[index] = candidate
        for index, coordinate in proposed.items():
            body.data.vertices[index].co = coordinate
    body.data.update()
    bpy.context.view_layer.update()
    changed = {
        index
        for index in indices
        if (body.data.vertices[index].co - initial[index]).length > 1.0e-12
    }
    maximum = max(
        ((body.data.vertices[index].co - initial[index]).length for index in changed),
        default=0.0,
    )
    if any((body.data.vertices[index].co - initial[index]).length > 1.0e-12 for index in boundary):
        raise KiraR18AuthoringError("local fairing moved a pinned mask boundary")
    return {
        "mask_vertex_count": len(indices),
        "mask_index_set_sha256": index_set_sha256(indices),
        "pinned_boundary_vertex_count": len(boundary),
        "interior_vertex_count": len(interior),
        "changed_vertex_count": len(changed),
        "changed_index_set_sha256": index_set_sha256(changed),
        "iterations": iterations,
        "alpha": alpha,
        "maximum_total_displacement_m": maximum,
        "topology_changed": False,
        "weights_changed": False,
    }


def _front_surface_y(tree: BVHTree, x: float, z: float, fallback_y: float) -> float:
    hit, _normal, _face, _distance = tree.ray_cast(
        Vector((x, -0.35, z)), Vector((0.0, 1.0, 0.0)), 0.50
    )
    return float(hit.y) if hit is not None else float(fallback_y)


def _replace_brows(body: Any, armature: Any, candidate_id: str) -> dict[str, Any]:
    old = sorted(
        [obj for obj in bpy.data.objects if "continuous_brow_v3_" in obj.name],
        key=lambda item: item.name,
    )
    if len(old) != 2:
        raise KiraR18AuthoringError(f"expected exact two R17 brow objects, found {len(old)}")
    body_tree = BVHTree.FromPolygons(
        [vertex.co.copy() for vertex in body.data.vertices],
        [[int(v) for v in face.vertices] for face in body.data.polygons],
        all_triangles=False,
    )
    old_records = []
    created = []
    for obj in old:
        side = "L" if obj.name.endswith("_L") else "R"
        body_inverse = body.matrix_world.inverted()
        points = [body_inverse @ (obj.matrix_world @ Vector(corner)) for corner in obj.bound_box]
        x_min, x_max = min(p.x for p in points), max(p.x for p in points)
        z_center = sum(p.z for p in points) / len(points)
        y_front = min(p.y for p in points)
        material = obj.data.materials[0] if len(obj.data.materials) else None
        old_records.append({"object": obj.name, "geometry_sha256": _mesh_object_geometry_digest(obj)})
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)

        inner = x_min if side == "L" else x_max
        outer = x_max if side == "L" else x_min
        vertices: list[tuple[float, float, float]] = []
        faces: list[tuple[int, int, int, int]] = []
        strand_count = 17
        for number in range(strand_count):
            t = number / (strand_count - 1)
            x = inner + (outer - inner) * t
            arch = math.sin(math.pi * min(1.0, max(0.0, t)))
            z = z_center + 0.0040 * arch - 0.0015 * t
            surface_y = _front_surface_y(body_tree, x, z, y_front)
            y = surface_y - 0.00065
            length = 0.0049 - 0.0014 * abs(t - 0.35)
            width = 0.00042 * (0.72 + 0.28 * arch)
            sign = 1.0 if side == "L" else -1.0
            hair_dx = sign * length * (0.52 + 0.28 * t)
            hair_dz = length * (0.86 - 0.52 * t)
            direction = Vector((hair_dx, 0.0, hair_dz)).normalized()
            normal = Vector((-direction.z, 0.0, direction.x))
            start = Vector((x, y, z)) - direction * (length * 0.45)
            end = Vector((x, y - 0.00005, z)) + direction * (length * 0.55)
            base = len(vertices)
            vertices.extend(
                [
                    tuple(start - normal * width),
                    tuple(start + normal * width),
                    tuple(end + normal * width * 0.18),
                    tuple(end - normal * width * 0.18),
                ]
            )
            faces.append((base, base + 1, base + 2, base + 3))
        mesh = bpy.data.meshes.new(f"{candidate_id}_natural_brow_strands_r18_{side}_mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        brow = bpy.data.objects.new(f"{candidate_id}_natural_brow_strands_r18_{side}", mesh)
        bpy.context.collection.objects.link(brow)
        if material is not None:
            mesh.materials.append(material)
            material.diffuse_color = (0.030, 0.017, 0.012, 1.0)
            material.use_nodes = True
            principled = material.node_tree.nodes.get("Principled BSDF")
            if principled is not None:
                principled.inputs["Base Color"].default_value = material.diffuse_color
                principled.inputs["Roughness"].default_value = 0.72
        brow.parent = armature
        brow.matrix_parent_inverse = armature.matrix_world.inverted()
        group = brow.vertex_groups.new(name="head")
        group.add(list(range(len(vertices))), 1.0, "REPLACE")
        modifier = brow.modifiers.new("R18_Brow_Head_Attachment", "ARMATURE")
        modifier.object = armature
        brow["candidate_id"] = candidate_id
        brow["inactive_candidate"] = True
        brow["private_owner_review_only"] = True
        brow["runtime_activation_allowed"] = False
        brow["facial_presentation_role"] = "brow"
        brow["scalp_hair"] = False
        created.append(
            {
                "object": brow.name,
                "side": side,
                "strand_count": strand_count,
                "vertex_count": len(vertices),
                "face_count": len(faces),
                "geometry_sha256": _mesh_object_geometry_digest(brow),
            }
        )
    return {
        "method": "detachable_mesh_brow_strands_r18",
        "old_objects": old_records,
        "new_objects": created,
        "object_count": len(created),
        "scalp_hair_dependency_created": False,
        "body_or_eye_geometry_changed": False,
    }


def _refine_nail_presentation(candidate_id: str) -> dict[str, Any]:
    nails = sorted(
        [obj for obj in bpy.data.objects if bool(obj.get("nail_component"))],
        key=lambda item: item.name,
    )
    if len(nails) != 20:
        raise KiraR18AuthoringError(f"expected 20 detachable nails, found {len(nails)}")
    records = []
    for nail in nails:
        old_name = nail.name
        if old_name.startswith(R17_CANDIDATE_ID):
            nail.name = candidate_id + old_name[len(R17_CANDIDATE_ID) :]
        nail["candidate_id"] = candidate_id
        nail["inactive_candidate"] = True
        nail["private_owner_review_only"] = True
        nail["runtime_activation_allowed"] = False
        for material in nail.data.materials:
            if material is None:
                continue
            material.use_nodes = True
            principled = material.node_tree.nodes.get("Principled BSDF")
            if principled is not None:
                if "free" in material.name.casefold():
                    principled.inputs["Roughness"].default_value = 0.33
                else:
                    principled.inputs["Roughness"].default_value = 0.30
                if "Coat Weight" in principled.inputs:
                    principled.inputs["Coat Weight"].default_value = 0.12
                if "Coat Roughness" in principled.inputs:
                    principled.inputs["Coat Roughness"].default_value = 0.24
        records.append(
            {
                "object": nail.name,
                "geometry_sha256": _mesh_object_geometry_digest(nail),
                "body_geometry_changed": False,
                "detachable": True,
            }
        )
    return {
        "method": "reuse_exact_natural_nail_v3_geometry_with_bounded_material_refinement",
        "count": len(records),
        "objects": records,
        "body_or_digit_mutation": False,
    }


def _rest_intersections(body: Any) -> set[tuple[int, int]]:
    bm = bmesh.new()
    try:
        bm.from_mesh(body.data)
        bm.faces.ensure_lookup_table()
        return set(_nonadjacent_intersection_face_pairs(bm))
    finally:
        bm.free()


def _evaluated_intersections(body: Any) -> set[tuple[int, int]]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        return set(_nonadjacent_intersection_face_pairs(bm))
    finally:
        bm.free()
        evaluated.to_mesh_clear()


def _retag_candidate(candidate_id: str, body: Any, armature: Any) -> list[Any]:
    candidate_objects = [
        obj
        for obj in bpy.data.objects
        if str(obj.get("candidate_id") or "") == R17_CANDIDATE_ID
        or str(obj.get("candidate_id") or "") == candidate_id
    ]
    for obj in candidate_objects:
        if obj.name.startswith(R17_CANDIDATE_ID):
            obj.name = candidate_id + obj.name[len(R17_CANDIDATE_ID) :]
        obj["candidate_id"] = candidate_id
        obj["inactive_candidate"] = True
        obj["private_owner_review_only"] = True
        obj["runtime_activation_allowed"] = False
        obj["assigned"] = False
        obj["activated"] = False
        obj["published"] = False
        obj["uploaded"] = False
    if body not in candidate_objects or armature not in candidate_objects:
        raise KiraR18AuthoringError("primary body or armature missing from retag inventory")
    scene = bpy.context.scene
    r16.r15._mark_inactive_private(candidate_objects, scene, candidate_id)  # noqa: SLF001
    scene["candidate_id"] = candidate_id
    scene["candidate_status"] = "INACTIVE_UNASSIGNED_AWAITING_OWNER_VISUAL_DECISION"
    scene["candidate_author_id"] = "kira_r18_bounded_targeted_bald_authoring"
    scene["candidate_asset_id"] = "KIRA_BALD_LOW_RESOURCE_BODY"
    scene["complete_natural_bald_scalp"] = True
    scene["scalp_hair_dependency_allowed"] = False
    scene["runtime_export_allowed"] = False
    body["candidate_asset_id"] = "KIRA_BALD_LOW_RESOURCE_BODY"
    body["complete_natural_bald_scalp"] = True
    body["scalp_hair_dependency_allowed"] = False
    body["owner_visual_review_required"] = True
    body["identity_match_claim_allowed"] = False
    return candidate_objects


def _render_probe(
    scene: Any, output: Path, body: Any, candidate_objects: Sequence[Any]
) -> list[dict[str, Any]]:
    camera, _lighting = install_shadow_controlled_review_rig_v2(scene, TARGET_HEIGHT_M)
    low, high = r16.r15._world_bounds([body])  # noqa: SLF001
    body_target = Vector((0.0, (low.y + high.y) * 0.5, TARGET_HEIGHT_M * 0.51))
    face_target = Vector((0.0, (low.y + high.y) * 0.5, high.z - TARGET_HEIGHT_M * 0.085))
    protected_target = Vector((0.0, -0.068, 0.767))
    views = [
        ("attempt_surface_front", protected_target, Vector((0.0, -1.0, 0.02)), TARGET_HEIGHT_M * 0.31, 900, 900),
        ("attempt_surface_three_quarter", protected_target, Vector((0.72, -0.70, 0.02)), TARGET_HEIGHT_M * 0.31, 900, 900),
        ("attempt_face_and_brows", face_target, Vector((0.0, -1.0, 0.01)), TARGET_HEIGHT_M * 0.33, 900, 900),
        ("attempt_complete_neutral", body_target, Vector((0.0, -1.0, 0.03)), TARGET_HEIGHT_M * 1.12, 900, 1100),
    ]
    records = []
    for label, target, direction, scale, width, height in views:
        camera.location = target + direction.normalized() * (TARGET_HEIGHT_M * 3.0)
        r16.r15._look_at(camera, target)  # noqa: SLF001
        camera.data.ortho_scale = scale
        scene.render.resolution_x = width
        scene.render.resolution_y = height
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        path = output / f"{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        records.append({"label": label, "path": path.name, "sha256": sha256_file(path)})
    return records


def _render_extra(
    scene: Any,
    output: Path,
    body: Any,
    armature: Any,
    knee_report: Mapping[str, Any],
    seat_name: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    camera = scene.camera
    if camera is None:
        raise KiraR18AuthoringError("review camera missing")
    low, high = r16.r15._world_bounds([body])  # noqa: SLF001
    face_target = Vector((0.0, (low.y + high.y) * 0.5, high.z - TARGET_HEIGHT_M * 0.10))
    protected_target = Vector((0.0, -0.068, 0.767))
    records: list[dict[str, Any]] = []
    pose_audits: dict[str, Any] = {}

    def render(label: str, target: Vector, direction: Vector, scale: float, portrait: bool = False) -> None:
        camera.location = target + direction.normalized() * (TARGET_HEIGHT_M * 3.0)
        r16.r15._look_at(camera, target)  # noqa: SLF001
        camera.data.ortho_scale = scale
        scene.render.resolution_x = 900
        scene.render.resolution_y = 1100 if portrait else 900
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        path = output / f"{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        records.append({"label": label, "path": path.name, "sha256": sha256_file(path)})

    reset_pose_v1(armature)
    render("brows_close", face_target, Vector((0.0, -1.0, 0.01)), TARGET_HEIGHT_M * 0.16)
    render(
        "diagnostic_medical_external_view",
        protected_target,
        Vector((0.0, -1.0, 0.02)),
        TARGET_HEIGHT_M * 0.24,
    )

    knee_center = (
        armature.matrix_world @ armature.data.bones["lowerleg01.L"].head_local
        + armature.matrix_world @ armature.data.bones["lowerleg01.R"].head_local
    ) * 0.5
    for side_name, solution_name in (("left", "left"), ("right", "right")):
        for degrees in (30, 55, 80):
            reset_pose_v1(armature)
            solution = dict(knee_report["solutions"][solution_name])
            solution["signed_angle_degrees"] = float(degrees) * float(solution.get("sign", 1.0))
            r16._set_knee_without_reset(armature, solution)  # noqa: SLF001
            bpy.context.view_layer.update()
            label = f"{side_name}_knee_bend_{degrees}deg"
            render(label, knee_center, Vector((0.0, -1.0, 0.08)), TARGET_HEIGHT_M * 0.62)
            if degrees == 80:
                pairs = _evaluated_intersections(body)
                pose_audits[label] = {
                    "nonadjacent_intersection_pair_count": len(pairs),
                    "pairs": [list(pair) for pair in sorted(pairs)],
                }
    for degrees in (30, 55, 80):
        reset_pose_v1(armature)
        for solution_name in ("left", "right"):
            solution = dict(knee_report["solutions"][solution_name])
            solution["signed_angle_degrees"] = float(degrees) * float(solution.get("sign", 1.0))
            r16._set_knee_without_reset(armature, solution)  # noqa: SLF001
        bpy.context.view_layer.update()
        label = f"bilateral_knee_bend_{degrees}deg"
        render(label, knee_center, Vector((0.0, -1.0, 0.08)), TARGET_HEIGHT_M * 0.62)
        if degrees == 80:
            pairs = _evaluated_intersections(body)
            pose_audits[label] = {
                "nonadjacent_intersection_pair_count": len(pairs),
                "pairs": [list(pair) for pair in sorted(pairs)],
            }

    reset_pose_v1(armature)
    seat = bpy.data.objects.get(seat_name)
    if seat is None:
        raise KiraR18AuthoringError("private seat prop missing")
    seat.hide_render = False
    seat_top = max(float((seat.matrix_world @ Vector(corner)).z) for corner in seat.bound_box)
    seated = apply_pose_foundation_v1(
        armature=armature,
        body=body,
        pose_name="seated",
        body_height_m=TARGET_HEIGHT_M,
        seat_top_z_m=seat_top,
    )
    render(
        "toilet_seated_diagnostic_contact",
        Vector((0.0, 0.0, TARGET_HEIGHT_M * 0.43)),
        Vector((0.68, -1.0, 0.07)),
        TARGET_HEIGHT_M * 0.98,
        portrait=True,
    )
    seated_pairs = _evaluated_intersections(body)
    pose_audits["toilet_seated_diagnostic_contact"] = {
        "pose_foundation": seated,
        "nonadjacent_intersection_pair_count": len(seated_pairs),
        "pairs": [list(pair) for pair in sorted(seated_pairs)],
        "bathroom_function_claimed": False,
        "visible_external_pose_and_contact_only": True,
    }
    seat.hide_render = True
    reset_pose_v1(armature)
    neutral_digest = _coordinate_digest(body)
    pose_audits["neutral_restored"] = {
        "rest_pose_restored": True,
        "body_base_coordinate_sha256": neutral_digest,
    }
    return records, pose_audits


def _build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    source, output, foundation = _validate_paths(args)
    source_validation = validate_sources(PROJECT_ROOT)
    if source_validation["r17_package_inventory_sha256"] != R17_PACKAGE_INVENTORY_SHA256:
        raise KiraR18AuthoringError("R17 package digest drifted before Blender open")
    live_before = capture_live_kira_state_hashes(PROJECT_ROOT)
    source_hash_before = sha256_file(source)
    package_rows_before, package_digest_before = package_inventory(source.parent)

    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    body = next(
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and bool(obj.get("primary_surface"))
    )
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    if str(scene.get("candidate_id") or "") != R17_CANDIDATE_ID:
        raise KiraR18AuthoringError("R17 in-Blend candidate identity drifted")
    reset_pose_v1(armature)
    r17._remove_private_pose_props()  # noqa: SLF001

    adjacency = _adjacency(body)
    exact_masks = _derive_masks(body)
    f1, f2, target_sets, prepared_source = _target_sets(body)
    if f1 != exact_masks["F1"] or f2 != exact_masks["F2"]:
        raise KiraR18AuthoringError("face-mask reconstruction drifted")

    before_coordinates = [vertex.co.copy() for vertex in body.data.vertices]
    immutable_before = {
        "coordinate_sha256": _coordinate_digest(body),
        "topology_sha256": _topology_digest(body),
        "deform_weight_sha256": _weight_digest(body),
        "attribute_sha256": _attribute_digest(body),
        "material_index_sha256": _material_index_digest(body),
        "armature_sha256": masks._armature_digest(armature),  # noqa: SLF001
        "actions_sha256": _action_digest(),
        "protected_object_geometry": _protected_object_geometry(),
    }
    inherited_pairs = _rest_intersections(body)
    if len(inherited_pairs) != 16:
        raise KiraR18AuthoringError(
            f"frozen R17 inherited intersection count drifted: {len(inherited_pairs)}"
        )

    face_report = _apply_face_targets(body, prepared_source, target_sets)
    post_face_pairs = _rest_intersections(body)
    if post_face_pairs:
        raise KiraR18AuthoringError(
            "exact F2 lower-lip correction did not clear inherited pairs before P1: "
            f"remaining={len(post_face_pairs)}"
        )
    surface_report = _apply_p1_reference_transfer(
        body,
        exact_masks["P1"],
        adjacency,
        foundation,
        float(args.surface_transfer_strength),
        post_face_pairs,
    )
    if surface_report["pinned_boundary_exact"] is not True:
        raise KiraR18AuthoringError("P1 pinned boundary moved")

    component_reports = {
        "S_rear_scalp": _smooth_mask(
            body,
            exact_masks["S"],
            adjacency,
            iterations=2,
            alpha=0.10,
            maximum_total_m=0.0012,
        ),
        "K_left": _smooth_mask(
            body,
            exact_masks["K_L"],
            adjacency,
            iterations=1,
            alpha=0.045,
            maximum_total_m=0.00055,
        ),
        "K_right": _smooth_mask(
            body,
            exact_masks["K_R"],
            adjacency,
            iterations=1,
            alpha=0.045,
            maximum_total_m=0.00055,
        ),
        "H_left": _smooth_mask(
            body,
            exact_masks["H_L"],
            adjacency,
            iterations=1,
            alpha=0.018,
            maximum_total_m=0.00020,
        ),
        "H_right": _smooth_mask(
            body,
            exact_masks["H_R"],
            adjacency,
            iterations=1,
            alpha=0.018,
            maximum_total_m=0.00020,
        ),
        "T_left": _smooth_mask(
            body,
            exact_masks["T_L"],
            adjacency,
            iterations=1,
            alpha=0.018,
            maximum_total_m=0.00020,
        ),
        "T_right": _smooth_mask(
            body,
            exact_masks["T_R"],
            adjacency,
            iterations=1,
            alpha=0.018,
            maximum_total_m=0.00020,
        ),
    }

    candidate_id = output.name
    brow_report = _replace_brows(body, armature, candidate_id)
    nail_report = _refine_nail_presentation(candidate_id)
    candidate_objects = _retag_candidate(candidate_id, body, armature)
    if len([obj for obj in candidate_objects if bool(obj.get("nail_component"))]) != 20:
        raise KiraR18AuthoringError("retagged nail inventory drifted")

    policy, policy_report = r16._validate_delivery_policy()  # noqa: SLF001
    zero_hair = r16._zero_scalp_hair_inventory(  # noqa: SLF001
        body=body, candidate_objects=candidate_objects, policy_report=policy_report
    )
    if zero_hair.get("passed") is not True:
        raise KiraR18AuthoringError(
            "zero scalp-hair dependency failed: " + "; ".join(zero_hair["blockers"])
        )

    changed_indices = {
        index
        for index, before in enumerate(before_coordinates)
        if (body.data.vertices[index].co - before).length > 1.0e-10
    }
    authorized_union = set().union(
        exact_masks["P1"],
        exact_masks["S"],
        exact_masks["K_L"],
        exact_masks["K_R"],
        exact_masks["F1"],
        exact_masks["F2"],
        exact_masks["H_L"],
        exact_masks["H_R"],
        exact_masks["T_L"],
        exact_masks["T_R"],
    )
    escaped = changed_indices.difference(authorized_union)
    if escaped:
        raise KiraR18AuthoringError(
            f"coordinate diff escaped authorized masks: {len(escaped)} vertices"
        )
    if any(
        (body.data.vertices[index].co - before_coordinates[index]).length > 1.0e-12
        for index in P1_BOUNDARY
    ):
        raise KiraR18AuthoringError("exact P1 boundary coordinate changed")

    immutable_after = {
        "coordinate_sha256": _coordinate_digest(body),
        "topology_sha256": _topology_digest(body),
        "deform_weight_sha256": _weight_digest(body),
        "attribute_sha256": _attribute_digest(body),
        "material_index_sha256": _material_index_digest(body),
        "armature_sha256": masks._armature_digest(armature),  # noqa: SLF001
        "actions_sha256": _action_digest(),
        "protected_object_geometry": _protected_object_geometry(),
    }
    invariant_gates = {
        "topology_exact": immutable_after["topology_sha256"] == immutable_before["topology_sha256"],
        "deform_weights_exact": immutable_after["deform_weight_sha256"] == immutable_before["deform_weight_sha256"],
        "attributes_exact": immutable_after["attribute_sha256"] == immutable_before["attribute_sha256"],
        "material_indices_exact": immutable_after["material_index_sha256"] == immutable_before["material_index_sha256"],
        "armature_exact": immutable_after["armature_sha256"] == immutable_before["armature_sha256"],
        "actions_exact": immutable_after["actions_sha256"] == immutable_before["actions_sha256"],
        "protected_eye_lid_lash_geometry_exact": immutable_after["protected_object_geometry"] == immutable_before["protected_object_geometry"],
        "coordinate_diff_inside_authorized_union": not escaped,
        "p1_boundary_exact": True,
        "zero_scalp_hair_dependency": zero_hair.get("passed") is True,
    }
    if not all(invariant_gates.values()):
        raise KiraR18AuthoringError(
            "immutable diff gate failed: "
            + ", ".join(name for name, passed in invariant_gates.items() if not passed)
        )

    final_pairs = _rest_intersections(body)
    new_pairs = final_pairs.difference(inherited_pairs)
    if new_pairs:
        raise KiraR18AuthoringError(
            f"R18 introduced {len(new_pairs)} new rest nonadjacent intersections"
        )
    if final_pairs:
        raise KiraR18AuthoringError(
            "exact lower-lip 0.20 to 0.12 repair did not clear all 16 inherited pairs: "
            f"remaining={len(final_pairs)}"
        )
    topology = r16.r15._mesh_topology_counts(body)  # noqa: SLF001
    if (
        topology["surface_components"] != 1
        or topology["boundary_edges"] != 0
        or topology["nonmanifold_edges"] != 0
    ):
        raise KiraR18AuthoringError("R18 primary surface is not one closed manifold")
    if capture_live_kira_state_hashes(PROJECT_ROOT) != live_before:
        raise KiraR18AuthoringError("live Kira state changed during authoring")

    output.mkdir(parents=True, exist_ok=False)
    render_records: list[dict[str, Any]] = []
    owner_review: dict[str, Any] | None = None
    movement: dict[str, Any] = {}
    if args.mode == "probe":
        render_records = _render_probe(scene, output, body, candidate_objects)
    else:
        protected_target = Vector((0.0, -0.068, 0.767))
        owner_review, knee_report = r17._core_owner_review(  # noqa: SLF001
            scene=scene,
            output_dir=output,
            body=body,
            armature=armature,
            candidate_objects=candidate_objects,
            protected_target=protected_target,
        )
        activity_review = r17._supplemental_activity_review(  # noqa: SLF001
            scene=scene,
            output_dir=output,
            body=body,
            armature=armature,
            seat_name=str(owner_review["private_seat_review_prop"]),
        )
        extra_renders, pose_audits = _render_extra(
            scene,
            output,
            body,
            armature,
            knee_report,
            str(owner_review["private_seat_review_prop"]),
        )
        render_records = [*owner_review["views"], *activity_review["views"], *extra_renders]
        movement = {
            "knee_axis_report": knee_report,
            "supplemental_activity_review": activity_review,
            "pose_intersection_audits": pose_audits,
            "neutral_restored_after_every_pose": True,
            "claim_limit": (
                "Static evaluated-pose evidence proves visible external modeling, "
                "clearance and deformation only. It does not prove full animation, "
                "eating, elimination, continence, internal anatomy, intimate behavior, "
                "reproduction, pregnancy, or autonomous human capability."
            ),
        }
    reset_pose_v1(armature)

    blend_path = output / f"{candidate_id}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    blend_sha = sha256_file(blend_path)
    source_hash_after = sha256_file(source)
    package_rows_after, package_digest_after = package_inventory(source.parent)
    live_after = capture_live_kira_state_hashes(PROJECT_ROOT)
    source_integrity = {
        "r17_blend_sha256_before": source_hash_before,
        "r17_blend_sha256_after": source_hash_after,
        "r17_package_file_count_before": len(package_rows_before),
        "r17_package_file_count_after": len(package_rows_after),
        "r17_package_inventory_sha256_before": package_digest_before,
        "r17_package_inventory_sha256_after": package_digest_after,
        "r17_whole_package_exact": (
            source_hash_after == R17_BLEND_SHA256
            and package_digest_before == package_digest_after == R17_PACKAGE_INVENTORY_SHA256
        ),
    }
    if source_integrity["r17_whole_package_exact"] is not True or live_after != live_before:
        raise KiraR18AuthoringError("source R17 or live Kira changed before evidence commit")

    visual_repair_attempt = (
        int(args.attempt_number) - 2
        if int(args.attempt_number) >= 3
        else int(args.attempt_number)
    )
    surface_visual_status = (
        "PENDING_PRIVATE_VISUAL_REVIEW_ATTEMPT_01"
        if visual_repair_attempt == 1
        else "BEST_SAFE_AFTER_TWO_BOUNDED_SURFACE_ATTEMPTS_PENDING_OWNER_REVIEW"
    )
    evidence = {
        "schema_version": 1,
        "evidence_type": (
            "kira_r18_bounded_bald_private_staging_probe"
            if args.mode == "probe"
            else "inactive_complete_kira_r18_bald_targeted_owner_review_candidate"
        ),
        "created_utc": _utc_now(),
        "candidate_id": candidate_id,
        "candidate_asset_id": "KIRA_BALD_LOW_RESOURCE_BODY",
        "status": (
            "INACTIVE_PRIVATE_STAGING_PROBE_NOT_A_CANDIDATE"
            if args.mode == "probe"
            else "INACTIVE_PRIVATE_COMPLETE_BODY_AWAITING_OWNER_VISUAL_DECISION"
        ),
        "owner_visual_status": surface_visual_status,
        "mode": args.mode,
        "append_only_execution_attempt": int(args.attempt_number),
        "bounded_surface_attempt": visual_repair_attempt,
        "attempt_classification": {
            "attempts_01_and_02": (
                "PRESERVED_MECHANICAL_PRE_AUTHORING_FAILURES_NO_MESH_MUTATION_OR_RENDER"
                if int(args.attempt_number) >= 3
                else "NOT_APPLICABLE_TO_THIS_EXECUTION"
            ),
            "this_attempt": "BOUNDED_VISIBLE_SURFACE_REPAIR",
        },
        "source": {
            "path": R17_BLEND_RELATIVE.as_posix(),
            "blend_sha256": R17_BLEND_SHA256,
            "reuse_policy": "reuse every accepted R17 component; never mutate R17",
            "authoring_plan": {"path": PLAN_RELATIVE.as_posix(), "sha256": PLAN_SHA256},
            "validation": source_validation,
            "integrity_after": source_integrity,
        },
        "targeted_corrections": {
            "F_face_and_lip": face_report,
            "P1_front_connected_surface": surface_report,
            "P2_rear_connected_surface": {
                "applied": False,
                "reason": "R17 evidence localized the visible plate defect to the front; P1 retains the posterior/perineal bridge",
            },
            "P3_combined_fallback": {"applied": False},
            "independent_component_fairing": component_reports,
            "F3_brows": brow_report,
            "N_nails": nail_report,
        },
        "intersection_evidence": {
            "inherited_rest_pair_count": len(inherited_pairs),
            "inherited_pairs": [list(pair) for pair in sorted(inherited_pairs)],
            "post_face_rest_pair_count": len(post_face_pairs),
            "post_face_pairs": [list(pair) for pair in sorted(post_face_pairs)],
            "final_rest_pair_count": len(final_pairs),
            "final_pairs": [list(pair) for pair in sorted(final_pairs)],
            "new_rest_pair_count": len(new_pairs),
            "lower_lip_0_20_to_0_12_applied": True,
        },
        "immutable_diff": {
            "before": immutable_before,
            "after": immutable_after,
            "changed_vertex_count": len(changed_indices),
            "changed_index_set_sha256": index_set_sha256(changed_indices),
            "authorized_union_vertex_count": len(authorized_union),
            "escaped_vertex_count": len(escaped),
            "gates": invariant_gates,
        },
        "final_primary_surface_topology": topology,
        "complete_body_boundary": {
            "structurally_complete_body": True,
            "adult_female_lane": True,
            "visible_external_adult_surface_modeled": True,
            "internal_organs_or_canals_implemented_or_claimed": False,
            "bathroom_function_implemented_or_claimed": False,
            "pregnancy_or_reproductive_function_implemented_or_claimed": False,
            "bald_low_resource_body": True,
            "natural_primary_skin_scalp": True,
            "eyebrows_and_eyelashes_retained": True,
            "scalp_hair_dependency": False,
        },
        "zero_scalp_hair_dependency": zero_hair,
        "owner_review": owner_review,
        "render_inventory": render_records,
        "movement_and_contact": movement,
        "outputs": {
            "blend": {"path": blend_path.name, "sha256": blend_sha},
            "private_glb": {"exported": False, "path": None},
        },
        "safety": {
            "inactive": True,
            "private_owner_review_only": True,
            "assigned": False,
            "activated": False,
            "clothing_created": False,
            "scalp_hair_created_or_loaded": False,
            "published": False,
            "uploaded": False,
            "runtime_exported": False,
            "live_kira_state_unchanged": live_after == live_before,
            "live_state_before": live_before,
            "live_state_after": live_after,
        },
        "known_limits_for_honest_owner_review": [
            "The face is a bounded qualitative Kira direction, not a measured biometric identity match.",
            *(
                [
                    "After the second and final bounded visible repair, the protected central external surface is structurally connected and zero-intersection but still reads conspicuously layered/plate-like in the front and three-quarter diagnostics; this unresolved visual defect is preserved for Robert's decision rather than starting another body or framework."
                ]
                if visual_repair_attempt == 2
                else []
            ),
            "No Blender-only static pose or visible external surface proves internal urinary, reproductive, digestive, pregnancy, intimate-behavior, or autonomous human function.",
            "Movement renders test only the exact documented states; full animation and environmental interaction remain unproven.",
            "The detachable scalp-hair master is intentionally absent from this 32 GB bald package.",
        ],
        "rollback": {
            "required": False,
            "instruction": (
                "Quarantine or remove only this new append-only R18 directory. "
                "The exact R17 package and live Kira runtime/selection remain unchanged."
            ),
        },
        "build_elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    evidence_path = output / "BUILD_EVIDENCE.json"
    evidence_path.write_text(
        json.dumps(_json_safe(evidence), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "status": evidence["status"],
        "candidate_id": candidate_id,
        "output_dir": output.relative_to(PROJECT_ROOT).as_posix(),
        "blend_sha256": blend_sha,
        "evidence_sha256": sha256_file(evidence_path),
        "render_count": len(render_records),
        "rest_intersections_before": len(inherited_pairs),
        "rest_intersections_after": len(final_pairs),
        "new_rest_intersections": len(new_pairs),
        "live_state_unchanged": True,
        "r17_package_unchanged": True,
    }


def main() -> int:
    args = _args()
    requested_output = (PROJECT_ROOT / Path(args.output_dir)).resolve()
    output_existed_before = requested_output.exists()
    try:
        result = _build(args)
    except Exception as exc:
        output = requested_output
        probe_parent = (PROJECT_ROOT / PROBE_PARENT).resolve()
        delivery_parent = (PROJECT_ROOT / DELIVERY_PARENT).resolve()
        allowed_probe = output in {
            (probe_parent / f"attempt_{number:02d}").resolve()
            for number in (1, 2, 3, 4)
        }
        allowed_delivery = (
            output.parent == delivery_parent
            and output.name.startswith(DELIVERY_PREFIX)
        )
        # Never append failure evidence to an output that existed before this
        # invocation. That protects R17, earlier attempts, and a previously
        # completed R18 package if validation fails before authoring begins.
        if (allowed_probe or allowed_delivery) and not output_existed_before:
            output.mkdir(parents=True, exist_ok=True)
            failure = {
                "schema_version": 1,
                "status": "R18_BOUNDED_BALD_AUTHORING_FAILED_INACTIVE_NO_ACTIVATION",
                "created_utc": _utc_now(),
                "exception_type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
                "runtime_activation_performed": False,
                "export_performed": False,
                "source_r17_targeted_for_write": False,
                "rollback": "Preserve this append-only failure directory; no live runtime file was targeted.",
            }
            failure_path = output / "FAILURE.json"
            if not failure_path.exists():
                failure_path.write_text(
                    json.dumps(failure, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
        raise
    print("KIRA_R18_RESULT=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
