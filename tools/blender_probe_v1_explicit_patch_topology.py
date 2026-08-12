"""Inspect the bounded V1 pelvis patch used by the explicit V23 trial."""

from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects["BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"]
mesh = body.data

patch_faces = [
    polygon
    for polygon in mesh.polygons
    if (
        abs(polygon.center.x) <= 0.10
        and 0.62 <= polygon.center.z <= 0.88
        and -0.22 <= polygon.center.y <= 0.13
    )
]
patch_face_indices = {polygon.index for polygon in patch_faces}
patch_vertex_indices = {
    vertex_index for polygon in patch_faces for vertex_index in polygon.vertices
}
kept_vertex_indices = {
    vertex_index
    for polygon in mesh.polygons
    if polygon.index not in patch_face_indices
    for vertex_index in polygon.vertices
}
boundary = patch_vertex_indices & kept_vertex_indices
interior = patch_vertex_indices - boundary

print("patch_faces", len(patch_faces))
print("patch_vertices", len(patch_vertex_indices))
print("boundary_vertices", len(boundary))
print("interior_vertices", len(interior))
for label, members in (("boundary", boundary), ("interior", interior)):
    points = [mesh.vertices[index].co for index in members]
    print(
        label,
        "bounds",
        (min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)),
        (max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)),
    )

front_candidates = []
for polygon in patch_faces:
    if polygon.center.y < -0.07 and 0.68 < polygon.center.z < 0.82:
        front_candidates.append(
            (
                polygon.index,
                tuple(round(value, 5) for value in polygon.center),
                tuple(polygon.vertices),
                polygon.material_index,
            )
        )
print("front_candidate_faces", len(front_candidates))
for item in sorted(front_candidates, key=lambda row: (row[1][2], row[1][0]))[:100]:
    print(item)

patch_adjacency = {polygon.index: set() for polygon in patch_faces}
edge_to_patch_faces = {}
for polygon in patch_faces:
    for edge_key in polygon.edge_keys:
        edge_to_patch_faces.setdefault(edge_key, []).append(polygon.index)
for face_indices in edge_to_patch_faces.values():
    for first in face_indices:
        patch_adjacency[first].update(index for index in face_indices if index != first)
unseen_patch = set(patch_adjacency)
patch_components = []
while unseen_patch:
    stack = [unseen_patch.pop()]
    members = set(stack)
    while stack:
        current = stack.pop()
        for neighbor in patch_adjacency[current]:
            if neighbor in unseen_patch:
                unseen_patch.remove(neighbor)
                members.add(neighbor)
                stack.append(neighbor)
    patch_components.append(members)
print("patch_face_components", sorted((len(component) for component in patch_components), reverse=True))
cross_midline = []
for polygon in patch_faces:
    xs = [mesh.vertices[index].co.x for index in polygon.vertices]
    if min(xs) <= 0.0 <= max(xs):
        cross_midline.append(
            (
                polygon.index,
                tuple(round(value, 5) for value in polygon.center),
                tuple(polygon.vertices),
                min(xs),
                max(xs),
            )
        )
print("cross_midline_faces", len(cross_midline))
for item in sorted(cross_midline, key=lambda row: (row[1][2], row[1][1])):
    print("cross", item)

for label, face_ids in {
    "root_2x2": {10741, 6168, 10740, 6167},
    "root_2x3": {10741, 6168, 10740, 6167, 10728, 6155},
    "root_central_2x3": {10119, 5547, 10417, 5845, 10520, 5948},
    "root_central_2x2": {10417, 5845, 10520, 5948},
    "root_coordinate_region": {
        polygon.index
        for polygon in patch_faces
        if (
            abs(polygon.center.x) < 0.035
            and polygon.center.y < -0.02
            and 0.70 < polygon.center.z < 0.80
        )
    },
    "root_connected_upper_region": {
        polygon.index
        for polygon in patch_faces
        if (
            abs(polygon.center.x) < 0.052
            and polygon.center.y < -0.02
            and 0.69 < polygon.center.z < 0.84
        )
    },
}.items():
    chosen = [mesh.polygons[index] for index in face_ids]
    counts = {}
    for polygon in chosen:
        for edge_key in polygon.edge_keys:
            counts[edge_key] = counts.get(edge_key, 0) + 1
    edge_keys = [edge_key for edge_key, count in counts.items() if count == 1]
    members = {index for edge_key in edge_keys for index in edge_key}
    points = [mesh.vertices[index].co for index in members]
    boundary_adjacency = {index: set() for index in members}
    for first, second in edge_keys:
        boundary_adjacency[first].add(second)
        boundary_adjacency[second].add(first)
    unseen = set(members)
    components = []
    while unseen:
        stack = [unseen.pop()]
        component = set(stack)
        while stack:
            current = stack.pop()
            for neighbor in boundary_adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    stack.append(neighbor)
        components.append(component)
    print(
        label,
        "faces",
        len(chosen),
        "boundary",
        len(edge_keys),
        "bounds",
        (min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)),
        (max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)),
        "verts",
        sorted(members),
        "components",
        [len(component) for component in components],
        "degree_set",
        sorted({len(boundary_adjacency[index]) for index in members}),
    )
