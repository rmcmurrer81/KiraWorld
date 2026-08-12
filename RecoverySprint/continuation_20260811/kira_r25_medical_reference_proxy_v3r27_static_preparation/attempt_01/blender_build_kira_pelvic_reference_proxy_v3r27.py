"""V3r27 isolated Stage-A clinical reference-proxy candidate.

Static author artifact only.  Do not invoke until a different fresh audit is
installed at the exact fixed path and grants the one-shot decision encoded by
the contract.  Even a successful later invocation makes a normalized clinical
reference scene, not Kira's body.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector


KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
ANATOMY_TRIAGE_ROOT = Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work\anatomy_asset_triage")
AUTHOR = "codex_r25_medical_reference_proxy_v3r27_static_author"
DECISION = "ACCEPTED_FOR_ONE_BOUNDED_STAGE_A_REFERENCE_PROXY_BUILD_SAVE_RELOAD_RENDER_V3R27_ONLY"
STATIC_ROOT = KIRA_ROOT / "RecoverySprint" / "continuation_20260811" / "kira_r25_medical_reference_proxy_v3r27_static_preparation" / "attempt_01"
AUDIT_ROOT = KIRA_ROOT / "RecoverySprint" / "continuation_20260811" / "kira_r25_medical_reference_proxy_v3r27_fresh_static_audit" / "attempt_01"
SEAL_PATH = STATIC_ROOT / "STATIC_SEAL_MANIFEST.json"
AUDIT_PATH = AUDIT_ROOT / "INDEPENDENT_AUDIT.tsv"
AUDIT_DIGEST_PATH = AUDIT_ROOT / "INDEPENDENT_AUDIT.sha256"
RECEIPT_PATH = STATIC_ROOT / "V3R27_ATTEMPT_CONSUMED.receipt.json"
EVIDENCE_PATH = STATIC_ROOT / "RUN_EVIDENCE.jsonl"
OUTCOME_PATH = STATIC_ROOT / "RUN_OUTCOME.json"
OUTPUT_ROOT = STATIC_ROOT / "outputs"
BLEND_PATH = OUTPUT_ROOT / "kira_v3r27_pelvic_core_reference_proxy.blend"
RENDER_PATHS = {
    "front_clinical": OUTPUT_ROOT / "front_clinical.png",
    "right_clinical": OUTPUT_ROOT / "right_clinical.png",
    "iso_clinical": OUTPUT_ROOT / "iso_clinical.png",
    "iso_xray": OUTPUT_ROOT / "iso_xray.png",
}
PROXY_IDS = (
    "pelvic_reference_envelope",
    "bladder_proxy",
    "uterus_proxy",
    "uterine_tube_left_proxy",
    "uterine_tube_right_proxy",
    "ovary_left_proxy",
    "ovary_right_proxy",
    "rectum_reference_proxy",
    "vulvar_region_reference_proxy",
)
EXPECTED_AUDIT_KEYS = (
    "decision",
    "auditor",
    "author",
    "package_root_sha256",
    "seal_sha256",
    "contract_sha256",
    "script_sha256",
    "upstream_closure_sha256",
    "license_manifest_sha256",
    "component_inventory_sha256",
    "placement_plan_sha256",
    "skeleton_mapping_sha256",
    "maximum_invocations",
    "stop_after",
)


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def durable_write(path: Path, data: bytes, exclusive: bool = False) -> None:
    mode = "xb" if exclusive else "wb"
    with path.open(mode) as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def durable_json(path: Path, value: dict, exclusive: bool = False) -> None:
    durable_write(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"), exclusive)


def append_evidence(event: str, **fields: object) -> None:
    record = {"event": event, "epoch": time.time(), **fields}
    with EVIDENCE_PATH.open("ab") as stream:
        stream.write((json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def parse_audit() -> dict[str, str]:
    raw = AUDIT_PATH.read_bytes()
    if b"\r" in raw or b"\0" in raw or not raw.endswith(b"\n"):
        raise RuntimeError("audit_encoding_or_termination")
    expected = AUDIT_DIGEST_PATH.read_text(encoding="ascii").strip()
    if len(expected) != 64 or expected.lower() != expected or hashlib.sha256(raw).hexdigest() != expected:
        raise RuntimeError("audit_digest")
    rows = list(csv.reader(raw.decode("utf-8").splitlines(), delimiter="\t"))
    if len(rows) != len(EXPECTED_AUDIT_KEYS) or any(len(row) != 2 for row in rows):
        raise RuntimeError("audit_shape")
    if tuple(row[0] for row in rows) != EXPECTED_AUDIT_KEYS:
        raise RuntimeError("audit_order")
    values = dict(rows)
    if values["decision"] != DECISION or values["author"] != AUTHOR:
        raise RuntimeError("audit_decision_or_author")
    if values["auditor"] == AUTHOR or not values["auditor"].startswith("codex_"):
        raise RuntimeError("audit_separation")
    if values["maximum_invocations"] != "1":
        raise RuntimeError("audit_invocation_ceiling")
    if values["stop_after"] != "saved_blend_reloaded_four_clinical_renders_and_durable_outcome":
        raise RuntimeError("audit_stop_boundary")
    return values


def verify_seal(audit: dict[str, str]) -> dict:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    if sha256_path(SEAL_PATH) != audit["seal_sha256"]:
        raise RuntimeError("seal_identity")
    if seal.get("schema") != "kira.r25.medical_reference_proxy.v3r27.static_seal.v1":
        raise RuntimeError("seal_schema")
    rows = seal.get("subjects")
    if not isinstance(rows, list) or len(rows) != 8:
        raise RuntimeError("seal_subject_count")
    canonical = bytearray()
    for row in sorted(rows, key=lambda item: item["path"]):
        path = STATIC_ROOT / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha256_path(path) != row["sha256"]:
            raise RuntimeError("sealed_subject_mismatch:" + row["path"])
        canonical.extend(f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n".encode("utf-8"))
    package_root = hashlib.sha256(canonical).hexdigest()
    if package_root != seal.get("package_root_sha256") or package_root != audit["package_root_sha256"]:
        raise RuntimeError("package_root")
    by_name = {row["path"]: row["sha256"] for row in rows}
    expected = {
        "CONTRACT.json": "contract_sha256",
        "blender_build_kira_pelvic_reference_proxy_v3r27.py": "script_sha256",
        "UPSTREAM_CLOSURE.tsv": "upstream_closure_sha256",
        "ATTRIBUTION_LICENSE_MANIFEST.tsv": "license_manifest_sha256",
        "MEDICAL_COMPONENT_INVENTORY.tsv": "component_inventory_sha256",
        "KIRA_RELATIVE_PLACEMENT_PLAN.json": "placement_plan_sha256",
        "SKELETON_136_MAPPING_PLAN.tsv": "skeleton_mapping_sha256",
    }
    for name, key in expected.items():
        if by_name.get(name) != audit[key]:
            raise RuntimeError("audit_subject_binding:" + name)
    return seal


def verify_upstream_closure() -> None:
    path = STATIC_ROOT / "UPSTREAM_CLOSURE.tsv"
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != 24:
        raise RuntimeError("upstream_closure_count")
    counts: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()
    for row in rows:
        scope = row["scope"]
        key = (scope, row["path"])
        if key in seen:
            raise RuntimeError("upstream_closure_duplicate")
        seen.add(key)
        counts[scope] = counts.get(scope, 0) + 1
        subject = (ANATOMY_TRIAGE_ROOT / row["path"]) if scope == "anatomy_triage" else (KIRA_ROOT / Path(row["path"]))
        if not subject.is_file() or subject.stat().st_size != int(row["bytes"]) or sha256_path(subject) != row["sha256"]:
            raise RuntimeError("upstream_closure_mismatch:" + row["path"])
    expected = {"v3r26_author": 10, "v3r26_audit": 6, "v3r26_run": 4, "anatomy_triage": 3, "anatomy_triage_root": 1}
    if counts != expected:
        raise RuntimeError("upstream_closure_scopes")
    outcome_path = KIRA_ROOT / "RecoverySprint" / "continuation_20260811" / "kira_r25_afes_execution_plan_validation_v3r26_static_preparation" / "attempt_01" / "RUN_OUTCOME.json"
    outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    if outcome.get("process_exit_code") != 0 or outcome.get("do_not_rerun_v3r26") is not True or outcome.get("truth") != "PURE_PLAN_CONTROL_LAYER_ACCEPTED_BY_CONSUMED_RUN_NOT_A_BODY":
        raise RuntimeError("v3r26_consumed_success_truth")


def preflight() -> tuple[dict[str, str], dict]:
    if not bpy.app.background:
        raise RuntimeError("background_mode_required")
    if Path.cwd().resolve() != KIRA_ROOT.resolve():
        raise RuntimeError("exact_working_directory_required")
    required = (SEAL_PATH, AUDIT_PATH, AUDIT_DIGEST_PATH, AUDIT_ROOT / "CHECKPOINT.md")
    if any(not path.is_file() for path in required):
        raise RuntimeError("different_audit_not_installed")
    forbidden_existing = (RECEIPT_PATH, EVIDENCE_PATH, OUTCOME_PATH, BLEND_PATH, *RENDER_PATHS.values())
    if any(path.exists() for path in forbidden_existing) or OUTPUT_ROOT.exists():
        raise RuntimeError("one_shot_output_already_exists")
    audit = parse_audit()
    seal = verify_seal(audit)
    verify_upstream_closure()
    return audit, seal


def reserve(audit: dict[str, str]) -> None:
    receipt = {
        "schema": "kira.r25.medical_reference_proxy.v3r27.attempt_receipt.v1",
        "state": "RESERVED_AUTHORITY_CONSUMED",
        "decision": audit["decision"],
        "auditor": audit["auditor"],
        "reserved_epoch": time.time(),
        "rerun_permitted": False,
    }
    durable_json(RECEIPT_PATH, receipt, exclusive=True)
    durable_write(EVIDENCE_PATH, b"", exclusive=True)
    OUTPUT_ROOT.mkdir(exist_ok=False)
    append_evidence("attempt_reserved", authority_consumed=True)


def new_material(name: str, rgba: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = rgba
    material.use_nodes = True
    node = material.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = rgba
    node.inputs["Roughness"].default_value = 0.55
    node.inputs["Alpha"].default_value = rgba[3]
    if rgba[3] < 1.0:
        material.surface_render_method = "DITHERED"
    return material


def tag_proxy(obj: bpy.types.Object, component_id: str, sources: str) -> None:
    obj.name = component_id
    obj["kira_v3r27_role"] = "NORMALIZED_CLINICAL_REFERENCE_PROXY_NOT_LIVE_BODY"
    obj["component_id"] = component_id
    obj["attribution_reference_ids"] = sources
    obj["functional_organ"] = False
    obj["approved_for_activation"] = False


def add_ellipsoid(component_id: str, location: tuple[float, float, float], scale: tuple[float, float, float], material: bpy.types.Material, sources: str) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, location=location)
    obj = bpy.context.object
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    tag_proxy(obj, component_id, sources)
    return obj


def add_curve(component_id: str, points: tuple[tuple[float, float, float], ...], radius: float, material: bpy.types.Material, sources: str) -> bpy.types.Object:
    curve = bpy.data.curves.new(component_id + "_curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for control, value in zip(spline.bezier_points, points):
        control.co = value
        control.handle_left_type = "AUTO"
        control.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(component_id, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    tag_proxy(obj, component_id, sources)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)
    return obj


def build_proxy_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in tuple(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    collection = bpy.data.collections.get("Collection")
    collection.name = "V3r27_Pelvic_Core_Reference_Proxy"
    bone = new_material("clinical_bone_envelope", (0.72, 0.70, 0.62, 0.28))
    urinary = new_material("clinical_urinary", (0.93, 0.69, 0.22, 0.82))
    reproductive = new_material("clinical_reproductive", (0.68, 0.20, 0.32, 0.86))
    connection = new_material("clinical_connections", (0.84, 0.34, 0.48, 0.90))
    digestive = new_material("clinical_digestive_reference", (0.43, 0.26, 0.16, 0.75))
    external_ref = new_material("clinical_external_reference", (0.56, 0.32, 0.38, 0.32))

    bpy.ops.mesh.primitive_torus_add(major_radius=0.42, minor_radius=0.025, major_segments=24, minor_segments=6, location=(0.0, 0.0, 0.0), rotation=(math.pi / 2.0, 0.0, 0.0))
    pelvis = bpy.context.object
    pelvis.scale = (1.0, 0.78, 0.78)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    pelvis.data.materials.append(bone)
    tag_proxy(pelvis, "pelvic_reference_envelope", "mri_pelvis_cc_by;female_repro_urinary_cc_by")

    add_ellipsoid("bladder_proxy", (0.0, 0.23, -0.012), (0.11, 0.095, 0.050), urinary, "mri_pelvis_cc_by;female_repro_urinary_cc_by")
    add_ellipsoid("uterus_proxy", (0.0, 0.035, 0.022), (0.095, 0.070, 0.052), reproductive, "mri_pelvis_cc_by;female_repro_urinary_cc_by")
    add_ellipsoid("ovary_left_proxy", (-0.26, 0.025, 0.033), (0.045, 0.030, 0.020), reproductive, "mri_pelvis_cc_by;female_repro_urinary_cc_by")
    add_ellipsoid("ovary_right_proxy", (0.26, 0.025, 0.033), (0.045, 0.030, 0.020), reproductive, "mri_pelvis_cc_by;female_repro_urinary_cc_by")
    add_curve("uterine_tube_left_proxy", ((-0.06, 0.035, 0.060), (-0.15, 0.045, 0.082), (-0.23, 0.030, 0.050)), 0.009, connection, "mri_pelvis_cc_by;female_repro_urinary_cc_by")
    add_curve("uterine_tube_right_proxy", ((0.06, 0.035, 0.060), (0.15, 0.045, 0.082), (0.23, 0.030, 0.050)), 0.009, connection, "mri_pelvis_cc_by;female_repro_urinary_cc_by")
    add_curve("rectum_reference_proxy", ((0.0, -0.27, 0.085), (0.0, -0.30, 0.0), (0.0, -0.25, -0.075)), 0.025, digestive, "mri_pelvis_cc_by")
    add_ellipsoid("vulvar_region_reference_proxy", (0.0, 0.22, -0.075), (0.055, 0.025, 0.018), external_ref, "mri_pelvis_cc_by")
    validate_proxy_scene()


def proxy_objects() -> list[bpy.types.Object]:
    return [obj for obj in bpy.data.objects if obj.get("kira_v3r27_role") == "NORMALIZED_CLINICAL_REFERENCE_PROXY_NOT_LIVE_BODY"]


def validate_proxy_scene() -> dict:
    objects = proxy_objects()
    ids = tuple(sorted(obj.get("component_id") for obj in objects))
    if len(objects) != 9 or ids != tuple(sorted(PROXY_IDS)):
        raise RuntimeError("proxy_inventory")
    if any(obj.type != "MESH" for obj in objects):
        raise RuntimeError("proxy_type")
    vertices = sum(len(obj.data.vertices) for obj in objects)
    if vertices <= 0 or vertices > 12000:
        raise RuntimeError("vertex_ceiling")
    if len(bpy.data.materials) > 6 or bpy.data.armatures or bpy.data.actions or bpy.data.images:
        raise RuntimeError("forbidden_scene_datablock")
    if any(obj.get("functional_organ") is not False or obj.get("approved_for_activation") is not False for obj in objects):
        raise RuntimeError("truth_tags")
    return {"proxy_objects": len(objects), "vertices": vertices, "materials": len(bpy.data.materials)}


def configure_evidence_rig() -> bpy.types.Object:
    bpy.ops.object.camera_add(location=(1.25, -1.55, 0.90))
    camera = bpy.context.object
    camera.name = "Evidence_Camera"
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(0.8, -1.0, 1.2))
    bpy.context.object.data.energy = 650
    bpy.context.object.data.shape = "DISK"
    bpy.context.object.data.size = 4.0
    bpy.ops.object.light_add(type="AREA", location=(-0.9, 0.6, 0.6))
    bpy.context.object.data.energy = 350
    bpy.context.object.data.size = 3.0
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.035, 0.035, 0.045)
    return camera


def point_camera(camera: bpy.types.Object, location: tuple[float, float, float]) -> None:
    camera.location = location
    target = Vector((0.0, 0.0, 0.0))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 58


def render_evidence(camera: bpy.types.Object) -> None:
    views = {
        "front_clinical": (0.0, -1.55, 0.10),
        "right_clinical": (1.55, 0.0, 0.10),
        "iso_clinical": (1.20, -1.35, 0.85),
        "iso_xray": (-1.20, -1.35, 0.85),
    }
    for view, location in views.items():
        point_camera(camera, location)
        bpy.context.scene.render.filepath = str(RENDER_PATHS[view])
        bpy.ops.render.render(write_still=True)
        path = RENDER_PATHS[view]
        if not path.is_file() or path.stat().st_size < 1024:
            raise RuntimeError("render_missing_or_small:" + view)
        append_evidence("render_complete", view=view, bytes=path.stat().st_size, sha256=sha256_path(path))


def execute() -> dict:
    build_proxy_scene()
    built = validate_proxy_scene()
    append_evidence("normalized_proxy_built", **built)
    configure_evidence_rig()
    bpy.context.scene["kira_v3r27_truth"] = "ISOLATED_NORMALIZED_REFERENCE_PROXY_NOT_KIRA_BODY"
    bpy.context.scene["source_meshes_imported"] = False
    bpy.context.scene["live_avatar_linked"] = False
    bpy.context.scene["regional_pigmentation_proven"] = False
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    if not BLEND_PATH.is_file() or BLEND_PATH.stat().st_size < 4096:
        raise RuntimeError("blend_save")
    saved_sha = sha256_path(BLEND_PATH)
    append_evidence("blend_saved", bytes=BLEND_PATH.stat().st_size, sha256=saved_sha)
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH), load_ui=False)
    reloaded = validate_proxy_scene()
    if bpy.context.scene.get("kira_v3r27_truth") != "ISOLATED_NORMALIZED_REFERENCE_PROXY_NOT_KIRA_BODY":
        raise RuntimeError("reload_truth_tag")
    append_evidence("blend_reloaded_and_validated", **reloaded)
    camera = bpy.data.objects.get("Evidence_Camera")
    if camera is None or camera.type != "CAMERA":
        raise RuntimeError("reloaded_camera")
    render_evidence(camera)
    return {"built": built, "reloaded": reloaded, "blend_bytes": BLEND_PATH.stat().st_size, "blend_sha256": saved_sha}


def main() -> int:
    started = time.time()
    reserved = False
    try:
        audit, seal = preflight()
        reserve(audit)
        reserved = True
        append_evidence("preflight_passed", package_root_sha256=seal["package_root_sha256"])
        result = execute()
        outcome = {
            "schema": "kira.r25.medical_reference_proxy.v3r27.run_outcome.v1",
            "status": "STAGE_A_REFERENCE_PROXY_SUCCESS_CONSUMED_NO_RERUN",
            "authority_consumed": True,
            "do_not_rerun_v3r27": True,
            "started_epoch": started,
            "ended_epoch": time.time(),
            "result": result,
            "truth": "ISOLATED_NORMALIZED_CLINICAL_REFERENCE_PROXY_NOT_KIRA_BODY",
            "not_proven": ["complete body", "functional organs", "Kira fitting", "rig", "weights", "deformation", "production materials", "regional pigmentation", "hair", "activation", "Avatar Builder promotion"],
        }
        durable_json(OUTCOME_PATH, outcome, exclusive=True)
        append_evidence("terminal_success", outcome_sha256=sha256_path(OUTCOME_PATH))
        receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        receipt.update({"state": "SUCCESS_CONSUMED_NO_RERUN", "completed_epoch": time.time(), "outcome_sha256": sha256_path(OUTCOME_PATH)})
        durable_json(RECEIPT_PATH, receipt)
        return 0
    except Exception as error:
        if reserved:
            try:
                append_evidence("terminal_failure", error_type=type(error).__name__, error=str(error)[:240])
                receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
                receipt.update({"state": "FAILURE_CONSUMED_NO_RERUN", "completed_epoch": time.time(), "error_type": type(error).__name__, "error": str(error)[:240]})
                durable_json(RECEIPT_PATH, receipt)
            except Exception:
                pass
        print("V3R27_FAIL:" + type(error).__name__ + ":" + str(error)[:240], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
