"""In-memory bounded diagnostic for the delivery adult-surface component.

The input candidate is opened by Blender.  This script never saves it, never
exports, never creates an avatar candidate directory and never activates or
assigns anything.  It may write only append-only evidence beneath
``RecoverySprint/adult_surface_delivery_probe``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import SurfaceFrame
from Core.avatar_adult_female_surface_authoring_delivery_v1 import parameters_from_mapping
from tools.blender_author_adult_female_external_surface_delivery_v1 import (
    refine_existing_continuous_adult_female_surface_delivery_v1,
)


CONFIG_PATH = Path(
    "Avatar/avatar_builder/tooling/adult_female_surface_delivery_v1_inactive_refinement.json"
)
BUILDER_CONFIG_PATH = Path(
    "Avatar/avatar_builder/tooling/profiled_adult_candidate_builder_v1.json"
)
ALLOWED_ROOT = (PROJECT_ROOT / "RecoverySprint" / "adult_surface_delivery_probe").resolve()


def _scaled_frame(raw: Mapping[str, Any], scale: float) -> SurfaceFrame:
    return SurfaceFrame(
        origin=tuple(float(value) * scale for value in raw["origin"]),
        lateral_axis=tuple(float(value) for value in raw["lateral_axis"]),
        longitudinal_axis=tuple(float(value) for value in raw["longitudinal_axis"]),
        outward_axis=tuple(float(value) for value in raw["outward_axis"]),
        half_width_m=float(raw["half_width_m"]) * scale,
        half_length_m=float(raw["half_length_m"]) * scale,
        max_surface_offset_m=float(raw["max_surface_offset_m"]) * scale,
    )


def _args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-out", required=True)
    parser.add_argument("--render-dir", required=True)
    return parser.parse_args(argv)


def _within_allowed(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    resolved = path.resolve()
    try:
        resolved.relative_to(ALLOWED_ROOT)
    except ValueError as exc:
        raise RuntimeError("delivery probe output escaped append-only evidence root") from exc
    return resolved


def _primary_surface() -> bpy.types.Object:
    rows = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and bool(obj.get("primary_surface"))
    ]
    if len(rows) != 1:
        raise RuntimeError(f"expected exactly one primary surface; found {len(rows)}")
    return rows[0]


def _write_report(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RuntimeError(f"append-only probe report already exists: {path}")
    path.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def _render_diagnostics(body: bpy.types.Object, output_dir: Path) -> list[dict[str, Any]]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"append-only render directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for obj in bpy.context.scene.objects:
        obj.hide_render = obj is not body
    body.hide_render = False

    material = bpy.data.materials.new("delivery_probe_warm_neutral_skin")
    material.diffuse_color = (0.28, 0.105, 0.065, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.28, 0.105, 0.065, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.64
    body.data.materials.clear()
    body.data.materials.append(material)

    world = bpy.context.scene.world or bpy.data.worlds.new("delivery_probe_world")
    bpy.context.scene.world = world
    world.color = (0.012, 0.012, 0.014)
    lights = (
        ("left_rake", (-0.62, -0.48, 0.93), 34.0, 0.34, (0.0, -0.035, 0.78)),
        ("right_fill", (0.55, -0.42, 0.80), 20.0, 0.42, (0.0, -0.035, 0.78)),
        ("rear_rake", (-0.34, 0.52, 0.91), 31.0, 0.32, (0.0, 0.02, 0.79)),
        ("torso_fill", (0.42, -0.58, 1.42), 28.0, 0.46, (0.0, -0.05, 1.18)),
    )
    for name, location, energy, size, target in lights:
        data = bpy.data.lights.new(f"delivery_probe_{name}", type="AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(data.name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = location
        _look_at(obj, Vector(target))

    camera_data = bpy.data.cameras.new("delivery_probe_camera")
    camera_data.lens = 78.0
    camera = bpy.data.objects.new("delivery_probe_camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.15
    views = (
        ("front_close", (0.0, -0.54, 0.79), (0.0, -0.055, 0.78), 78.0),
        ("left_three_quarter_close", (0.31, -0.47, 0.79), (0.0, -0.05, 0.78), 78.0),
        ("right_three_quarter_close", (-0.31, -0.47, 0.79), (0.0, -0.05, 0.78), 78.0),
        ("rear_perineal_anal_close", (0.0, 0.54, 0.81), (0.0, 0.025, 0.79), 78.0),
        ("left_relationship_profile", (0.46, -0.02, 0.80), (0.0, -0.01, 0.78), 78.0),
        ("torso_front_relief", (0.0, -0.76, 1.19), (0.0, -0.055, 1.18), 74.0),
        ("torso_left_three_quarter", (0.37, -0.69, 1.20), (0.0, -0.045, 1.18), 74.0),
    )
    outputs: list[dict[str, Any]] = []
    for label, location, target, lens in views:
        camera.data.lens = lens
        camera.location = location
        _look_at(camera, Vector(target))
        path = output_dir / f"{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        outputs.append({"label": label, "path": str(path), "bytes": path.stat().st_size})
    return outputs


def main() -> None:
    args = _args()
    report_path = _within_allowed(args.report_out)
    render_dir = _within_allowed(args.render_dir)
    body = _primary_surface()
    config = json.loads((PROJECT_ROOT / CONFIG_PATH).read_text(encoding="utf-8-sig"))
    builder = json.loads((PROJECT_ROOT / BUILDER_CONFIG_PATH).read_text(encoding="utf-8-sig"))
    height = max(float(vertex.co.z) for vertex in body.data.vertices) - min(
        float(vertex.co.z) for vertex in body.data.vertices
    )
    scale = height / float(config["baseline_height_m"])
    parameter_values = dict(config["parameters"])
    parameter_values["front_prominence_scale_m"] *= scale
    parameter_values["rear_prominence_scale_m"] *= scale
    parameter_values["degeneracy_area_m2"] *= scale * scale
    parameters = parameters_from_mapping(parameter_values)
    legacy = builder["adult_surface_authoring"]
    detail_config = legacy["structured_detail_refinement"]
    try:
        detail = refine_existing_continuous_adult_female_surface_delivery_v1(
            body,
            front_frame=_scaled_frame(config["front_visible_sheet_frame"], scale),
            rear_frame=_scaled_frame(config["rear_anal_sheet_frame"], scale),
            parameters=parameters,
            legacy_v2_frame=_scaled_frame(legacy["frame"], scale),
            legacy_v2_posterior_frame=_scaled_frame(detail_config["posterior_frame"], scale),
            legacy_v2_relief_scale_m=float(detail_config["baseline_relief_scale_m"]) * scale,
            legacy_v2_taper_power=int(detail_config["boundary_taper_power"]),
            legacy_v2_minimum_normal_alignment=float(
                config["legacy_v2_full_field_removal"]["minimum_normal_alignment_from_v1_base"]
            ),
            front_visible_sheet_minimum_outward_depth_m=float(
                config["surface_selection"]["front_visible_sheet_minimum_outward_depth_m"]
            )
            * scale,
            rear_visible_sheet_minimum_outward_depth_m=float(
                config["surface_selection"]["rear_visible_sheet_minimum_outward_depth_m"]
            )
            * scale,
            body_scale=scale,
        )
    except Exception as exc:
        payload = {
            "schema_version": 1,
            "probe_id": "adult_female_surface_delivery_v1_in_memory_probe",
            "status": "FAILED_BEFORE_DIAGNOSTIC_RENDER",
            "input_blend": bpy.data.filepath,
            "input_never_saved": True,
            "candidate_directory_created": False,
            "export_performed": False,
            "activation_performed": False,
            "object_height_m": height,
            "baseline_scale": scale,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
            "diagnostic_renders": [],
        }
        _write_report(report_path, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        raise

    rendered = _render_diagnostics(body, render_dir)
    payload = {
        "schema_version": 1,
        "probe_id": "adult_female_surface_delivery_v1_in_memory_probe",
        "status": "INACTIVE_COMPONENT_DIAGNOSTIC_RENDERED_AWAITING_VISUAL_REVIEW",
        "input_blend": bpy.data.filepath,
        "input_never_saved": True,
        "candidate_directory_created": False,
        "export_performed": False,
        "activation_performed": False,
        "object_height_m": height,
        "baseline_scale": scale,
        "detail": detail,
        "diagnostic_renders": rendered,
    }
    _write_report(report_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
