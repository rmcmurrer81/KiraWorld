"""Render isolated mapped AFES core layers from rejected R23 Attempt 05.

The rejected body is never saved.  This diagnostic removes the failed outer
transition from view so the qualified mapped core can be judged separately.
"""

from collections import defaultdict, deque
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import blender_simulate_kira_r24_broad_inplace_surface as visual  # noqa: E402


SOURCE = ROOT / (
    "RecoverySprint/continuation_20260803/kira_r23_cc0_afes_author/attempt_05/"
    "kira_r23_cc0_afes_core_transfer_attempt_05.blend"
)
OUTPUT = ROOT / (
    "RecoverySprint/continuation_20260803/"
    "kira_r23_mapped_core_visual_diagnostic/attempt_01"
)
BODY = "Kira_R23_CC0_AFES_CoreTransfer_Primary_Surface"
PATCH_MATERIAL = 6
THRESHOLDS = (4, 6, 8)


def patch_distances(mesh: bpy.types.Mesh):
    patch = {int(face.index) for face in mesh.polygons if int(face.material_index) == PATCH_MATERIAL}
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    neighbors = [set() for _ in mesh.polygons]
    for face in mesh.polygons:
        vertices = list(map(int, face.vertices))
        for offset, first in enumerate(vertices):
            second = vertices[(offset + 1) % len(vertices)]
            edge_faces[tuple(sorted((first, second)))].append(int(face.index))
    for faces in edge_faces.values():
        for first in faces:
            neighbors[first].update(second for second in faces if second != first)
    boundary = {
        face
        for faces in edge_faces.values()
        if any(face in patch for face in faces) and any(face not in patch for face in faces)
        for face in faces
        if face in patch
    }
    distance = {face: 0 for face in boundary}
    queue = deque(sorted(boundary))
    while queue:
        current = queue.popleft()
        for neighbor in neighbors[current]:
            if neighbor in patch and neighbor not in distance:
                distance[neighbor] = distance[current] + 1
                queue.append(neighbor)
    return distance


def extract(body: bpy.types.Object, faces: set[int], name: str) -> bpy.types.Object:
    source = body.data
    used = sorted({int(vertex) for face in faces for vertex in source.polygons[face].vertices})
    mapping = {old: new for new, old in enumerate(used)}
    vertices = [tuple(body.matrix_world @ source.vertices[index].co) for index in used]
    polygons = [tuple(mapping[int(vertex)] for vertex in source.polygons[face].vertices) for face in sorted(faces)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], polygons)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    material = visual.material(f"{name}_ClinicalSurface", (0.62, 0.34, 0.29, 1.0))
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    modifier = obj.modifiers.new("CoreDiagnosticSubdivision", "SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = 1
    modifier.render_levels = 1
    return obj


def render(obj: bpy.types.Object, directory: Path) -> list[str]:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.006, 0.011, 0.018)
    scene.view_settings.look = "AgX - Medium High Contrast"
    points = [vertex.co for vertex in obj.data.vertices]
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    center = (minimum + maximum) * 0.5
    extent = max(maximum.x - minimum.x, maximum.z - minimum.z)
    for name, location, energy, size in (
        ("CoreKey", (2.0, -2.8, 2.6), 850.0, 3.0),
        ("CoreFill", (-2.0, -2.0, 1.5), 480.0, 2.6),
        ("CoreRear", (0.7, 2.5, 2.0), 600.0, 2.5),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.size = size
        light = bpy.data.objects.new(name, data)
        light.location = location
        bpy.context.collection.objects.link(light)
        visual.look_at(light, center)
    camera_data = bpy.data.cameras.new("CoreCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("CoreCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    views = {
        "front.png": (Vector((center.x, minimum.y - 1.2, center.z)), center),
        "left_three_quarter.png": (Vector((center.x - 0.7, minimum.y - 0.95, center.z)), center),
        "side.png": (Vector((center.x - 1.2, center.y, center.z)), center),
    }
    rendered = []
    for filename, (location, target) in views.items():
        camera.location = location
        camera.data.ortho_scale = extent * 1.22
        visual.look_at(camera, target)
        scene.render.filepath = str(directory / filename)
        bpy.ops.render.render(write_still=True)
        rendered.append(filename)
    return rendered


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("append-only diagnostic exists")
    OUTPUT.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    body = bpy.data.objects[BODY]
    distance = patch_distances(body.data)
    for candidate in list(bpy.context.scene.objects):
        candidate.hide_render = True
    results = []
    for threshold in THRESHOLDS:
        selected = {face for face, value in distance.items() if value >= threshold}
        obj = extract(body, selected, f"R23MappedCoreDistance{threshold}")
        obj.hide_render = False
        directory = OUTPUT / f"distance_{threshold:02d}"
        directory.mkdir()
        rendered = render(obj, directory)
        results.append({"threshold": threshold, "faces": len(selected), "rendered": rendered})
        obj.hide_render = True
        for candidate in list(bpy.context.scene.objects):
            if candidate.type in {"LIGHT", "CAMERA"}:
                bpy.data.objects.remove(candidate, do_unlink=True)
    report = {
        "schema": "kira.avatar.r23_mapped_core_visual_diagnostic.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "purpose": "isolate qualified mapped core from rejected transition; no candidate",
        "results": results,
        "blend_saved": False,
    }
    (OUTPUT / "DIAGNOSTIC.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
