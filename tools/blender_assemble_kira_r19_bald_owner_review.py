#!/usr/bin/env python3
"""Assemble the append-only, private Kira R19 bald owner-review package.

This worker deliberately does *not* promote or activate a body.  It starts
from the exact regular-CDT attempt-05 Blend because that is the strongest
complete connected R19 surface currently available.  It preserves the
independent visual rejection of that surface's superior pelvic seam/recessed
trapezoid, while integrating the separately accepted warm regional texture
graphs and Brows01 selection, the native 188-joint rig, the measured seated
contact action, and exactly twenty externally reviewed, licensed source-native
detachable nail components.

The resulting package is an owner-visible checkpoint, not an assertion that
the rejected pelvic component or the whole body has passed owner review.  It
is private, inactive, unassigned, unpublished, bald, and has no live/runtime
export path.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import traceback
from typing import Any, Iterable, Sequence

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_exact_mesh_intersections as exact_intersections  # noqa: E402
import blender_probe_blackproject_r19_seated_contact as seated_worker  # noqa: E402


BODY_OBJECT_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
RIG_OBJECT_NAME = "Kira_R19_BlackProject_Native_188_Rig"
SOURCE_LICENSE = "CC BY 4.0"
SOURCE_GLTF_REL = (
    "Avatar/avatar_builder/asset_library/base_body_reference/"
    "base_female_character_blackproject_cc_by_4.glb"
)
SOURCE_GLTF_SHA256 = (
    "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"
)
SOURCE_AUTHORITY_REL = (
    "Avatar/avatar_builder/asset_library/base_body_reference/"
    "base_female_character_blackproject_cc_by_4.authority.json"
)
SOURCE_AUTHORITY_SHA256 = (
    "d632a501edb2177aed7299aa257b61784685bdf2d9c88fa280370b640c4b508c"
)
FACE_REFERENCE_MESHES = {
    "Ariel_Mesh_Torso_0": "R19_WarmTexture_Torso",
    "Ariel_Mesh_Arms_0": "R19_WarmTexture_Arms",
    "Ariel_Mesh_Legs_0": "R19_WarmTexture_Legs",
    "Ariel_Mesh_Face_0": "R19_WarmTexture_Face",
    "Ariel_Mesh_Ears_0": "R19_WarmTexture_Ears",
    "Ariel_Mesh_Genitalia_0": "R19_WarmTexture_Genitalia",
}
SOURCE_NAIL_MESHES = {
    "Ariel_Mesh_Fingernails_0",
    "Ariel_Mesh_Toenails_0",
}
SELECTED_BROW_MESH = "Eye_Brows_Brows01_0"
SEATED_ACTION_NAME = "KIRA_R19_BLACKPROJECT_SEATED_CONTACT_ATTEMPT_01"
POSE_FRAME = 30
DEFAULT_CONFIG_REL = (
    "RecoverySprint/continuation_20260802/"
    "KIRA_R19_BALD_OWNER_REVIEW_CONFIG_ATTEMPT_01.json"
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / DEFAULT_CONFIG_REL),
    )
    parser.add_argument("--preflight-only", action="store_true")
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def vector_record(value: Vector) -> list[float]:
    return [round(float(component), 9) for component in value]


def canonical_name(name: str) -> str:
    """Remove only Blender's terminal numeric duplicate suffix."""

    if len(name) > 4 and name[-4] == "." and name[-3:].isdigit():
        return name[:-4]
    return name


def quantile(values: Iterable[float], fraction: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    position = max(0.0, min(1.0, float(fraction))) * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    alpha = position - low
    return ordered[low] * (1.0 - alpha) + ordered[high] * alpha


def bounds(points: Sequence[Vector]) -> dict[str, list[float]]:
    low = Vector(tuple(min(float(point[axis]) for point in points) for axis in range(3)))
    high = Vector(tuple(max(float(point[axis]) for point in points) for axis in range(3)))
    return {
        "low": vector_record(low),
        "high": vector_record(high),
        "size": vector_record(high - low),
    }


def resolve_and_verify(
    root: Path,
    config: dict[str, Any],
    path_key: str,
    hash_key: str,
) -> Path:
    value = str(config[path_key])
    expected = str(config[hash_key]).lower()
    if value.startswith("PENDING_") or expected.startswith("pending_"):
        raise RuntimeError(
            f"{path_key}/{hash_key} must be replaced with the accepted append-only nail path and hash"
        )
    path = (root / value).resolve(strict=True)
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{path_key} hash mismatch: {actual} != {expected}")
    return path


def load_config(path: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    config = json.loads(path.read_text(encoding="utf-8"))
    root = Path(config["project_root"]).resolve(strict=True)
    if root != PROJECT_ROOT.resolve():
        raise RuntimeError(f"config project root drifted: {root}")
    required_false = (
        "runtime_activation_allowed",
        "live_export_allowed",
        "scalp_hair_allowed",
    )
    if any(config.get(name) is not False for name in required_false):
        raise RuntimeError("private bald package cannot enable runtime, export, or scalp hair")
    if any(config.get(name) is not True for name in ("private", "inactive", "unassigned", "unpublished")):
        raise RuntimeError("private/inactive/unassigned/unpublished contract drifted")
    paths = {
        "source_body": resolve_and_verify(root, config, "source_body_blend", "source_body_sha256"),
        "face_blend": resolve_and_verify(root, config, "face_material_blend", "face_material_sha256"),
        "face_evidence": resolve_and_verify(root, config, "face_material_evidence", "face_material_evidence_sha256"),
        "correction_memory": resolve_and_verify(root, config, "kira_correction_memory", "kira_correction_memory_sha256"),
        "seated_blend": resolve_and_verify(root, config, "seated_contact_blend", "seated_contact_sha256"),
        "seated_evidence": resolve_and_verify(root, config, "seated_contact_evidence", "seated_contact_evidence_sha256"),
        "nail_blend": resolve_and_verify(root, config, "nail_blend", "nail_blend_sha256"),
        "nail_report": resolve_and_verify(root, config, "nail_report", "nail_report_sha256"),
        "nail_visual_review": resolve_and_verify(root, config, "nail_visual_review", "nail_visual_review_sha256"),
        "nail_manifest": resolve_and_verify(root, config, "nail_manifest", "nail_manifest_sha256"),
    }
    source_gltf = (root / SOURCE_GLTF_REL).resolve(strict=True)
    authority = (root / SOURCE_AUTHORITY_REL).resolve(strict=True)
    if sha256_file(source_gltf) != SOURCE_GLTF_SHA256:
        raise RuntimeError("enrolled BlackProject GLB hash drifted")
    if sha256_file(authority) != SOURCE_AUTHORITY_SHA256:
        raise RuntimeError("enrolled BlackProject authority hash drifted")
    paths["source_gltf"] = source_gltf
    paths["authority"] = authority
    return config, paths


def preflight_records(config: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    body_evidence_path = paths["source_body"].parent / "BUILD_EVIDENCE.json"
    body_visual_path = paths["source_body"].parent / "INDEPENDENT_VISUAL_REVIEW.json"
    body_report_path = paths["source_body"].parent / "REPORT.md"
    face_visual_path = paths["face_evidence"].parent / "VISUAL_REVIEW.md"
    for path in (body_evidence_path, body_visual_path, body_report_path, face_visual_path):
        if not path.is_file():
            raise RuntimeError(f"required attempt-05 record missing: {path}")
    body_evidence = json.loads(body_evidence_path.read_text(encoding="utf-8"))
    body_visual = json.loads(body_visual_path.read_text(encoding="utf-8"))
    face_evidence = json.loads(paths["face_evidence"].read_text(encoding="utf-8"))
    seated_evidence = json.loads(paths["seated_evidence"].read_text(encoding="utf-8"))
    nail_report = json.loads(paths["nail_report"].read_text(encoding="utf-8"))
    nail_visual_text = paths["nail_visual_review"].read_text(encoding="utf-8")
    nail_manifest = json.loads(paths["nail_manifest"].read_text(encoding="utf-8"))
    correction_memory = json.loads(paths["correction_memory"].read_text(encoding="utf-8"))

    structural = body_evidence.get("attempt_05_scoped_structural_gate", {})
    required_structural = (
        "exactly_34_seam_merges",
        "one_connected_primary_component",
        "zero_new_patch_or_seam_boundary_edges",
        "zero_patch_related_exact_intersections",
        "zero_source_interior_geometry_reused",
        "zero_center_fan_or_star_spokes",
    )
    if not all(structural.get(name) is True for name in required_structural):
        raise RuntimeError("attempt-05 bounded structural gates no longer match")
    if body_visual.get("status") != "REJECTED_VISUAL_HARD_SEAM_RECESSED_PANEL_AND_MISSING_WIRE_LINES":
        raise RuntimeError("attempt-05 visual rejection record drifted")
    if body_visual.get("decision") != "DO_NOT_TRANSFER_ATTEMPT_05_TO_A_KIRA_CANDIDATE":
        raise RuntimeError("attempt-05 non-promotion decision drifted")

    selected_brow = face_evidence.get("brows", {}).get("selected_for_warm_comparison", {})
    if selected_brow.get("mesh") != SELECTED_BROW_MESH:
        raise RuntimeError("accepted face component no longer selects Brows01")
    derived = face_evidence.get("materials", {}).get("derived_tint_records", [])
    derived_names = {record.get("derived_material") for record in derived}
    if set(FACE_REFERENCE_MESHES.values()) - derived_names:
        raise RuntimeError("accepted face/material package lacks one or more exact warm regional graphs")
    if face_evidence.get("materials", {}).get("packed_source_texture_graph_retained") is not True:
        raise RuntimeError("accepted regional source texture graph gate drifted")
    face_visual_text = face_visual_path.read_text(encoding="utf-8")
    if "COMPONENT_ACCEPTED_FOR_COMPLETE-CANDIDATE ASSEMBLY; OWNER APPROVAL NOT CLAIMED" not in face_visual_text:
        raise RuntimeError("accepted face/material visual-review decision drifted")
    correction_text = json.dumps(correction_memory, sort_keys=True).lower()
    if correction_memory.get("requested_eye_color") != "brown" or correction_text.count("eye_color:brown") < 2 or "warm brown" not in correction_text:
        raise RuntimeError("durable Kira warm-brown eye correction memory no longer matches")

    seat_action = seated_evidence.get("authored_action", {})
    if seat_action.get("name") != SEATED_ACTION_NAME:
        raise RuntimeError("sealed seated action name drifted")
    if seated_evidence.get("gates", {}).get("contact_geometry_gate_passed") is not True:
        raise RuntimeError("sealed seated contact component no longer passes contact gate")

    records = nail_report.get("adapter", {}).get("records", [])
    if len(records) != 20:
        raise RuntimeError(f"nail report must bind exactly 20 reviewed source-native components, found {len(records)}")
    object_names = [str(record.get("object", "")) for record in records]
    bone_names = [str(record.get("bone", "")) for record in records]
    if len(set(object_names)) != 20 or len(set(bone_names)) != 20 or any(not name for name in object_names + bone_names):
        raise RuntimeError("nail report object/bone inventory is not exact and unique")
    # The compatibility count retains its historical key, but the controlling
    # per-record provenance explicitly says these are reviewed source-native
    # split components, not procedurally regenerated shells.
    if int(nail_report.get("adapter", {}).get("generated_short_conformal_curved_shell_count", -1)) != 20:
        raise RuntimeError("nail report compatibility count is not exactly 20")
    provenance = {record.get("component_provenance") for record in records}
    if provenance != {"licensed_blackproject_cc_by_4_source_native_split"}:
        raise RuntimeError(f"nail component provenance drifted: {sorted(str(value) for value in provenance)}")
    if any(record.get("nail_component") is not True for record in records):
        raise RuntimeError("one or more source-native split records lacks nail_component=true")
    required_nail_visual_status = "COMPLETE_SOURCE_NATIVE_FALLBACK_READY_FOR_PRIVATE_R19_ASSEMBLY_WITH_RECORDED_SOURCE_SEAMS_AND_VISIBLE_STYLE_DEFECTS"
    if required_nail_visual_status not in nail_visual_text:
        raise RuntimeError("source-native nail fallback visual-review status drifted")
    for required_truth in (
        "691 raw pairs and 698 evaluated pairs",
        "long, squared/rectangular French-manicure-style nails",
        "Toenail outlines/cuticle transitions are somewhat polygonal or faceted",
    ):
        if required_truth not in nail_visual_text:
            raise RuntimeError(f"source-native nail fallback limitation disappeared: {required_truth}")
    nail_manifest_failures = []
    for entry in nail_manifest.get("files", []):
        bound_path = (PROJECT_ROOT / str(entry["path"])).resolve(strict=True)
        actual_hash = sha256_file(bound_path)
        actual_bytes = bound_path.stat().st_size
        if actual_hash != str(entry["sha256"]).lower() or actual_bytes != int(entry["bytes"]):
            nail_manifest_failures.append(
                {
                    "path": project_relative(bound_path),
                    "expected_sha256": entry["sha256"],
                    "actual_sha256": actual_hash,
                    "expected_bytes": entry["bytes"],
                    "actual_bytes": actual_bytes,
                }
            )
    if nail_manifest_failures or len(nail_manifest.get("files", [])) != 22:
        raise RuntimeError(
            f"source-native nail manifest rehash failed: count={len(nail_manifest.get('files', []))}; failures={nail_manifest_failures}"
        )

    return {
        "config_sha256": sha256_file(Path(config["_config_path"])),
        "source_attempt_05": {
            "blend": project_relative(paths["source_body"]),
            "blend_sha256": sha256_file(paths["source_body"]),
            "build_evidence": project_relative(body_evidence_path),
            "build_evidence_sha256": sha256_file(body_evidence_path),
            "visual_rejection": project_relative(body_visual_path),
            "visual_rejection_sha256": sha256_file(body_visual_path),
            "visual_status": body_visual["status"],
            "visual_decision_preserved": body_visual["decision"],
        },
        "face_material_component": {
            "blend": project_relative(paths["face_blend"]),
            "blend_sha256": sha256_file(paths["face_blend"]),
            "evidence": project_relative(paths["face_evidence"]),
            "evidence_sha256": sha256_file(paths["face_evidence"]),
            "visual_review": project_relative(face_visual_path),
            "visual_review_sha256": sha256_file(face_visual_path),
            "selected_brow_mesh": selected_brow["mesh"],
            "derived_materials": sorted(derived_names),
        },
        "kira_correction_memory": {
            "path": project_relative(paths["correction_memory"]),
            "sha256": sha256_file(paths["correction_memory"]),
            "requested_eye_color": correction_memory["requested_eye_color"],
            "eye_color_brown_correction_occurrence_count": correction_text.count("eye_color:brown"),
            "warm_brown_memory_present": "warm brown" in correction_text,
        },
        "seated_contact_component": {
            "blend": project_relative(paths["seated_blend"]),
            "blend_sha256": sha256_file(paths["seated_blend"]),
            "evidence": project_relative(paths["seated_evidence"]),
            "evidence_sha256": sha256_file(paths["seated_evidence"]),
            "action": seat_action,
        },
        "nail_component": {
            "blend": project_relative(paths["nail_blend"]),
            "blend_sha256": sha256_file(paths["nail_blend"]),
            "report": project_relative(paths["nail_report"]),
            "report_sha256": sha256_file(paths["nail_report"]),
            "visual_review": project_relative(paths["nail_visual_review"]),
            "visual_review_sha256": sha256_file(paths["nail_visual_review"]),
            "manifest": project_relative(paths["nail_manifest"]),
            "manifest_sha256": sha256_file(paths["nail_manifest"]),
            "manifest_entry_count": 22,
            "manifest_rehash_passed": True,
            "visual_status": required_nail_visual_status,
            "component_provenance": "licensed_blackproject_cc_by_4_source_native_split",
            "procedurally_regenerated_shells_claimed": False,
            "known_visible_limitations": [
                "long squared French-tip fingernails with opaque white free edges",
                "somewhat polygonal/faceted toenail and cuticle transitions",
                "native attachment-seam exact crossings: 691 raw / 698 evaluated in source evidence",
            ],
            "records": records,
        },
        "licensed_source": {
            "path": SOURCE_GLTF_REL,
            "sha256": SOURCE_GLTF_SHA256,
            "authority_path": SOURCE_AUTHORITY_REL,
            "authority_sha256": SOURCE_AUTHORITY_SHA256,
            "license": SOURCE_LICENSE,
        },
    }


def find_body_and_rig() -> tuple[bpy.types.Object, bpy.types.Object]:
    body = bpy.data.objects.get(BODY_OBJECT_NAME)
    rig = bpy.data.objects.get(RIG_OBJECT_NAME)
    if body is None or body.type != "MESH":
        raise RuntimeError(f"exact attempt-05 body object missing: {BODY_OBJECT_NAME}")
    if rig is None or rig.type != "ARMATURE":
        raise RuntimeError(f"exact native rig object missing: {RIG_OBJECT_NAME}")
    if len(rig.data.bones) != 188:
        raise RuntimeError(f"native rig must retain 188 joints, found {len(rig.data.bones)}")
    modifiers = [modifier for modifier in body.modifiers if modifier.type == "ARMATURE"]
    if len(modifiers) != 1 or modifiers[0].object != rig:
        raise RuntimeError("attempt-05 body does not bind exactly to its native rig")
    return body, rig


def append_objects(blend_path: Path, requested_names: Sequence[str]) -> list[bpy.types.Object]:
    with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
        missing = sorted(set(requested_names) - set(data_from.objects))
        if missing:
            raise RuntimeError(f"library objects missing from {blend_path}: {missing}")
        data_to.objects = list(requested_names)
    return [obj for obj in data_to.objects if obj is not None]


def append_action(blend_path: Path, action_name: str) -> bpy.types.Action:
    with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
        if action_name not in data_from.actions:
            raise RuntimeError(f"action {action_name} missing from {blend_path}")
        data_to.actions = [action_name]
    action = data_to.actions[0]
    if action is None:
        raise RuntimeError(f"failed to append action {action_name}")
    action.use_fake_user = True
    return action


def reference_polygon_tree(obj: bpy.types.Object) -> KDTree:
    tree = KDTree(len(obj.data.polygons))
    matrix = obj.matrix_world
    for polygon in obj.data.polygons:
        center = matrix @ polygon.center
        tree.insert(center, int(polygon.index))
    tree.balance()
    return tree


def material_graph_gate(material: bpy.types.Material, expected_name: str) -> dict[str, Any]:
    if canonical_name(material.name) != expected_name:
        raise RuntimeError(f"wrong accepted material: {material.name} != {expected_name}")
    if not material.use_nodes or material.node_tree is None:
        raise RuntimeError(f"accepted material has no nodes: {material.name}")
    node_names = {node.name for node in material.node_tree.nodes}
    node_types = Counter(node.bl_idname for node in material.node_tree.nodes)
    image_nodes = [
        node
        for node in material.node_tree.nodes
        if node.bl_idname == "ShaderNodeTexImage" and node.image is not None
    ]
    tint_nodes = [node for node in material.node_tree.nodes if node.name == "R19_Bounded_Warm_Texture_Tint"]
    if len(image_nodes) < 3 or len(tint_nodes) != 1:
        raise RuntimeError(
            f"accepted material graph incomplete: {material.name}; images={len(image_nodes)}, tint={len(tint_nodes)}"
        )
    packed = sum(node.image.packed_file is not None for node in image_nodes)
    if packed < 3 or node_types["ShaderNodeNormalMap"] < 1:
        raise RuntimeError(f"accepted packed texture/normal graph incomplete: {material.name}")
    return {
        "material": material.name,
        "node_count": len(node_names),
        "image_node_count": len(image_nodes),
        "packed_image_node_count": packed,
        "normal_map_node_count": node_types["ShaderNodeNormalMap"],
        "warm_tint_node_count": len(tint_nodes),
    }


def set_armature_target(obj: bpy.types.Object, rig: bpy.types.Object) -> None:
    world = obj.matrix_world.copy()
    armature_modifiers = [modifier for modifier in obj.modifiers if modifier.type == "ARMATURE"]
    for modifier in armature_modifiers:
        modifier.object = rig
        modifier.use_vertex_groups = True
    if obj.parent is not None and obj.parent.type == "ARMATURE":
        obj.parent = rig
        obj.matrix_parent_inverse = rig.matrix_world.inverted()
        obj.matrix_world = world


def mesh_geometry_uv_signature(obj: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    digest.update(canonical_name(obj.data.name).encode("utf-8"))
    for vertex in obj.data.vertices:
        digest.update(
            (f"v:{vertex.index}:{float(vertex.co.x):.12g}:{float(vertex.co.y):.12g}:{float(vertex.co.z):.12g};").encode("ascii")
        )
    for polygon in obj.data.polygons:
        digest.update(("p:" + ",".join(str(int(index)) for index in polygon.vertices) + ";").encode("ascii"))
    for layer in obj.data.uv_layers:
        digest.update(f"uv:{layer.name};".encode("utf-8"))
        for entry in layer.data:
            digest.update((f"{float(entry.uv.x):.12g},{float(entry.uv.y):.12g};").encode("ascii"))
    return digest.hexdigest()


def material_binding_signature(obj: bpy.types.Object) -> list[str]:
    return [slot.material.name if slot.material is not None else "" for slot in obj.material_slots]


def derive_warm_brown_iris_material(
    target_meshes: Sequence[bpy.types.Object],
) -> dict[str, Any]:
    iris_objects = [
        obj
        for obj in target_meshes
        if obj.name in bpy.data.objects and canonical_name(obj.data.name) == "Ariel_Mesh_Irises_0"
    ]
    if len(iris_objects) != 1:
        raise RuntimeError(f"exactly one named iris object is required, found {len(iris_objects)}")
    iris = iris_objects[0]
    protected_mesh_names = {
        "Ariel_Mesh_Pupils_0",
        "Ariel_Mesh_Cornea_0",
        "Ariel_Mesh_Sclera_0",
    }
    protected = {
        canonical_name(obj.data.name): {
            "geometry_uv_sha256": mesh_geometry_uv_signature(obj),
            "material_bindings": material_binding_signature(obj),
        }
        for obj in target_meshes
        if obj.name in bpy.data.objects and canonical_name(obj.data.name) in protected_mesh_names
    }
    if set(protected) != protected_mesh_names:
        raise RuntimeError(f"pupil/cornea/sclera preservation inventory incomplete: {sorted(protected)}")

    geometry_before = mesh_geometry_uv_signature(iris)
    modifier_before = [
        (modifier.name, modifier.type, modifier.object.name if modifier.type == "ARMATURE" and modifier.object else "")
        for modifier in iris.modifiers
    ]
    if len(iris.material_slots) != 1 or iris.material_slots[0].material is None:
        raise RuntimeError("named iris object must have one source texture material")
    source_material = iris.material_slots[0].material
    if canonical_name(source_material.name) != "Irises":
        raise RuntimeError(f"unexpected source iris material: {source_material.name}")
    if not source_material.use_nodes or source_material.node_tree is None:
        raise RuntimeError("source iris material lacks its texture graph")
    source_principled = [
        node for node in source_material.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"
    ]
    if len(source_principled) != 1:
        raise RuntimeError("source iris graph must have exactly one Principled node")
    source_base = source_principled[0].inputs.get("Base Color")
    if source_base is None or len(source_base.links) != 1:
        raise RuntimeError("source iris Base Color must have one exact texture feed")

    derived = source_material.copy()
    derived.name = "Kira_R19_Derived_WarmBrown_Irises_From_SourceTexture"
    nodes = derived.node_tree.nodes
    links = derived.node_tree.links
    principals = [node for node in nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"]
    if len(principals) != 1:
        raise RuntimeError("derived iris graph lost its exact Principled node")
    base = principals[0].inputs.get("Base Color")
    incoming = list(base.links) if base is not None else []
    if base is None or len(incoming) != 1:
        raise RuntimeError("derived iris Base Color source feed is ambiguous")
    source_socket = incoming[0].from_socket
    source_node = incoming[0].from_node
    links.remove(incoming[0])
    colorize = nodes.new("ShaderNodeMixRGB")
    colorize.name = "KIRA_R19_WARM_BROWN_IRIS_TEXTURE_COLORIZE"
    colorize.label = "Owner correction: warm brown; source iris texture detail retained"
    colorize.blend_type = "COLOR"
    colorize.inputs[0].default_value = 0.82
    colorize.inputs[2].default_value = (0.22, 0.055, 0.012, 1.0)
    links.new(source_socket, colorize.inputs[1])
    links.new(colorize.outputs[0], base)
    iris.material_slots[0].material = derived

    geometry_after = mesh_geometry_uv_signature(iris)
    modifier_after = [
        (modifier.name, modifier.type, modifier.object.name if modifier.type == "ARMATURE" and modifier.object else "")
        for modifier in iris.modifiers
    ]
    protected_after = {
        canonical_name(obj.data.name): {
            "geometry_uv_sha256": mesh_geometry_uv_signature(obj),
            "material_bindings": material_binding_signature(obj),
        }
        for obj in target_meshes
        if obj.name in bpy.data.objects and canonical_name(obj.data.name) in protected_mesh_names
    }
    colorizers = [node for node in derived.node_tree.nodes if node.name == "KIRA_R19_WARM_BROWN_IRIS_TEXTURE_COLORIZE"]
    if geometry_after != geometry_before or modifier_after != modifier_before:
        raise RuntimeError("material-only iris correction changed geometry, UV, rig, or modifier binding")
    if protected_after != protected:
        raise RuntimeError("iris correction changed pupil, cornea, or sclera")
    if len(colorizers) != 1:
        raise RuntimeError("derived iris graph does not contain exactly one named warm-brown colorizer")
    source_feed_retained = any(
        link.from_node == source_node and link.to_node == colorize
        for link in derived.node_tree.links
    )
    if not source_feed_retained:
        raise RuntimeError("derived warm-brown iris graph lost the exact source texture feed")
    iris["owner_requested_eye_color"] = "warm brown"
    iris["material_only_eye_correction"] = True
    iris["old_unapproved_v3_2_geometry_imported"] = False
    return {
        "object": iris.name,
        "mesh": canonical_name(iris.data.name),
        "source_material": source_material.name,
        "derived_material": derived.name,
        "source_texture_feed_node": source_node.name,
        "colorizing_node": colorize.name,
        "blend_mode": colorize.blend_type,
        "factor": float(colorize.inputs[0].default_value),
        "warm_brown_color_linear_rgba": [float(value) for value in colorize.inputs[2].default_value],
        "source_texture_feed_retained": source_feed_retained,
        "derived_iris_graph_count": 1,
        "geometry_uv_sha256_before": geometry_before,
        "geometry_uv_sha256_after": geometry_after,
        "geometry_uv_unchanged": geometry_before == geometry_after,
        "rig_modifier_bindings_unchanged": modifier_before == modifier_after,
        "pupils_cornea_sclera_unchanged": protected_after == protected,
        "flat_painted_eye_used": False,
        "old_unapproved_v3_2_geometry_imported": False,
        "owner_approval_claimed": False,
    }


def integrate_face_and_material_component(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    face_blend: Path,
    candidate_collection: bpy.types.Collection,
) -> dict[str, Any]:
    """Transfer exact accepted material graphs and Brows01 without duplicating skin."""

    with bpy.data.libraries.load(str(face_blend), link=False) as (data_from, data_to):
        # Load the complete saved hierarchy into a temporary linked
        # collection.  The BlackProject hierarchy carries its 1/105 world
        # scale above the mesh objects; appending Object_* alone leaves their
        # matrix_world stale at identity and makes equal surfaces appear 105x
        # apart.  No hierarchy geometry is transferred to the result.
        data_to.objects = list(data_from.objects)
    loaded_objects = [obj for obj in data_to.objects if obj is not None]
    references = [obj for obj in loaded_objects if obj.type == "MESH"]
    if not references:
        raise RuntimeError("accepted face/material Blend yielded no mesh references")
    temporary_collection = bpy.data.collections.new("R19_ACCEPTED_FACE_MATERIAL_TRANSFER_ONLY")
    bpy.context.scene.collection.children.link(temporary_collection)
    for obj in loaded_objects:
        temporary_collection.objects.link(obj)
        obj.hide_render = True
        # Blender 5.1 does not evaluate a newly appended parent hierarchy on
        # its first dependency-graph update when every object is already
        # hidden from the viewport.  Keep the transfer hierarchy visible only
        # until its saved parent scale has been evaluated and classification
        # is complete.  It remains render-hidden throughout.
        obj.hide_viewport = False
    bpy.context.view_layer.update()

    by_mesh: dict[str, list[bpy.types.Object]] = {}
    for obj in references:
        by_mesh.setdefault(canonical_name(obj.data.name), []).append(obj)
    missing = sorted(set(FACE_REFERENCE_MESHES) - set(by_mesh))
    if missing:
        raise RuntimeError(f"accepted material references missing: {missing}")

    torso_reference = by_mesh["Ariel_Mesh_Torso_0"][0]
    transform_delta = max(
        abs(float(torso_reference.matrix_world[row][column]) - float(body.matrix_world[row][column]))
        for row in range(4)
        for column in range(4)
    )
    body_world_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    torso_world_points = [
        torso_reference.matrix_world @ vertex.co
        for vertex in torso_reference.data.vertices
    ]
    body_world_bounds = [
        [min(float(point[axis]) for point in body_world_points) for axis in range(3)],
        [max(float(point[axis]) for point in body_world_points) for axis in range(3)],
    ]
    torso_world_bounds = [
        [min(float(point[axis]) for point in torso_world_points) for axis in range(3)],
        [max(float(point[axis]) for point in torso_world_points) for axis in range(3)],
    ]
    torso_within_body_bounds = all(
        body_world_bounds[0][axis] - 1.0e-6 <= torso_world_bounds[0][axis]
        and torso_world_bounds[1][axis] <= body_world_bounds[1][axis] + 1.0e-6
        for axis in range(3)
    )
    if transform_delta > 1.0e-7 or not torso_within_body_bounds:
        raise RuntimeError(
            "accepted hierarchy world-space verification failed: "
            f"transform_delta={transform_delta}, body_bounds={body_world_bounds}, "
            f"torso_bounds={torso_world_bounds}"
        )

    region_refs: dict[str, bpy.types.Object] = {}
    region_materials: dict[str, bpy.types.Material] = {}
    graph_records: list[dict[str, Any]] = []
    for mesh_name, material_name in FACE_REFERENCE_MESHES.items():
        ref = by_mesh[mesh_name][0]
        if len(ref.material_slots) != 1 or ref.material_slots[0].material is None:
            raise RuntimeError(f"accepted region {mesh_name} lacks one exact material")
        material = ref.material_slots[0].material
        graph_records.append(material_graph_gate(material, material_name))
        region_refs[mesh_name] = ref
        region_materials[mesh_name] = material

    patch_slot_indices = {
        index
        for index, material in enumerate(body.data.materials)
        if material is not None and "Patch_Skin_Audit_Tag" in material.name
    }
    patch_faces = {
        int(polygon.index)
        for polygon in body.data.polygons
        if int(polygon.material_index) in patch_slot_indices
    }
    if len(patch_faces) != 376:
        raise RuntimeError(f"attempt-05 patch-face identity drifted: {len(patch_faces)} != 376")

    trees = {name: reference_polygon_tree(obj) for name, obj in region_refs.items() if name != "Ariel_Mesh_Genitalia_0"}
    assignments: dict[int, str] = {}
    distances: dict[str, list[float]] = {name: [] for name in trees}
    body_matrix = body.matrix_world
    for polygon in body.data.polygons:
        index = int(polygon.index)
        if index in patch_faces:
            assignments[index] = "Ariel_Mesh_Genitalia_0"
            continue
        center = body_matrix @ polygon.center
        nearest = []
        for name, tree in trees.items():
            _co, _index, distance = tree.find(center)
            nearest.append((float(distance), name))
        distance, selected = min(nearest, key=lambda item: (item[0], item[1]))
        if distance > 0.002:
            raise RuntimeError(
                f"body face {index} cannot be bound exactly to accepted regional texture graph; distance={distance}"
            )
        assignments[index] = selected
        distances[selected].append(distance)

    body.data.materials.clear()
    material_slot_by_mesh: dict[str, int] = {}
    for mesh_name in FACE_REFERENCE_MESHES:
        body.data.materials.append(region_materials[mesh_name])
        material_slot_by_mesh[mesh_name] = len(body.data.materials) - 1
    for polygon in body.data.polygons:
        polygon.material_index = material_slot_by_mesh[assignments[int(polygon.index)]]

    # Classification has consumed the correctly evaluated world-space
    # hierarchy.  Hide transfer-only references now, never before their first
    # dependency-graph evaluation.
    for obj in loaded_objects:
        obj.hide_viewport = True
    bpy.context.view_layer.update()

    # Transfer exact source/accepted materials to every non-body component
    # that survived attempt 05.  The old flat nail objects and wrong brow are
    # removed below rather than hidden.
    target_meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj != body and obj not in references]
    material_rebindings: list[dict[str, Any]] = []
    removed_source_nails: list[str] = []
    removed_wrong_brows: list[str] = []
    for obj in list(target_meshes):
        mesh_name = canonical_name(obj.data.name)
        if mesh_name in SOURCE_NAIL_MESHES:
            removed_source_nails.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        if mesh_name.startswith("Eye_Brows_"):
            removed_wrong_brows.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        candidates = by_mesh.get(mesh_name, [])
        if not candidates:
            continue
        ref = candidates[0]
        obj.data.materials.clear()
        for slot in ref.material_slots:
            if slot.material is not None:
                obj.data.materials.append(slot.material)
        set_armature_target(obj, rig)
        material_rebindings.append(
            {
                "object": obj.name,
                "mesh": mesh_name,
                "materials": [slot.material.name for slot in obj.material_slots if slot.material],
            }
        )

    live_target_meshes = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and obj != body and obj not in references
    ]
    iris_correction = derive_warm_brown_iris_material(live_target_meshes)

    brow_candidates = by_mesh.get(SELECTED_BROW_MESH, [])
    if len(brow_candidates) != 1:
        raise RuntimeError(f"accepted Brows01 reference count must be one, found {len(brow_candidates)}")
    selected_brow = brow_candidates[0]
    temporary_collection.objects.unlink(selected_brow)
    candidate_collection.objects.link(selected_brow)
    selected_brow.hide_render = False
    selected_brow.hide_viewport = False
    selected_brow.hide_set(False)
    selected_brow.name = "Kira_R19_Accepted_Brows01"
    set_armature_target(selected_brow, rig)
    selected_brow["accepted_component_source"] = project_relative(face_blend)
    selected_brow["owner_approved"] = False
    selected_brow["private_review_only"] = True

    for obj in list(loaded_objects):
        if obj != selected_brow:
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(temporary_collection)

    body["regional_texture_graphs_retained"] = True
    body["warm_tint_strength"] = 0.34
    body["selected_brow_mesh"] = SELECTED_BROW_MESH
    return {
        "exact_component_blend": project_relative(face_blend),
        "material_graphs": graph_records,
        "body_face_region_counts": dict(sorted(Counter(assignments.values()).items())),
        "classification_maximum_centroid_distance_m": {
            name: round(max(values, default=0.0), 12) for name, values in sorted(distances.items())
        },
        "reference_world_space_normalization": {
            "method": "link_complete_saved_hierarchy_visible_then_evaluate_verify_classify_then_hide",
            "source_scale_hierarchy_loaded": True,
            "torso_to_body_matrix_max_abs_delta": transform_delta,
            "body_world_bounds_m": body_world_bounds,
            "torso_world_bounds_m": torso_world_bounds,
            "torso_within_body_bounds": torso_within_body_bounds,
            "reference_geometry_changed": False,
            "candidate_geometry_changed": False,
        },
        "patch_face_count_bound_to_regional_genitalia_graph": len(patch_faces),
        "patch_uv_quality_accepted": False,
        "patch_uv_truth_note": (
            "The generated attempt-05 patch receives the accepted regional graph, but its generated UV/visible "
            "superior-seam/trapezoid result remains independently rejected and is not promoted by this transfer."
        ),
        "support_component_material_rebindings": material_rebindings,
        "warm_brown_iris_material_only_correction": iris_correction,
        "selected_brow": {"object": selected_brow.name, "mesh": canonical_name(selected_brow.data.name)},
        "removed_wrong_brow_objects": sorted(removed_wrong_brows),
        "removed_source_nail_objects": sorted(removed_source_nails),
        "flat_single_color_skin_replacement_retained": False,
    }


def import_exact_nails(
    nail_blend: Path,
    nail_report: dict[str, Any],
    rig: bpy.types.Object,
    candidate_collection: bpy.types.Collection,
    candidate_id: str,
) -> tuple[list[bpy.types.Object], dict[str, Any]]:
    records = nail_report["adapter"]["records"]
    requested = [str(record["object"]) for record in records]
    objects = append_objects(nail_blend, requested)
    if len(objects) != 20:
        raise RuntimeError(f"exact nail append returned {len(objects)} objects")
    by_name = {canonical_name(obj.name): obj for obj in objects}
    imported_records: list[dict[str, Any]] = []
    for record in records:
        source_name = str(record["object"])
        obj = by_name.get(source_name)
        if obj is None or obj.type != "MESH":
            raise RuntimeError(f"exact reviewed nail object not loaded: {source_name}")
        candidate_collection.objects.link(obj)
        world = obj.matrix_world.copy()
        obj.parent = rig
        obj.matrix_parent_inverse = rig.matrix_world.inverted()
        obj.matrix_world = world
        armature_modifiers = [modifier for modifier in obj.modifiers if modifier.type == "ARMATURE"]
        if len(armature_modifiers) != 1:
            raise RuntimeError(f"nail {source_name} lacks one exact armature modifier")
        armature_modifiers[0].object = rig
        armature_modifiers[0].use_vertex_groups = True
        bone_name = str(record["bone"])
        group = obj.vertex_groups.get(bone_name)
        if group is None:
            raise RuntimeError(f"nail {source_name} lacks expected terminal group {bone_name}")
        other_positive_assignment_count = 0
        for vertex in obj.data.vertices:
            positive_assignments = [
                assignment
                for assignment in vertex.groups
                if float(assignment.weight) > 0.0
            ]
            terminal_assignments = [
                assignment
                for assignment in positive_assignments
                if int(assignment.group) == int(group.index)
            ]
            other_positive_assignments = [
                assignment
                for assignment in positive_assignments
                if int(assignment.group) != int(group.index)
            ]
            other_positive_assignment_count += len(other_positive_assignments)
            if (
                len(terminal_assignments) != 1
                or abs(float(terminal_assignments[0].weight) - 1.0) > 1.0e-7
                or other_positive_assignments
            ):
                raise RuntimeError(
                    f"nail {source_name} does not retain its exact unit terminal assignment to {bone_name}"
                )
        obj["candidate_id"] = candidate_id
        obj["private_owner_review_only"] = True
        obj["inactive_candidate"] = True
        obj["runtime_activation_allowed"] = False
        obj["nail_component"] = True
        obj["component_provenance"] = "licensed_blackproject_cc_by_4_source_native_split"
        imported_records.append(
            {
                "nail_id": str(record["nail_id"]),
                "object": obj.name,
                "bone": bone_name,
                "kind": str(record["kind"]),
                "side": str(record["side"]),
                "digit": int(record["digit"]),
                "vertex_count": len(obj.data.vertices),
                "polygon_count": len(obj.data.polygons),
                "material_names": [slot.material.name for slot in obj.material_slots if slot.material],
                "one_terminal_bone_unit_weight": True,
                "retained_vertex_group_datablock_count": len(obj.vertex_groups),
                "retained_vertex_group_datablock_names": [
                    vertex_group.name for vertex_group in obj.vertex_groups
                ],
                "other_positive_group_assignment_count": other_positive_assignment_count,
                "modifier_targets_native_rig": armature_modifiers[0].object == rig,
                "parent_is_native_rig": obj.parent == rig,
                "component_provenance": str(record["component_provenance"]),
                "source_native_material_uv_weight_facts": {
                    key: value
                    for key, value in record.items()
                    if any(token in str(key) for token in ("source", "material", "uv", "weight", "follow"))
                },
            }
        )
    expected_inventory = Counter((record["kind"], record["side"]) for record in imported_records)
    if expected_inventory != Counter({("fingernail", "L"): 5, ("fingernail", "R"): 5, ("toenail", "L"): 5, ("toenail", "R"): 5}):
        raise RuntimeError(f"20-nail kind/side inventory drifted: {expected_inventory}")
    return objects, {
        "source_blend": project_relative(nail_blend),
        "exact_reviewed_source_native_component_count": 20,
        "component_provenance": "licensed_blackproject_cc_by_4_source_native_split",
        "procedurally_regenerated_shells_claimed": False,
        "unsplit_legacy_combined_source_nail_objects_present": False,
        "records": imported_records,
    }


def reset_pose(rig: bpy.types.Object) -> None:
    rig.animation_data_create()
    rig.animation_data.action = None
    for pose_bone in rig.pose.bones:
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def apply_rotations(
    rig: bpy.types.Object,
    rotations: dict[str, tuple[float, float, float]],
) -> None:
    reset_pose(rig)
    for bone_name, rotation in rotations.items():
        pose_bone = rig.pose.bones.get(bone_name)
        if pose_bone is None:
            raise RuntimeError(f"required native pose bone missing: {bone_name}")
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = rotation
    bpy.context.scene.frame_set(POSE_FRAME)
    bpy.context.view_layer.update()


def degrees_to_radians(
    rotations: dict[str, Sequence[float]],
) -> dict[str, tuple[float, float, float]]:
    return {
        name: tuple(math.radians(float(value)) for value in values)
        for name, values in rotations.items()
    }


def knee_pose(side: str, degrees: float) -> dict[str, tuple[float, float, float]]:
    if side == "left":
        return {
            "lThighBend_05": (math.radians(10.0), 0.0, math.radians(2.0)),
            "lShin_07": (math.radians(degrees), 0.0, 0.0),
        }
    if side == "right":
        return {
            "rThighBend_021": (math.radians(10.0), 0.0, math.radians(-2.0)),
            "rShin_023": (math.radians(degrees), 0.0, 0.0),
        }
    if side == "bilateral":
        return {
            "lThighBend_05": (math.radians(8.0), 0.0, math.radians(3.0)),
            "rThighBend_021": (math.radians(8.0), 0.0, math.radians(-3.0)),
            "lShin_07": (math.radians(degrees), 0.0, 0.0),
            "rShin_023": (math.radians(degrees), 0.0, 0.0),
        }
    raise ValueError(side)


def pose_definitions(seated_evidence: dict[str, Any]) -> dict[str, dict[str, tuple[float, float, float]]]:
    poses: dict[str, dict[str, tuple[float, float, float]]] = {"neutral": {}}
    for side in ("left", "right", "bilateral"):
        for degrees in (30.0, 55.0, 80.0):
            poses[f"{side}_knee_{int(degrees)}"] = knee_pose(side, degrees)
    poses["supported_seated"] = degrees_to_radians(
        seated_evidence["authored_action"]["rotations_degrees_xyz"]
    )
    poses["supine_lying_foundation"] = {
        "hip_03": (math.radians(90.0), 0.0, 0.0),
        "lShldrBend_042": (0.0, 0.0, math.radians(18.0)),
        "rShldrBend_067": (0.0, 0.0, math.radians(-18.0)),
        "lShin_07": (math.radians(8.0), 0.0, 0.0),
        "rShin_023": (math.radians(8.0), 0.0, 0.0),
    }
    poses["eating_reach_foundation"] = {
        "chestUpper_040": (0.0, math.radians(-5.0), 0.0),
        "lShldrBend_042": (math.radians(-10.0), math.radians(-18.0), math.radians(54.0)),
        "lForearmBend_044": (0.0, math.radians(72.0), 0.0),
        "lHand_046": (math.radians(8.0), 0.0, math.radians(-8.0)),
        "lThumb1_047": (math.radians(18.0), 0.0, 0.0),
        "lIndex1_051": (math.radians(18.0), 0.0, 0.0),
        "lMid1_055": (math.radians(18.0), 0.0, 0.0),
    }
    poses["hands_fingers_foundation"] = {
        "lShldrBend_042": (0.0, math.radians(-10.0), math.radians(48.0)),
        "rShldrBend_067": (0.0, math.radians(10.0), math.radians(-48.0)),
        "lForearmBend_044": (0.0, math.radians(38.0), 0.0),
        "rForearmBend_069": (0.0, math.radians(-38.0), 0.0),
        "lIndex1_051": (math.radians(22.0), 0.0, 0.0),
        "lIndex2_052": (math.radians(28.0), 0.0, 0.0),
        "lIndex3_053": (math.radians(20.0), 0.0, 0.0),
        "lMid1_055": (math.radians(24.0), 0.0, 0.0),
        "lMid2_056": (math.radians(30.0), 0.0, 0.0),
        "lMid3_057": (math.radians(22.0), 0.0, 0.0),
        "lRing1_059": (math.radians(24.0), 0.0, 0.0),
        "lRing2_060": (math.radians(30.0), 0.0, 0.0),
        "lRing3_061": (math.radians(22.0), 0.0, 0.0),
        "lPinky1_063": (math.radians(26.0), 0.0, 0.0),
        "lPinky2_064": (math.radians(30.0), 0.0, 0.0),
        "lPinky3_065": (math.radians(22.0), 0.0, 0.0),
        "rIndex1_076": (math.radians(22.0), 0.0, 0.0),
        "rIndex2_077": (math.radians(28.0), 0.0, 0.0),
        "rIndex3_078": (math.radians(20.0), 0.0, 0.0),
        "rMid1_080": (math.radians(24.0), 0.0, 0.0),
        "rMid2_081": (math.radians(30.0), 0.0, 0.0),
        "rMid3_082": (math.radians(22.0), 0.0, 0.0),
        "rRing1_084": (math.radians(24.0), 0.0, 0.0),
        "rRing2_00": (math.radians(30.0), 0.0, 0.0),
        "rRing3_01": (math.radians(22.0), 0.0, 0.0),
        "rPinky1_086": (math.radians(26.0), 0.0, 0.0),
        "rPinky2_087": (math.radians(30.0), 0.0, 0.0),
        "rPinky3_088": (math.radians(22.0), 0.0, 0.0),
    }
    return poses


def action_rotations_degrees(rotations: dict[str, tuple[float, float, float]]) -> dict[str, list[float]]:
    return {
        name: [round(math.degrees(float(value)), 6) for value in rotation]
        for name, rotation in sorted(rotations.items())
    }


def author_action(
    rig: bpy.types.Object,
    name: str,
    rotations: dict[str, tuple[float, float, float]],
    candidate_id: str,
) -> bpy.types.Action:
    existing = bpy.data.actions.get(name)
    if existing is not None:
        raise RuntimeError(f"refusing to overwrite existing action {name}")
    reset_pose(rig)
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = action
    for frame in (1, POSE_FRAME):
        for pose_bone in rig.pose.bones:
            pose_bone.rotation_mode = "XYZ"
            pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        for bone_name, rotation in rotations.items():
            pose_bone = rig.pose.bones.get(bone_name)
            if pose_bone is None:
                raise RuntimeError(f"required action bone missing: {bone_name}")
            pose_bone.rotation_euler = rotation if frame == POSE_FRAME else (0.0, 0.0, 0.0)
            pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone_name)
    action["candidate_id"] = candidate_id
    action["private_owner_review_only"] = True
    action["runtime_assignment_allowed"] = False
    action["movement_foundation_not_full_human_capability_claim"] = True
    return action


def evaluated_mesh(obj: bpy.types.Object) -> tuple[bpy.types.Object, bpy.types.Mesh]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    return evaluated, evaluated.to_mesh()


def evaluated_vertices(obj: bpy.types.Object) -> list[Vector]:
    evaluated, mesh = evaluated_mesh(obj)
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def exact_body_intersection_report(obj: bpy.types.Object) -> dict[str, Any]:
    evaluated, mesh = evaluated_mesh(obj)
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bmesh.ops.transform(bm, matrix=evaluated.matrix_world, verts=list(bm.verts))
        return exact_intersections.exact_nonadjacent_intersection_report(
            bm,
            include_pair_details=True,
        )
    finally:
        bm.free()
        evaluated.to_mesh_clear()


def region_indices(
    obj: bpy.types.Object,
    prefixes: tuple[str, ...],
    minimum_weight: float,
) -> list[int]:
    group_indices = {
        group.index
        for group in obj.vertex_groups
        if group.name.startswith(prefixes)
    }
    return [
        int(vertex.index)
        for vertex in obj.data.vertices
        if any(
            assignment.group in group_indices and float(assignment.weight) >= minimum_weight
            for assignment in vertex.groups
        )
    ]


def edge_stretch_report(
    body: bpy.types.Object,
    neutral_points: Sequence[Vector],
    posed_points: Sequence[Vector],
    knee_indices: set[int],
) -> dict[str, Any]:
    ratios: list[float] = []
    knee_ratios: list[float] = []
    collapsed_edges = 0
    for edge in body.data.edges:
        first, second = map(int, edge.vertices)
        neutral_length = (neutral_points[first] - neutral_points[second]).length
        posed_length = (posed_points[first] - posed_points[second]).length
        if neutral_length <= 1.0e-10:
            collapsed_edges += 1
            continue
        ratio = posed_length / neutral_length
        ratios.append(ratio)
        if first in knee_indices or second in knee_indices:
            knee_ratios.append(ratio)

    def summary(values: Sequence[float]) -> dict[str, Any]:
        changes = [abs(value - 1.0) for value in values]
        return {
            "edge_count": len(values),
            "minimum_ratio": round(min(values, default=1.0), 9),
            "median_ratio": round(statistics.median(values) if values else 1.0, 9),
            "p95_absolute_change": round(quantile(changes, 0.95), 9),
            "p99_absolute_change": round(quantile(changes, 0.99), 9),
            "maximum_ratio": round(max(values, default=1.0), 9),
            "maximum_absolute_change": round(max(changes, default=0.0), 9),
        }

    return {
        "all_body_edges": summary(ratios),
        "weighted_knee_region_edges": summary(knee_ratios),
        "zero_length_neutral_edges_excluded": collapsed_edges,
        "measurement_only_not_visual_acceptance": True,
    }


def triangulated_world_mesh(obj: bpy.types.Object) -> tuple[list[Vector], list[tuple[int, int, int]], bpy.types.Object]:
    evaluated, mesh = evaluated_mesh(obj)
    mesh.calc_loop_triangles()
    points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    triangles = [tuple(int(index) for index in triangle.vertices) for triangle in mesh.loop_triangles]
    return points, triangles, evaluated


def exact_cross_intersections(
    body: bpy.types.Object,
    nails: Sequence[bpy.types.Object],
) -> dict[str, Any]:
    body_eval, body_mesh = evaluated_mesh(body)
    body_mesh.calc_loop_triangles()
    body_points = [body_eval.matrix_world @ vertex.co for vertex in body_mesh.vertices]
    body_triangles = [tuple(int(index) for index in triangle.vertices) for triangle in body_mesh.loop_triangles]
    body_tree = BVHTree.FromPolygons(body_points, body_triangles, all_triangles=True)
    records: list[dict[str, Any]] = []
    total_genuine = 0
    try:
        for nail in nails:
            nail_eval, nail_mesh = evaluated_mesh(nail)
            try:
                nail_mesh.calc_loop_triangles()
                nail_points = [nail_eval.matrix_world @ vertex.co for vertex in nail_mesh.vertices]
                nail_triangles = [tuple(int(index) for index in triangle.vertices) for triangle in nail_mesh.loop_triangles]
                nail_tree = BVHTree.FromPolygons(nail_points, nail_triangles, all_triangles=True)
                overlaps = body_tree.overlap(nail_tree)
                diagonal = (Vector(bounds(body_points)["high"]) - Vector(bounds(body_points)["low"])).length
                tolerance = max(1.0e-10, diagonal * 1.0e-8)
                genuine = 0
                touches = 0
                for body_index, nail_index in overlaps:
                    result = exact_intersections.classify_triangle_pair(
                        tuple(body_points[index] for index in body_triangles[body_index]),
                        tuple(nail_points[index] for index in nail_triangles[nail_index]),
                        linear_tolerance=tolerance,
                    )
                    if result.get("genuine_penetration") is True:
                        genuine += 1
                    elif result.get("classification") != "bvh_aabb_only":
                        touches += 1
                total_genuine += genuine
                records.append(
                    {
                        "object": nail.name,
                        "bvh_triangle_pair_count": len(overlaps),
                        "exact_genuine_triangle_pair_count": genuine,
                        "touch_or_coplanar_triangle_pair_count": touches,
                    }
                )
            finally:
                nail_eval.to_mesh_clear()
    finally:
        body_eval.to_mesh_clear()
    return {
        "method": "separate_evaluated_mesh_BVH_broad_phase_plus_exact_triangle_narrow_phase",
        "nail_count": len(nails),
        "total_exact_genuine_body_nail_triangle_pair_count": total_genuine,
        "records": records,
    }


def nail_follow_report(
    rig: bpy.types.Object,
    nails: Sequence[bpy.types.Object],
    nail_records: Sequence[dict[str, Any]],
    neutral_vertices: dict[str, list[Vector]],
) -> dict[str, Any]:
    bone_by_object = {str(record["object"]): str(record["bone"]) for record in nail_records}
    records: list[dict[str, Any]] = []
    for nail in nails:
        neutral = neutral_vertices[nail.name]
        posed = evaluated_vertices(nail)
        bone_name = bone_by_object[canonical_name(nail.name)] if canonical_name(nail.name) in bone_by_object else bone_by_object[nail.name]
        bone = rig.data.bones[bone_name]
        pose_bone = rig.pose.bones[bone_name]
        deform = rig.matrix_world @ pose_bone.matrix @ bone.matrix_local.inverted() @ rig.matrix_world.inverted()
        predicted = [deform @ point for point in neutral]
        residuals = [(actual - expected).length for actual, expected in zip(posed, predicted)]
        neutral_center = sum(neutral, Vector()) / len(neutral)
        posed_center = sum(posed, Vector()) / len(posed)
        edge_changes: list[float] = []
        for edge in nail.data.edges:
            first, second = map(int, edge.vertices)
            edge_changes.append(
                abs(
                    (posed[first] - posed[second]).length
                    - (neutral[first] - neutral[second]).length
                )
            )
        records.append(
            {
                "object": nail.name,
                "bone": bone_name,
                "centroid_displacement_m": round((posed_center - neutral_center).length, 9),
                "maximum_expected_rigid_follow_residual_m": round(max(residuals, default=0.0), 9),
                "maximum_internal_edge_length_change_m": round(max(edge_changes, default=0.0), 9),
            }
        )
    return {
        "method": "evaluated_vertices_vs_native_terminal_bone_deform_matrix",
        "records": records,
        "maximum_expected_rigid_follow_residual_m": max(
            (record["maximum_expected_rigid_follow_residual_m"] for record in records),
            default=0.0,
        ),
        "maximum_internal_edge_length_change_m": max(
            (record["maximum_internal_edge_length_change_m"] for record in records),
            default=0.0,
        ),
    }


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float = 0.7,
) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color
    principal = next(
        (node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"),
        None,
    )
    if principal is not None:
        principal.inputs["Base Color"].default_value = color
        principal.inputs["Roughness"].default_value = roughness
    return material


def make_cube(
    collection: bpy.types.Collection,
    name: str,
    center: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    material: bpy.types.Material,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    half = Vector(dimensions) * 0.5
    cx, cy, cz = center
    vertices = [
        (cx + sx * half.x, cy + sy * half.y, cz + sz * half.z)
        for sx, sy, sz in (
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
        )
    ]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7),
    ]
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj.data.materials.append(material)
    obj["review_context_prop_only"] = True
    obj["candidate_component"] = False
    obj["must_not_export"] = True
    obj["private_review_only"] = True
    obj.hide_render = True
    obj.hide_viewport = True
    return obj


def plane_contact_metrics(
    points: Sequence[Vector],
    plane_z: float,
    tolerance: float,
) -> dict[str, Any]:
    gaps = [float(point.z) - float(plane_z) for point in points]
    penetration = [max(0.0, -gap) for gap in gaps]
    return {
        "point_count": len(points),
        "plane_top_z_m": round(float(plane_z), 9),
        "minimum_signed_gap_m": round(min(gaps, default=999.0), 9),
        "minimum_absolute_contact_residual_m": round(min((abs(gap) for gap in gaps), default=999.0), 9),
        "maximum_penetration_depth_m": round(max(penetration, default=0.0), 9),
        "contact_point_count_within_tolerance": sum(-1.0e-9 <= gap <= tolerance for gap in gaps),
        "within_contact_tolerance": min((abs(gap) for gap in gaps), default=999.0) <= tolerance,
        "no_penetration": max(penetration, default=0.0) <= 1.0e-9,
    }


def build_support_props_and_metrics(
    body: bpy.types.Object,
    body_points: list[Vector],
    pose_name: str,
    region_map: dict[str, list[int]],
    collection: bpy.types.Collection,
    contact_tolerance: float,
    epsilon: float,
) -> tuple[dict[str, Any] | None, list[bpy.types.Object]]:
    material = make_material("Kira_R19_Review_Support_Navy", (0.025, 0.09, 0.15, 1.0), 0.78)
    floor_material = make_material("Kira_R19_Review_Floor", (0.055, 0.065, 0.075, 1.0), 0.85)
    props: list[bpy.types.Object] = []
    if pose_name == "supported_seated":
        regions = {
            "pelvis": region_map["pelvis"],
            "left_foot": region_map["left_foot"],
            "right_foot": region_map["right_foot"],
        }
        contact = seated_worker.contact_solution(body, body_points, regions)
        seat = contact["seat"]
        floor = contact["floor"]
        props.append(
            make_cube(
                collection,
                "Kira_R19_Seated_Support",
                (
                    (seat["x_min_m"] + seat["x_max_m"]) * 0.5,
                    (seat["y_min_m"] + seat["y_max_m"]) * 0.5,
                    seat["top_z_m"] - 0.025,
                ),
                (
                    seat["x_max_m"] - seat["x_min_m"],
                    seat["y_max_m"] - seat["y_min_m"],
                    0.05,
                ),
                material,
            )
        )
        box = bounds(body_points)
        low, high = Vector(box["low"]), Vector(box["high"])
        props.append(
            make_cube(
                collection,
                "Kira_R19_Seated_Common_Floor",
                ((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, floor["top_z_m"] - 0.0125),
                ((high.x - low.x) + 0.5, (high.y - low.y) + 0.5, 0.025),
                floor_material,
            )
        )
        return contact, props
    if pose_name == "supine_lying_foundation":
        box = bounds(body_points)
        low, high = Vector(box["low"]), Vector(box["high"])
        bed_top = low.z - epsilon
        near = [point for point in body_points if float(point.z) <= low.z + 0.10]
        metrics = plane_contact_metrics(near, bed_top, contact_tolerance)
        props.append(
            make_cube(
                collection,
                "Kira_R19_Supine_Support",
                ((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, bed_top - 0.04),
                ((high.x - low.x) + 0.3, (high.y - low.y) + 0.3, 0.08),
                material,
            )
        )
        return {
            "kind": "supine_support_foundation",
            "body_bounds_m": box,
            "support": metrics,
            "truth_note": "This proves a bounded no-penetration support plane for this pose, not sleep comfort or all lying motions.",
        }, props
    if pose_name == "eating_reach_foundation":
        hand_points = [body_points[index] for index in region_map["left_hand"]]
        hand_box = bounds(hand_points)
        low, high = Vector(hand_box["low"]), Vector(hand_box["high"])
        table_top = low.z - epsilon
        near = [point for point in hand_points if float(point.z) <= low.z + 0.035]
        metrics = plane_contact_metrics(near, table_top, contact_tolerance)
        props.append(
            make_cube(
                collection,
                "Kira_R19_Eating_Reach_Table",
                ((low.x + high.x) * 0.5, (low.y + high.y) * 0.5, table_top - 0.025),
                (0.48, 0.42, 0.05),
                material,
            )
        )
        # A context-only cup makes the intended reach legible.  It is not
        # parented to the hand and no grasp claim is made.
        cup = make_cube(
            collection,
            "Kira_R19_Eating_Context_Cup",
            (float(high.x) + 0.035, (low.y + high.y) * 0.5, table_top + 0.055),
            (0.055, 0.055, 0.11),
            make_material("Kira_R19_Context_Cup", (0.14, 0.42, 0.56, 1.0), 0.45),
        )
        props.append(cup)
        return {
            "kind": "eating_reach_table_foundation",
            "left_hand_bounds_m": hand_box,
            "table_contact": metrics,
            "truth_note": "This is hand-to-table reach/contact evidence only; it does not claim grasping, eating, swallowing, or full activity readiness.",
        }, props
    return None, props


def hide_all_review_props(props: Sequence[bpy.types.Object], hidden: bool = True) -> None:
    for obj in props:
        obj.hide_render = hidden
        obj.hide_viewport = hidden
        obj.hide_set(hidden)


def configure_render(config: dict[str, Any]) -> tuple[bpy.types.Scene, bpy.types.Object]:
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = int(config.get("render_resolution", 900))
    scene.render.resolution_y = int(config.get("render_resolution", 900))
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.006, 0.010, 0.017)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.55
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = int(config.get("render_samples", 32))

    def area(name: str, location: tuple[float, float, float], energy: float, size: float, target: Vector) -> None:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()

    area("Kira_R19_Key", (-2.1, -2.9, 2.55), 650.0, 2.1, Vector((0.0, 0.0, 1.05)))
    area("Kira_R19_Fill", (2.5, -1.9, 1.8), 330.0, 2.0, Vector((0.0, 0.0, 1.0)))
    area("Kira_R19_Rim", (0.0, 2.4, 2.25), 420.0, 1.7, Vector((0.0, 0.0, 1.2)))
    camera_data = bpy.data.cameras.new("Kira_R19_Owner_Review_Camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("Kira_R19_Owner_Review_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return scene, camera


def render_view(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output_dir: Path,
    name: str,
    location: Vector,
    target: Vector,
    scale: float,
) -> str:
    camera.location = location
    camera.data.ortho_scale = float(scale)
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    path = output_dir / f"{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path.name


def region_center(points: Sequence[Vector], indices: Sequence[int]) -> Vector:
    selected = [points[index] for index in indices]
    return sum(selected, Vector()) / len(selected)


def render_pose_evidence(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output_dir: Path,
    pose_name: str,
    points: list[Vector],
    region_map: dict[str, list[int]],
    props: Sequence[bpy.types.Object],
) -> dict[str, str]:
    box = bounds(points)
    low, high = Vector(box["low"]), Vector(box["high"])
    center = (low + high) * 0.5
    height = high.z - low.z
    width = high.x - low.x
    depth = high.y - low.y
    distance = max(height, width, depth) * 2.3 + 1.0
    renders: dict[str, str] = {}
    if pose_name == "neutral":
        views = {
            "neutral_front": (Vector((center.x, center.y - distance, center.z)), center, height * 1.08),
            "neutral_left_three_quarter": (Vector((center.x - distance * 0.65, center.y - distance, center.z)), center, height * 1.10),
            "neutral_right_three_quarter": (Vector((center.x + distance * 0.65, center.y - distance, center.z)), center, height * 1.10),
            "neutral_left_profile": (Vector((center.x - distance, center.y, center.z)), center, height * 1.08),
            "neutral_right_profile": (Vector((center.x + distance, center.y, center.z)), center, height * 1.08),
            "neutral_rear": (Vector((center.x, center.y + distance, center.z)), center, height * 1.08),
            "crown_top": (Vector((center.x, center.y - 0.12, high.z + distance)), Vector((center.x, center.y, high.z - 0.10)), 0.48),
            "rear_scalp_hairline": (Vector((center.x, center.y + distance, high.z - 0.15)), Vector((center.x, center.y, high.z - 0.18)), 0.57),
            "close_face_eyes_brows": (Vector((center.x, center.y - distance, high.z - 0.22)), Vector((center.x, center.y, high.z - 0.22)), 0.56),
        }
        for name, (location, target, scale) in views.items():
            renders[name] = render_view(scene, camera, output_dir, name, location, target, scale)
        iris_objects = [
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH" and canonical_name(obj.data.name) == "Ariel_Mesh_Irises_0"
        ]
        if len(iris_objects) != 1:
            raise RuntimeError(f"close-eye render requires exactly one iris object, found {len(iris_objects)}")
        iris_points = evaluated_vertices(iris_objects[0])
        split_x = statistics.median(float(point.x) for point in iris_points)
        eye_point_sets = {
            "close_negative_x_eye_warm_brown": [point for point in iris_points if float(point.x) <= split_x],
            "close_positive_x_eye_warm_brown": [point for point in iris_points if float(point.x) > split_x],
        }
        for name, eye_points in eye_point_sets.items():
            if not eye_points:
                raise RuntimeError(f"iris geometry could not be split for {name}")
            eye_target = sum(eye_points, Vector()) / len(eye_points)
            eye_box = bounds(eye_points)
            eye_size = max(Vector(eye_box["size"]).x, Vector(eye_box["size"]).z)
            renders[name] = render_view(
                scene,
                camera,
                output_dir,
                name,
                Vector((eye_target.x, eye_target.y - 1.2, eye_target.z)),
                eye_target,
                max(0.13, eye_size * 4.2),
            )
        for label, region in (
            ("left_hand_fingernails", "left_hand"),
            ("right_hand_fingernails", "right_hand"),
            ("left_foot_toenails", "left_foot"),
            ("right_foot_toenails", "right_foot"),
        ):
            target = region_center(points, region_map[region])
            location = Vector((target.x, target.y - 1.4, target.z + (0.12 if "foot" in label else 0.0)))
            renders[label] = render_view(scene, camera, output_dir, label, location, target, 0.31 if "hand" in label else 0.36)
        pelvis = region_center(points, region_map["pelvis"])
        protected_views = {
            "protected_adult_front": (Vector((pelvis.x, pelvis.y - 1.5, pelvis.z)), pelvis, 0.48),
            "protected_adult_left_three_quarter": (Vector((pelvis.x - 0.85, pelvis.y - 1.3, pelvis.z)), pelvis, 0.50),
            "protected_adult_right_profile": (Vector((pelvis.x + 1.5, pelvis.y, pelvis.z)), pelvis, 0.48),
            "protected_adult_rear": (Vector((pelvis.x, pelvis.y + 1.5, pelvis.z)), pelvis, 0.48),
        }
        for name, (location, target, scale) in protected_views.items():
            renders[name] = render_view(scene, camera, output_dir, name, location, target, scale)
        return renders

    hide_all_review_props(props, False)
    if "knee_" in pose_name:
        name = f"{pose_name}_three_quarter"
        renders[name] = render_view(
            scene,
            camera,
            output_dir,
            name,
            Vector((center.x + distance * 0.58, center.y - distance, center.z)),
            center,
            height * 1.12,
        )
        if pose_name.endswith("_80"):
            knee_target = region_center(points, region_map["knees"])
            close = f"{pose_name}_knee_close"
            renders[close] = render_view(
                scene, camera, output_dir, close,
                Vector((knee_target.x + 1.45, knee_target.y - 1.0, knee_target.z)),
                knee_target,
                0.62,
            )
    elif pose_name == "supported_seated":
        for suffix, location in {
            "front_three_quarter": Vector((center.x + distance * 0.58, center.y - distance, center.z)),
            "left_profile": Vector((center.x - distance, center.y, center.z)),
            "right_profile": Vector((center.x + distance, center.y, center.z)),
            "rear_three_quarter": Vector((center.x - distance * 0.58, center.y + distance, center.z)),
        }.items():
            name = f"supported_seated_{suffix}"
            renders[name] = render_view(scene, camera, output_dir, name, location, center, height * 1.16)
        feet = (region_center(points, region_map["left_foot"]) + region_center(points, region_map["right_foot"])) * 0.5
        renders["supported_seated_feet_contact"] = render_view(
            scene, camera, output_dir, "supported_seated_feet_contact",
            Vector((feet.x + 1.5, feet.y - 1.2, feet.z + 0.08)), feet, 0.62,
        )
    elif pose_name == "supine_lying_foundation":
        for suffix, location in {
            "side": Vector((center.x + distance, center.y, center.z)),
            "three_quarter": Vector((center.x + distance * 0.65, center.y - distance * 0.75, center.z + distance * 0.25)),
            "top": Vector((center.x, center.y, center.z + distance)),
        }.items():
            name = f"supine_lying_foundation_{suffix}"
            renders[name] = render_view(scene, camera, output_dir, name, location, center, max(width, depth) * 1.15)
    elif pose_name == "eating_reach_foundation":
        for suffix, location in {
            "front_three_quarter": Vector((center.x + distance * 0.58, center.y - distance, center.z)),
            "left_profile": Vector((center.x - distance, center.y, center.z)),
        }.items():
            name = f"eating_reach_foundation_{suffix}"
            renders[name] = render_view(scene, camera, output_dir, name, location, center, height * 1.12)
        target = region_center(points, region_map["left_hand"])
        renders["eating_reach_hand_table_close"] = render_view(
            scene, camera, output_dir, "eating_reach_hand_table_close",
            Vector((target.x + 1.2, target.y - 1.0, target.z + 0.15)), target, 0.52,
        )
    elif pose_name == "hands_fingers_foundation":
        for side in ("left", "right"):
            target = region_center(points, region_map[f"{side}_hand"])
            name = f"hands_fingers_foundation_{side}_close"
            renders[name] = render_view(
                scene, camera, output_dir, name,
                Vector((target.x, target.y - 1.35, target.z + 0.05)), target, 0.34,
            )
        renders["hands_fingers_foundation_full"] = render_view(
            scene, camera, output_dir, "hands_fingers_foundation_full",
            Vector((center.x, center.y - distance, center.z)), center, height * 1.08,
        )
    hide_all_review_props(props, True)
    return renders


def scalp_hair_dependency_audit() -> dict[str, Any]:
    forbidden_objects: list[str] = []
    allowed_brow_lash_objects: list[str] = []
    for obj in bpy.data.objects:
        identity = f"{obj.name} {getattr(obj.data, 'name', '')}".lower()
        if "brow" in identity or "lash" in identity:
            allowed_brow_lash_objects.append(obj.name)
            continue
        if any(token in identity for token in ("hair", "groom", "scalp_cap", "scalpcap")):
            if obj.type in {"MESH", "CURVE", "CURVES", "PARTICLE", "VOLUME"}:
                forbidden_objects.append(obj.name)
    particle_collection = getattr(bpy.data, "particles", ())
    particle_settings = [settings.name for settings in particle_collection]
    hair_curve_collection = getattr(bpy.data, "hair_curves", ())
    hair_curve_data = [curve.name for curve in hair_curve_collection]
    if forbidden_objects or particle_settings or hair_curve_data:
        raise RuntimeError(
            "bald package contains a scalp-hair runtime dependency: "
            + json.dumps(
                {
                    "objects": forbidden_objects,
                    "particle_settings": particle_settings,
                    "hair_curve_data": hair_curve_data,
                }
            )
        )
    return {
        "forbidden_scalp_hair_objects": forbidden_objects,
        "particle_hair_settings": particle_settings,
        "hair_curve_data": hair_curve_data,
        "allowed_eyebrow_eyelash_objects": sorted(allowed_brow_lash_objects),
        "scalp_hair_objects_excluded_not_hidden": True,
        "scalp_hair_runtime_dependency_count": 0,
    }


def object_scope_audit(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    nails: Sequence[bpy.types.Object],
) -> dict[str, Any]:
    candidate_meshes = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH" and not bool(obj.get("review_context_prop_only"))
    ]
    source_nails = [
        obj.name
        for obj in candidate_meshes
        if canonical_name(obj.data.name) in SOURCE_NAIL_MESHES
    ]
    if source_nails:
        raise RuntimeError(f"legacy/source nail geometry survived assembly: {source_nails}")
    return {
        "body": body.name,
        "rig": rig.name,
        "native_joint_count": len(rig.data.bones),
        "candidate_mesh_objects": sorted(obj.name for obj in candidate_meshes),
        "exact_reviewed_source_native_nail_component_count": len(nails),
        "unsplit_legacy_source_nail_object_count": len(source_nails),
        "scene_collection_count": len(bpy.data.collections),
        "private": True,
        "inactive": True,
        "unassigned": True,
        "unpublished": True,
        "runtime_activation_allowed": False,
        "live_export_present": False,
        "clothing_included": False,
    }


def restoration_report(
    rig: bpy.types.Object,
    body: bpy.types.Object,
    neutral_points: Sequence[Vector],
) -> dict[str, Any]:
    reset_pose(rig)
    restored = evaluated_vertices(body)
    if len(restored) != len(neutral_points):
        raise RuntimeError("neutral restoration changed evaluated vertex count")
    deltas = [(first - second).length for first, second in zip(neutral_points, restored)]
    maximum = max(deltas, default=0.0)
    pose_nonzero = [
        pose_bone.name
        for pose_bone in rig.pose.bones
        if sum(abs(float(value)) for value in pose_bone.rotation_euler) > 1.0e-12
        or pose_bone.location.length > 1.0e-12
        or (Vector(pose_bone.scale) - Vector((1.0, 1.0, 1.0))).length > 1.0e-12
    ]
    result = {
        "evaluated_vertex_count": len(restored),
        "maximum_neutral_coordinate_delta_m": round(maximum, 12),
        "pose_bones_nonneutral_after_restore": pose_nonzero,
        "armature_action_after_restore": rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None,
        "exact_neutral_restoration_passed": maximum <= 1.0e-9 and not pose_nonzero and (not rig.animation_data or rig.animation_data.action is None),
    }
    if not result["exact_neutral_restoration_passed"]:
        raise RuntimeError(f"exact neutral restoration failed: {result}")
    return result


def render_bindings(output_dir: Path, names: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, filename in sorted(names.items()):
        path = output_dir / filename
        if not path.is_file() or path.stat().st_size <= 1000:
            raise RuntimeError(f"render missing or empty: {path}")
        result[name] = {
            "path": project_relative(path),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
    return result


def write_manifest(output_dir: Path) -> Path:
    manifest_path = output_dir / "PACKAGE_MANIFEST.json"
    entries = []
    for path in sorted(output_dir.rglob("*"), key=lambda item: item.as_posix().lower()):
        if path.is_file() and path != manifest_path:
            entries.append(
                {
                    "path": project_relative(path),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    write_json(
        manifest_path,
        {
            "schema_version": 1,
            "append_only_attempt": output_dir.name,
            "created_utc": utc_now(),
            "files_excluding_this_manifest": entries,
        },
    )
    return manifest_path


def pose_slug_to_action_name(pose_name: str) -> str:
    return f"KIRA_R19_{pose_name.upper()}"


def run_assembly(
    config_path: Path,
    config: dict[str, Any],
    paths: dict[str, Path],
    preflight: dict[str, Any],
) -> int:
    if Path(bpy.data.filepath).resolve() != paths["source_body"]:
        raise RuntimeError(
            "worker must be launched with the exact regular-CDT attempt-05 Blend as Blender input"
        )
    output_dir = (PROJECT_ROOT / str(config["output_dir"])).resolve()
    if output_dir.exists():
        raise FileExistsError(f"append-only output already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    intersections_dir = output_dir / "exact_intersections"
    intersections_dir.mkdir()

    body, rig = find_body_and_rig()
    # Move the result into a clearly named private collection without changing
    # any source file.  Existing source collection links are retained.
    candidate_collection = bpy.data.collections.new("KIRA_R19_BALD_LOW_RESOURCE_PRIVATE_OWNER_REVIEW")
    bpy.context.scene.collection.children.link(candidate_collection)
    for obj in (body, rig):
        if candidate_collection.objects.get(obj.name) is None:
            candidate_collection.objects.link(obj)

    face_record = integrate_face_and_material_component(
        body,
        rig,
        paths["face_blend"],
        candidate_collection,
    )
    nail_source_report = json.loads(paths["nail_report"].read_text(encoding="utf-8"))
    nails, nail_record = import_exact_nails(
        paths["nail_blend"],
        nail_source_report,
        rig,
        candidate_collection,
        str(config["candidate_id"]),
    )

    for datablock in (body, rig):
        datablock["candidate_id"] = str(config["candidate_id"])
        datablock["private_owner_review_only"] = True
        datablock["inactive_candidate"] = True
        datablock["owner_approved"] = False
        datablock["runtime_assignment_allowed"] = False
        datablock["runtime_activation_allowed"] = False
        datablock["public_export_allowed"] = False
        datablock["scalp_hair_runtime_dependency"] = False
    body["adult_status"] = "confirmed_adult"
    body["body_class"] = "adult_female"
    body["pelvic_component_visual_status"] = "REJECTED_HARD_SUPERIOR_SEAM_RECESSED_TRAPEZOID"
    body["pelvic_component_owner_approved"] = False
    rig["native_joint_count"] = 188

    seated_action = append_action(paths["seated_blend"], SEATED_ACTION_NAME)
    if seated_action.name != SEATED_ACTION_NAME:
        raise RuntimeError(
            f"exact seated action collided with an existing datablock: {seated_action.name}"
        )
    seated_action["transferred_exactly_from_append_only_probe"] = True
    seated_action["source_blend_sha256"] = sha256_file(paths["seated_blend"])
    seated_evidence = json.loads(paths["seated_evidence"].read_text(encoding="utf-8"))
    poses = pose_definitions(seated_evidence)
    action_records: dict[str, Any] = {
        "supported_seated": {
            "name": seated_action.name,
            "source": project_relative(paths["seated_blend"]),
            "source_sha256": sha256_file(paths["seated_blend"]),
            "exact_append": True,
            "rotations_degrees_xyz": action_rotations_degrees(poses["supported_seated"]),
        }
    }
    for pose_name, rotations in poses.items():
        if pose_name == "supported_seated":
            continue
        action = author_action(
            rig,
            pose_slug_to_action_name(pose_name),
            rotations,
            str(config["candidate_id"]),
        )
        action_records[pose_name] = {
            "name": action.name,
            "exact_append": False,
            "authored_for_this_private_candidate": True,
            "rotations_degrees_xyz": action_rotations_degrees(rotations),
        }

    # Weighted regions are durable indices on the joined primary surface.
    region_map = {
        "pelvis": region_indices(body, ("pelvis_", "lThighBend_", "rThighBend_"), 0.16),
        "left_foot": region_indices(body, ("lFoot_", "lToe_", "lMetatarsals_"), 0.10),
        "right_foot": region_indices(body, ("rFoot_", "rToe_", "rMetatarsals_"), 0.10),
        "left_hand": region_indices(body, ("lHand_", "lThumb", "lIndex", "lMid", "lRing", "lPinky"), 0.10),
        "right_hand": region_indices(body, ("rHand_", "rThumb", "rIndex", "rMid", "rRing", "rPinky"), 0.10),
        "knees": region_indices(body, ("lThighBend_", "rThighBend_", "lShin_", "rShin_"), 0.28),
    }
    if any(not values for values in region_map.values()):
        raise RuntimeError(
            "one or more native weighted movement/contact regions is empty: "
            + json.dumps({name: len(values) for name, values in region_map.items()})
        )

    reset_pose(rig)
    neutral_points = evaluated_vertices(body)
    neutral_nails = {nail.name: evaluated_vertices(nail) for nail in nails}
    knee_indices = set(region_map["knees"])
    context_collection = bpy.data.collections.new("KIRA_R19_REVIEW_CONTEXT_PROPS_DO_NOT_EXPORT")
    bpy.context.scene.collection.children.link(context_collection)
    all_props: list[bpy.types.Object] = []
    pose_reports: dict[str, Any] = {}
    render_names: dict[str, str] = {}
    scene, camera = configure_render(config)

    for pose_name, rotations in poses.items():
        apply_rotations(rig, rotations)
        posed_points = evaluated_vertices(body)
        exact_report = exact_body_intersection_report(body)
        exact_path = intersections_dir / f"{pose_name}.json"
        write_json(exact_path, exact_report)
        contact, props = build_support_props_and_metrics(
            body,
            posed_points,
            pose_name,
            region_map,
            context_collection,
            float(config["contact_tolerance_m"]),
            float(config["no_penetration_epsilon_m"]),
        )
        all_props.extend(props)
        hide_all_review_props(all_props, True)
        stretch = edge_stretch_report(body, neutral_points, posed_points, knee_indices)
        nail_follow = nail_follow_report(
            rig,
            nails,
            nail_record["records"],
            neutral_nails,
        )
        nail_cross = exact_cross_intersections(body, nails)
        pose_renders = render_pose_evidence(
            scene,
            camera,
            output_dir,
            pose_name,
            posed_points,
            region_map,
            props,
        )
        render_names.update(pose_renders)
        pose_reports[pose_name] = {
            "action": action_records[pose_name],
            "body_bounds_m": bounds(posed_points),
            "evaluated_exact_self_intersections": {
                "report": project_relative(exact_path),
                "report_sha256": sha256_file(exact_path),
                "exact_genuine_penetration_pair_count": exact_report["exact_genuine_penetration_pair_count"],
                "touch_or_coplanar_false_positive_pair_count": exact_report["touch_or_coplanar_false_positive_pair_count"],
            },
            "deformation_stretch": stretch,
            "support_contact": contact,
            "nail_attachment_follow": nail_follow,
            "evaluated_exact_body_nail_intersections": nail_cross,
            "renders": sorted(pose_renders),
            "visual_acceptance_claimed": False,
        }

    restore = restoration_report(rig, body, neutral_points)
    hair_audit = scalp_hair_dependency_audit()
    scope_audit = object_scope_audit(body, rig, nails)

    bpy.context.scene["candidate_id"] = str(config["candidate_id"])
    bpy.context.scene["private_owner_review_only"] = True
    bpy.context.scene["inactive_candidate"] = True
    bpy.context.scene["owner_approved"] = False
    bpy.context.scene["runtime_assignment_allowed"] = False
    bpy.context.scene["runtime_activation_allowed"] = False
    bpy.context.scene["public_export_allowed"] = False
    bpy.context.scene["no_scalp_hair_dependency"] = True
    bpy.context.scene["pelvic_component_visual_acceptance"] = False
    bpy.context.scene["known_pelvic_component_defect"] = "hard superior seam / recessed trapezoid"

    blend_path = output_dir / "kira_r19_bald_low_resource_private_owner_review.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    source_hashes_after = {
        key: sha256_file(path)
        for key, path in paths.items()
    }
    expected_after = {
        "source_body": config["source_body_sha256"],
        "face_blend": config["face_material_sha256"],
        "face_evidence": config["face_material_evidence_sha256"],
        "correction_memory": config["kira_correction_memory_sha256"],
        "seated_blend": config["seated_contact_sha256"],
        "seated_evidence": config["seated_contact_evidence_sha256"],
        "nail_blend": config["nail_blend_sha256"],
        "nail_report": config["nail_report_sha256"],
        "nail_visual_review": config["nail_visual_review_sha256"],
        "nail_manifest": config["nail_manifest_sha256"],
        "source_gltf": SOURCE_GLTF_SHA256,
        "authority": SOURCE_AUTHORITY_SHA256,
    }
    drifted = {
        key: {"after": source_hashes_after[key], "expected": expected}
        for key, expected in expected_after.items()
        if source_hashes_after[key] != str(expected).lower()
    }
    if drifted:
        raise RuntimeError(f"one or more protected source files changed: {drifted}")

    render_evidence = render_bindings(output_dir, render_names)
    pose_intersection_counts = {
        name: report["evaluated_exact_self_intersections"]["exact_genuine_penetration_pair_count"]
        for name, report in pose_reports.items()
    }
    nail_intersection_counts = {
        name: report["evaluated_exact_body_nail_intersections"]["total_exact_genuine_body_nail_triangle_pair_count"]
        for name, report in pose_reports.items()
    }
    evidence = {
        "schema_version": 1,
        "candidate_id": str(config["candidate_id"]),
        "status": "PRIVATE_INACTIVE_COMPLETE_OWNER_REVIEW_ASSEMBLY_WITH_DISCLOSED_REJECTED_PELVIC_COMPONENT",
        "created_utc": utc_now(),
        "preflight": preflight,
        "scope": {
            "private": True,
            "inactive": True,
            "unassigned": True,
            "unpublished": True,
            "owner_approved": False,
            "runtime_activation_allowed": False,
            "live_export_created": False,
            "glb_export_created": False,
            "clothing_included": False,
            "scalp_hair_included": False,
            "adult_status": "confirmed_adult",
            "body_class": "adult_female",
        },
        "known_unresolved_visual_defect": {
            "component": "regular-CDT attempt-05 pelvic/perineal replacement",
            "status": "REJECTED_VISUAL_HARD_SEAM_RECESSED_PANEL_AND_TRAPEZOID",
            "owner_approved": False,
            "accepted_or_promoted_by_this_assembly": False,
            "truth": (
                "Attempt 05 remains the best structurally bounded complete surface available for review, "
                "but its hard superior seam/recessed trapezoid is plainly disclosed and remains rejected."
            ),
        },
        "face_and_material_integration": face_record,
        "native_rig": {
            "object": rig.name,
            "joint_count": len(rig.data.bones),
            "exact_188_joint_gate_passed": len(rig.data.bones) == 188,
        },
        "nails": nail_record,
        "actions": action_records,
        "region_vertex_counts": {name: len(values) for name, values in sorted(region_map.items())},
        "poses": pose_reports,
        "pose_exact_body_intersection_counts": pose_intersection_counts,
        "pose_exact_body_nail_intersection_counts": nail_intersection_counts,
        "exact_neutral_restoration": restore,
        "bald_runtime_contract": hair_audit,
        "object_scope": scope_audit,
        "artifacts": {
            "blend": {
                "path": project_relative(blend_path),
                "sha256": sha256_file(blend_path),
                "size_bytes": blend_path.stat().st_size,
            },
            "renders": render_evidence,
        },
        "protected_source_hashes_after": source_hashes_after,
        "gates": {
            "private_inactive_unassigned_unpublished": True,
            "native_188_joint_rig": len(rig.data.bones) == 188,
            "exact_twenty_reviewed_source_native_nail_components": len(nails) == 20,
            "unsplit_legacy_source_nail_objects_absent": scope_audit["unsplit_legacy_source_nail_object_count"] == 0,
            "scalp_hair_runtime_dependency_absent": hair_audit["scalp_hair_runtime_dependency_count"] == 0,
            "accepted_regional_texture_graphs_integrated": True,
            "accepted_Brows01_integrated": face_record["selected_brow"]["mesh"] == SELECTED_BROW_MESH,
            "durable_warm_brown_eye_correction_bound": preflight["kira_correction_memory"]["requested_eye_color"] == "brown",
            "exactly_one_source_texture_colorized_warm_brown_iris_graph": face_record["warm_brown_iris_material_only_correction"]["derived_iris_graph_count"] == 1,
            "iris_geometry_uv_rig_unchanged": (
                face_record["warm_brown_iris_material_only_correction"]["geometry_uv_unchanged"]
                and face_record["warm_brown_iris_material_only_correction"]["rig_modifier_bindings_unchanged"]
            ),
            "pupils_cornea_sclera_unchanged_by_iris_correction": face_record["warm_brown_iris_material_only_correction"]["pupils_cornea_sclera_unchanged"],
            "old_unapproved_v3_2_eye_geometry_imported": False,
            "exact_neutral_restoration": restore["exact_neutral_restoration_passed"],
            "required_pose_inventory_present": set(poses) == set(pose_reports),
            "required_review_render_inventory_present": len(render_evidence) >= 30,
            "pelvic_component_visual_acceptance": False,
            "whole_body_owner_acceptance": False,
            "runtime_eligibility": False,
        },
        "movement_truth_note": (
            "These actions and measurements are bounded pose/deformation/contact foundations. They do not prove "
            "that Kira can already perform every ordinary human activity, eat, swallow, sleep, or reproduce."
        ),
        "owner_review_truth_note": (
            "This complete package is intentionally shown despite the disclosed pelvic seam/trapezoid defect. "
            "Robert must decide whether to target that component again; no activation or assignment occurs."
        ),
    }
    evidence_path = output_dir / "BUILD_EVIDENCE.json"
    write_json(evidence_path, evidence)

    rollback_path = output_dir / "ROLLBACK.md"
    rollback_path.write_text(
        "\n".join(
            [
                "# Kira R19 bald private assembly rollback",
                "",
                "This attempt did not modify a live avatar, roster assignment, launcher, runtime package, or any sealed input.",
                "Rollback therefore means moving this one append-only attempt directory to an owner-selected archive location.",
                "Do not delete or overwrite the sealed attempt-05, face/material attempt-03, seated-contact attempt-01, or nail source package.",
                "No automatic rollback command is executed by this worker.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    review_path = output_dir / "OWNER_REVIEW_README.md"
    review_path.write_text(
        "\n".join(
            [
                "# Kira R19 bald low-resource body — private owner review",
                "",
                "Status: **COMPLETE REVIEW ASSEMBLY; NOT ACCEPTED OR ACTIVE**",
                "",
                "This package contains the full bald body, native 188-joint rig, accepted warm regional texture graphs, Brows01, a material-only source-textured warm-brown iris correction, eyes/lashes, and exactly twenty reviewed detachable licensed source-native nail components.",
                "It includes all requested neutral angles, face/scalp/hands/feet details, protected adult views, knee tests at 30/55/80 degrees, seated contact, a supine support foundation, an eating/reach foundation, and finger movement evidence.",
                "",
                "The attempt-05 pelvic/perineal component remains visibly rejected: a hard superior seam and recessed trapezoid/panel are still legible. This package does not conceal or promote that defect.",
                "Exact intersection and body-to-nail reports are per pose in `exact_intersections/` and `BUILD_EVIDENCE.json`; any nonzero result is evidence, not a pass.",
                "The warm-brown iris correction preserves iris geometry/UV/rig and leaves pupils, cornea, and sclera unchanged; the old unapproved v3.2 eye geometry is not imported.",
                "No scalp hair, clothing, GLB, live runtime assignment, activation, publication, or upload is present.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    checkpoint_path = output_dir / "CHECKPOINT.md"
    checkpoint_path.write_text(
        "\n".join(
            [
                "# Kira R19 bald private assembly checkpoint",
                "",
                f"Created UTC: `{evidence['created_utc']}`",
                f"Candidate: `{config['candidate_id']}`",
                f"Blend: `{project_relative(blend_path)}`",
                f"Blend SHA-256: `{sha256_file(blend_path)}`",
                f"Build evidence: `{project_relative(evidence_path)}`",
                f"Build evidence SHA-256 before manifest: `{sha256_file(evidence_path)}`",
                "",
                "The package is private, inactive, unassigned, unpublished, and not runtime eligible.",
                "The attempt-05 pelvic superior-seam/recessed-trapezoid visual rejection remains controlling.",
                "Rollback instructions are in `ROLLBACK.md`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = write_manifest(output_dir)
    print(
        json.dumps(
            {
                "ok": True,
                "status": evidence["status"],
                "output_dir": project_relative(output_dir),
                "blend_sha256": sha256_file(blend_path),
                "evidence_sha256": sha256_file(evidence_path),
                "checkpoint_sha256": sha256_file(checkpoint_path),
                "manifest_sha256": sha256_file(manifest_path),
                "render_count": len(render_evidence),
                "pose_exact_body_intersection_counts": pose_intersection_counts,
                "pose_exact_body_nail_intersection_counts": nail_intersection_counts,
                "pelvic_component_visual_acceptance": False,
                "owner_approval": False,
                "runtime_eligibility": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def preserve_failure(
    config: dict[str, Any],
    config_path: Path,
    exc: BaseException,
) -> None:
    output_dir = (PROJECT_ROOT / str(config.get("output_dir", "RecoverySprint/continuation_20260802/kira_r19_bald_owner_review/attempt_01"))).resolve()
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=False)
    failure_path = output_dir / "FAILURE_EVIDENCE.json"
    if failure_path.exists():
        return
    write_json(
        failure_path,
        {
            "schema_version": 1,
            "status": "FAILED_BEFORE_PRIVATE_OWNER_REVIEW_ASSEMBLY_COMPLETION",
            "created_utc": utc_now(),
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
            "config": project_relative(config_path),
            "config_sha256": sha256_file(config_path),
            "worker": project_relative(Path(__file__).resolve()),
            "worker_sha256": sha256_file(Path(__file__).resolve()),
            "earlier_attempts_modified": False,
            "runtime_or_assignment_changed": False,
            "owner_approval_claimed": False,
        },
    )
    write_manifest(output_dir)


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["_config_path"] = str(config_path)
    try:
        config, paths = load_config(config_path)
        config["_config_path"] = str(config_path)
        preflight = preflight_records(config, paths)
        if args.preflight_only:
            print(json.dumps({"ok": True, "preflight_only": True, **preflight}, indent=2, sort_keys=True))
            return 0
        return run_assembly(config_path, config, paths, preflight)
    except BaseException as exc:
        if not args.preflight_only:
            preserve_failure(config, config_path, exc)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
