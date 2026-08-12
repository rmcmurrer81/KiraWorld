"""V3r30 sealed Stage-2 Blender worker template.

This file has no authority by itself.  It may run only as the exact child of a
materialized, Audit-B-pinned native anchor.  Stage 1 and Audit A cannot invoke
it.  A successful future run creates only normalized clinical reference
proxies, never Kira's body or functional anatomy.
"""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import zlib

import bpy
from mathutils import Vector


STAGE2_ROOT = Path(r"C:\Users\robmc\Kira\RecoverySprint\continuation_20260811\kira_r25_medical_reference_proxy_v3r30_stage2\attempt_01")
WORKER_PATH = STAGE2_ROOT / "blender_worker_v3r30.py"
SPEC_PATH = STAGE2_ROOT / "PROXY_SPEC.json"
FRAME_PATH = STAGE2_ROOT / "NORMALIZED_REFERENCE_FRAME.json"
LEDGER_PATH = STAGE2_ROOT / "V3R30_ATTEMPT_OUTCOME_RECEIPT.bin"
OUTPUT_ROOT = STAGE2_ROOT / "outputs" / "worker_staging"
BLEND_PATH = OUTPUT_ROOT / "kira_v3r30_normalized_pelvic_core_reference_proxy.blend"
RESULT_PATH = OUTPUT_ROOT / "WORKER_RESULT.json"
RECEIPT_PATH = OUTPUT_ROOT / "WORKER_RECEIPT.tsv"
RENDER_PATHS = {
    "front_clinical": OUTPUT_ROOT / "front_clinical.png",
    "right_clinical": OUTPUT_ROOT / "right_clinical.png",
    "iso_clinical": OUTPUT_ROOT / "iso_clinical.png",
    "iso_xray": OUTPUT_ROOT / "iso_xray.png",
}
EXPECTED_STAGING_PATHS = (
    BLEND_PATH,
    RENDER_PATHS["front_clinical"],
    RENDER_PATHS["right_clinical"],
    RENDER_PATHS["iso_clinical"],
    RENDER_PATHS["iso_xray"],
    RESULT_PATH,
    RECEIPT_PATH,
)
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
EXPECTED_VERSION = "5.1.2"
ROLE = "NORMALIZED_CLINICAL_REFERENCE_PROXY_NOT_LIVE_BODY"
SEALED_SPEC_SHA256 = "60ad9beca7e2869fbf3ba914a535f0c288fc48e3190fe6e71539b1585c7c3bec"
SEALED_FRAME_SHA256 = "1edc43eb1760316f8242244783ba3c1c2ba930893e0ac5043e99f8430329256e"
EXPECTED_MATERIALS = {
    "clinical_bone_envelope": ((0.72, 0.70, 0.62, 0.28), 0.55),
    "clinical_urinary": ((0.93, 0.69, 0.22, 0.82), 0.55),
    "clinical_reproductive": ((0.68, 0.20, 0.32, 0.86), 0.55),
    "clinical_connections": ((0.84, 0.34, 0.48, 0.90), 0.55),
    "clinical_digestive_reference": ((0.43, 0.26, 0.16, 0.75), 0.55),
    "clinical_external_reference": ((0.56, 0.32, 0.38, 0.32), 0.55),
}
EXPECTED_COMPONENT_BINDINGS = {
    "pelvic_reference_envelope": ("TORUS", ("mri_pelvis_cc_by", "female_repro_urinary_cc_by"), "clinical_bone_envelope"),
    "bladder_proxy": ("UV_SPHERE", ("mri_pelvis_cc_by", "female_repro_urinary_cc_by"), "clinical_urinary"),
    "uterus_proxy": ("UV_SPHERE", ("mri_pelvis_cc_by", "female_repro_urinary_cc_by"), "clinical_reproductive"),
    "uterine_tube_left_proxy": ("BEZIER_MESH", ("mri_pelvis_cc_by", "female_repro_urinary_cc_by"), "clinical_connections"),
    "uterine_tube_right_proxy": ("BEZIER_MESH", ("mri_pelvis_cc_by", "female_repro_urinary_cc_by"), "clinical_connections"),
    "ovary_left_proxy": ("UV_SPHERE", ("mri_pelvis_cc_by", "female_repro_urinary_cc_by"), "clinical_reproductive"),
    "ovary_right_proxy": ("UV_SPHERE", ("mri_pelvis_cc_by", "female_repro_urinary_cc_by"), "clinical_reproductive"),
    "rectum_reference_proxy": ("BEZIER_MESH", ("mri_pelvis_cc_by",), "clinical_digestive_reference"),
    "vulvar_region_reference_proxy": ("UV_SPHERE", ("mri_pelvis_cc_by",), "clinical_external_reference"),
}
EXPECTED_RELATIONS = (
    "bladder_proxy.y > uterus_proxy.y",
    "rectum_reference_proxy.y < uterus_proxy.y",
    "ovary_left_proxy.x < uterus_proxy.x < ovary_right_proxy.x",
    "abs(ovary_left_proxy.x + ovary_right_proxy.x) <= 0.000001",
    "abs(ovary_left_proxy.y - ovary_right_proxy.y) <= 0.000001",
    "abs(ovary_left_proxy.z - ovary_right_proxy.z) <= 0.000001",
    "vulvar_region_reference_proxy.z < uterus_proxy.z",
    "all_proxy_bounds_inside_normalized_outer_clearance",
)
EXPECTED_FORBIDDEN = ("parent", "modifiers", "constraints", "animation_data", "library", "override_library", "vertex_groups", "shape_keys")
EXPECTED_TRUTH_TAGS = {
    "kira_v3r30_role": ROLE,
    "functional_organ": False,
    "approved_for_activation": False,
    "kira_fitted": False,
    "source_topology_copied": False,
}
EXPECTED_CAMERAS = {
    "front_clinical": (0.0, 1.55, 0.1),
    "right_clinical": (1.55, 0.0, 0.1),
    "iso_clinical": (1.2, 1.35, 0.85),
    "iso_xray": (-1.2, 1.35, 0.85),
}
ALLOWED_BPY_OPS = (
    "mesh.primitive_torus_add",
    "mesh.primitive_uv_sphere_add",
    "object.camera_add",
    "object.convert",
    "object.delete",
    "object.light_add",
    "object.select_all",
    "object.transform_apply",
    "render.render",
    "wm.open_mainfile",
    "wm.save_as_mainfile",
)


class Refuse(RuntimeError):
    pass


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reject_constant(value: str) -> None:
    raise Refuse("nonfinite_json:" + value)


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise Refuse("duplicate_json_key:" + key)
        result[key] = value
    return result


def strict_json_bytes(raw: bytes, label: str) -> dict[str, object]:
    if b"\r" in raw or b"\0" in raw or not raw.endswith(b"\n"):
        raise Refuse(label + ":encoding")
    value = json.loads(
        raw.decode("utf-8"),
        parse_constant=reject_constant,
        object_pairs_hook=unique_object,
    )
    if not isinstance(value, dict):
        raise Refuse(label + ":object")
    return value


def strict_json_path(path: Path, expected_sha256: str, label: str) -> dict[str, object]:
    if not path.is_file() or not path.resolve().is_relative_to(STAGE2_ROOT.resolve()):
        raise Refuse(label + ":path")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise Refuse(label + ":sha256")
    return strict_json_bytes(raw, label)


def finite_vector(value: object, label: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise Refuse(label + ":shape")
    result = tuple(float(part) for part in value)
    if not all(math.isfinite(part) for part in result):
        raise Refuse(label + ":finite")
    return result


def parse_args() -> argparse.Namespace:
    if "--" not in sys.argv:
        raise Refuse("missing_worker_separator")
    tail = sys.argv[sys.argv.index("--") + 1 :]
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--capability", required=True)
    parser.add_argument("--capability-sha256", required=True)
    values, extras = parser.parse_known_args(tail)
    if extras or len(values.capability_sha256) != 64 or values.capability_sha256.lower() != values.capability_sha256:
        raise Refuse("worker_arguments")
    if not all(char in "0123456789abcdef" for char in values.capability_sha256):
        raise Refuse("capability_digest_grammar")
    return values


def load_capability(args: argparse.Namespace) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    path = Path(args.capability)
    expected = STAGE2_ROOT / "V3R30_NATIVE_CAPABILITY.json"
    if path.resolve() != expected.resolve() or not path.is_file():
        raise Refuse("capability_path")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.capability_sha256:
        raise Refuse("capability_sha256")
    capability = strict_json_bytes(raw, "capability")
    expected_keys = {
        "schema", "state", "nonce", "native_parent_pid", "stage1_package_root",
        "audit_a_sha256", "worker_sha256", "spec_sha256", "frame_sha256",
        "output_root", "blend_path", "result_path", "receipt_path", "render_paths",
        "staging_count", "staging_pre_reserved", "staging_single_link",
    }
    if set(capability) != expected_keys:
        raise Refuse("capability_keys")
    if capability["schema"] != "kira.r25.medical_reference_proxy.v3r30.native_capability.v1" or capability["state"] != "PENDING_CONSUMED":
        raise Refuse("capability_schema_state")
    nonce = capability["nonce"]
    if not isinstance(nonce, str) or re_full_hex(nonce, 64) is False:
        raise Refuse("capability_nonce")
    for key in ("stage1_package_root", "audit_a_sha256", "worker_sha256", "spec_sha256", "frame_sha256"):
        if not isinstance(capability[key], str) or not re_full_hex(capability[key], 64):
            raise Refuse("capability_digest:" + key)
    if capability["spec_sha256"] != SEALED_SPEC_SHA256 or capability["frame_sha256"] != SEALED_FRAME_SHA256:
        raise Refuse("capability_sealed_spec_or_frame")
    if int(capability["native_parent_pid"]) <= 0 or os.getppid() != int(capability["native_parent_pid"]):
        raise Refuse("native_parent_pid")
    if sha256_path(WORKER_PATH) != capability["worker_sha256"]:
        raise Refuse("worker_self_identity")
    if Path(str(capability["output_root"])).resolve() != OUTPUT_ROOT.resolve():
        raise Refuse("output_root")
    if Path(str(capability["blend_path"])).resolve() != BLEND_PATH.resolve() or Path(str(capability["result_path"])).resolve() != RESULT_PATH.resolve():
        raise Refuse("output_paths")
    if Path(str(capability["receipt_path"])).resolve() != RECEIPT_PATH.resolve():
        raise Refuse("receipt_path")
    if capability["render_paths"] != {key: str(value) for key, value in RENDER_PATHS.items()}:
        raise Refuse("render_paths")
    if (type(capability["staging_count"]) is not int
            or capability["staging_count"] != len(EXPECTED_STAGING_PATHS)
            or capability["staging_pre_reserved"] is not True
            or capability["staging_single_link"] is not True):
        raise Refuse("staging_reservation_claim")
    if not LEDGER_PATH.is_file() or LEDGER_PATH.stat().st_size != 4096:
        raise Refuse("native_ledger_absent")
    spec = strict_json_path(SPEC_PATH, str(capability["spec_sha256"]), "spec")
    frame = strict_json_path(FRAME_PATH, str(capability["frame_sha256"]), "frame")
    return capability, spec, frame


def re_full_hex(value: str, length: int) -> bool:
    return len(value) == length and value.lower() == value and all(char in "0123456789abcdef" for char in value)


def exact_identity(path: Path, label: str, *, require_empty: bool = False) -> tuple[int, int]:
    try:
        info = path.stat(follow_symlinks=False)
    except (FileNotFoundError, OSError) as error:
        raise Refuse(label + ":stat") from error
    if (path.is_symlink()
            or (getattr(info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT) != 0
            or not path.is_file()
            or int(info.st_nlink) != 1):
        raise Refuse(label + ":type_reparse_or_link_count")
    if require_empty and int(info.st_size) != 0:
        raise Refuse(label + ":not_empty")
    return int(info.st_dev), int(info.st_ino)


def validate_pre_reserved_outputs() -> dict[Path, tuple[int, int]]:
    try:
        root_info = OUTPUT_ROOT.stat(follow_symlinks=False)
    except (FileNotFoundError, OSError) as error:
        raise Refuse("worker_output_root_absent") from error
    if (not OUTPUT_ROOT.is_dir()
            or OUTPUT_ROOT.is_symlink()
            or (getattr(root_info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT) != 0):
        raise Refuse("worker_output_root_type_or_reparse")
    identities: dict[Path, tuple[int, int]] = {}
    for index, path in enumerate(EXPECTED_STAGING_PATHS):
        identities[path] = exact_identity(path, f"staging_{index}", require_empty=True)
    if len(set(identities.values())) != len(EXPECTED_STAGING_PATHS):
        raise Refuse("staging_identity_alias")
    return identities


def validate_reserved_identity(
    path: Path,
    expected: tuple[int, int],
    label: str,
    *,
    minimum_bytes: int | None = None,
) -> int:
    current = exact_identity(path, label)
    if current != expected:
        raise Refuse(label + ":identity_changed")
    size = int(path.stat(follow_symlinks=False).st_size)
    if minimum_bytes is not None and size < minimum_bytes:
        raise Refuse(label + ":too_small")
    return size


def validate_frame(frame: dict[str, object]) -> dict[str, tuple[float, float, float]]:
    if set(frame) != {"schema", "status", "units", "origin", "axis", "landmarks", "gates", "cameras", "truth"}:
        raise Refuse("frame_top_keys")
    if frame.get("schema") != "kira.r25.medical_reference_proxy.v3r30.normalized_reference_frame.v1" or frame.get("status") != "NORMALIZED_REFERENCE_ONLY_NOT_KIRA_MEASUREMENT_NOT_BODY":
        raise Refuse("frame_schema_status")
    if (frame.get("units") != "normalized_reference_units"
            or finite_vector(frame.get("origin"), "frame_origin") != (0.0, 0.0, 0.0)
            or frame.get("truth") != "These are synthetic normalized placement anchors. They are not measured Kira landmarks and do not establish Kira dimensions or fit."):
        raise Refuse("frame_origin_units_truth")
    if frame.get("axis") != {"positive_x": "anatomical_right", "positive_y": "anatomical_anterior", "positive_z": "anatomical_superior"}:
        raise Refuse("frame_axis")
    landmarks_raw = frame.get("landmarks")
    if not isinstance(landmarks_raw, dict):
        raise Refuse("landmark_object")
    expected_names = {
        "pelvis_left_lateral_anchor", "pelvis_right_lateral_anchor",
        "pubic_anterior_anchor", "sacral_posterior_anchor",
        "pelvic_floor_anchor", "pelvic_inlet_superior_anchor",
        "outer_shell_anterior_clearance", "outer_shell_posterior_clearance",
    }
    if set(landmarks_raw) != expected_names:
        raise Refuse("landmark_names")
    expected_gates = {
        "exact_landmark_count": 8,
        "all_coordinates_finite": True,
        "left_x_less_than_right_x": True,
        "pubic_y_greater_than_sacral_y": True,
        "floor_z_less_than_inlet_z": True,
        "anterior_clearance_y_greater_than_pubic_y": True,
        "posterior_clearance_y_less_than_sacral_y": True,
        "bilateral_midpoint_equals_origin_tolerance": 1e-9,
        "minimum_pelvis_width": 0.99,
        "minimum_pelvis_depth": 0.99,
        "kira_height_required": False,
        "kira_outer_shell_required": False,
    }
    if frame.get("gates") != expected_gates:
        raise Refuse("landmark_gate_declaration")
    landmarks = {name: finite_vector(value, "landmark:" + name) for name, value in landmarks_raw.items()}
    left = landmarks["pelvis_left_lateral_anchor"]
    right = landmarks["pelvis_right_lateral_anchor"]
    pubic = landmarks["pubic_anterior_anchor"]
    sacral = landmarks["sacral_posterior_anchor"]
    floor = landmarks["pelvic_floor_anchor"]
    inlet = landmarks["pelvic_inlet_superior_anchor"]
    anterior = landmarks["outer_shell_anterior_clearance"]
    posterior = landmarks["outer_shell_posterior_clearance"]
    if not (left[0] < right[0] and right[0] - left[0] >= 0.99):
        raise Refuse("landmark_left_right")
    if not (pubic[1] > sacral[1] and pubic[1] - sacral[1] >= 0.99):
        raise Refuse("landmark_anterior_posterior")
    if not floor[2] < inlet[2]:
        raise Refuse("landmark_floor_inlet")
    if not (anterior[1] > pubic[1] and posterior[1] < sacral[1]):
        raise Refuse("landmark_outer_clearance")
    midpoint = tuple((left[index] + right[index]) / 2.0 for index in range(3))
    if any(abs(value) > 1e-9 for value in midpoint):
        raise Refuse("landmark_midpoint")
    cameras = frame.get("cameras")
    if not isinstance(cameras, dict) or set(cameras) != set(RENDER_PATHS):
        raise Refuse("camera_names")
    camera_values = {name: finite_vector(value, "camera:" + name) for name, value in cameras.items()}
    if (camera_values != EXPECTED_CAMERAS or camera_values["front_clinical"][1] <= 0
            or camera_values["right_clinical"][0] <= 0):
        raise Refuse("camera_anatomical_axis")
    return camera_values


def external_paths() -> list[str]:
    found: list[str] = []
    for library in bpy.data.libraries:
        found.append("library:" + str(library.filepath))
    for label in ("images", "movieclips", "sounds", "fonts", "volumes", "cache_files"):
        collection = getattr(bpy.data, label, ())
        for item in collection:
            filepath = str(getattr(item, "filepath", ""))
            if filepath and filepath not in {"<builtin>", "Bfont"}:
                found.append(label + ":" + filepath)
    return found


def validate_factory_runtime() -> None:
    if not bpy.app.background or bpy.app.version_string != EXPECTED_VERSION:
        raise Refuse("blender_background_or_version")
    if bpy.data.filepath != "" or external_paths():
        raise Refuse("factory_input_or_external_dependency")
    observed = {(obj.name, obj.type) for obj in bpy.data.objects}
    if observed != {("Camera", "CAMERA"), ("Cube", "MESH"), ("Light", "LIGHT")}:
        raise Refuse("factory_startup_objects")
    if len(bpy.data.scenes) != 1 or len(bpy.data.collections) != 1 or len(bpy.data.meshes) != 1 or len(bpy.data.cameras) != 1 or len(bpy.data.lights) != 1:
        raise Refuse("factory_startup_datablocks")
    if bpy.data.armatures or bpy.data.actions or bpy.data.materials or bpy.data.images or bpy.data.libraries:
        raise Refuse("factory_startup_forbidden_data")


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in tuple(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for label in ("meshes", "curves", "cameras", "lights", "materials", "images"):
        collection = getattr(bpy.data, label)
        for item in tuple(collection):
            collection.remove(item)
    if bpy.data.objects or bpy.data.collections or bpy.data.meshes or bpy.data.curves or bpy.data.cameras or bpy.data.lights or bpy.data.materials or bpy.data.images or external_paths():
        raise Refuse("reset_not_empty")
    collection = bpy.data.collections.new("V3r30_Normalized_Pelvic_Core_Reference_Proxy")
    bpy.context.scene.collection.children.link(collection)
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[collection.name]


def new_material(name: str, values: dict[str, object]) -> bpy.types.Material:
    rgba = tuple(float(value) for value in values["rgba"])
    roughness = float(values["roughness"])
    if len(rgba) != 4 or not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in rgba) or not 0.0 <= roughness <= 1.0:
        raise Refuse("material_spec:" + name)
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    node = material.node_tree.nodes.get("Principled BSDF")
    if node is None:
        raise Refuse("principled_node:" + name)
    node.inputs["Base Color"].default_value = rgba
    node.inputs["Roughness"].default_value = roughness
    node.inputs["Alpha"].default_value = rgba[3]
    if rgba[3] < 1.0:
        material.surface_render_method = "DITHERED"
    return material


def tag_proxy(obj: bpy.types.Object, row: dict[str, object]) -> None:
    obj.name = str(row["id"])
    obj["kira_v3r30_role"] = ROLE
    obj["component_id"] = str(row["id"])
    obj["primitive_contract"] = str(row["primitive"])
    obj["attribution_reference_ids"] = ";".join(str(value) for value in row["sources"])
    obj["functional_organ"] = False
    obj["approved_for_activation"] = False
    obj["kira_fitted"] = False
    obj["source_topology_copied"] = False


def add_sphere(row: dict[str, object], scale: tuple[float, float, float], material: bpy.types.Material) -> bpy.types.Object:
    location = finite_vector(row["location"], "location:" + str(row["id"]))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1.0, location=location)
    obj = bpy.context.object
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.data.materials.append(material)
    tag_proxy(obj, row)
    return obj


def add_curve(row: dict[str, object], points: tuple[tuple[float, float, float], ...], radius: float, material: bpy.types.Material) -> bpy.types.Object:
    curve = bpy.data.curves.new(str(row["id"]) + "_curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for control, point in zip(spline.bezier_points, points):
        control.co = point
        control.handle_left_type = "AUTO"
        control.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(str(row["id"]), curve)
    bpy.data.collections["V3r30_Normalized_Pelvic_Core_Reference_Proxy"].objects.link(obj)
    obj.data.materials.append(material)
    tag_proxy(obj, row)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)
    for orphan in tuple(bpy.data.curves):
        if orphan.users == 0:
            bpy.data.curves.remove(orphan)
    if bpy.data.curves:
        raise Refuse("curve_conversion_residue:" + str(row["id"]))
    return obj


def validate_interval(value: object, label: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise Refuse(label + ":shape")
    low, high = float(value[0]), float(value[1])
    if not (math.isfinite(low) and math.isfinite(high) and low < high):
        raise Refuse(label + ":finite_order")
    return low, high


def validate_spec_contract(spec: dict[str, object]) -> None:
    expected_top_keys = {
        "schema", "status", "object_count_exact", "material_count_exact",
        "total_vertex_maximum", "coordinate_tolerance", "dimension_tolerance",
        "materials", "objects", "relations", "forbidden_per_object", "truth_tags",
    }
    if set(spec) != expected_top_keys:
        raise Refuse("spec_top_keys")
    if (spec["schema"] != "kira.r25.medical_reference_proxy.v3r30.proxy_spec.v1"
            or spec["status"] != "EXACT_NORMALIZED_CLINICAL_PROXY_SPEC_NOT_BODY"
            or spec["object_count_exact"] != 9 or spec["material_count_exact"] != 6
            or spec["total_vertex_maximum"] != 12000
            or float(spec["coordinate_tolerance"]) != 1e-6
            or float(spec["dimension_tolerance"]) != 0.003
            or tuple(spec["relations"]) != EXPECTED_RELATIONS
            or tuple(spec["forbidden_per_object"]) != EXPECTED_FORBIDDEN
            or spec["truth_tags"] != EXPECTED_TRUTH_TAGS):
        raise Refuse("spec_exact_contract")
    materials = spec["materials"]
    if not isinstance(materials, dict) or set(materials) != set(EXPECTED_MATERIALS):
        raise Refuse("spec_material_names")
    for name, (expected_rgba, expected_roughness) in EXPECTED_MATERIALS.items():
        row = materials[name]
        if not isinstance(row, dict) or set(row) != {"rgba", "roughness"}:
            raise Refuse("spec_material_shape:" + name)
        rgba = tuple(float(value) for value in row["rgba"])
        if (len(rgba) != 4 or not all(math.isfinite(value) for value in rgba)
                or any(abs(value - expected) > 1e-12 for value, expected in zip(rgba, expected_rgba))
                or abs(float(row["roughness"]) - expected_roughness) > 1e-12):
            raise Refuse("spec_material_value:" + name)
    object_rows = spec["objects"]
    if not isinstance(object_rows, list) or len(object_rows) != 9 or not all(isinstance(row, dict) for row in object_rows):
        raise Refuse("spec_object_rows")
    rows = {str(row.get("id")): row for row in object_rows}
    if set(rows) != set(EXPECTED_COMPONENT_BINDINGS) or len(rows) != len(object_rows):
        raise Refuse("spec_object_ids")
    for component_id, (primitive, sources, material) in EXPECTED_COMPONENT_BINDINGS.items():
        row = rows[component_id]
        location_based = primitive in {"TORUS", "UV_SPHERE"}
        expected_keys = {"id", "primitive", "sources", "material", "vertex_interval"}
        expected_keys |= {"location", "dimensions_interval"} if location_based else {"location_interval", "dimension_interval"}
        if set(row) != expected_keys or row["primitive"] != primitive or tuple(row["sources"]) != sources or row["material"] != material:
            raise Refuse("spec_component_binding:" + component_id)
        vertex_low, vertex_high = validate_interval(row["vertex_interval"], "spec_vertex_interval:" + component_id)
        if not vertex_low.is_integer() or not vertex_high.is_integer() or vertex_low < 4 or vertex_high > 12000:
            raise Refuse("spec_vertex_bounds:" + component_id)
        if location_based:
            finite_vector(row["location"], "spec_location:" + component_id)
            intervals = row["dimensions_interval"]
        else:
            intervals = row["dimension_interval"]
            locations = row["location_interval"]
            if not isinstance(locations, list) or len(locations) != 3:
                raise Refuse("spec_location_intervals:" + component_id)
            for index, value in enumerate(locations):
                validate_interval(value, f"spec_location_interval:{component_id}:{index}")
        if not isinstance(intervals, list) or len(intervals) != 3:
            raise Refuse("spec_dimension_intervals:" + component_id)
        for index, value in enumerate(intervals):
            low, _ = validate_interval(value, f"spec_dimension_interval:{component_id}:{index}")
            if low <= 0.0:
                raise Refuse("spec_positive_dimension:" + component_id)


def build_scene(spec: dict[str, object]) -> None:
    validate_spec_contract(spec)
    material_rows = spec.get("materials")
    object_rows = spec.get("objects")
    if not isinstance(material_rows, dict) or len(material_rows) != 6 or not isinstance(object_rows, list) or len(object_rows) != 9:
        raise Refuse("spec_counts")
    materials = {name: new_material(name, values) for name, values in material_rows.items()}
    rows = {str(row["id"]): row for row in object_rows}
    if len(rows) != 9:
        raise Refuse("spec_duplicate_object")
    pelvis_row = rows["pelvic_reference_envelope"]
    bpy.ops.mesh.primitive_torus_add(major_radius=0.42, minor_radius=0.025, major_segments=24, minor_segments=6, location=(0.0, 0.0, 0.0))
    pelvis = bpy.context.object
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    pelvis.data.materials.append(materials[str(pelvis_row["material"])])
    tag_proxy(pelvis, pelvis_row)
    add_sphere(rows["bladder_proxy"], (0.11, 0.095, 0.050), materials["clinical_urinary"])
    add_sphere(rows["uterus_proxy"], (0.095, 0.070, 0.052), materials["clinical_reproductive"])
    add_sphere(rows["ovary_left_proxy"], (0.045, 0.030, 0.020), materials["clinical_reproductive"])
    add_sphere(rows["ovary_right_proxy"], (0.045, 0.030, 0.020), materials["clinical_reproductive"])
    add_curve(rows["uterine_tube_left_proxy"], ((-0.06, 0.035, 0.060), (-0.15, 0.045, 0.082), (-0.23, 0.030, 0.050)), 0.009, materials["clinical_connections"])
    add_curve(rows["uterine_tube_right_proxy"], ((0.06, 0.035, 0.060), (0.15, 0.045, 0.082), (0.23, 0.030, 0.050)), 0.009, materials["clinical_connections"])
    add_curve(rows["rectum_reference_proxy"], ((0.0, -0.27, 0.085), (0.0, -0.30, 0.0), (0.0, -0.25, -0.075)), 0.025, materials["clinical_digestive_reference"])
    add_sphere(rows["vulvar_region_reference_proxy"], (0.055, 0.025, 0.018), materials["clinical_external_reference"])


def interval_contains(interval: object, value: float, label: str) -> None:
    if not isinstance(interval, list) or len(interval) != 2:
        raise Refuse(label + ":interval")
    low, high = float(interval[0]), float(interval[1])
    if not (math.isfinite(low) and math.isfinite(high) and low <= value <= high):
        raise Refuse(label + ":outside")


def world_bounds(obj: bpy.types.Object) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    if not points:
        raise Refuse("empty_mesh:" + obj.name)
    low = tuple(min(point[index] for point in points) for index in range(3))
    high = tuple(max(point[index] for point in points) for index in range(3))
    if not all(math.isfinite(value) for value in (*low, *high)):
        raise Refuse("nonfinite_mesh:" + obj.name)
    return low, high


def validate_material(material: bpy.types.Material, name: str, row: dict[str, object]) -> None:
    if (material.name != name or not material.use_nodes or material.library is not None
            or material.override_library is not None or material.keys()):
        raise Refuse("material_identity:" + name)
    if set(node.name for node in material.node_tree.nodes) != {"Principled BSDF", "Material Output"} or len(material.node_tree.links) != 1:
        raise Refuse("material_node_closure:" + name)
    node = material.node_tree.nodes.get("Principled BSDF")
    if node is None:
        raise Refuse("material_node:" + name)
    actual_rgba = tuple(float(value) for value in node.inputs["Base Color"].default_value)
    expected_rgba = tuple(float(value) for value in row["rgba"])
    if any(abs(a - b) > 1e-6 for a, b in zip(actual_rgba, expected_rgba)):
        raise Refuse("material_rgba:" + name)
    if abs(float(node.inputs["Roughness"].default_value) - float(row["roughness"])) > 1e-6:
        raise Refuse("material_roughness:" + name)
    if abs(float(node.inputs["Alpha"].default_value) - expected_rgba[3]) > 1e-6:
        raise Refuse("material_alpha:" + name)
    if expected_rgba[3] < 1.0 and material.surface_render_method != "DITHERED":
        raise Refuse("material_render_method:" + name)


def validate_topology_values(vertex_count: int, edge_pairs: list[tuple[int, int]],
                             polygon_areas: list[float], coordinates: list[tuple[float, float, float]],
                             component_id: str) -> None:
    if vertex_count < 4 or len(coordinates) != vertex_count or not edge_pairs or not polygon_areas:
        raise Refuse("mesh_empty:" + component_id)
    adjacency: list[set[int]] = [set() for _ in range(vertex_count)]
    for first, second in edge_pairs:
        if first == second or not (0 <= first < vertex_count and 0 <= second < vertex_count):
            raise Refuse("mesh_bad_edge:" + component_id)
        adjacency[first].add(second)
        adjacency[second].add(first)
    if any(not neighbors for neighbors in adjacency):
        raise Refuse("mesh_loose_vertex:" + component_id)
    visited = {0}
    frontier = [0]
    while frontier:
        current = frontier.pop()
        for neighbor in adjacency[current] - visited:
            visited.add(neighbor)
            frontier.append(neighbor)
    if len(visited) != vertex_count:
        raise Refuse("mesh_disconnected:" + component_id)
    if any(not math.isfinite(area) or area <= 1e-12 for area in polygon_areas):
        raise Refuse("mesh_degenerate_face:" + component_id)
    if any(len(coordinate) != 3 or not all(math.isfinite(value) for value in coordinate) for coordinate in coordinates):
        raise Refuse("mesh_nonfinite_vertex:" + component_id)


def validate_mesh_topology(obj: bpy.types.Object, component_id: str) -> None:
    validate_topology_values(
        len(obj.data.vertices),
        [tuple(int(value) for value in edge.vertices) for edge in obj.data.edges],
        [float(polygon.area) for polygon in obj.data.polygons],
        [tuple(float(value) for value in vertex.co) for vertex in obj.data.vertices],
        component_id,
    )


def forbid_unexpected_datablocks() -> None:
    for label in (
        "armatures", "actions", "curves", "grease_pencils_v3", "hair_curves",
        "lattices", "metaballs", "movieclips", "node_groups", "paint_curves",
        "pointclouds", "sounds", "speakers", "texts", "textures", "volumes",
    ):
        collection = getattr(bpy.data, label, ())
        if len(collection):
            raise Refuse("unexpected_datablock:" + label)


def validate_spatial_relations(bounds: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]]) -> None:
    if set(bounds) != set(EXPECTED_COMPONENT_BINDINGS):
        raise Refuse("relation_inventory")
    centers = {
        name: tuple((low[index] + high[index]) / 2.0 for index in range(3))
        for name, (low, high) in bounds.items()
    }
    if not centers["bladder_proxy"][1] > centers["uterus_proxy"][1]:
        raise Refuse("relation_bladder_anterior")
    if not centers["rectum_reference_proxy"][1] < centers["uterus_proxy"][1]:
        raise Refuse("relation_rectum_posterior")
    left, uterus, right = centers["ovary_left_proxy"], centers["uterus_proxy"], centers["ovary_right_proxy"]
    if not left[0] < uterus[0] < right[0] or abs(left[0] + right[0]) > 1e-6 or abs(left[1] - right[1]) > 1e-6 or abs(left[2] - right[2]) > 1e-6:
        raise Refuse("relation_ovary_bilateral")
    if not centers["vulvar_region_reference_proxy"][2] < centers["uterus_proxy"][2]:
        raise Refuse("relation_vulvar_below_uterus")
    for component_id, (low, high) in bounds.items():
        if any(not math.isfinite(value) for value in (*low, *high)) or any(low[index] >= high[index] for index in range(3)):
            raise Refuse("relation_nonfinite_or_degenerate_bounds:" + component_id)
        if low[0] < -0.62 or high[0] > 0.62 or low[1] < -0.62 or high[1] > 0.62 or low[2] < -0.12 or high[2] > 0.12:
            raise Refuse("relation_outer_clearance:" + component_id)


def validate_proxy_scene(spec: dict[str, object], with_rig: bool) -> dict[str, object]:
    validate_spec_contract(spec)
    forbid_unexpected_datablocks()
    rows = {str(row["id"]): row for row in spec["objects"]}
    proxies = {obj.get("component_id"): obj for obj in bpy.data.objects if obj.get("kira_v3r30_role") == ROLE}
    if set(proxies) != set(rows) or len(proxies) != 9:
        raise Refuse("proxy_inventory")
    if len(bpy.data.materials) != 6 or set(material.name for material in bpy.data.materials) != set(spec["materials"]):
        raise Refuse("material_inventory")
    for name, material_row in spec["materials"].items():
        validate_material(bpy.data.materials[name], name, material_row)
    expected_material_users = {
        "clinical_bone_envelope": 1,
        "clinical_urinary": 1,
        "clinical_reproductive": 3,
        "clinical_connections": 2,
        "clinical_digestive_reference": 1,
        "clinical_external_reference": 1,
    }
    if any(bpy.data.materials[name].users != users for name, users in expected_material_users.items()):
        raise Refuse("material_user_counts")
    total_vertices = 0
    bounds: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {}
    evidence: dict[str, object] = {}
    for component_id, row in rows.items():
        obj = proxies[component_id]
        if obj.type != "MESH" or obj.library is not None or obj.override_library is not None:
            raise Refuse("proxy_type_or_library:" + component_id)
        if obj.parent is not None or obj.modifiers or obj.constraints or obj.animation_data is not None or obj.vertex_groups or obj.data.shape_keys is not None:
            raise Refuse("proxy_forbidden_attachment:" + component_id)
        if (tuple(collection.name for collection in obj.users_collection) != ("V3r30_Normalized_Pelvic_Core_Reference_Proxy",)
                or any(abs(float(value)) > 1e-8 for value in obj.delta_location)
                or any(abs(float(value)) > 1e-8 for value in obj.delta_rotation_euler)
                or any(abs(float(value) - 1.0) > 1e-8 for value in obj.delta_scale)):
            raise Refuse("proxy_collection_or_delta_transform:" + component_id)
        if len(obj.data.materials) != 1 or obj.data.materials[0].name != row["material"]:
            raise Refuse("proxy_material:" + component_id)
        expected_sources = ";".join(str(value) for value in row["sources"])
        expected_tags = {
            "kira_v3r30_role": ROLE,
            "component_id": component_id,
            "primitive_contract": row["primitive"],
            "attribution_reference_ids": expected_sources,
            "functional_organ": False,
            "approved_for_activation": False,
            "kira_fitted": False,
            "source_topology_copied": False,
        }
        if set(obj.keys()) != set(expected_tags) or any(obj.get(key) != value for key, value in expected_tags.items()):
            raise Refuse("proxy_truth_or_attribution:" + component_id)
        if obj.data.library is not None or obj.data.keys():
            raise Refuse("proxy_mesh_library_or_custom_data:" + component_id)
        if any(abs(float(value)) > 1e-8 for value in obj.rotation_euler) or any(abs(float(value) - 1.0) > 1e-8 for value in obj.scale):
            raise Refuse("proxy_unapplied_transform:" + component_id)
        vertices = len(obj.data.vertices)
        interval_contains(row["vertex_interval"], vertices, "vertices:" + component_id)
        if obj.data.users != 1 or any(int(polygon.material_index) != 0 for polygon in obj.data.polygons):
            raise Refuse("proxy_mesh_users_or_material_index:" + component_id)
        validate_mesh_topology(obj, component_id)
        total_vertices += vertices
        low, high = world_bounds(obj)
        center = tuple((low[index] + high[index]) / 2.0 for index in range(3))
        dimensions = tuple(high[index] - low[index] for index in range(3))
        bounds[component_id] = (low, high)
        if "location" in row:
            expected_location = finite_vector(row["location"], "expected_location:" + component_id)
            if any(abs(center[index] - expected_location[index]) > 0.003 for index in range(3)):
                raise Refuse("proxy_centroid:" + component_id)
            intervals = row["dimensions_interval"]
        else:
            for index, axis in enumerate("xyz"):
                interval_contains(row["location_interval"][index], center[index], "center_" + axis + ":" + component_id)
            intervals = row["dimension_interval"]
        for index, axis in enumerate("xyz"):
            interval_contains(intervals[index], dimensions[index], "dimension_" + axis + ":" + component_id)
        evidence[component_id] = {"vertices": vertices, "edges": len(obj.data.edges), "faces": len(obj.data.polygons), "center": center, "dimensions": dimensions, "material": row["material"], "sources": expected_sources}
    if total_vertices <= 0 or total_vertices > int(spec["total_vertex_maximum"]):
        raise Refuse("total_vertices")
    validate_spatial_relations(bounds)
    expected_objects = 12 if with_rig else 9
    if len(bpy.data.objects) != expected_objects or len(bpy.data.meshes) != 9 or bpy.data.curves or bpy.data.armatures or bpy.data.actions or bpy.data.images or bpy.data.libraries or external_paths():
        raise Refuse("scene_datablock_closure")
    if with_rig:
        scene = bpy.context.scene
        rig_objects = {obj.name: obj for obj in bpy.data.objects if obj.type in {"CAMERA", "LIGHT"}}
        if (len(bpy.data.cameras) != 1 or len(bpy.data.lights) != 2
                or set(rig_objects) != {"V3r30_Evidence_Camera", "V3r30_Key_Light", "V3r30_Fill_Light"}
                or rig_objects["V3r30_Evidence_Camera"].data.lens != 58.0
                or rig_objects["V3r30_Key_Light"].data.type != "AREA"
                or rig_objects["V3r30_Fill_Light"].data.type != "AREA"):
            raise Refuse("evidence_rig_inventory")
        for obj in rig_objects.values():
            if (obj.library is not None or obj.override_library is not None or obj.parent is not None
                    or obj.modifiers or obj.constraints or obj.animation_data is not None or obj.keys()
                    or obj.data.library is not None or obj.data.keys()):
                raise Refuse("evidence_rig_attachment_or_custom_data:" + obj.name)
        expected_scene_tags = {
            "kira_v3r30_truth": "ISOLATED_NORMALIZED_REFERENCE_PROXY_NOT_KIRA_BODY",
            "source_meshes_imported": False,
            "external_dependencies": 0,
            "live_avatar_linked": False,
            "rig_or_weights_present": False,
        }
        if (set(scene.keys()) != set(expected_scene_tags)
                or any(scene.get(key) != value for key, value in expected_scene_tags.items())
                or scene.camera != rig_objects["V3r30_Evidence_Camera"]
                or scene.render.engine != "BLENDER_EEVEE_NEXT"
                or (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage) != (640, 640, 100)
                or scene.render.image_settings.file_format != "PNG"
                or scene.render.image_settings.color_mode != "RGBA"
                or scene.render.film_transparent is not False
                or len(bpy.data.scenes) != 1 or len(bpy.data.collections) != 1
                or len(bpy.data.worlds) != 1 or scene.world not in bpy.data.worlds.values()
                or scene.world.library is not None):
            raise Refuse("scene_evidence_contract")
        camera = rig_objects["V3r30_Evidence_Camera"]
        expected_camera = Vector(EXPECTED_CAMERAS["iso_clinical"])
        forward = camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
        expected_forward = (-expected_camera).normalized()
        if ((camera.location - expected_camera).length > 1e-9
                or (forward.normalized() - expected_forward).length > 1e-8
                or not all(math.isfinite(float(value)) for row in camera.matrix_world for value in row)):
            raise Refuse("saved_camera_iso_pose")
    elif bpy.data.cameras or bpy.data.lights:
        raise Refuse("premature_evidence_rig")
    return {"proxy_objects": 9, "materials": 6, "vertices": total_vertices, "objects": evidence}


def configure_evidence_rig() -> bpy.types.Object:
    collection = bpy.data.collections["V3r30_Normalized_Pelvic_Core_Reference_Proxy"]
    bpy.ops.object.camera_add(location=(1.2, 1.35, 0.85))
    camera = bpy.context.object
    camera.name = "V3r30_Evidence_Camera"
    camera.data.lens = 58.0
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(0.8, 1.0, 1.2))
    key = bpy.context.object
    key.name = "V3r30_Key_Light"
    key.data.energy = 650
    key.data.shape = "DISK"
    key.data.size = 4.0
    bpy.ops.object.light_add(type="AREA", location=(-0.9, -0.6, 0.6))
    fill = bpy.context.object
    fill.name = "V3r30_Fill_Light"
    fill.data.energy = 350
    fill.data.size = 3.0
    if camera.users_collection != (collection,) or key.users_collection != (collection,) or fill.users_collection != (collection,):
        raise Refuse("evidence_rig_collection")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.world.color = (0.035, 0.035, 0.045)
    scene["kira_v3r30_truth"] = "ISOLATED_NORMALIZED_REFERENCE_PROXY_NOT_KIRA_BODY"
    scene["source_meshes_imported"] = False
    scene["external_dependencies"] = 0
    scene["live_avatar_linked"] = False
    scene["rig_or_weights_present"] = False
    point_camera(camera, EXPECTED_CAMERAS["iso_clinical"])
    return camera


def point_camera(camera: bpy.types.Object, location: tuple[float, float, float]) -> list[float]:
    camera.location = location
    camera.rotation_euler = (Vector((0.0, 0.0, 0.0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 58.0
    bpy.context.view_layer.update()
    matrix = [round(float(value), 9) for row in camera.matrix_world for value in row]
    expected_location = Vector(location)
    forward = camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    if ((camera.location - expected_location).length > 1e-9
            or (forward.normalized() - (-expected_location).normalized()).length > 1e-8
            or len(matrix) != 16 or not all(math.isfinite(value) for value in matrix)):
        raise Refuse("camera_view_matrix")
    return matrix


def parse_png(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    if len(raw) < 1024 or len(raw) > 64 * 1024 * 1024 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise Refuse("png_signature_or_size:" + path.name)
    offset = 8
    width = height = bit_depth = color_type = None
    compressed = bytearray()
    seen_iend = False
    ihdr_count = idat_count = iend_count = 0
    while offset < len(raw):
        if offset + 12 > len(raw):
            raise Refuse("png_truncated:" + path.name)
        length = struct.unpack(">I", raw[offset : offset + 4])[0]
        kind = raw[offset + 4 : offset + 8]
        data = raw[offset + 8 : offset + 8 + length]
        crc = struct.unpack(">I", raw[offset + 8 + length : offset + 12 + length])[0]
        if len(data) != length or binascii.crc32(kind + data) & 0xFFFFFFFF != crc:
            raise Refuse("png_crc:" + path.name)
        if kind == b"IHDR":
            ihdr_count += 1
            if offset != 8 or length != 13 or ihdr_count != 1:
                raise Refuse("png_ihdr_count_order:" + path.name)
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", data)
            if (width, height, bit_depth, compression, filtering, interlace) != (640, 640, 8, 0, 0, 0) or color_type not in (2, 6):
                raise Refuse("png_ihdr:" + path.name)
        elif kind == b"IDAT":
            idat_count += 1
            if ihdr_count != 1 or seen_iend:
                raise Refuse("png_idat_order:" + path.name)
            compressed.extend(data)
        elif kind == b"IEND":
            iend_count += 1
            if length != 0 or iend_count != 1 or idat_count == 0:
                raise Refuse("png_iend_count:" + path.name)
            seen_iend = True
            if offset + 12 + length != len(raw):
                raise Refuse("png_trailing_bytes:" + path.name)
        offset += 12 + length
    if not seen_iend or ihdr_count != 1 or iend_count != 1 or idat_count == 0 or width != 640 or height != 640 or color_type not in (2, 6):
        raise Refuse("png_structure:" + path.name)
    channels = 3 if color_type == 2 else 4
    stride = width * channels
    expected_decoded = height * (stride + 1)
    decompressor = zlib.decompressobj()
    decoded = decompressor.decompress(bytes(compressed), expected_decoded + 1)
    if decompressor.unconsumed_tail or len(decoded) > expected_decoded:
        raise Refuse("png_zlib_limit:" + path.name)
    decoded += decompressor.flush(expected_decoded + 1 - len(decoded))
    if not decompressor.eof or decompressor.unused_data or decompressor.unconsumed_tail:
        raise Refuse("png_zlib_stream:" + path.name)
    if len(decoded) != expected_decoded:
        raise Refuse("png_decoded_size:" + path.name)
    previous = bytearray(stride)
    pixels: set[bytes] = set()
    nonuniform_rows = 0
    cursor = 0
    for _ in range(height):
        filter_type = decoded[cursor]
        source = decoded[cursor + 1 : cursor + 1 + stride]
        cursor += stride + 1
        row = bytearray(stride)
        for index, value in enumerate(source):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                base = left + up - upper_left
                pa, pb, pc = abs(base - left), abs(base - up), abs(base - upper_left)
                predictor = left if pa <= pb and pa <= pc else (up if pb <= pc else upper_left)
            else:
                raise Refuse("png_filter:" + path.name)
            row[index] = (value + predictor) & 0xFF
        row_pixels = {bytes(row[index : index + channels]) for index in range(0, stride, channels)}
        pixels.update(row_pixels)
        if len(row_pixels) > 8:
            nonuniform_rows += 1
        previous = row
    if len(pixels) < 128 or nonuniform_rows < 160:
        raise Refuse("png_content_gate:" + path.name)
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "width": width, "height": height, "channels": channels, "unique_pixels_at_least": min(len(pixels), 128), "nonuniform_rows": nonuniform_rows}


def render_views(
    camera: bpy.types.Object,
    cameras: dict[str, tuple[float, float, float]],
    reserved: dict[Path, tuple[int, int]],
) -> dict[str, object]:
    results: dict[str, object] = {}
    original_alpha = {material.name: float(material.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value) for material in bpy.data.materials}
    for view in ("front_clinical", "right_clinical", "iso_clinical", "iso_xray"):
        matrix = point_camera(camera, cameras[view])
        if view == "iso_xray":
            for material in bpy.data.materials:
                material.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = min(original_alpha[material.name], 0.24)
        render_path = RENDER_PATHS[view]
        validate_reserved_identity(render_path, reserved[render_path], "render_before:" + view)
        bpy.context.scene.render.filepath = str(render_path)
        bpy.ops.render.render(write_still=True)
        validate_reserved_identity(
            render_path, reserved[render_path], "render_after:" + view, minimum_bytes=1024
        )
        results[view] = {**parse_png(render_path), "camera_matrix_world": matrix, "xray_material_override": view == "iso_xray"}
        if view == "iso_xray":
            for material in bpy.data.materials:
                material.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = original_alpha[material.name]
    if len({value["sha256"] for value in results.values()}) != 4:
        raise Refuse("render_views_not_distinct")
    return results


def remove_render_images() -> None:
    for image in tuple(bpy.data.images):
        bpy.data.images.remove(image)
    if bpy.data.images:
        raise Refuse("render_images_retained")


def durable_reserved_json(path: Path, value: dict[str, object], identity: tuple[int, int]) -> None:
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    durable_reserved_bytes(path, raw, identity)


def durable_reserved_bytes(path: Path, raw: bytes, identity: tuple[int, int]) -> None:
    validate_reserved_identity(path, identity, "reserved_write_before:" + path.name)
    with path.open("r+b") as stream:
        stream.seek(0)
        stream.truncate(0)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    validate_reserved_identity(
        path, identity, "reserved_write_after:" + path.name, minimum_bytes=len(raw)
    )
    if path.read_bytes() != raw:
        raise Refuse("reserved_write_readback:" + path.name)


def exact_record(path: Path) -> tuple[int, str]:
    raw = path.read_bytes()
    return len(raw), hashlib.sha256(raw).hexdigest()


def build_worker_receipt(capability: dict[str, object], capability_sha256: str) -> bytes:
    records = {
        "blend": exact_record(BLEND_PATH),
        "front_clinical": exact_record(RENDER_PATHS["front_clinical"]),
        "right_clinical": exact_record(RENDER_PATHS["right_clinical"]),
        "iso_clinical": exact_record(RENDER_PATHS["iso_clinical"]),
        "iso_xray": exact_record(RENDER_PATHS["iso_xray"]),
        "worker_result_json": exact_record(RESULT_PATH),
    }
    lines = [
        "schema\tkira.r25.medical_reference_proxy.v3r30.worker_receipt.v1",
        "status\tWORKER_VALIDATED_AWAITING_NATIVE_FINALIZATION",
        "truth\tISOLATED_NORMALIZED_CLINICAL_REFERENCE_PROXY_NOT_KIRA_BODY",
        f"stage1_package_root\t{capability['stage1_package_root']}",
        f"audit_a_sha256\t{capability['audit_a_sha256']}",
        f"capability_sha256\t{capability_sha256}",
    ]
    for key in ("blend", "front_clinical", "right_clinical", "iso_clinical", "iso_xray", "worker_result_json"):
        byte_count, digest = records[key]
        lines.append(f"{key}\t{byte_count}\t{digest}")
    lines.extend((
        "proxy_objects\t9",
        "proxy_materials\t6",
        "landmark_gates\t8",
        "render_views\t4",
        "initial_reload_validated\ttrue",
        "final_snapshot_reload_validated\ttrue",
        "source_imported\tfalse",
        "exported\tfalse",
        "rig_weights_animation\tfalse",
        "live_avatar_activation_promotion\tfalse",
    ))
    raw = ("\n".join(lines) + "\n").encode("ascii")
    if b"\r" in raw or b"\0" in raw:
        raise Refuse("worker_receipt_grammar")
    return raw


def execute(
    capability: dict[str, object],
    spec: dict[str, object],
    frame: dict[str, object],
    reserved: dict[Path, tuple[int, int]],
) -> dict[str, object]:
    cameras = validate_frame(frame)
    validate_factory_runtime()
    reset_scene()
    build_scene(spec)
    built = validate_proxy_scene(spec, with_rig=False)
    camera = configure_evidence_rig()
    before_save = validate_proxy_scene(spec, with_rig=True)
    validate_reserved_identity(BLEND_PATH, reserved[BLEND_PATH], "initial_blend_before")
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    validate_reserved_identity(
        BLEND_PATH, reserved[BLEND_PATH], "initial_blend_after", minimum_bytes=4096
    )
    initial_blend_sha256 = sha256_path(BLEND_PATH)
    validate_reserved_identity(BLEND_PATH, reserved[BLEND_PATH], "initial_reload_before", minimum_bytes=4096)
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH), load_ui=False)
    validate_reserved_identity(BLEND_PATH, reserved[BLEND_PATH], "initial_reload_after", minimum_bytes=4096)
    if Path(bpy.data.filepath).resolve() != BLEND_PATH.resolve():
        raise Refuse("initial_reload_filepath")
    initial_reload = validate_proxy_scene(spec, with_rig=True)
    if bpy.context.scene.get("kira_v3r30_truth") != "ISOLATED_NORMALIZED_REFERENCE_PROXY_NOT_KIRA_BODY":
        raise Refuse("initial_reload_scene_truth")
    camera = bpy.data.objects.get("V3r30_Evidence_Camera")
    if camera is None or camera.type != "CAMERA":
        raise Refuse("initial_reload_camera")
    renders = render_views(camera, cameras, reserved)
    remove_render_images()
    point_camera(camera, cameras["iso_clinical"])
    bpy.context.scene.render.filepath = ""
    before_final_save = validate_proxy_scene(spec, with_rig=True)
    validate_reserved_identity(BLEND_PATH, reserved[BLEND_PATH], "final_blend_before", minimum_bytes=4096)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    validate_reserved_identity(BLEND_PATH, reserved[BLEND_PATH], "final_blend_after", minimum_bytes=4096)
    final_blend_sha256 = sha256_path(BLEND_PATH)
    validate_reserved_identity(BLEND_PATH, reserved[BLEND_PATH], "final_reload_before", minimum_bytes=4096)
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH), load_ui=False)
    validate_reserved_identity(BLEND_PATH, reserved[BLEND_PATH], "final_reload_after", minimum_bytes=4096)
    if Path(bpy.data.filepath).resolve() != BLEND_PATH.resolve():
        raise Refuse("final_reload_filepath")
    final_reload = validate_proxy_scene(spec, with_rig=True)
    if bpy.context.scene.get("source_meshes_imported") is not False or bpy.context.scene.get("external_dependencies") != 0 or bpy.context.scene.get("live_avatar_linked") is not False or bpy.context.scene.get("rig_or_weights_present") is not False:
        raise Refuse("final_reload_scene_truth")
    for view, path in RENDER_PATHS.items():
        current = parse_png(path)
        if current["sha256"] != renders[view]["sha256"]:
            raise Refuse("late_render_mutation:" + view)
    if sha256_path(BLEND_PATH) != final_blend_sha256:
        raise Refuse("late_blend_mutation")
    return {
        "schema": "kira.r25.medical_reference_proxy.v3r30.worker_result.v1",
        "status": "WORKER_VALIDATED_AWAITING_NATIVE_FINALIZATION",
        "nonce": capability["nonce"],
        "stage1_package_root": capability["stage1_package_root"],
        "audit_a_sha256": capability["audit_a_sha256"],
        "truth": "ISOLATED_NORMALIZED_CLINICAL_REFERENCE_PROXY_NOT_KIRA_BODY",
        "built": built,
        "before_save": before_save,
        "initial_blend_sha256": initial_blend_sha256,
        "initial_reload": initial_reload,
        "renders": renders,
        "before_final_save": before_final_save,
        "final_blend": {"path": str(BLEND_PATH), "bytes": BLEND_PATH.stat().st_size, "sha256": final_blend_sha256},
        "final_reload": final_reload,
        "external_dependencies": [],
        "source_imported": False,
        "exported": False,
        "rig_weights_animation": False,
        "live_avatar_activation_promotion": False,
        "staging_pre_reserved": True,
        "staging_identity_revalidated": True,
        "not_proven": ["Kira body", "complete anatomy", "functional organs", "physiology", "sensation", "rig", "weights", "deformation", "production materials", "regional pigmentation", "hair", "activation", "Avatar Builder promotion"],
    }


def main() -> int:
    args = parse_args()
    capability, spec, frame = load_capability(args)
    reserved = validate_pre_reserved_outputs()
    result = execute(capability, spec, frame, reserved)
    durable_reserved_json(RESULT_PATH, result, reserved[RESULT_PATH])
    receipt = build_worker_receipt(capability, args.capability_sha256)
    durable_reserved_bytes(RECEIPT_PATH, receipt, reserved[RECEIPT_PATH])
    for index, path in enumerate(EXPECTED_STAGING_PATHS):
        validate_reserved_identity(path, reserved[path], f"terminal_staging_{index}", minimum_bytes=1)
    print("V3R30_WORKER_VALIDATED:" + sha256_path(RECEIPT_PATH), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("V3R30_WORKER_FAIL:" + type(error).__name__ + ":" + str(error)[:240], file=sys.stderr, flush=True)
        raise
