"""Read-only topology/locality audit for the preserved BlackProject Attempt 02.

The worker opens the preserved R19 reconstruction probe, records every exact
nonadjacent intersection with its source-topology identity and boundary-ring
distance, compares those pairs with the immutable CC BY 4.0 GLB, and compares
the unchanged 34-point interface with the sealed R19 body used by R24.  It
does not alter or save a Blend and it does not render.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.blender_exact_mesh_intersections import (  # noqa: E402
    exact_nonadjacent_intersection_report,
)


ATTEMPT02_BLEND = ROOT / (
    "RecoverySprint/continuation_20260802/r19_blackproject_patch_reconstruction/"
    "attempt_02/r19_patch_reconstruction_probe.blend"
)
ATTEMPT02_BLEND_SHA256 = (
    "47cbf26279bc3b75076caf43f96c1c3441dd86e48ad0c404f7a45504985add4d"
)
SOURCE_GLB = ROOT / (
    "Avatar/avatar_builder/asset_library/base_body_reference/"
    "base_female_character_blackproject_cc_by_4.glb"
)
SOURCE_GLB_SHA256 = (
    "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"
)
R24_SOURCE_BLEND = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/"
    "attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
)
R24_SOURCE_BLEND_SHA256 = (
    "dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f"
)
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260807/"
    "r24_blackproject_patch_reconstruction_diagnostic/attempt_01"
)
ADULT_MESH_NAME = "Ariel_Mesh_Genitalia_0"
R24_BODY_NAME = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
R24_PATCH_MATERIAL_INDEX = 5


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def vector_record(value: Vector) -> list[float]:
    return [round(float(component), 12) for component in value]


def boundary_cycle_for_standalone_mesh(
    obj: bpy.types.Object,
) -> tuple[list[int], list[tuple[int, int]]]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    boundary_edges = [edge for edge in bm.edges if len(edge.link_faces) == 1]
    adjacency: dict[int, set[int]] = {}
    for edge in boundary_edges:
        first, second = (int(vertex.index) for vertex in edge.verts)
        adjacency.setdefault(first, set()).add(second)
        adjacency.setdefault(second, set()).add(first)
    if not adjacency or any(len(neighbors) != 2 for neighbors in adjacency.values()):
        bm.free()
        raise RuntimeError("standalone patch boundary is not one simple cycle")
    start = min(adjacency)
    cycle = [start]
    previous = None
    current = start
    while True:
        candidates = sorted(value for value in adjacency[current] if value != previous)
        next_value = candidates[0]
        if next_value == start:
            break
        cycle.append(next_value)
        previous, current = current, next_value
        if len(cycle) > len(adjacency):
            bm.free()
            raise RuntimeError("boundary traversal exceeded boundary vertex count")
    edges = sorted(
        tuple(sorted((int(edge.verts[0].index), int(edge.verts[1].index))))
        for edge in boundary_edges
    )
    bm.free()
    return cycle, edges


def vertex_distance_from_boundary(
    obj: bpy.types.Object,
    boundary: set[int],
) -> dict[int, int]:
    adjacency: dict[int, set[int]] = {index: set() for index in range(len(obj.data.vertices))}
    for edge in obj.data.edges:
        first, second = map(int, edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)
    distances = {index: 0 for index in boundary}
    queue = deque(sorted(boundary))
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current]:
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    return distances


def exact_report(obj: bpy.types.Object) -> dict:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    report = exact_nonadjacent_intersection_report(bm, include_pair_details=True)
    bm.free()
    return report


def world_bounds(points: list[Vector]) -> dict[str, list[float]]:
    return {
        "min": [round(min(float(point[axis]) for point in points), 12) for axis in range(3)],
        "max": [round(max(float(point[axis]) for point in points), 12) for axis in range(3)],
    }


def pair_components(pairs: list[dict]) -> list[dict]:
    remaining = {
        tuple(map(int, record["face_indices"])): record for record in pairs
    }
    face_to_pairs: dict[int, set[tuple[int, int]]] = {}
    for key in remaining:
        for face in key:
            face_to_pairs.setdefault(face, set()).add(key)
    components = []
    seen: set[tuple[int, int]] = set()
    for seed in sorted(remaining):
        if seed in seen:
            continue
        queue = deque([seed])
        seen.add(seed)
        keys = []
        while queue:
            current = queue.popleft()
            keys.append(current)
            for face in current:
                for neighbor in face_to_pairs[face]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        queue.append(neighbor)
        components.append(
            {
                "pair_count": len(keys),
                "face_indices": sorted({face for key in keys for face in key}),
                "pairs": [list(key) for key in sorted(keys)],
            }
        )
    return components


def capture_attempt02() -> dict:
    bpy.ops.wm.open_mainfile(filepath=str(ATTEMPT02_BLEND), load_ui=False)
    obj = next(
        (
            value
            for value in bpy.data.objects
            if value.type == "MESH" and value.data.name == ADULT_MESH_NAME
        ),
        None,
    )
    if obj is None:
        raise RuntimeError("Attempt 02 adult patch not found")
    cycle, boundary_edges = boundary_cycle_for_standalone_mesh(obj)
    boundary = set(cycle)
    distances = vertex_distance_from_boundary(obj, boundary)
    report = exact_report(obj)
    faces = {
        int(face.index): list(map(int, face.vertices)) for face in obj.data.polygons
    }
    details = []
    involved_vertices: set[int] = set()
    involved_faces: set[int] = set()
    world_points_all: list[Vector] = []
    for record in report["pairs"]:
        if not record["genuine_positive_area_or_segment_penetration"]:
            continue
        first, second = map(int, record["face_indices"])
        face_vertices = [faces[first], faces[second]]
        vertices = sorted({value for row in face_vertices for value in row})
        involved_vertices.update(vertices)
        involved_faces.update((first, second))
        world_points = [obj.matrix_world @ obj.data.vertices[index].co for index in vertices]
        world_points_all.extend(world_points)
        world_centers = [
            obj.matrix_world
            @ sum(
                (obj.data.vertices[index].co for index in faces[face_index]),
                Vector((0.0, 0.0, 0.0)),
            )
            / float(len(faces[face_index]))
            for face_index in (first, second)
        ]
        details.append(
            {
                "face_indices": [first, second],
                "face_vertex_indices": face_vertices,
                "involved_vertex_indices": vertices,
                "minimum_vertex_ring_distance_from_34_seam": min(
                    distances[index] for index in vertices
                ),
                "maximum_vertex_ring_distance_from_34_seam": max(
                    distances[index] for index in vertices
                ),
                "topology_edge_hops_between_faces": record["topology_edge_hops"],
                "local_face_centers_source_cm": record["face_centers"],
                "world_face_centers_m": [vector_record(value) for value in world_centers],
                "world_combined_bounds_m": world_bounds(world_points),
                "triangle_pair_classifications": record[
                    "triangle_pair_classifications"
                ],
            }
        )
    boundary_world = [obj.matrix_world @ obj.data.vertices[index].co for index in cycle]
    return {
        "object_name": obj.name,
        "mesh_name": obj.data.name,
        "object_matrix_world": [list(map(float, row)) for row in obj.matrix_world],
        "vertex_count": len(obj.data.vertices),
        "edge_count": len(obj.data.edges),
        "face_count": len(obj.data.polygons),
        "faces": [faces[index] for index in range(len(faces))],
        "coordinates_local": [vector_record(vertex.co) for vertex in obj.data.vertices],
        "boundary_cycle_vertex_indices": cycle,
        "boundary_edges": [list(value) for value in boundary_edges],
        "boundary_world_m": [vector_record(value) for value in boundary_world],
        "boundary_world_sha256": sha256_json(
            sorted(vector_record(value) for value in boundary_world)
        ),
        "exact_report": report,
        "genuine_pair_details": details,
        "genuine_pair_components_by_shared_face": pair_components(details),
        "involved_face_indices": sorted(involved_faces),
        "involved_vertex_indices": sorted(involved_vertices),
        "involved_vertex_count": len(involved_vertices),
        "minimum_involved_vertex_ring_distance_from_34_seam": min(
            (distances[index] for index in involved_vertices), default=None
        ),
        "maximum_involved_vertex_ring_distance_from_34_seam": max(
            (distances[index] for index in involved_vertices), default=None
        ),
        "combined_world_bounds_m": world_bounds(world_points_all),
    }


def capture_source() -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE_GLB))
    imported = set(bpy.data.objects) - before
    obj = next(
        (
            value
            for value in imported
            if value.type == "MESH" and value.data.name == ADULT_MESH_NAME
        ),
        None,
    )
    if obj is None:
        raise RuntimeError("immutable source adult patch not found")
    cycle, boundary_edges = boundary_cycle_for_standalone_mesh(obj)
    report = exact_report(obj)
    boundary_world = [obj.matrix_world @ obj.data.vertices[index].co for index in cycle]
    return {
        "vertex_count": len(obj.data.vertices),
        "edge_count": len(obj.data.edges),
        "face_count": len(obj.data.polygons),
        "faces": [list(map(int, face.vertices)) for face in obj.data.polygons],
        "coordinates_local": [vector_record(vertex.co) for vertex in obj.data.vertices],
        "boundary_cycle_vertex_indices": cycle,
        "boundary_edges": [list(value) for value in boundary_edges],
        "boundary_world_m": [vector_record(value) for value in boundary_world],
        "boundary_world_sha256": sha256_json(
            sorted(vector_record(value) for value in boundary_world)
        ),
        "exact_report": report,
    }


def capture_r24_source_interface() -> dict:
    bpy.ops.wm.open_mainfile(filepath=str(R24_SOURCE_BLEND), load_ui=False)
    body = bpy.data.objects.get(R24_BODY_NAME)
    if body is None or body.type != "MESH":
        raise RuntimeError("sealed R19/R24 source body not found")
    patch_faces = {
        int(face.index)
        for face in body.data.polygons
        if int(face.material_index) == R24_PATCH_MATERIAL_INDEX
    }
    patch_vertices = {
        int(index)
        for face_index in patch_faces
        for index in body.data.polygons[face_index].vertices
    }
    edge_membership: dict[tuple[int, int], list[int]] = {}
    for face in body.data.polygons:
        values = list(map(int, face.vertices))
        is_patch = int(face.index) in patch_faces
        for index in range(len(values)):
            key = tuple(sorted((values[index], values[(index + 1) % len(values)])))
            counts = edge_membership.setdefault(key, [0, 0])
            counts[0 if is_patch else 1] += 1
    boundary_edges = {
        key
        for key, (linked_patch, linked_nonpatch) in edge_membership.items()
        if linked_patch == 1 and linked_nonpatch == 1
    }
    boundary_vertices = sorted({value for edge in boundary_edges for value in edge})
    boundary_world = [
        body.matrix_world @ body.data.vertices[index].co for index in boundary_vertices
    ]
    return {
        "body": body.name,
        "patch_material_index": R24_PATCH_MATERIAL_INDEX,
        "patch_face_count": len(patch_faces),
        "patch_vertex_count": len(patch_vertices),
        "boundary_vertex_indices": boundary_vertices,
        "boundary_edges": [list(value) for value in sorted(boundary_edges)],
        "boundary_world_m": [vector_record(value) for value in boundary_world],
        "boundary_world_sha256": sha256_json(
            sorted(vector_record(value) for value in boundary_world)
        ),
    }


def nearest_interface_comparison(
    first: list[list[float]], second: list[list[float]]
) -> dict:
    first_vectors = [Vector(value) for value in first]
    second_vectors = [Vector(value) for value in second]
    mapping = []
    used: set[int] = set()
    for first_index, point in enumerate(first_vectors):
        candidates = sorted(
            ((point - other).length, second_index)
            for second_index, other in enumerate(second_vectors)
        )
        distance, second_index = candidates[0]
        mapping.append(
            {
                "first_index": first_index,
                "second_index": second_index,
                "distance_m": float(distance),
            }
        )
        used.add(second_index)
    return {
        "first_count": len(first_vectors),
        "second_count": len(second_vectors),
        "bijection": len(mapping) == len(first_vectors) == len(second_vectors) == len(used),
        "maximum_nearest_distance_m": max(
            (record["distance_m"] for record in mapping), default=None
        ),
        "mapping": mapping,
    }


def main() -> None:
    for path, expected in (
        (ATTEMPT02_BLEND, ATTEMPT02_BLEND_SHA256),
        (SOURCE_GLB, SOURCE_GLB_SHA256),
        (R24_SOURCE_BLEND, R24_SOURCE_BLEND_SHA256),
    ):
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"bound input hash mismatch: {path}")
    if OUTPUT.exists():
        raise RuntimeError(f"append-only output already exists: {OUTPUT}")

    attempt = capture_attempt02()
    source = capture_source()
    r24 = capture_r24_source_interface()

    attempt_pairs = {
        tuple(map(int, record["face_indices"]))
        for record in attempt["genuine_pair_details"]
    }
    source_pairs = {
        tuple(map(int, record["face_indices"]))
        for record in source["exact_report"]["pairs"]
        if record["genuine_positive_area_or_segment_penetration"]
    }
    changed = []
    for index, (before, after) in enumerate(
        zip(source["coordinates_local"], attempt["coordinates_local"])
    ):
        distance = (Vector(after) - Vector(before)).length
        if distance > 1.0e-10:
            changed.append({"vertex_index": index, "movement_source_cm": float(distance)})

    report = {
        "schema": "kira.avatar.r24.blackproject_attempt02_intersection_topology.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_NO_RENDER_NO_SAVE",
        "authority": {
            "source_license": "CC BY 4.0",
            "source_use": "licensed derivative investigation only",
            "source_overwritten": False,
            "runtime_activation_or_assignment": False,
        },
        "inputs": {
            "attempt02_blend": {
                "path": str(ATTEMPT02_BLEND.relative_to(ROOT)).replace("\\", "/"),
                "sha256": ATTEMPT02_BLEND_SHA256,
            },
            "immutable_source_glb": {
                "path": str(SOURCE_GLB.relative_to(ROOT)).replace("\\", "/"),
                "sha256": SOURCE_GLB_SHA256,
            },
            "r24_source_blend": {
                "path": str(R24_SOURCE_BLEND.relative_to(ROOT)).replace("\\", "/"),
                "sha256": R24_SOURCE_BLEND_SHA256,
            },
        },
        "attempt02": {
            key: value
            for key, value in attempt.items()
            if key not in {"faces", "coordinates_local"}
        },
        "source_comparison": {
            "same_vertex_count": attempt["vertex_count"] == source["vertex_count"],
            "same_edge_count": attempt["edge_count"] == source["edge_count"],
            "same_face_count": attempt["face_count"] == source["face_count"],
            "same_face_index_topology": attempt["faces"] == source["faces"],
            "same_boundary_index_cycle_set": set(attempt["boundary_cycle_vertex_indices"])
            == set(source["boundary_cycle_vertex_indices"]),
            "same_boundary_edges": attempt["boundary_edges"] == source["boundary_edges"],
            "attempt02_pairs_are_exact_subset_of_source_pairs": attempt_pairs
            <= source_pairs,
            "source_pair_count": len(source_pairs),
            "attempt02_pair_count": len(attempt_pairs),
            "source_pairs_removed_by_attempt02_count": len(source_pairs - attempt_pairs),
            "new_pairs_introduced_by_attempt02": [
                list(value) for value in sorted(attempt_pairs - source_pairs)
            ],
            "surviving_pairs": [list(value) for value in sorted(attempt_pairs)],
            "changed_vertex_count": len(changed),
            "maximum_vertex_movement_source_cm": max(
                (record["movement_source_cm"] for record in changed), default=0.0
            ),
            "changed_vertex_indices": [
                record["vertex_index"] for record in changed
            ],
            "source_exact_report_summary": {
                key: value
                for key, value in source["exact_report"].items()
                if key != "pairs"
            },
            "attempt02_to_source_boundary": nearest_interface_comparison(
                attempt["boundary_world_m"], source["boundary_world_m"]
            ),
        },
        "r24_interface": r24,
        "attempt02_to_r24_interface": nearest_interface_comparison(
            attempt["boundary_world_m"], r24["boundary_world_m"]
        ),
        "truth": {
            "attempt02_is_zero_intersection": len(attempt_pairs) == 0,
            "r24_attempt14_patch_zero_intersections_from_bound_report": True,
            "r24_attempt14_whole_intersection_count_from_bound_report": 29,
            "visual_approval_claimed": False,
            "internal_function_claimed": False,
        },
    }

    OUTPUT.mkdir(parents=True)
    path = OUTPUT / "BLACKPROJECT_ATTEMPT02_INTERSECTION_TOPOLOGY.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for input_path, expected in (
        (ATTEMPT02_BLEND, ATTEMPT02_BLEND_SHA256),
        (SOURCE_GLB, SOURCE_GLB_SHA256),
        (R24_SOURCE_BLEND, R24_SOURCE_BLEND_SHA256),
    ):
        if sha256_file(input_path) != expected:
            raise RuntimeError(f"input changed during diagnostic: {input_path}")
    print(json.dumps({"report": str(path), "sha256": sha256_file(path)}))


if __name__ == "__main__":
    main()
