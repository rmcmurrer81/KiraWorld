"""Apply appearance v3 to R16 in memory and emit private diagnostic evidence.

This probe never saves a Blend file and never activates, assigns, exports, or
publishes a candidate.  It exists only to prove the reusable adapter executes
against the delivered body and to provide bounded face/torso visual evidence.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import traceback
from typing import Any

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.blender_kira_appearance_delivery_v3 import (  # noqa: E402
    apply_kira_appearance_delivery_v3,
)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(values)


def _look_at(camera: Any, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def _render(scene: Any, camera: Any, path: Path, location: tuple[float, float, float], target: tuple[float, float, float], lens: float) -> dict[str, Any]:
    camera.location = location
    camera.data.lens = float(lens)
    _look_at(camera, Vector(target))
    scene.camera = camera
    scene.render.filepath = str(path)
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)
    return {
        "path": path.name,
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
        "camera_location": list(location),
        "target": list(target),
        "lens_mm": float(lens),
    }


def main() -> None:
    args = _arguments()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise RuntimeError(f"append-only probe output already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    evidence_path = output_dir / "APPEARANCE_V3_IN_MEMORY_EVIDENCE.json"
    source_blend = Path(bpy.data.filepath).resolve(strict=True)
    evidence: dict[str, Any] = {
        "schema_version": 1,
        "evidence_type": "kira_appearance_delivery_v3_in_memory_probe",
        "source_blend": {
            "path": source_blend.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": _sha256_file(source_blend),
        },
        "output_blend_saved": False,
        "runtime_activation_allowed": False,
        "glb_exported": False,
        "status": "STARTED",
    }
    try:
        body = next(
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH" and bool(obj.get("primary_surface"))
        )
        armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
        eye_objects = [
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH"
            and any(token in obj.name.casefold() for token in ("sclera", "disc_"))
        ]
        superseded = [
            obj
            for obj in bpy.data.objects
            if str(obj.get("facial_presentation_role", ""))
            in {"brow", "upper_lash", "upper_lid", "lower_lid"}
        ]
        candidate_id = str(body.get("candidate_id", body.name))
        new_objects, report = apply_kira_appearance_delivery_v3(
            body=body,
            armature=armature,
            eye_objects=eye_objects,
            candidate_id=candidate_id,
            project_root=PROJECT_ROOT,
            superseded_facial_objects=superseded,
        )
        scene = bpy.context.scene
        camera_data = bpy.data.cameras.new("Kira_Appearance_V3_Probe_Camera")
        camera = bpy.data.objects.new("Kira_Appearance_V3_Probe_Camera", camera_data)
        bpy.context.collection.objects.link(camera)
        renders = {
            "face": _render(
                scene,
                camera,
                output_dir / "face_appearance_v3.png",
                (0.0, -0.72, 1.535),
                (0.0, -0.105, 1.535),
                70.0,
            ),
            "torso": _render(
                scene,
                camera,
                output_dir / "torso_skin_tones_v3.png",
                (0.0, -1.12, 1.17),
                (0.0, -0.080, 1.17),
                67.0,
            ),
        }
        evidence.update(
            {
                "status": "ENGINEERING_PASS_VISUAL_REVIEW_REQUIRED",
                "candidate_id": candidate_id,
                "adapter_report": report,
                "new_facial_objects": [obj.name for obj in new_objects],
                "renders": renders,
                "source_blend_saved_or_overwritten": False,
                "body_activation_or_assignment_performed": False,
            }
        )
    except Exception as exc:
        evidence.update(
            {
                "status": "ENGINEERING_FAIL",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )
        evidence_path.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        raise
    evidence_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"evidence": str(evidence_path), "status": evidence["status"]}))


if __name__ == "__main__":
    main()
