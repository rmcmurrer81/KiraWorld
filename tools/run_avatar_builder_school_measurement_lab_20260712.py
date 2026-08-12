"""Blender measurement lab for Avatar Builder School.

Run with Blender:
  "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background --python tools/run_avatar_builder_school_measurement_lab_20260712.py
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import bpy
import mathutils


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILDER_ROOT = PROJECT_ROOT / "Avatar" / "avatar_builder"
MANIFEST_PATH = BUILDER_ROOT / "asset_library" / "manifest.json"
SCHOOL_ROOT = BUILDER_ROOT / "school"
ASSIGNMENT_ROOT = SCHOOL_ROOT / "assignments"
PROGRESS_PATH = SCHOOL_ROOT / "progress" / "avatar_builder_school_progress_20260712.json"
MARINETTE_ID = "ladybug_marinette_expanded_smoke"
GWEN_ID = "spider_gwen_spider_gwen_20260606_013325"

CANDIDATE_MODELS = {
    MARINETTE_ID: PROJECT_ROOT / "Avatar" / "models" / "temp_ai" / MARINETTE_ID / "avatar_builder_silhouette_overlay_calibration_20260712.glb",
    GWEN_ID: PROJECT_ROOT / "Avatar" / "models" / "temp_ai" / GWEN_ID / "avatar_builder_silhouette_overlay_calibration_20260712.glb",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default.copy() if isinstance(default, dict) else default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for image in list(bpy.data.images):
        bpy.data.images.remove(image)


def bounds_for(obj: bpy.types.Object) -> tuple[list[float], list[float]]:
    points = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    return (
        [min(point[index] for point in points) for index in range(3)],
        [max(point[index] for point in points) for index in range(3)],
    )


def bounds_size(bounds: tuple[list[float], list[float]]) -> list[float]:
    low, high = bounds
    return [high[index] - low[index] for index in range(3)]


def scene_bounds() -> tuple[list[float], list[float]]:
    points: list[mathutils.Vector] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ mathutils.Vector(corner))
    if not points:
        return [0, 0, 0], [0, 0, 0]
    return (
        [min(point[index] for point in points) for index in range(3)],
        [max(point[index] for point in points) for index in range(3)],
    )


def import_glb(path: Path) -> None:
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update()


def inspect_eye_asset(path: Path, asset_record: dict) -> dict:
    import_glb(path)
    mesh_records: list[dict] = []
    eye_like: list[dict] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        bounds = bounds_for(obj)
        size = bounds_size(bounds)
        materials = [mat.name for mat in obj.data.materials if mat]
        record = {
            "name": obj.name,
            "bounds": bounds,
            "size": size,
            "materials": materials,
            "vertex_count": len(obj.data.vertices),
        }
        mesh_records.append(record)
        lowered = " ".join([obj.name, obj.data.name, " ".join(materials)]).lower()
        if any(term in lowered for term in ("eye", "iris", "pupil", "sclera", "cornea", "lens")):
            eye_like.append(record)
    low, high = scene_bounds()
    return {
        "asset_id": asset_record.get("id"),
        "filename": asset_record.get("filename"),
        "local_file": rel(path),
        "scene_bounds": [low, high],
        "scene_size": [high[i] - low[i] for i in range(3)],
        "mesh_count": len(mesh_records),
        "eye_like_meshes": eye_like,
        "largest_meshes": sorted(mesh_records, key=lambda item: max(item["size"]), reverse=True)[:12],
        "lesson": "Use this as geometry/reference evidence. Do not paste the whole asset blindly onto a candidate face.",
    }


def inspect_candidate(candidate_id: str, path: Path) -> dict:
    import_glb(path)
    all_meshes: list[dict] = []
    eye_meshes: list[dict] = []
    body_meshes: list[dict] = []
    overlay_meshes: list[str] = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        bounds = bounds_for(obj)
        size = bounds_size(bounds)
        lowered = obj.name.lower()
        record = {
            "name": obj.name,
            "bounds": bounds,
            "size": size,
            "center": [(bounds[0][i] + bounds[1][i]) / 2 for i in range(3)],
            "materials": [mat.name for mat in obj.data.materials if mat],
        }
        all_meshes.append(record)
        if any(term in lowered for term in ("round_eye", "iris", "pupil", "sclera", "catchlight")):
            eye_meshes.append(record)
        if "body" in lowered and "overlay" not in lowered:
            body_meshes.append(record)
        if "silhouette_overlay_image_plane" in lowered:
            overlay_meshes.append(obj.name)
    low, high = scene_bounds()
    scene_height = high[2] - low[2]
    body = max(body_meshes, key=lambda item: item["size"][2], default=None)
    sclera = [item for item in eye_meshes if "sclera" in item["name"].lower()]
    sclera_diameters = [max(item["size"]) for item in sclera]
    eye_centers = [item["center"] for item in sclera]
    if len(eye_centers) >= 2:
        eye_spacing = abs(eye_centers[0][0] - eye_centers[1][0])
    else:
        eye_spacing = 0.0
    max_eye_diameter = max(sclera_diameters) if sclera_diameters else 0.0
    eye_to_spacing_ratio = max_eye_diameter / eye_spacing if eye_spacing else None
    body_width = body["size"][0] if body else 0.0
    body_height = body["size"][2] if body else 0.0
    return {
        "candidate_id": candidate_id,
        "model": rel(path),
        "status": "failed_robert_review_school_measurement",
        "scene_bounds": [low, high],
        "scene_height": scene_height,
        "body_mesh": body,
        "body_width": body_width,
        "body_height": body_height,
        "eye_meshes": eye_meshes,
        "sclera_diameters": sclera_diameters,
        "eye_spacing": eye_spacing,
        "eye_to_spacing_ratio": eye_to_spacing_ratio,
        "overlay_planes": overlay_meshes,
        "school_grade": "F",
        "robert_failure_reason": (
            "Eyes appear too large/protruding in workspace review; head/body/hair still fail likeness. "
            "This measurement file is evidence for the redo, not a pass."
        ),
        "next_required_actions": [
            "use a real eye-reference GLB to derive eye structure",
            "fit eyes against candidate head landmarks, not absolute hard-coded coordinates",
            "create a head landmark map before placing eyes",
            "measure eye protrusion against face plane/profile screenshot",
            "rebuild body/head/hair after maturity policy check",
        ],
    }


def update_progress(paths: dict[str, str]) -> None:
    progress = read_json(PROGRESS_PATH, {})
    progress["updated_at"] = now_iso()
    progress["status"] = "school_in_progress_failed_current_previews"
    classes = progress.setdefault("classes", {})
    for class_id in ("eye_model_lab_001", "body_anatomy_and_maturity_001"):
        entry = classes.setdefault(class_id, {})
        entry["status"] = "lesson_started_current_preview_failed"
        entry["grade"] = "F_current_preview_redo_required"
    progress["latest_measurement_outputs"] = paths
    progress.setdefault("blocked_preview_claims", []).append(
        "Measurement lab ran; current eyes/body remain failed and must be rebuilt from the class assignments."
    )
    write_json(PROGRESS_PATH, progress)


def main() -> int:
    manifest = read_json(MANIFEST_PATH, {"records": []})
    eye_records = [record for record in manifest.get("records", []) if record.get("category") == "eye_reference"]
    eye_assets: list[dict] = []
    for record in eye_records:
        local = record.get("local_file")
        if not local:
            continue
        path = PROJECT_ROOT / str(local)
        if path.exists():
            eye_assets.append(inspect_eye_asset(path, record))
    eye_ledger_path = ASSIGNMENT_ROOT / "eye_asset_measurement_ledger_20260712.json"
    write_json(eye_ledger_path, {
        "schema_version": 1,
        "updated_at": now_iso(),
        "status": "measured_assets_current_candidate_eyes_failed",
        "eye_assets": eye_assets,
        "rule": "The next eye pass must use this ledger and candidate head landmarks before placing/scaling eyes.",
    })

    candidate_checks = [inspect_candidate(candidate_id, path) for candidate_id, path in CANDIDATE_MODELS.items() if path.exists()]
    candidate_eye_path = ASSIGNMENT_ROOT / "candidate_eye_scale_checks_20260712.json"
    write_json(candidate_eye_path, {
        "schema_version": 1,
        "updated_at": now_iso(),
        "status": "failed_redo_required",
        "candidate_checks": candidate_checks,
        "global_verdict": "F - current eyes are not approved; use real eye model class and head landmark map before rebuilding.",
    })

    body_path = ASSIGNMENT_ROOT / "body_measurement_ledger_20260712.json"
    write_json(body_path, {
        "schema_version": 1,
        "updated_at": now_iso(),
        "status": "rough_measurement_started_failed_redo_required",
        "candidate_body_checks": [
            {
                "candidate_id": item["candidate_id"],
                "model": item["model"],
                "body_width": item["body_width"],
                "body_height": item["body_height"],
                "body_mesh": item["body_mesh"],
                "school_grade": "F",
                "policy_note": (
                    "Marinette: non-adult doll-safe only. Gwen: adult anatomy-guided body; no Barbie treatment."
                    if item["candidate_id"] == GWEN_ID
                    else "Normal Marinette remains non-adult doll-safe; do not use adult anatomy."
                ),
            }
            for item in candidate_checks
        ],
        "next_required": "Full head/body landmark maps and silhouette delta morph targets are still needed.",
    })

    paths = {
        "eye_asset_measurement_ledger": rel(eye_ledger_path),
        "candidate_eye_scale_checks": rel(candidate_eye_path),
        "body_measurement_ledger": rel(body_path),
    }
    update_progress(paths)
    print(json.dumps({"ok": True, "outputs": paths}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
