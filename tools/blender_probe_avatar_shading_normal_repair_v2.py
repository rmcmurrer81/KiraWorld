"""Append-only before/after rear-scalp visual probe for normal repair v2."""

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

from tools.blender_avatar_human_pose_clearance_v1 import reset_pose_v1  # noqa: E402
from tools.blender_avatar_shading_normal_repair_v2 import (  # noqa: E402
    install_rear_scalp_custom_normal_repair_v2,
)


def _arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-blend", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(values)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounds(body: Any) -> tuple[Vector, Vector]:
    points = [body.matrix_world @ Vector(corner) for corner in body.bound_box]
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def _render(
    *, scene: Any, camera: Any, path: Path, target: Vector, direction: Vector, scale: float
) -> dict[str, Any]:
    camera.location = target + direction.normalized() * max(3.0, float(scale) * 3.2)
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = float(scale)
    scene.camera = camera
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {
        "path": path.name,
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
        "target": list(target),
        "direction": list(direction),
        "ortho_scale_m": float(scale),
    }


def main() -> None:
    args = _arguments()
    source = args.source_blend.resolve(strict=True)
    output_dir = args.output_dir.resolve()
    output_dir.relative_to(PROJECT_ROOT)
    if output_dir.exists():
        raise RuntimeError(f"append-only output already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    evidence_path = output_dir / "SHADING_NORMAL_REPAIR_V2_EVIDENCE.json"
    source_hash_before = _sha256_file(source)
    evidence: dict[str, Any] = {
        "schema_version": 1,
        "evidence_type": "avatar_shading_normal_repair_v2_rear_before_after_probe",
        "status": "STARTED",
        "source_blend": {
            "path": source.relative_to(PROJECT_ROOT).as_posix(),
            "sha256_before": source_hash_before,
        },
        "candidate_created": False,
        "blend_saved": False,
        "runtime_activation_allowed": False,
        "knee_repair_claimed": False,
    }
    try:
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
        scene = bpy.context.scene
        body = next(
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH" and bool(obj.get("primary_surface"))
        )
        armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
        reset_pose_v1(armature)
        camera_data = bpy.data.cameras.new("Shading_Normal_Repair_V2_Probe_Camera")
        camera = bpy.data.objects.new(
            "Shading_Normal_Repair_V2_Probe_Camera", camera_data
        )
        bpy.context.collection.objects.link(camera)
        low, high = _bounds(body)
        height = float(high.z - low.z)
        mid_y = (low.y + high.y) * 0.5
        target = Vector((0.0, mid_y, high.z - height * 0.085))
        direction = Vector((0.0, 1.0, 0.01))
        scale = height * 0.36
        baseline = _render(
            scene=scene,
            camera=camera,
            path=output_dir / "baseline_rear_scalp_hairline.png",
            target=target,
            direction=direction,
            scale=scale,
        )
        repair = install_rear_scalp_custom_normal_repair_v2(
            body=body,
            armature=armature,
            project_root=PROJECT_ROOT,
        )
        repaired = _render(
            scene=scene,
            camera=camera,
            path=output_dir / "repaired_rear_scalp_hairline.png",
            target=target,
            direction=direction,
            scale=scale,
        )
        source_hash_after = _sha256_file(source)
        if source_hash_after != source_hash_before:
            raise RuntimeError("source staging Blend changed during no-save probe")
        evidence.update(
            {
                "status": "ENGINEERING_PASS_OWNER_VISUAL_REVIEW_REQUIRED",
                "repair": repair,
                "renders": {"baseline_rear_scalp": baseline, "repaired_rear_scalp": repaired},
                "render_hash_changed": baseline["sha256"] != repaired["sha256"],
                "source_blend_sha256_after": source_hash_after,
                "source_blend_unchanged": True,
                "blend_saved": False,
                "candidate_created": False,
                "scalp_hair_objects_created": 0,
                "knee_geometry_normals_materials_or_pose_changed": False,
                "knee_repair_claimed": False,
                "owner_visual_review_required": True,
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
    print(json.dumps({"status": evidence["status"], "evidence": str(evidence_path)}))


if __name__ == "__main__":
    main()
