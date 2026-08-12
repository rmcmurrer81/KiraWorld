"""Read-only search for smaller bilateral V1 pelvis openings.

This opens the protected V1 likeness, freezes only the review-time modifiers,
and analyzes symmetric subsets of the existing 11-face-per-side root patch.
It never saves a Blender file or modifies the source.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
)
BODY_NAME = "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1"


def is_root_face(center: Vector) -> bool:
    return abs(center.x) < 0.035 and center.y < -0.02 and 0.70 < center.z < 0.80


def edge_key(edge):
    return tuple(sorted(vertex.index for vertex in edge.verts))


def components_from_edges(edge_pairs):
    adjacency = {}
    for a, b in edge_pairs:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    result = []
    unseen = set(adjacency)
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        group = {seed}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    group.add(neighbor)
                    stack.append(neighbor)
        result.append(group)
    return result, adjacency


def ordered_cycle_from_pairs(edge_pairs):
    components, adjacency = components_from_edges(edge_pairs)
    if len(components) != 1 or {len(adjacency[v]) for v in components[0]} != {2}:
        raise RuntimeError("not a simple cycle")
    start = min(components[0])
    order = [start]
    previous = None
    current = start
    while True:
        choices = [item for item in adjacency[current] if item != previous]
        following = min(choices) if previous is None else choices[0]
        if following == start:
            break
        order.append(following)
        previous, current = current, following
    return order


def path_between(order, start, end, forward=True):
    result = [start]
    index = order.index(start)
    step = 1 if forward else -1
    while result[-1] != end:
        index = (index + step) % len(order)
        result.append(order[index])
    return result


def medial_path_for_cycle(order, coordinates):
    inferior = min(order, key=lambda index: coordinates[index][2])
    superior = max(order, key=lambda index: coordinates[index][2])
    paths = [
        path_between(order, inferior, superior, True),
        path_between(order, inferior, superior, False),
    ]
    return min(
        paths,
        key=lambda path: (
            sum(abs(coordinates[index][0]) for index in path) / len(path),
            len(path),
        ),
    )


def mirror_vertex(vertex, vertices):
    target = Vector((-vertex.co.x, vertex.co.y, vertex.co.z))
    return min(vertices, key=lambda item: (item.co - target).length)


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects.get(BODY_NAME)
if body is None:
    raise RuntimeError("V1 body missing")
for modifier in list(body.modifiers):
    if modifier.type in {"ARMATURE", "CORRECTIVE_SMOOTH"}:
        bpy.context.view_layer.objects.active = body
        body.select_set(True)
        bpy.ops.object.modifier_apply(modifier=modifier.name)

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

root_faces = [face for face in bm.faces if is_root_face(face.calc_center_median())]
root_set = set(root_faces)
face_components = []
unseen_faces = set(root_faces)
while unseen_faces:
    seed = unseen_faces.pop()
    stack = [seed]
    group = {seed}
    while stack:
        face = stack.pop()
        for edge in face.edges:
            for linked in edge.link_faces:
                if linked in unseen_faces and linked in root_set:
                    unseen_faces.remove(linked)
                    group.add(linked)
                    stack.append(linked)
    face_components.append(group)
if sorted(map(len, face_components)) != [11, 11]:
    raise RuntimeError(f"expected two 11-face components, got {list(map(len, face_components))}")
face_components.sort(
    key=lambda group: sum(face.calc_center_median().x for face in group) / len(group)
)
left, right = map(list, face_components)

# Match faces by reflected centroid.
pairs = []
remaining_right = set(right)
for left_face in sorted(left, key=lambda face: face.calc_center_median().z):
    lc = left_face.calc_center_median()
    right_face = min(
        remaining_right,
        key=lambda face: (
            face.calc_center_median()
            - Vector((-lc.x, lc.y, lc.z))
        ).length,
    )
    remaining_right.remove(right_face)
    pairs.append((left_face, right_face))

root_vertices = {vertex for face in root_faces for vertex in face.verts}
mirror = {
    vertex.index: mirror_vertex(vertex, root_vertices).index for vertex in root_vertices
}
coords = {vertex.index: [round(value, 6) for value in vertex.co] for vertex in root_vertices}

pair_records = []
for pair_index, (left_face, right_face) in enumerate(pairs):
    pair_records.append(
        {
            "pair": pair_index,
            "left_face_index": left_face.index,
            "right_face_index": right_face.index,
            "left_center": [
                round(value, 6) for value in left_face.calc_center_median()
            ],
            "right_center": [
                round(value, 6) for value in right_face.calc_center_median()
            ],
            "left_vertices": [vertex.index for vertex in left_face.verts],
            "right_vertices": [vertex.index for vertex in right_face.verts],
        }
    )

shortlist = []
for count in range(1, 12):
    for chosen in itertools.combinations(range(11), count):
        deleted = {
            face
            for pair_index in chosen
            for face in pairs[pair_index]
        }
        # Each deleted side must be face-connected.
        left_deleted = {pairs[index][0] for index in chosen}
        pending = {next(iter(left_deleted))}
        reached = set()
        while pending:
            face = pending.pop()
            reached.add(face)
            for edge in face.edges:
                pending.update(
                    linked
                    for linked in edge.link_faces
                    if linked in left_deleted and linked not in reached
                )
        if reached != left_deleted:
            continue

        boundary = [
            edge
            for edge in {edge for face in deleted for edge in face.edges}
            if sum(linked in deleted for linked in edge.link_faces) == 1
        ]
        edge_pairs = [edge_key(edge) for edge in boundary]
        pre_components, pre_adjacency = components_from_edges(edge_pairs)
        if len(pre_components) != 2:
            continue
        if any(set(len(pre_adjacency[v]) for v in component) != {2} for component in pre_components):
            continue

        # Quotient the bilateral boundary by the lower-|x| route between the
        # inferior and superior junctions on each side.
        parent = {vertex: vertex for edge in edge_pairs for vertex in edge}

        def find(value):
            while parent[value] != value:
                parent[value] = parent[parent[value]]
                value = parent[value]
            return value

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        component_pairs = [
            [pair for pair in edge_pairs if pair[0] in component and pair[1] in component]
            for component in pre_components
        ]
        component_orders = [ordered_cycle_from_pairs(items) for items in component_pairs]
        component_orders.sort(
            key=lambda order: sum(coords[index][0] for index in order) / len(order)
        )
        left_medial = medial_path_for_cycle(component_orders[0], coords)
        right_medial = medial_path_for_cycle(component_orders[1], coords)
        if len(left_medial) != len(right_medial):
            continue
        if coords[left_medial[0]][2] > coords[left_medial[-1]][2]:
            left_medial.reverse()
        if coords[right_medial[0]][2] > coords[right_medial[-1]][2]:
            right_medial.reverse()
        welded_pairs = []
        for left_vertex, right_vertex in zip(left_medial, right_medial):
            union(left_vertex, right_vertex)
            welded_pairs.append((left_vertex, right_vertex))

        quotient_edges = {
            tuple(sorted((find(a), find(b))))
            for a, b in edge_pairs
            if find(a) != find(b)
        }
        post_components, post_adjacency = components_from_edges(quotient_edges)
        if len(post_components) != 1:
            continue
        degree_set = {len(post_adjacency[vertex]) for vertex in post_components[0]}
        if degree_set != {2}:
            continue

        centers = [
            face.calc_center_median()
            for pair_index in chosen
            for face in pairs[pair_index]
        ]
        shortlist.append(
            {
                "chosen_pairs": list(chosen),
                "face_indices": sorted(face.index for face in deleted),
                "faces_per_side": count,
                "max_center_z": max(center.z for center in centers),
                "min_center_z": min(center.z for center in centers),
                "pre_boundary_component_sizes": sorted(map(len, pre_components)),
                "welded_vertex_pairs": welded_pairs,
                "post_boundary_vertex_count": len(post_components[0]),
                "post_boundary_edge_count": len(quotient_edges),
                "post_degree_set": sorted(degree_set),
            }
        )

report = {
    "source": str(SOURCE),
    "root_face_pairs": pair_records,
    "left_pair_adjacency": {
        str(index): sorted(
            other
            for other, (other_face, _) in enumerate(pairs)
            if other != index
            and any(
                edge in other_face.edges
                for edge in pairs[index][0].edges
            )
        )
        for index in range(11)
    },
    "root_vertex_coordinates": {str(index): co for index, co in sorted(coords.items())},
    "shortlist": sorted(
        shortlist,
        key=lambda item: (
            item["faces_per_side"],
            item["max_center_z"],
            item["chosen_pairs"],
        ),
    ),
}

candidate_diagnostics = []
for chosen in (
    (0,),
    (0, 3),
    (0, 2, 3),
    (0, 1, 2, 3),
    (0, 1, 2, 3, 4, 5, 6),
    (0, 1, 2, 3, 4, 5, 6, 8),
    (0, 1, 2, 3, 4, 5, 6, 7, 8),
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
):
    deleted = {face for index in chosen for face in pairs[index]}
    boundary = [
        edge
        for edge in {edge for face in deleted for edge in face.edges}
        if sum(linked in deleted for linked in edge.link_faces) == 1
    ]
    edge_pairs = [edge_key(edge) for edge in boundary]
    comps, adjacency = components_from_edges(edge_pairs)
    cycles = []
    for component in comps:
        component_edges = [
            pair for pair in edge_pairs if pair[0] in component and pair[1] in component
        ]
        order = ordered_cycle_from_pairs(component_edges)
        medial = medial_path_for_cycle(order, coords)
        cycles.append(
            {
                "cycle_size": len(order),
                "cycle": order,
                "cycle_coords": [coords[index] for index in order],
                "medial_size": len(medial),
                "medial": medial,
                "medial_coords": [coords[index] for index in medial],
            }
        )
    cycles.sort(
        key=lambda item: sum(co[0] for co in item["cycle_coords"]) / item["cycle_size"]
    )
    candidate_diagnostics.append(
        {
            "chosen_pairs": chosen,
            "face_indices": sorted(face.index for face in deleted),
            "components": cycles,
        }
    )
report["candidate_diagnostics"] = candidate_diagnostics

baseline_boundary = sum(len(edge.link_faces) == 1 for edge in bm.edges)
baseline_multi = sum(len(edge.link_faces) > 2 for edge in bm.edges)
actual_weld_trials = []
for diagnostic in candidate_diagnostics:
    chosen = diagnostic["chosen_pairs"]
    trial = bm.copy()
    trial.verts.ensure_lookup_table()
    trial.faces.ensure_lookup_table()
    trial_vertices_by_index = {vertex.index: vertex for vertex in trial.verts}
    delete_indices = set(diagnostic["face_indices"])
    trial_faces = [face for face in trial.faces if face.index in delete_indices]

    left_medial = diagnostic["components"][0]["medial"]
    right_medial = diagnostic["components"][1]["medial"]
    if coords[left_medial[0]][2] > coords[left_medial[-1]][2]:
        left_medial = list(reversed(left_medial))
    if coords[right_medial[0]][2] > coords[right_medial[-1]][2]:
        right_medial = list(reversed(right_medial))
    same_error = sum(
        (
            Vector(coords[right_index])
            - Vector((-coords[left_index][0], coords[left_index][1], coords[left_index][2]))
        ).length
        for left_index, right_index in zip(left_medial, right_medial)
    )
    reverse_error = sum(
        (
            Vector(coords[right_index])
            - Vector((-coords[left_index][0], coords[left_index][1], coords[left_index][2]))
        ).length
        for left_index, right_index in zip(left_medial, reversed(right_medial))
    )
    if reverse_error < same_error:
        right_medial = list(reversed(right_medial))

    bmesh.ops.delete(trial, geom=trial_faces, context="FACES")
    pair_coordinates = []
    weld_vertices = []
    for left_index, right_index in zip(left_medial, right_medial):
        left_vertex = trial_vertices_by_index[left_index]
        right_vertex = trial_vertices_by_index[right_index]
        midpoint = (left_vertex.co + right_vertex.co) * 0.5
        midpoint.x = 0.0
        left_vertex.co = midpoint
        right_vertex.co = midpoint
        weld_vertices.extend((left_vertex, right_vertex))
        pair_coordinates.append(
            {
                "left": left_index,
                "right": right_index,
                "midpoint": [round(value, 6) for value in midpoint],
            }
        )
    bmesh.ops.remove_doubles(
        trial, verts=list(dict.fromkeys(weld_vertices)), dist=0.00005
    )
    trial.verts.ensure_lookup_table()
    trial.edges.ensure_lookup_table()
    roi_edges = [
        edge
        for edge in trial.edges
        if len(edge.link_faces) == 1
        and all(
            abs(vertex.co.x) < 0.10
            and -0.22 < vertex.co.y < 0.13
            and 0.62 < vertex.co.z < 0.88
            for vertex in edge.verts
        )
    ]
    roi_pairs = [
        tuple(sorted(vertex.index for vertex in edge.verts)) for edge in roi_edges
    ]
    roi_components, roi_adjacency = components_from_edges(roi_pairs)
    face_signatures = {}
    duplicate_signatures = []
    for face in trial.faces:
        signature = tuple(sorted(vertex.index for vertex in face.verts))
        if signature in face_signatures:
            duplicate_signatures.append(
                (face_signatures[signature].index, face.index)
            )
        else:
            face_signatures[signature] = face
    degenerate_faces = [
        face.index for face in trial.faces if face.calc_area() < 1.0e-10
    ]
    actual_weld_trials.append(
        {
            "chosen_pairs": chosen,
            "face_indices": sorted(delete_indices),
            "weld_pairs": pair_coordinates,
            "global_boundary_delta": sum(
                len(edge.link_faces) == 1 for edge in trial.edges
            )
            - baseline_boundary,
            "global_multi_face_delta": sum(
                len(edge.link_faces) > 2 for edge in trial.edges
            )
            - baseline_multi,
            "degenerate_face_count": len(degenerate_faces),
            "degenerate_face_indices": degenerate_faces[:20],
            "duplicate_face_count": len(duplicate_signatures),
            "duplicate_face_indices": duplicate_signatures[:20],
            "roi_boundary_edges": len(roi_edges),
            "roi_boundary_vertices": sorted(
                (
                    {
                        vertex.index: [round(value, 6) for value in vertex.co]
                        for edge in roi_edges
                        for vertex in edge.verts
                    }
                ).items()
            ),
            "roi_component_vertex_counts": sorted(map(len, roi_components)),
            "roi_degree_sets": [
                sorted({len(roi_adjacency[vertex]) for vertex in component})
                for component in roi_components
            ],
        }
    )
    trial.free()
report["actual_weld_trials"] = actual_weld_trials
output_path = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/V1_MINIMAL_ROOT_PATCH_ANALYSIS.json"
)
output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({
    "output": str(output_path),
    "actual_weld_trials": report["actual_weld_trials"],
}, indent=2))
bm.free()
