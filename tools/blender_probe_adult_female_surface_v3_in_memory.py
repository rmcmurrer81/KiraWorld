"""Apply the v3 adult-surface refinement in memory and emit probe evidence.

The input ``.blend`` must be opened by Blender before this script runs.  The
process never saves or exports that file and never writes a candidate folder.
Optional close diagnostic PNGs are restricted to the supplied non-candidate
probe directory.
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
from Core.avatar_adult_female_surface_authoring_v3 import parameters_from_mapping
from tools.blender_author_adult_female_external_surface_v3 import (
    refine_existing_continuous_adult_female_surface_v3,
)


CONFIG_PATH = Path(
    "Avatar/avatar_builder/tooling/adult_female_surface_v3_inactive_refinement.json"
)
BUILDER_CONFIG_PATH = Path(
    "Avatar/avatar_builder/tooling/profiled_adult_candidate_builder_v1.json"
)


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
    parser.add_argument("--report-out")
    parser.add_argument("--render-dir")
    return parser.parse_args(argv)


def _primary_surface() -> bpy.types.Object:
    rows = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and bool(obj.get("primary_surface"))
    ]
    if len(rows) != 1:
        raise RuntimeError(f"expected exactly one primary surface; found {len(rows)}")
    return rows[0]


def _write_probe_report(path_value: str, payload: Mapping[str, Any]) -> None:
    output = Path(path_value)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    allowed = (PROJECT_ROOT / "RecoverySprint" / "adult_surface_v3_probe").resolve()
    resolved = output.resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise RuntimeError("probe report path escaped v3 probe root") from exc
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def _render_diagnostics(body: bpy.types.Object, output_dir: Path) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for obj in bpy.context.scene.objects:
        obj.hide_render = obj is not body
    body.hide_render = False

    material = bpy.data.materials.new("v3_probe_neutral_skin")
    material.diffuse_color = (0.38, 0.19, 0.13, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.38, 0.19, 0.13, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.58
    body.data.materials.clear()
    body.data.materials.append(material)

    world = bpy.context.scene.world or bpy.data.worlds.new("v3_probe_world")
    bpy.context.scene.world = world
    world.color = (0.025, 0.025, 0.025)
    for name, location, energy, size in (
        ("key", (-0.60, -0.85, 1.05), 42.0, 0.55),
        ("fill", (0.55, -0.55, 0.78), 26.0, 0.45),
        ("rear_fill", (0.0, 0.75, 0.82), 32.0, 0.45),
    ):
        data = bpy.data.lights.new(f"v3_probe_{name}", type="AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(data.name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = location
        _look_at(obj, Vector((0.0, 0.0, 0.78)))

    camera_data = bpy.data.cameras.new("v3_probe_camera")
    camera_data.lens = 72.0
    camera = bpy.data.objects.new("v3_probe_camera", camera_data)
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
    scene.view_settings.exposure = -0.75
    views = (
        ("front_close", (0.0, -0.54, 0.79), (0.0, -0.06, 0.78)),
        ("left_three_quarter_close", (0.31, -0.47, 0.79), (0.0, -0.055, 0.78)),
        ("right_three_quarter_close", (-0.31, -0.47, 0.79), (0.0, -0.055, 0.78)),
        ("rear_perineal_anal_close", (0.0, 0.54, 0.81), (0.0, 0.025, 0.79)),
        ("left_relationship_profile", (0.46, -0.02, 0.80), (0.0, -0.01, 0.78)),
    )
    outputs: list[dict[str, Any]] = []
    for label, location, target in views:
        camera.location = location
        _look_at(camera, Vector(target))
        path = output_dir / f"{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        outputs.append({"label": label, "path": str(path), "bytes": path.stat().st_size})
    return outputs


def main() -> None:
    args = _args()
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
    detail = legacy["structured_detail_refinement"]
    try:
        report = refine_existing_continuous_adult_female_surface_v3(
            body,
            front_frame=_scaled_frame(config["front_visible_sheet_frame"], scale),
            rear_frame=_scaled_frame(config["rear_anal_sheet_frame"], scale),
            parameters=parameters,
            legacy_v2_frame=_scaled_frame(legacy["frame"], scale),
            legacy_v2_posterior_frame=_scaled_frame(detail["posterior_frame"], scale),
            legacy_v2_relief_scale_m=float(detail["baseline_relief_scale_m"]) * scale,
            legacy_v2_taper_power=int(detail["boundary_taper_power"]),
            front_visible_sheet_minimum_outward_depth_m=float(
                config["surface_selection"]["front_visible_sheet_minimum_outward_depth_m"]
            )
            * scale,
            rear_visible_sheet_minimum_outward_depth_m=float(
                config["surface_selection"]["rear_visible_sheet_minimum_outward_depth_m"]
            )
            * scale,
        )
    except Exception as exc:
        payload = {
            "schema_version": 1,
            "probe_id": "adult_female_surface_v3_in_memory_probe_v1",
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
        if args.report_out:
            _write_probe_report(args.report_out, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        raise
    rendered: list[dict[str, Any]] = []
    if args.render_dir:
        render_dir = Path(args.render_dir)
        if not render_dir.is_absolute():
            render_dir = PROJECT_ROOT / render_dir
        allowed = (PROJECT_ROOT / "RecoverySprint" / "adult_surface_v3_probe").resolve()
        resolved = render_dir.resolve()
        try:
            resolved.relative_to(allowed)
        except ValueError as exc:
            raise RuntimeError("diagnostic render directory escaped v3 probe root") from exc
        rendered = _render_diagnostics(body, resolved)
    payload = {
        "schema_version": 1,
        "probe_id": "adult_female_surface_v3_in_memory_probe_v1",
        "input_blend": bpy.data.filepath,
        "input_never_saved": True,
        "candidate_directory_created": False,
        "export_performed": False,
        "activation_performed": False,
        "object_height_m": height,
        "baseline_scale": scale,
        "detail": report,
        "diagnostic_renders": rendered,
    }
    if args.report_out:
        _write_probe_report(args.report_out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
