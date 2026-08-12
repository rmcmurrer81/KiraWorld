"""Read-only R19 pelvic mesh/material diagnostic; never saves a Blend."""

from collections import Counter, defaultdict, deque
import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/"
    "attempt_06/kira_r19_bald_targeted_material_movement_correction.blend"
)
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r24_broad_inplace_surface_diagnostic/attempt_04_material_inputs"
)
BODY = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
PATCH_MATERIAL = 5


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("append-only diagnostic output already exists")
    OUTPUT.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects[BODY]
    mesh = body.data
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    face_neighbors: list[set[int]] = [set() for _ in mesh.polygons]
    for face in mesh.polygons:
        verts = list(map(int, face.vertices))
        for offset, first in enumerate(verts):
            second = verts[(offset + 1) % len(verts)]
            edge_faces[tuple(sorted((first, second)))].append(int(face.index))
    for faces in edge_faces.values():
        for first in faces:
            face_neighbors[first].update(second for second in faces if second != first)
    patch_faces = {
        int(face.index) for face in mesh.polygons if int(face.material_index) == PATCH_MATERIAL
    }
    distances = {face: 0 for face in patch_faces}
    queue = deque(sorted(patch_faces))
    while queue:
        current = queue.popleft()
        for neighbor in face_neighbors[current]:
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    ring_materials = {}
    ring_bounds = {}
    for ring in range(0, 9):
        faces = [index for index, distance in distances.items() if distance == ring]
        materials = Counter(int(mesh.polygons[index].material_index) for index in faces)
        vertices = {
            int(vertex) for index in faces for vertex in mesh.polygons[index].vertices
        }
        worlds = [body.matrix_world @ mesh.vertices[index].co for index in vertices]
        ring_materials[str(ring)] = dict(sorted(materials.items()))
        ring_bounds[str(ring)] = {
            "face_count": len(faces),
            "vertex_count": len(vertices),
            "minimum": [min(point[axis] for point in worlds) for axis in range(3)],
            "maximum": [max(point[axis] for point in worlds) for axis in range(3)],
        }
    boundary_edges = [
        edge for edge, faces in edge_faces.items()
        if sum(face in patch_faces for face in faces) == 1
    ]
    boundary_vertices = sorted({vertex for edge in boundary_edges for vertex in edge})
    uv_layer = mesh.uv_layers.active
    patch_boundary_uv = defaultdict(list)
    torso_boundary_uv = defaultdict(list)
    if uv_layer is not None:
        for face in mesh.polygons:
            destination = patch_boundary_uv if int(face.index) in patch_faces else torso_boundary_uv
            for loop_index in face.loop_indices:
                vertex = int(mesh.loops[loop_index].vertex_index)
                if vertex in boundary_vertices:
                    destination[vertex].append(tuple(map(float, uv_layer.data[loop_index].uv)))
    uv_deltas = []
    for vertex in boundary_vertices:
        if patch_boundary_uv[vertex] and torso_boundary_uv[vertex]:
            patch_average = tuple(
                sum(value[axis] for value in patch_boundary_uv[vertex]) / len(patch_boundary_uv[vertex])
                for axis in range(2)
            )
            torso_average = tuple(
                sum(value[axis] for value in torso_boundary_uv[vertex]) / len(torso_boundary_uv[vertex])
                for axis in range(2)
            )
            uv_deltas.append(
                ((patch_average[0] - torso_average[0]) ** 2 + (patch_average[1] - torso_average[1]) ** 2) ** 0.5
            )
    report = {
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "body": BODY,
        "vertices": len(mesh.vertices),
        "faces": len(mesh.polygons),
        "material_slots": [
            {"index": index, "name": slot.material.name if slot.material else None}
            for index, slot in enumerate(body.material_slots)
        ],
        "torso_material_nodes": [
            {
                "name": node.name,
                "type": node.bl_idname,
                "label": node.label,
                "image": (
                    node.image.filepath if hasattr(node, "image") and node.image else None
                ),
                "base_color_default": (
                    list(map(float, node.inputs["Base Color"].default_value))
                    if node.bl_idname == "ShaderNodeBsdfPrincipled" and "Base Color" in node.inputs
                    else None
                ),
                "inputs": {
                    socket.name: (
                        list(map(float, socket.default_value))
                        if hasattr(socket.default_value, "__len__") and not isinstance(socket.default_value, str)
                        else float(socket.default_value)
                        if isinstance(socket.default_value, (int, float))
                        else str(socket.default_value)
                    )
                    for socket in node.inputs
                    if hasattr(socket, "default_value")
                },
            }
            for node in (
                body.material_slots[0].material.node_tree.nodes
                if body.material_slots[0].material and body.material_slots[0].material.use_nodes
                else []
            )
        ],
        "torso_material_links": [
            {
                "from_node": link.from_node.name,
                "from_socket": link.from_socket.name,
                "to_node": link.to_node.name,
                "to_socket": link.to_socket.name,
            }
            for link in (
                body.material_slots[0].material.node_tree.links
                if body.material_slots[0].material and body.material_slots[0].material.use_nodes
                else []
            )
        ],
        "whole_body_face_material_counts": dict(
            sorted(Counter(int(face.material_index) for face in mesh.polygons).items())
        ),
        "patch_face_count": len(patch_faces),
        "patch_boundary_edge_count": len(boundary_edges),
        "patch_boundary_vertex_count": len(boundary_vertices),
        "patch_boundary_vertex_indices": boundary_vertices,
        "active_uv_layer": uv_layer.name if uv_layer else None,
        "boundary_uv_pair_count": len(uv_deltas),
        "boundary_uv_mean_patch_to_torso_delta": (
            sum(uv_deltas) / len(uv_deltas) if uv_deltas else None
        ),
        "boundary_uv_max_patch_to_torso_delta": max(uv_deltas, default=None),
        "face_ring_material_counts": ring_materials,
        "face_ring_world_bounds": ring_bounds,
        "blend_saved": False,
    }
    (OUTPUT / "DIAGNOSTIC.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
