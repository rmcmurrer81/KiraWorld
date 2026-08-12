"""Read-only topology-layer audit of the rejected R23 Attempt 05 patch."""

from collections import Counter, defaultdict, deque
import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "RecoverySprint/continuation_20260803/kira_r23_cc0_afes_author/attempt_05/"
    "kira_r23_cc0_afes_core_transfer_attempt_05.blend"
)
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_attempt05_patch_layer_diagnostic/attempt_01"
)
BODY = "Kira_R23_CC0_AFES_CoreTransfer_Primary_Surface"
PATCH_MATERIAL = 6


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("append-only diagnostic already exists")
    OUTPUT.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects[BODY]
    mesh = body.data
    patch_faces = {
        int(face.index) for face in mesh.polygons if int(face.material_index) == PATCH_MATERIAL
    }
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    face_neighbors = [set() for _ in mesh.polygons]
    for face in mesh.polygons:
        vertices = list(map(int, face.vertices))
        for offset, first in enumerate(vertices):
            second = vertices[(offset + 1) % len(vertices)]
            edge_faces[tuple(sorted((first, second)))].append(int(face.index))
    for faces in edge_faces.values():
        for first in faces:
            face_neighbors[first].update(second for second in faces if second != first)
    boundary_patch_faces = {
        face
        for edge, faces in edge_faces.items()
        if any(face in patch_faces for face in faces)
        and any(face not in patch_faces for face in faces)
        for face in faces
        if face in patch_faces
    }
    distance = {face: 0 for face in boundary_patch_faces}
    queue = deque(sorted(boundary_patch_faces))
    while queue:
        current = queue.popleft()
        for neighbor in face_neighbors[current]:
            if neighbor in patch_faces and neighbor not in distance:
                distance[neighbor] = distance[current] + 1
                queue.append(neighbor)
    groups = []
    for group in body.vertex_groups:
        if "AFES" in group.name.upper() or "R23" in group.name.upper():
            members = [
                int(vertex.index)
                for vertex in mesh.vertices
                if any(item.group == group.index and item.weight > 0 for item in vertex.groups)
            ]
            groups.append({"name": group.name, "member_count": len(members)})
    report = {
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "body": BODY,
        "patch_faces": len(patch_faces),
        "patch_boundary_faces": len(boundary_patch_faces),
        "maximum_face_distance_from_outer_boundary": max(distance.values()),
        "face_count_by_outer_boundary_distance": dict(sorted(Counter(distance.values()).items())),
        "deep_core_face_counts": {
            str(threshold): sum(value >= threshold for value in distance.values())
            for threshold in range(1, max(distance.values()) + 1)
        },
        "candidate_semantic_vertex_groups": groups,
        "blend_saved": False,
    }
    (OUTPUT / "DIAGNOSTIC.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
