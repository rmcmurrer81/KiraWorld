"""Locate retained surface strips around the V23 superior-pubic dark gap.

This is a read-only engineering diagnostic.  It uses front-view ray samples
and mesh adjacency to identify:

* the lower-abdomen/upper-pubic strip immediately above the visible gap;
* the retained pubic/root strip immediately below the gap; and
* the face/vertex rows that can be cut and stitched by a later hand-authored
  bridge repair.

The candidate .blend is opened but never saved.

Usage:
    blender --background --python \
      tools/blender_inspect_v23_superior_pubic_bridge_strips.py -- \
      candidate.blend output-directory
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


if "--" not in sys.argv:
    raise SystemExit("expected -- candidate.blend output-directory")
arguments = sys.argv[sys.argv.index("--") + 1 :]
if len(arguments) != 2:
    raise SystemExit("expected candidate.blend and output-directory")
source = Path(arguments[0]).resolve()
output = Path(arguments[1]).resolve()
output.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(source))
body = max(
    (obj for obj in bpy.data.objects if obj.type == "MESH"),
    key=lambda obj: len(obj.data.vertices),
)

# Work in the body's local coordinate system.  Current V23 bodies have an
# identity transform, but recording the matrix makes that assumption auditable.
mesh = body.data
bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bvh = BVHTree.FromBMesh(bm)


def rounded_vector(vector: Vector) -> list[float]:
    return [round(value, 7) for value in vector]


def first_front_surface(x: float, z: float) -> dict[str, object] | None:
    """Return the first ray hit and enough data to classify the silhouette."""

    location, normal, face_index, distance = bvh.ray_cast(
        Vector((x, -0.35, z)),
        Vector((0.0, 1.0, 0.0)),
        0.70,
    )
    if location is None:
        return None
    return {
        "x": round(x, 6),
        "z": round(z, 6),
        "hit": rounded_vector(location),
        "normal": rounded_vector(normal),
        "face_index": int(face_index),
        "distance": round(distance, 7),
        # The normal test separates a real anterior/pubic surface from a deep
        # back-side hit through a gap.
        "anterior_facing": normal.y < -0.10,
    }


# Sample the exact projected area in which the dark teardrop appears.  A
# 0.5-mm vertical step is fine enough to locate the two retained surface rows
# without mistaking a single anti-aliased render pixel for geometry.
x_samples = [
    round(-0.030 + index * 0.005, 6)
    for index in range(13)
]
z_samples = [
    round(0.775 + index * 0.0005, 7)
    for index in range(111)
]
ray_columns: dict[str, list[dict[str, object]]] = {}
gap_intervals: dict[str, list[dict[str, float]]] = {}
for x in x_samples:
    column = []
    is_gap = []
    for z in z_samples:
        hit = first_front_surface(x, z)
        if hit is None:
            column.append(
                {
                    "x": x,
                    "z": z,
                    "hit": None,
                    "anterior_facing": False,
                }
            )
            is_gap.append(True)
        else:
            column.append(hit)
            # A deep hit at positive/near-zero Y, or a back-facing hit, means
            # the intended front surface is absent at this projected sample.
            hit_y = hit["hit"][1]
            is_gap.append(
                hit_y > -0.035 or not hit["anterior_facing"]
            )
    ray_columns[f"{x:+.3f}"] = column

    intervals = []
    start = None
    for index, gap in enumerate(is_gap + [False]):
        if gap and start is None:
            start = index
        elif not gap and start is not None:
            end = index - 1
            if end - start + 1 >= 2:
                intervals.append(
                    {
                        "min_z": z_samples[start],
                        "max_z": z_samples[end],
                        "height": round(
                            z_samples[end] - z_samples[start],
                            7,
                        ),
                    }
                )
            start = None
    gap_intervals[f"{x:+.3f}"] = intervals


def face_record(face: bmesh.types.BMFace) -> dict[str, object]:
    return {
        "face_index": face.index,
        "center": rounded_vector(face.calc_center_median()),
        "normal": rounded_vector(face.normal),
        "vertex_indices": [vertex.index for vertex in face.verts],
        "vertex_coordinates": [
            rounded_vector(vertex.co) for vertex in face.verts
        ],
    }


# Pick the nearest valid anterior hit immediately above and below each central
# gap interval.  Expand one adjacency ring so the eventual bridge has a stable
# hand-authored cut row rather than relying on one triangle at each column.
central_interval_candidates = gap_intervals.get("+0.000", [])
central_interval = (
    max(
        (
            item
            for item in central_interval_candidates
            if item["max_z"] >= 0.805
        ),
        key=lambda item: item["height"],
    )
    if central_interval_candidates
    else {"min_z": 0.795, "max_z": 0.818, "height": 0.023}
)


def nearest_valid_face(
    x: float,
    start_z: float,
    direction: float,
) -> bmesh.types.BMFace | None:
    for step in range(1, 81):
        z = start_z + direction * step * 0.0005
        hit = first_front_surface(x, z)
        if (
            hit is not None
            and hit["anterior_facing"]
            and hit["hit"][1] <= -0.035
        ):
            return bm.faces[hit["face_index"]]
    return None


upper_seed_faces: set[bmesh.types.BMFace] = set()
lower_seed_faces: set[bmesh.types.BMFace] = set()
gap_border_samples = []
for x in x_samples:
    if abs(x) > 0.025:
        continue
    upper = nearest_valid_face(
        x,
        central_interval["max_z"],
        +1.0,
    )
    lower = nearest_valid_face(
        x,
        central_interval["min_z"],
        -1.0,
    )
    if upper is not None:
        upper_seed_faces.add(upper)
    if lower is not None:
        lower_seed_faces.add(lower)
    upper_hit = None
    lower_hit = None
    for step in range(1, 81):
        candidate = first_front_surface(
            x,
            central_interval["max_z"] + step * 0.0005,
        )
        if (
            candidate is not None
            and candidate["anterior_facing"]
            and candidate["hit"][1] <= -0.035
        ):
            upper_hit = candidate
            break
    for step in range(1, 81):
        candidate = first_front_surface(
            x,
            central_interval["min_z"] - step * 0.0005,
        )
        if (
            candidate is not None
            and candidate["anterior_facing"]
            and candidate["hit"][1] <= -0.035
        ):
            lower_hit = candidate
            break
    gap_border_samples.append(
        {
            "x": x,
            "upper_border_hit": upper_hit,
            "lower_border_hit": lower_hit,
            "bridge_profile": (
                None
                if upper_hit is None or lower_hit is None
                else {
                    "surface_delta": [
                        round(
                            lower_hit["hit"][axis]
                            - upper_hit["hit"][axis],
                            7,
                        )
                        for axis in range(3)
                    ],
                    "straight_span": round(
                        (
                            Vector(lower_hit["hit"])
                            - Vector(upper_hit["hit"])
                        ).length,
                        7,
                    ),
                    "upper_downward_cross_tangent": rounded_vector(
                        (
                            lambda tangent: (
                                tangent
                                if tangent.z <= 0.0
                                else -tangent
                            )
                        )(
                            Vector(
                                (
                                    0.0,
                                    upper_hit["normal"][2],
                                    -upper_hit["normal"][1],
                                )
                            ).normalized()
                        )
                    ),
                    "lower_downward_cross_tangent": rounded_vector(
                        (
                            lambda tangent: (
                                tangent
                                if tangent.z <= 0.0
                                else -tangent
                            )
                        )(
                            Vector(
                                (
                                    0.0,
                                    lower_hit["normal"][2],
                                    -lower_hit["normal"][1],
                                )
                            ).normalized()
                        )
                    ),
                }
            ),
        }
    )


def grow_faces(
    seeds: set[bmesh.types.BMFace],
    *,
    min_z: float,
    max_z: float,
) -> set[bmesh.types.BMFace]:
    result = set(seeds)
    frontier = set(seeds)
    for _ in range(2):
        following = set()
        for face in frontier:
            for edge in face.edges:
                for neighbor in edge.link_faces:
                    center = neighbor.calc_center_median()
                    if (
                        neighbor not in result
                        and abs(center.x) <= 0.046
                        and -0.185 <= center.y <= -0.025
                        and min_z <= center.z <= max_z
                    ):
                        following.add(neighbor)
        result.update(following)
        frontier = following
    return result


upper_faces = grow_faces(
    upper_seed_faces,
    min_z=central_interval["max_z"] - 0.004,
    max_z=central_interval["max_z"] + 0.017,
)
lower_faces = grow_faces(
    lower_seed_faces,
    min_z=central_interval["min_z"] - 0.017,
    max_z=central_interval["min_z"] + 0.004,
)


def boundary_edges_for_patch(
    faces: set[bmesh.types.BMFace],
) -> list[bmesh.types.BMEdge]:
    return sorted(
        (
            edge
            for face in faces
            for edge in face.edges
            if sum(neighbor in faces for neighbor in edge.link_faces) == 1
        ),
        key=lambda edge: (
            sum(vertex.co.z for vertex in edge.verts) / 2.0,
            sum(vertex.co.x for vertex in edge.verts) / 2.0,
        ),
    )


def edge_record(edge: bmesh.types.BMEdge) -> dict[str, object]:
    midpoint = (edge.verts[0].co + edge.verts[1].co) * 0.5
    return {
        "edge_index": edge.index,
        "midpoint": rounded_vector(midpoint),
        "vertex_indices": [vertex.index for vertex in edge.verts],
        "vertex_coordinates": [
            rounded_vector(vertex.co) for vertex in edge.verts
        ],
        "linked_face_indices": [face.index for face in edge.link_faces],
    }


upper_vertices = {
    vertex for face in upper_faces for vertex in face.verts
}
lower_vertices = {
    vertex for face in lower_faces for vertex in face.verts
}


def strip_vertices(
    vertices: set[bmesh.types.BMVert],
    *,
    lower: bool,
) -> list[dict[str, object]]:
    # Return the patch edge nearest the gap.  For the upper patch that is the
    # lowest Z row; for the lower patch it is the highest Z row.
    if not vertices:
        return []
    target = (
        min(vertex.co.z for vertex in vertices)
        if not lower
        else max(vertex.co.z for vertex in vertices)
    )
    tolerance = 0.0045
    chosen = [
        vertex
        for vertex in vertices
        if abs(vertex.co.z - target) <= tolerance
        and abs(vertex.co.x) <= 0.038
    ]
    return [
        {
            "vertex_index": vertex.index,
            "coordinate": rounded_vector(vertex.co),
            "normal": rounded_vector(vertex.normal),
            "linked_faces": sorted(face.index for face in vertex.link_faces),
        }
        for vertex in sorted(chosen, key=lambda item: (item.co.x, item.co.z))
    ]


# Render a non-destructive color-ID view of the two strips.  This is geometry
# evidence only; no candidate file is saved.
upper_material = bpy.data.materials.new("V23_BRIDGE_UPPER_STRIP")
upper_material.diffuse_color = (0.95, 0.12, 0.08, 1.0)
lower_material = bpy.data.materials.new("V23_BRIDGE_LOWER_STRIP")
lower_material.diffuse_color = (0.05, 0.45, 1.0, 1.0)
other_material = bpy.data.materials.new("V23_BRIDGE_OTHER_SURFACE")
other_material.diffuse_color = (0.52, 0.55, 0.58, 1.0)

body.data.materials.clear()
body.data.materials.append(other_material)
body.data.materials.append(upper_material)
body.data.materials.append(lower_material)
for polygon in body.data.polygons:
    polygon.material_index = 0
for face in upper_faces:
    body.data.polygons[face.index].material_index = 1
for face in lower_faces:
    body.data.polygons[face.index].material_index = 2

for obj in list(bpy.data.objects):
    if obj.type in {"CAMERA", "LIGHT"}:
        bpy.data.objects.remove(obj, do_unlink=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "FLAT"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = False
scene.display.shading.show_cavity = False
scene.display.shading.show_specular_highlight = False
scene.display.shading.background_type = "WORLD"
scene.world.color = (0.025, 0.025, 0.025)
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"

camera_data = bpy.data.cameras.new("V23BridgeStripCamera")
camera = bpy.data.objects.new("V23BridgeStripCamera", camera_data)
bpy.context.collection.objects.link(camera)
camera.location = (0.0, -1.22, 0.785)
camera.rotation_euler = (
    Vector((0.0, -0.045, 0.785)) - camera.location
).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 82
scene.camera = camera
render_path = output / "superior_pubic_bridge_strip_ids_front.png"
scene.render.filepath = str(render_path)
bpy.ops.render.render(write_still=True)

report = {
    "schema": "kira.avatar.v23.superior_pubic_bridge_strip_diagnostic.v1",
    "source_blend": str(source),
    "body_object": body.name,
    "body_matrix_world": [
        [round(value, 7) for value in row] for row in body.matrix_world
    ],
    "diagnostic_only": True,
    "candidate_saved_or_modified": False,
    "front_ray_definition": {
        "origin_y": -0.35,
        "direction": [0.0, 1.0, 0.0],
        "x_samples": x_samples,
        "z_min": min(z_samples),
        "z_max": max(z_samples),
        "z_step": 0.0005,
        "front_surface_max_y": -0.035,
        "front_normal_y_max": -0.10,
    },
    "projected_gap_intervals": gap_intervals,
    "central_gap_interval": central_interval,
    "gap_border_samples": gap_border_samples,
    "upper_strip": {
        "seed_face_indices": sorted(face.index for face in upper_seed_faces),
        "face_indices": sorted(face.index for face in upper_faces),
        "faces": [
            face_record(face)
            for face in sorted(upper_faces, key=lambda item: item.index)
        ],
        "gap_edge_vertices": strip_vertices(upper_vertices, lower=False),
        "patch_boundary_edges": [
            edge_record(edge)
            for edge in boundary_edges_for_patch(upper_faces)
        ],
    },
    "lower_strip": {
        "seed_face_indices": sorted(face.index for face in lower_seed_faces),
        "face_indices": sorted(face.index for face in lower_faces),
        "faces": [
            face_record(face)
            for face in sorted(lower_faces, key=lambda item: item.index)
        ],
        "gap_edge_vertices": strip_vertices(lower_vertices, lower=True),
        "patch_boundary_edges": [
            edge_record(edge)
            for edge in boundary_edges_for_patch(lower_faces)
        ],
    },
    "ray_columns": ray_columns,
    "evidence_render": str(render_path),
}
report_path = output / "SUPERIOR_PUBIC_BRIDGE_STRIP_DIAGNOSTIC.json"
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(report_path)
print(render_path)

bm.free()
