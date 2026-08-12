"""Read-only exact R18 correction-mask and immutable-component report.

This tool opens the exact frozen R17 Blend, computes deterministic masks and
component digests, prints JSON, and exits. It never edits geometry, saves,
renders, exports, creates a candidate, or touches the live runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from typing import Any, Iterable, Mapping, Sequence

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tools.blender_build_profiled_kira_bald_delivery_candidate as r16
from Core.avatar_kira_face_delivery_v3 import (
    HEAD_REGION_MINIMUM_HEIGHT_FRACTION,
    TARGETS,
)
from Core.avatar_shading_normal_repair_v2 import rear_scalp_mask_weight_v2
from tools.blender_kira_face_delivery_v3 import _read_target


R17_RELATIVE = Path(
    "Avatar/private_owner_review/"
    "kira_profiled_adult_candidate_r17_bald_corrected_20260801_165816/"
    "kira_profiled_adult_candidate_r17_bald_corrected_20260801_165816.blend"
)
R17_SHA256 = "7f7a6519ee5902fb01b247add864a4f41f4be6e600ab917cc5195ca9ea21e493"
TARGET_HEIGHT_M = 1.651
LANDMARK_PREFIX = "AFES_LANDMARK__"
SCALP_CONFIG = Path(
    "Avatar/avatar_builder/tooling/avatar_shading_normal_repair_v2.json"
)
INTERSECTION_FACES = (
    (329, 334), (329, 349), (331, 334), (334, 346),
    (335, 349), (337, 430), (340, 430), (346, 349),
    (6956, 6961), (6956, 6976), (6958, 6961), (6961, 6973),
    (6962, 6976), (6964, 13361), (6973, 6976), (13361, 13377),
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-blend", default=R17_RELATIVE.as_posix())
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _index_sha(indices: Iterable[int]) -> str:
    digest = hashlib.sha256()
    rows = sorted({int(value) for value in indices})
    digest.update(struct.pack("<Q", len(rows)))
    for value in rows:
        digest.update(struct.pack("<I", value))
    return digest.hexdigest()


def _coordinate_sha(body: Any, indices: Iterable[int]) -> str:
    digest = hashlib.sha256()
    rows = sorted({int(value) for value in indices})
    digest.update(struct.pack("<Q", len(rows)))
    for index in rows:
        point = body.data.vertices[index].co
        digest.update(struct.pack("<I3d", index, float(point.x), float(point.y), float(point.z)))
    return digest.hexdigest()


def _bounds(body: Any, indices: Iterable[int]) -> dict[str, list[float]] | None:
    rows = [body.data.vertices[int(index)].co for index in sorted(set(indices))]
    if not rows:
        return None
    return {
        "minimum_object_m": [min(float(point[axis]) for point in rows) for axis in range(3)],
        "maximum_object_m": [max(float(point[axis]) for point in rows) for axis in range(3)],
    }


def _ranges(indices: Iterable[int]) -> list[list[int]]:
    rows = sorted({int(value) for value in indices})
    if not rows:
        return []
    result: list[list[int]] = []
    start = previous = rows[0]
    for value in rows[1:]:
        if value != previous + 1:
            result.append([start, previous])
            start = value
        previous = value
    result.append([start, previous])
    return result


def _mask_record(body: Any, indices: Iterable[int], *, rule: str) -> dict[str, Any]:
    rows = sorted({int(value) for value in indices})
    row_set = set(rows)
    touching_faces = [
        int(face.index)
        for face in body.data.polygons
        if any(int(value) in row_set for value in face.vertices)
    ]
    fully_contained_faces = [
        int(face.index)
        for face in body.data.polygons
        if face.vertices and all(int(value) in row_set for value in face.vertices)
    ]
    return {
        "selection_rule": rule,
        "vertex_count": len(rows),
        "sorted_vertex_index_sha256": _index_sha(rows),
        "current_coordinate_sha256": _coordinate_sha(body, rows),
        "coordinate_bounds": _bounds(body, rows),
        "contiguous_index_ranges": _ranges(rows),
        "touching_face_count": len(touching_faces),
        "touching_face_index_sha256": _index_sha(touching_faces),
        "fully_contained_face_count": len(fully_contained_faces),
        "fully_contained_face_index_sha256": _index_sha(fully_contained_faces),
    }


def _weights(body: Any, group_name: str) -> dict[int, float]:
    group = body.vertex_groups.get(group_name)
    if group is None:
        return {}
    result: dict[int, float] = {}
    for vertex in body.data.vertices:
        for assignment in vertex.groups:
            if int(assignment.group) == int(group.index) and float(assignment.weight) > 0.0:
                result[int(vertex.index)] = float(assignment.weight)
                break
    return result


def _weight_digest(body: Any, indices: Iterable[int], included_names: set[str]) -> str:
    group_names = {int(group.index): group.name for group in body.vertex_groups}
    digest = hashlib.sha256()
    rows = sorted({int(value) for value in indices})
    digest.update(struct.pack("<Q", len(rows)))
    for index in rows:
        assignments = sorted(
            (
                group_names[int(item.group)],
                float(item.weight),
            )
            for item in body.data.vertices[index].groups
            if group_names.get(int(item.group)) in included_names
            and float(item.weight) > 1.0e-12
        )
        digest.update(struct.pack("<II", index, len(assignments)))
        for name, weight in assignments:
            encoded = name.encode("utf-8")
            digest.update(struct.pack("<I", len(encoded)))
            digest.update(encoded)
            digest.update(struct.pack("<d", weight))
    return digest.hexdigest()


def _pelvic_mask(body: Any) -> tuple[set[int], dict[str, Any]]:
    names = sorted(
        group.name for group in body.vertex_groups if group.name.startswith(LANDMARK_PREFIX)
    )
    core = {
        index
        for name in names
        for index, weight in _weights(body, name).items()
        if weight > 0.5
    }
    adjacency = [set() for _ in body.data.vertices]
    for edge in body.data.edges:
        left, right = (int(value) for value in edge.vertices)
        adjacency[left].add(right)
        adjacency[right].add(left)
    boundary = {index for index in core if adjacency[index].difference(core)}
    outside_guard = {
        neighbor
        for index in boundary
        for neighbor in adjacency[index]
        if neighbor not in core
    }
    record = _mask_record(
        body,
        core,
        rule=(
            "union of exact R17 vertex memberships >0.5 in every group whose name "
            "starts AFES_LANDMARK__; boundary vertices are pinned unless the later "
            "topology plan explicitly reuses the same boundary coordinate"
        ),
    )
    record.update(
        {
            "landmark_group_count": len(names),
            "landmark_groups": names,
            "boundary_vertex_count": len(boundary),
            "boundary_vertex_index_sha256": _index_sha(boundary),
            "boundary_coordinate_sha256": _coordinate_sha(body, boundary),
            "outside_guard_vertex_count": len(outside_guard),
            "outside_guard_vertex_index_sha256": _index_sha(outside_guard),
            "outside_guard_coordinate_sha256": _coordinate_sha(body, outside_guard),
            "interior_vertex_count": len(core.difference(boundary)),
            "interior_vertex_index_sha256": _index_sha(core.difference(boundary)),
        }
    )
    return core, record


def _scalp_mask(body: Any) -> tuple[set[int], dict[str, Any]]:
    config = json.loads((PROJECT_ROOT / SCALP_CONFIG).read_text(encoding="utf-8-sig"))
    mask_config = config["rear_scalp_mask"]
    z_values = [float(vertex.co.z) for vertex in body.data.vertices]
    z_min, z_max = min(z_values), max(z_values)
    height = z_max - z_min
    names = list(mask_config["required_existing_membership_groups"])
    membership = {name: _weights(body, name) for name in names}
    head_related = [
        vertex
        for vertex in body.data.vertices
        if sum(membership[name].get(vertex.index, 0.0) for name in names)
        >= float(mask_config["minimum_existing_membership_sum"])
    ]
    head_x_half = max(abs(float(vertex.co.x)) for vertex in head_related)
    head_y_min = min(float(vertex.co.y) for vertex in head_related)
    head_y_max = max(float(vertex.co.y) for vertex in head_related)
    weighted: dict[int, float] = {}
    for vertex in body.data.vertices:
        member = sum(membership[name].get(vertex.index, 0.0) for name in names)
        rearwardness = (float(vertex.co.y) - head_y_min) / (head_y_max - head_y_min)
        value = rear_scalp_mask_weight_v2(
            normalized_body_height=(float(vertex.co.z) - z_min) / height,
            normalized_head_rearwardness=rearwardness,
            normalized_head_lateral=float(vertex.co.x) / head_x_half,
            existing_head_neck_membership=member,
        )
        if value > 0.005:
            weighted[int(vertex.index)] = float(value)
    indices = set(weighted)
    record = _mask_record(
        body,
        indices,
        rule=(
            "exact avatar_shading_normal_repair_v2 rear_scalp_mask_weight_v2 "
            "selection with stored config and weight >0.005; proposed R18 geometry "
            "fairing may move only these vertices and must pin the mask boundary"
        ),
    )
    record.update(
        {
            "mask_config_path": SCALP_CONFIG.as_posix(),
            "mask_config_sha256": _sha_file(PROJECT_ROOT / SCALP_CONFIG),
            "minimum_mask_weight": min(weighted.values()),
            "maximum_mask_weight": max(weighted.values()),
            "required_membership_groups": names,
        }
    )
    return indices, record


def _knee_masks(body: Any) -> tuple[set[int], dict[str, Any]]:
    result: dict[str, Any] = {}
    union: set[int] = set()
    for side in ("L", "R"):
        name = f"AVATAR_BUILDER_KNEE_CORRECTIVE_V2_{side}"
        weighted = _weights(body, name)
        indices = set(weighted)
        union.update(indices)
        record = _mask_record(
            body,
            indices,
            rule=f"all exact positive memberships in existing R17 group {name}",
        )
        record.update(
            {
                "vertex_group": name,
                "weight_minimum": min(weighted.values()),
                "weight_maximum": max(weighted.values()),
                "modifier": f"AvatarBuilder_Knee_CorrectiveSmooth_V2_{side}",
            }
        )
        result[side] = record
    return union, result


def _prepared_source() -> dict[str, Any]:
    config, _report = r16.load_validated_profiled_candidate_builder_config(PROJECT_ROOT)
    profile = r16._read_json(PROJECT_ROOT / config["style_profile"]["path"])
    resolved = [dict(row, verified=True) for row in profile["shape_targets"]]
    return r16.prepare_profiled_body_source(
        base_path=PROJECT_ROOT / config["makehuman_source_set"]["base_body"]["path"],
        female_macros=config["makehuman_source_set"]["female_macros"],
        resolved_style_targets=resolved,
        project_root=PROJECT_ROOT,
        target_height_m=TARGET_HEIGHT_M,
    )


def _face_masks(body: Any) -> tuple[set[int], dict[str, Any]]:
    source = _prepared_source()
    source_to_body = source["source_to_body"]
    baseline = source["body_vertices"]
    minimum_z = TARGET_HEIGHT_M * HEAD_REGION_MINIMUM_HEIGHT_FRACTION
    target_sets: dict[str, set[int]] = {}
    feature_sets: dict[str, set[int]] = {}
    for target in TARGETS:
        indices: set[int] = set()
        for source_index in _read_target(PROJECT_ROOT / str(target["path"])):
            compact = source_to_body.get(source_index)
            if compact is not None and float(baseline[compact].z) >= minimum_z:
                indices.add(int(compact))
        target_sets[str(target["target_id"])] = indices
        feature_sets.setdefault(str(target["feature"]), set()).update(indices)
    likeness = set().union(
        *(indices for target_id, indices in target_sets.items() if target_id != "head_oval_soft")
    )
    lower_lip = target_sets["lower_lip_natural_volume"]
    collision_faces = {face for pair in INTERSECTION_FACES for face in pair}
    collision_vertices = {
        int(vertex)
        for face_index in collision_faces
        for vertex in body.data.polygons[face_index].vertices
    }
    record = {
        "front_face_likeness": _mask_record(
            body,
            likeness,
            rule=(
                "union of exact source-to-compact mapped vertices in the ten current "
                "Kira face-v3 targets other than head_oval_soft, with baseline z >= "
                "0.76*1.651 m; excludes broad cranium/head-oval regeneration"
            ),
        ),
        "lower_lip_morph_repair": _mask_record(
            body,
            lower_lip,
            rule=(
                "exact mapped support of lower_lip_natural_volume target; only its "
                "weight may be line-searched from 0.20 to the clean proposal 0.12"
            ),
        ),
        "observed_collision_vertices": _mask_record(
            body,
            collision_vertices,
            rule="union of vertices on the 20 unique faces participating in the inherited 16 pairs",
        ),
        "feature_masks": {
            name: {
                "vertex_count": len(indices),
                "sorted_vertex_index_sha256": _index_sha(indices),
            }
            for name, indices in sorted(feature_sets.items())
        },
        "excluded_target": "head_oval_soft",
        "minimum_baseline_z_m": minimum_z,
    }
    return likeness, record


def _limb_mask(
    body: Any, *, side: str, kind: str, minimum_membership: float = 0.05
) -> tuple[set[int], dict[str, Any]]:
    if kind == "hand":
        names = [
            group.name
            for group in body.vertex_groups
            if group.name in {f"wrist.{side}"}
            or group.name.startswith("finger") and group.name.endswith(f".{side}")
            or group.name.startswith("metacarpal") and group.name.endswith(f".{side}")
        ]
    elif kind == "foot":
        names = [
            group.name
            for group in body.vertex_groups
            if group.name == f"foot.{side}"
            or group.name.startswith("toe") and group.name.endswith(f".{side}")
        ]
    else:
        raise ValueError(kind)
    maps = {name: _weights(body, name) for name in names}
    sums = {
        int(vertex.index): sum(values.get(vertex.index, 0.0) for values in maps.values())
        for vertex in body.data.vertices
    }
    indices = {index for index, value in sums.items() if value >= minimum_membership}
    record = _mask_record(
        body,
        indices,
        rule=(
            f"sum of exact R17 {kind} deform memberships for side {side} across "
            f"{len(names)} named groups >= {minimum_membership:.2f}"
        ),
    )
    record.update(
        {
            "deform_groups": sorted(names),
            "minimum_membership_sum": minimum_membership,
            "membership_sum_minimum_in_mask": min(sums[index] for index in indices),
            "membership_sum_maximum_in_mask": max(sums[index] for index in indices),
        }
    )
    return indices, record


def _mesh_digest(obj: Any) -> str:
    digest = hashlib.sha256()
    mesh = obj.data
    digest.update(struct.pack("<QQ", len(mesh.vertices), len(mesh.polygons)))
    for vertex in mesh.vertices:
        digest.update(struct.pack("<I3d", int(vertex.index), *(float(value) for value in vertex.co)))
    for face in mesh.polygons:
        values = [int(value) for value in face.vertices]
        digest.update(struct.pack("<II", int(face.index), len(values)))
        digest.update(struct.pack(f"<{len(values)}I", *values))
    return digest.hexdigest()


def _object_record(obj: Any) -> dict[str, Any]:
    matrix = [float(value) for row in obj.matrix_world for value in row]
    record: dict[str, Any] = {
        "name": obj.name,
        "type": obj.type,
        "matrix_world_sha256": hashlib.sha256(
            struct.pack(f"<{len(matrix)}d", *matrix)
        ).hexdigest(),
        "parent": obj.parent.name if obj.parent else None,
        "parent_type": str(obj.parent_type),
        "parent_bone": str(obj.parent_bone),
        "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
        "modifiers": [
            {
                "name": modifier.name,
                "type": modifier.type,
                "object": modifier.object.name if getattr(modifier, "object", None) else None,
                "vertex_group": str(getattr(modifier, "vertex_group", "")),
            }
            for modifier in obj.modifiers
        ],
    }
    if obj.type == "MESH":
        record.update(
            {
                "vertex_count": len(obj.data.vertices),
                "edge_count": len(obj.data.edges),
                "polygon_count": len(obj.data.polygons),
                "mesh_sha256": _mesh_digest(obj),
                "bounds": {
                    "minimum_object_m": [
                        min(float(vertex.co[axis]) for vertex in obj.data.vertices)
                        for axis in range(3)
                    ],
                    "maximum_object_m": [
                        max(float(vertex.co[axis]) for vertex in obj.data.vertices)
                        for axis in range(3)
                    ],
                },
            }
        )
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    record["record_sha256"] = hashlib.sha256(encoded).hexdigest()
    return record


def _armature_digest(armature: Any) -> str:
    rows = []
    for bone in sorted(armature.data.bones, key=lambda value: value.name):
        rows.append(
            {
                "name": bone.name,
                "head": [float(value) for value in bone.head_local],
                "tail": [float(value) for value in bone.tail_local],
                "matrix": [float(value) for row in bone.matrix_local for value in row],
                "parent": bone.parent.name if bone.parent else None,
                "use_connect": bool(bone.use_connect),
                "use_deform": bool(bone.use_deform),
            }
        )
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _action_digest() -> str:
    rows = []
    for action in sorted(bpy.data.actions, key=lambda value: value.name):
        curves = []
        for curve in sorted(action.fcurves, key=lambda value: (value.data_path, value.array_index)):
            curves.append(
                {
                    "path": curve.data_path,
                    "index": int(curve.array_index),
                    "keys": [
                        [float(point.co.x), float(point.co.y), str(point.interpolation)]
                        for point in curve.keyframe_points
                    ],
                }
            )
        rows.append({"name": action.name, "curves": curves})
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _overlaps(masks: Mapping[str, set[int]]) -> dict[str, int]:
    names = sorted(masks)
    return {
        f"{left}__{right}": len(masks[left].intersection(masks[right]))
        for offset, left in enumerate(names)
        for right in names[offset + 1 :]
    }


def main() -> None:
    args = _args()
    source = (PROJECT_ROOT / Path(args.source_blend)).resolve(strict=True)
    source.relative_to(PROJECT_ROOT)
    if source != (PROJECT_ROOT / R17_RELATIVE).resolve() or _sha_file(source) != R17_SHA256:
        raise RuntimeError("only the exact frozen R17 Blend is permitted")
    hash_before = _sha_file(source)
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    body = next(
        obj for obj in bpy.data.objects if obj.type == "MESH" and bool(obj.get("primary_surface"))
    )
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")

    pelvic, pelvic_record = _pelvic_mask(body)
    scalp, scalp_record = _scalp_mask(body)
    knees, knee_records = _knee_masks(body)
    face, face_record = _face_masks(body)
    limb_sets: dict[str, set[int]] = {}
    limb_records: dict[str, Any] = {}
    for kind in ("hand", "foot"):
        for side in ("L", "R"):
            name = f"{kind}_{side}"
            limb_sets[name], limb_records[name] = _limb_mask(
                body, side=side, kind=kind
            )

    all_body_masks = {
        "pelvic_perineal": pelvic,
        "rear_scalp": scalp,
        "knees": knees,
        "front_face": face,
        **limb_sets,
    }
    editable_union = set().union(*all_body_masks.values())
    outside = set(range(len(body.data.vertices))).difference(editable_union)
    deform_names = {bone.name for bone in armature.data.bones if bone.use_deform}
    outside_faces = [
        int(face_item.index)
        for face_item in body.data.polygons
        if all(int(value) in outside for value in face_item.vertices)
    ]

    nail_objects = sorted(
        (obj for obj in bpy.data.objects if bool(obj.get("nail_component"))),
        key=lambda value: value.name,
    )
    eye_objects = sorted(
        (
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH"
            and any(token in obj.name.casefold() for token in ("sclera", "iris", "cornea"))
        ),
        key=lambda value: value.name,
    )
    brow_objects = sorted(
        (obj for obj in bpy.data.objects if "brow" in obj.name.casefold()),
        key=lambda value: value.name,
    )
    lid_lash_objects = sorted(
        (
            obj
            for obj in bpy.data.objects
            if any(token in obj.name.casefold() for token in ("lid", "lash"))
            and obj not in eye_objects
        ),
        key=lambda value: value.name,
    )
    support_objects = sorted(
        (obj.name for obj in bpy.data.objects if bool(obj.get("private_review_prop_only")))
    )

    report = {
        "schema_version": 1,
        "artifact_type": "kira_r18_preflight_exact_correction_masks",
        "status": "PREFLIGHT_ONLY_NO_MESH_MUTATION",
        "source": {
            "path": R17_RELATIVE.as_posix(),
            "sha256_before": hash_before,
            "sha256_after": _sha_file(source),
            "object_matrix_is_identity": body.matrix_world == body.matrix_world.Identity(4),
            "body_object": body.name,
            "armature_object": armature.name,
            "body_vertex_count": len(body.data.vertices),
            "body_face_count": len(body.data.polygons),
        },
        "masks": {
            "pelvic_perineal": pelvic_record,
            "nails": {
                "selection_rule": "replace exactly the 20 separate objects with nail_component=true; do not edit body solely to replace nail plates",
                "object_count": len(nail_objects),
                "objects": [_object_record(obj) for obj in nail_objects],
            },
            "rear_scalp": scalp_record,
            "knees": knee_records,
            "face": {
                **face_record,
                "replaceable_brow_objects": [_object_record(obj) for obj in brow_objects],
            },
            "hands_and_feet": limb_records,
        },
        "body_mask_overlaps": _overlaps(all_body_masks),
        "immutable_boundary": {
            "outside_all_proposed_body_masks": {
                "vertex_count": len(outside),
                "sorted_vertex_index_sha256": _index_sha(outside),
                "coordinate_sha256": _coordinate_sha(body, outside),
                "deform_weight_sha256": _weight_digest(body, outside, deform_names),
                "fully_outside_face_count": len(outside_faces),
                "fully_outside_face_index_sha256": _index_sha(outside_faces),
            },
            "armature": {
                "object": armature.name,
                "bone_count": len(armature.data.bones),
                "rest_structure_sha256": _armature_digest(armature),
                "all_actions_sha256": _action_digest(),
            },
            "eye_objects": [_object_record(obj) for obj in eye_objects],
            "lid_and_lash_objects": [_object_record(obj) for obj in lid_lash_objects],
            "private_review_support_objects": support_objects,
            "body_material_slots": [
                slot.material.name if slot.material else None for slot in body.material_slots
            ],
            "body_modifier_stack": [
                {
                    "name": modifier.name,
                    "type": modifier.type,
                    "vertex_group": str(getattr(modifier, "vertex_group", "")),
                    "object": modifier.object.name if getattr(modifier, "object", None) else None,
                }
                for modifier in body.modifiers
            ],
        },
        "operations": {
            "mesh_mutation_performed": False,
            "save_performed": False,
            "render_performed": False,
            "export_performed": False,
            "candidate_created": False,
            "runtime_mutation_performed": False,
        },
    }
    if report["source"]["sha256_before"] != report["source"]["sha256_after"]:
        raise RuntimeError("frozen R17 Blend changed during read-only report")
    print("R18_PREFLIGHT_MASKS=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
