"""Read-only geometry inventory for the final bounded v5 surface repair."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tools.blender_build_profiled_kira_bald_delivery_candidate as r16
from Core.avatar_adult_female_surface_authoring import frame_from_mapping


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    source_path = (PROJECT_ROOT / argv[0]).resolve(strict=True)
    bpy.ops.wm.open_mainfile(filepath=str(source_path), load_ui=False)
    body = max(
        (
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH" and bool(obj.get("primary_surface"))
        ),
        key=lambda obj: len(obj.data.vertices),
    )
    config, _ = r16.load_validated_profiled_candidate_builder_config(PROJECT_ROOT)
    profile = r16._read_json(PROJECT_ROOT / config["style_profile"]["path"])
    prepared = r16.prepare_profiled_body_source(
        base_path=PROJECT_ROOT / config["makehuman_source_set"]["base_body"]["path"],
        female_macros=config["makehuman_source_set"]["female_macros"],
        resolved_style_targets=[dict(row, verified=True) for row in profile["shape_targets"]],
        project_root=PROJECT_ROOT,
        target_height_m=1.651,
    )
    anchors = prepared["body_vertices"]
    surface_config = r16._read_json(
        PROJECT_ROOT
        / "Avatar/avatar_builder/tooling/adult_female_surface_delivery_v4_inactive_refinement.json"
    )
    ratio = 1.651 / float(surface_config["baseline_height_m"])
    frame = r16._scaled_frame(surface_config["front_visible_sheet_frame"], ratio)
    origin = Vector(frame.origin)
    lateral = Vector(frame.lateral_axis)
    longitudinal = Vector(frame.longitudinal_axis)
    outward = Vector(frame.outward_axis)
    original_count = len(anchors)
    mesh_count = len(body.data.vertices)
    original_roi = []
    new_roi = []
    anchor_deltas = []
    for vertex in body.data.vertices:
        relative = vertex.co - origin
        u = float(relative.dot(lateral)) / float(frame.half_width_m)
        v = float(relative.dot(longitudinal)) / float(frame.half_length_m)
        depth = float(relative.dot(outward))
        if abs(u) <= 1.25 and -1.20 <= v <= 1.20 and -0.04 <= depth <= 0.11:
            (original_roi if vertex.index < original_count else new_roi).append(vertex.index)
        if vertex.index < original_count and abs(u) <= 1.25 and -1.20 <= v <= 1.20:
            delta = vertex.co - anchors[vertex.index]
            anchor_deltas.append((float(delta.length), int(vertex.index), u, v, depth, list(delta)))
    anchor_deltas.sort(reverse=True)
    new_indices = set(range(original_count, mesh_count))
    adjacency = {index: set() for index in new_indices}
    anchor_neighbors = {index: set() for index in new_indices}
    for edge in body.data.edges:
        a, b = (int(value) for value in edge.vertices)
        if a in new_indices and b in new_indices:
            adjacency[a].add(b)
            adjacency[b].add(a)
        elif a in new_indices and b < original_count:
            anchor_neighbors[a].add(b)
        elif b in new_indices and a < original_count:
            anchor_neighbors[b].add(a)
    pending = set(new_indices)
    components = []
    while pending:
        seed = min(pending)
        stack = [seed]
        component = set()
        while stack:
            index = stack.pop()
            if index not in pending:
                continue
            pending.remove(index)
            component.add(index)
            stack.extend(adjacency[index].intersection(pending))
        coordinates = [body.data.vertices[index].co for index in component]
        anchors_for_component = {
            anchor
            for index in component
            for anchor in anchor_neighbors[index]
        }
        components.append(
            {
                "size": len(component),
                "minimum_index": min(component),
                "maximum_index": max(component),
                "anchor_neighbor_count": len(anchors_for_component),
                "bounds": {
                    "minimum": [min(float(co[axis]) for co in coordinates) for axis in range(3)],
                    "maximum": [max(float(co[axis]) for co in coordinates) for axis in range(3)],
                },
            }
        )
    components.sort(key=lambda row: int(row["size"]), reverse=True)
    payload = {
        "source": str(source_path),
        "body": body.name,
        "method": body.get("adult_female_surface_detail_method_id"),
        "mesh_vertex_count": mesh_count,
        "original_anchor_count": original_count,
        "new_vertex_count": mesh_count - original_count,
        "front_original_roi_count": len(original_roi),
        "front_new_roi_count": len(new_roi),
        "new_vertex_components": components,
        "prepared_source_keys": sorted(prepared.keys()),
        "mesh_uv_layers": [layer.name for layer in body.data.uv_layers],
        "maximum_anchor_delta_rows": [
            {
                "length": row[0],
                "index": row[1],
                "u": row[2],
                "v": row[3],
                "depth": row[4],
                "delta": row[5],
            }
            for row in anchor_deltas[:40]
        ],
        "properties": {
            "primary_surface": body.get("primary_surface"),
            "adult_female_surface_detail_method_id": body.get(
                "adult_female_surface_detail_method_id"
            ),
            "adult_female_surface_detail_status": body.get(
                "adult_female_surface_detail_status"
            ),
        },
    }
    print("V5_STAGING_INSPECTION=" + json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
