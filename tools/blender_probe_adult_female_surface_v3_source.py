"""Read-only density/orientation probe for the v3 adult-surface repair.

Run Blender with the exact candidate or foundation ``.blend`` already open,
then execute this file.  It emits measurements only: it never changes, saves,
renders, exports, selects, or activates an avatar.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

import bmesh
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_adult_female_surface_authoring import SurfaceFrame
from Core.avatar_adult_female_surface_authoring_v2 import (
    FEATURE_SAMPLE_POINTS,
    POSTERIOR_FEATURE_SAMPLE_POINTS,
)
from tools.blender_author_adult_female_external_surface import (
    _local_coordinates,
    _topology_record,
)


CONFIG_PATH = Path(
    "Avatar/avatar_builder/tooling/profiled_adult_candidate_builder_v1.json"
)


def _percentiles(values: Iterable[float]) -> dict[str, float | int]:
    rows = sorted(float(value) for value in values)
    if not rows:
        return {"count": 0, "minimum": 0.0, "p50": 0.0, "p95": 0.0, "maximum": 0.0}

    def at(fraction: float) -> float:
        index = min(len(rows) - 1, max(0, round((len(rows) - 1) * fraction)))
        return rows[index]

    return {
        "count": len(rows),
        "minimum": rows[0],
        "p50": at(0.50),
        "p95": at(0.95),
        "maximum": rows[-1],
    }


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


def _nearest_spacing_m(points: list[tuple[float, float]]) -> dict[str, float | int]:
    if len(points) < 2:
        return _percentiles([])
    tree = KDTree(len(points))
    for index, point in enumerate(points):
        tree.insert(Vector((point[0], point[1], 0.0)), index)
    tree.balance()
    distances: list[float] = []
    for index, point in enumerate(points):
        rows = tree.find_n(Vector((point[0], point[1], 0.0)), 2)
        candidates = [float(distance) for _co, other, distance in rows if other != index]
        if candidates:
            distances.append(min(candidates))
    return _percentiles(distances)


def _frame_report(
    bm: bmesh.types.BMesh,
    frame: SurfaceFrame,
    samples: Mapping[str, tuple[float, float]],
    *,
    label: str,
) -> dict[str, Any]:
    outward = Vector(frame.outward_axis)
    vertices: list[tuple[int, float, float, float, float]] = []
    metric_points: list[tuple[float, float]] = []
    normal_alignments: list[float] = []
    for vert in bm.verts:
        u, v, depth = _local_coordinates(vert.co, frame)
        if u * u + v * v > 0.82 * 0.82 or abs(depth) > frame.max_surface_offset_m:
            continue
        alignment = float(vert.normal.dot(outward))
        vertices.append((int(vert.index), float(u), float(v), float(depth), alignment))
        metric_points.append((float(u) * frame.half_width_m, float(v) * frame.half_length_m))
        normal_alignments.append(alignment)

    selected = {row[0] for row in vertices}
    edge_lengths = [
        float(edge.calc_length())
        for edge in bm.edges
        if all(int(vert.index) in selected for vert in edge.verts)
    ]
    selected_faces = [
        face
        for face in bm.faces
        if all(int(vert.index) in selected for vert in face.verts)
    ]
    face_areas = [float(face.calc_area()) for face in selected_faces]
    nearest: dict[str, Any] = {}
    for name, point in samples.items():
        if not vertices:
            break
        row = min(vertices, key=lambda value: (value[1] - point[0]) ** 2 + (value[2] - point[1]) ** 2)
        nearest[name] = {
            "vertex_index": row[0],
            "nearest_uv": [row[1], row[2]],
            "normalized_distance": math.hypot(row[1] - point[0], row[2] - point[1]),
            "outward_depth_m": row[3],
            "normal_alignment": row[4],
        }

    row_counts: dict[str, int] = {}
    frontmost_centerline_rows: dict[str, Any] = {}
    frontmost_depth_profiles: dict[str, Any] = {}
    for center in (-0.40, -0.20, 0.0, 0.14, 0.28, 0.40):
        row_counts[f"v_{center:+.2f}"] = sum(abs(value[2] - center) <= 0.025 for value in vertices)
        band = [
            value
            for value in vertices
            if abs(value[1]) <= 0.10 and abs(value[2] - center) <= 0.045
        ]
        frontmost = max(band, key=lambda value: value[3], default=None)
        frontmost_centerline_rows[f"v_{center:+.2f}"] = (
            {
                "vertex_index": frontmost[0],
                "uv": [frontmost[1], frontmost[2]],
                "outward_depth_m": frontmost[3],
                "normal_alignment": frontmost[4],
                "band_vertex_count": len(band),
            }
            if frontmost is not None
            else {"band_vertex_count": 0}
        )
        profile: dict[str, Any] = {}
        for u_center in (-0.45, -0.30, -0.20, -0.10, 0.0, 0.10, 0.20, 0.30, 0.45):
            cell = [
                value
                for value in vertices
                if abs(value[1] - u_center) <= 0.055
                and abs(value[2] - center) <= 0.045
            ]
            row = max(cell, key=lambda value: value[3], default=None)
            profile[f"u_{u_center:+.2f}"] = (
                {
                    "depth_m": row[3],
                    "normal_alignment": row[4],
                    "uv": [row[1], row[2]],
                }
                if row is not None
                else None
            )
        frontmost_depth_profiles[f"v_{center:+.2f}"] = profile
    core = [row for row in vertices if abs(row[1]) <= 0.45 and -0.45 <= row[2] <= 0.45]
    return {
        "label": label,
        "frame": {
            "origin": list(frame.origin),
            "lateral_axis": list(frame.lateral_axis),
            "longitudinal_axis": list(frame.longitudinal_axis),
            "outward_axis": list(frame.outward_axis),
            "half_width_m": frame.half_width_m,
            "half_length_m": frame.half_length_m,
            "max_surface_offset_m": frame.max_surface_offset_m,
        },
        "selected_vertex_count": len(vertices),
        "selected_face_count": len(selected_faces),
        "core_vertex_count": len(core),
        "nearest_planar_vertex_spacing_m": _nearest_spacing_m(metric_points),
        "selected_edge_length_m": _percentiles(edge_lengths),
        "selected_face_area_m2": _percentiles(face_areas),
        "normal_alignment": _percentiles(normal_alignments),
        "normalized_uv_bounds": {
            "u": [min((row[1] for row in vertices), default=0.0), max((row[1] for row in vertices), default=0.0)],
            "v": [min((row[2] for row in vertices), default=0.0), max((row[2] for row in vertices), default=0.0)],
            "depth_m": [min((row[3] for row in vertices), default=0.0), max((row[3] for row in vertices), default=0.0)],
        },
        "narrow_longitudinal_row_counts": row_counts,
        "frontmost_centerline_rows": frontmost_centerline_rows,
        "frontmost_depth_profiles": frontmost_depth_profiles,
        "nearest_feature_samples": nearest,
    }


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--object-name")
    parser.add_argument("--json-out")
    return parser.parse_args(argv)


def main() -> None:
    args = _arguments()
    candidates = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and bool(obj.get("primary_surface"))
    ]
    if args.object_name:
        obj = bpy.data.objects.get(args.object_name)
        if obj is None or obj.type != "MESH":
            raise RuntimeError("requested mesh object not found")
    elif len(candidates) == 1:
        obj = candidates[0]
    else:
        raise RuntimeError(f"expected exactly one marked primary surface; found {len(candidates)}")

    config = json.loads((PROJECT_ROOT / CONFIG_PATH).read_text(encoding="utf-8-sig"))
    surface = config["adult_surface_authoring"]
    height = max(float(vertex.co.z) for vertex in obj.data.vertices) - min(
        float(vertex.co.z) for vertex in obj.data.vertices
    )
    scale = height / float(surface["baseline_height_m"])
    main_frame = _scaled_frame(surface["frame"], scale)
    posterior_frame = _scaled_frame(
        surface["structured_detail_refinement"]["posterior_frame"],
        scale,
    )
    # v1/v2 use a tilted plane that spans both the visible ventral sheet and
    # the returning under-body sheet.  This additional camera-front chart is
    # measured explicitly because v3 must not confuse those two surfaces.
    camera_front_frame = SurfaceFrame(
        origin=(0.0, -0.070 * scale, 0.790 * scale),
        lateral_axis=(1.0, 0.0, 0.0),
        longitudinal_axis=(0.0, 0.0, 1.0),
        outward_axis=(0.0, -1.0, 0.0),
        half_width_m=0.045 * scale,
        half_length_m=0.090 * scale,
        max_surface_offset_m=0.090 * scale,
    )
    camera_rear_frame = SurfaceFrame(
        origin=(0.0, 0.050 * scale, 0.820 * scale),
        lateral_axis=(1.0, 0.0, 0.0),
        longitudinal_axis=(0.0, 0.0, 1.0),
        outward_axis=(0.0, 1.0, 0.0),
        half_width_m=0.045 * scale,
        half_length_m=0.070 * scale,
        max_surface_offset_m=0.085 * scale,
    )

    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()
        topology = _topology_record(bm, degeneracy_area_m2=1.0e-12 * scale * scale, include_intersections=False)
        rear_centerline_z_scan: dict[str, Any] = {}
        for baseline_z in (0.62, 0.66, 0.70, 0.74, 0.78, 0.82, 0.86, 0.90, 0.94):
            center_z = baseline_z * scale
            rows = [
                vert
                for vert in bm.verts
                if abs(float(vert.co.x)) <= 0.018 * scale
                and abs(float(vert.co.z) - center_z) <= 0.012 * scale
                and float(vert.normal.y) >= 0.05
            ]
            rear = max(rows, key=lambda vert: float(vert.co.y), default=None)
            rear_centerline_z_scan[f"baseline_z_{baseline_z:.2f}"] = (
                {
                    "vertex_index": int(rear.index),
                    "co": [float(value) for value in rear.co],
                    "normal": [float(value) for value in rear.normal],
                    "candidate_count": len(rows),
                }
                if rear is not None
                else {"candidate_count": 0}
            )
        report = {
            "schema_version": 1,
            "probe_id": "adult_female_continuous_surface_v3_source_density_probe_v1",
            "read_only": True,
            "render_performed": False,
            "export_performed": False,
            "save_performed": False,
            "object_name": obj.name,
            "object_height_m": height,
            "baseline_scale": scale,
            "mesh": topology,
            "rear_centerline_z_scan": rear_centerline_z_scan,
            "main_frame": _frame_report(bm, main_frame, FEATURE_SAMPLE_POINTS, label="ventral_vulvar_frame"),
            "camera_front_frame": _frame_report(
                bm,
                camera_front_frame,
                FEATURE_SAMPLE_POINTS,
                label="camera_front_visible_sheet_frame_v3_probe",
            ),
            "camera_rear_frame": _frame_report(
                bm,
                camera_rear_frame,
                {
                    "fourchette_return": (0.0, -0.45),
                    "perineal_transition": (0.0, -0.18),
                    "anal_recess": (0.0, 0.15),
                },
                label="camera_rear_perineal_anal_sheet_frame_v3_probe",
            ),
            "posterior_frame": _frame_report(
                bm,
                posterior_frame,
                POSTERIOR_FEATURE_SAMPLE_POINTS,
                label="curved_fourchette_perineal_anal_frame",
            ),
        }
    finally:
        bm.free()

    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.json_out:
        output = Path(args.json_out)
        if not output.is_absolute():
            output = PROJECT_ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
