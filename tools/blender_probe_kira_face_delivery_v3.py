"""Render a bounded in-memory comparison of Kira face delivery v3.

The source R16 blend is opened read-only, the qualitative face delta is applied
only in memory, and three diagnostic PNGs plus JSON evidence are written under
RecoverySprint.  No blend, GLB, runtime body, or owner-review candidate is saved.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tools.blender_build_profiled_kira_bald_delivery_candidate as r16
from Core.avatar_profiled_adult_candidate_contract import capture_live_kira_state_hashes
from tools.blender_kira_face_delivery_v3 import apply_kira_face_direction_to_source_v3


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-blend", required=True)
    parser.add_argument("--output-dir", required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def _render(scene: object, camera: object, body: object, path: Path, direction: Vector) -> None:
    low, high = r16.r15._world_bounds([body])  # noqa: SLF001
    target_height = float(high.z - low.z)
    target = Vector((0.0, (low.y + high.y) * 0.5, high.z - target_height * 0.085))
    camera.location = target + direction.normalized() * target_height * 3.0
    r16.r15._look_at(camera, target)  # noqa: SLF001
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = target_height * 0.33
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> int:
    args = _args()
    source_path = (PROJECT_ROOT / args.source_blend).resolve(strict=True)
    output_dir = (PROJECT_ROOT / args.output_dir).resolve()
    output_dir.relative_to(PROJECT_ROOT)
    if output_dir.exists():
        raise RuntimeError("probe output already exists")
    output_dir.mkdir(parents=True, exist_ok=False)
    source_hash = r16.r15.sha256_file(source_path)
    live_before = capture_live_kira_state_hashes(PROJECT_ROOT)

    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    scene = bpy.context.scene
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    body = max(
        (obj for obj in bpy.data.objects if obj.type == "MESH" and obj.get("primary_surface")),
        key=lambda obj: len(obj.data.vertices),
    )
    r16.reset_pose(armature)
    camera = scene.camera or next(obj for obj in bpy.data.objects if obj.type == "CAMERA")
    before_path = output_dir / "face_before_exact_r16.png"
    _render(scene, camera, body, before_path, Vector((0.0, -1.0, 0.01)))

    config, _config_report = r16.load_validated_profiled_candidate_builder_config(PROJECT_ROOT)
    profile = r16._read_json(PROJECT_ROOT / config["style_profile"]["path"])
    resolved_style = [dict(row, verified=True) for row in profile["shape_targets"]]
    source = r16.prepare_profiled_body_source(
        base_path=PROJECT_ROOT / config["makehuman_source_set"]["base_body"]["path"],
        female_macros=config["makehuman_source_set"]["female_macros"],
        resolved_style_targets=resolved_style,
        project_root=PROJECT_ROOT,
        target_height_m=float(profile["dimensions"]["target_height_m"]),
    )
    baseline = [point.copy() for point in source["body_vertices"]]
    report = apply_kira_face_direction_to_source_v3(
        source,
        project_root=PROJECT_ROOT,
        target_height_m=float(profile["dimensions"]["target_height_m"]),
    )
    if len(body.data.vertices) < len(baseline):
        raise RuntimeError("R16 body lost source-stable vertices")
    for index, (before, after) in enumerate(zip(baseline, source["body_vertices"])):
        body.data.vertices[index].co += after - before
    body.data.update()
    bpy.context.view_layer.update()

    front_path = output_dir / "face_after_front.png"
    three_quarter_path = output_dir / "face_after_left_three_quarter.png"
    _render(scene, camera, body, front_path, Vector((0.0, -1.0, 0.01)))
    _render(scene, camera, body, three_quarter_path, Vector((-0.68, -0.73, 0.01)))
    live_after = capture_live_kira_state_hashes(PROJECT_ROOT)
    evidence = {
        "schema_version": 1,
        "status": "IN_MEMORY_FACE_DIRECTION_RENDERED_FOR_VISUAL_SELECTION",
        "source_blend": args.source_blend,
        "source_blend_sha256": source_hash,
        "face_report": report,
        "renders": [
            {"path": before_path.name, "sha256": r16.r15.sha256_file(before_path)},
            {"path": front_path.name, "sha256": r16.r15.sha256_file(front_path)},
            {"path": three_quarter_path.name, "sha256": r16.r15.sha256_file(three_quarter_path)},
        ],
        "blend_saved": False,
        "glb_exported": False,
        "candidate_created": False,
        "runtime_activation_allowed": False,
        "live_state_unchanged": live_before == live_after,
        "live_state_before": live_before,
        "live_state_after": live_after,
        "identity_match_claim_allowed": False,
    }
    (output_dir / "PROBE_EVIDENCE.json").write_text(
        json.dumps(r16.r15._json_safe(evidence), indent=2, sort_keys=True) + "\n",  # noqa: SLF001
        encoding="utf-8",
    )
    print(json.dumps({"status": evidence["status"], "output": args.output_dir}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
