"""Probe only the split Object003 body family from the adult reference.

The GLB renderer shows that the four Object003 mesh chunks collectively form
the visible body while a single chunk is only a scan slab.  This diagnostic
preserves shared indices inside each chunk, excludes Object001/Object002
families, crops the same bounded pelvis region, and remeshes only the combined
local evidence.  It remains reference evidence, never Robert geometry.
"""

from __future__ import annotations

import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = (
    ROOT
    / "Avatar/avatar_builder/asset_library/adult_anatomy_reference/"
    "male_nude_2_1_f117148577.glb"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "anatomy_reference_audit/male_nude_2_object003_family_local_crop_probe"
)
OUT.mkdir(parents=True, exist_ok=True)
BLEND_PATH = OUT / "AUTHORIZED_REFERENCE_OBJECT003_LOCAL_CROP_PROBE.blend"
REPORT_PATH = OUT / "OBJECT003_FAMILY_LOCAL_CROP_REPORT.json"

SCALE = 1.813 / 71.688
SOURCE_CENTER_X = 1.690873
SOURCE_CENTER_Y = 0.435622
SOURCE_FLOOR_Z = -0.092019


def target_point(point: Vector) -> Vector:
    return Vector(
        (
            -(point.x - SOURCE_CENTER_X) * SCALE,
            -(point.y - SOURCE_CENTER_Y) * SCALE,
            (point.z - SOURCE_FLOOR_Z) * SCALE,
        )
    )


def topology(obj: bpy.types.Object) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    unseen = set(bm.verts)
    components = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        count = 1
        while stack:
            vertex = stack.pop()
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in unseen:
                    unseen.remove(other)
                    stack.append(other)
                    count += 1
        components.append(count)
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in bm.edges),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in bm.edges
        ),
        "connected_components": len(components),
        "largest_component_vertices": max(components, default=0),
    }
    bm.free()
    return result


def look_at(obj: bpy.types.Object, point: Vector) -> None:
    obj.rotation_euler = (point - obj.location).to_track_quat("-Z", "Y").to_euler()


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(REFERENCE))
sources = sorted(
    [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and obj.name.startswith("Object003_Object003_mtl_0")
    ],
    key=lambda obj: obj.name,
)
if not sources:
    raise RuntimeError("Object003 body-family chunks are missing")

vertices: list[Vector] = []
faces: list[tuple[int, ...]] = []
source_rows = []
for source in sources:
    world_points = [
        target_point(source.matrix_world @ vertex.co)
        for vertex in source.data.vertices
    ]
    chosen = []
    chosen_indices: set[int] = set()
    for polygon in source.data.polygons:
        points = [world_points[index] for index in polygon.vertices]
        center = sum(points, Vector()) / len(points)
        if (
            abs(center.x) <= 0.090
            and -0.270 <= center.y <= -0.035
            and 0.625 <= center.z <= 0.860
            and all(abs(point.x) <= 0.115 for point in points)
        ):
            chosen.append(tuple(polygon.vertices))
            chosen_indices.update(polygon.vertices)
    ordered = sorted(chosen_indices)
    mapping = {
        old: len(vertices) + new for new, old in enumerate(ordered)
    }
    vertices.extend(world_points[index] for index in ordered)
    faces.extend(tuple(mapping[index] for index in polygon) for polygon in chosen)
    source_rows.append(
        {
            "name": source.name,
            "source_vertices": len(source.data.vertices),
            "source_polygons": len(source.data.polygons),
            "selected_vertices": len(ordered),
            "selected_polygons": len(chosen),
        }
    )

if len(faces) < 200:
    raise RuntimeError(f"Object003-family crop too small: {len(faces)} faces")

mesh = bpy.data.meshes.new("Object003FamilyLocalCropRaw")
mesh.from_pydata(vertices, [], faces)
mesh.update()
patch = bpy.data.objects.new("Object003FamilyLocalCropRaw", mesh)
bpy.context.collection.objects.link(patch)
raw_topology = topology(patch)

for obj in list(bpy.data.objects):
    if obj is not patch:
        bpy.data.objects.remove(obj, do_unlink=True)

bpy.context.view_layer.objects.active = patch
patch.select_set(True)
solidify = patch.modifiers.new("ReferenceCropInwardShell", "SOLIDIFY")
solidify.thickness = 0.012
solidify.offset = -1.0
solidify.use_rim = True
bpy.ops.object.modifier_apply(modifier=solidify.name)
patch.data.remesh_voxel_size = 0.00125
patch.data.remesh_voxel_adaptivity = 0.0
bpy.ops.object.voxel_remesh()
patch.name = "AUTHORIZED_REFERENCE_OBJECT003_FAMILY_LOCAL_REMESH"
for polygon in patch.data.polygons:
    polygon.use_smooth = True
remeshed_topology = topology(patch)

material = bpy.data.materials.new("ReferenceProbeNeutral")
material.diffuse_color = (0.58, 0.40, 0.34, 1.0)
material.roughness = 0.72
patch.data.materials.append(material)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
world = bpy.data.worlds.new("ReferenceProbeWorld")
world.color = (0.035, 0.038, 0.045)
scene.world = world

camera_data = bpy.data.cameras.new("ReferenceProbeCamera")
camera_data.type = "ORTHO"
camera_data.ortho_scale = 0.32
camera = bpy.data.objects.new("ReferenceProbeCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera

target = Vector((0.0, -0.14, 0.742))
for location, energy, size in [
    ((-0.35, -0.55, 1.05), 700, 0.55),
    ((0.42, -0.35, 0.88), 500, 0.40),
    ((0.00, 0.30, 0.82), 280, 0.35),
]:
    data = bpy.data.lights.new("ReferenceProbeArea", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new("ReferenceProbeArea", data)
    light.location = location
    look_at(light, target)
    bpy.context.collection.objects.link(light)

views = {
    "front": Vector((0.0, -0.64, 0.742)),
    "side": Vector((0.50, -0.14, 0.742)),
    "three_quarter": Vector((0.40, -0.50, 0.755)),
}
render_paths = {}
for name, location in views.items():
    camera.location = location
    look_at(camera, target)
    destination = OUT / f"{name}.png"
    scene.render.filepath = str(destination)
    bpy.ops.render.render(write_still=True)
    render_paths[name] = str(destination)

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
report = {
    "schema": "kira.avatar.authorized_reference.object003_crop_probe.v1",
    "status": "REFERENCE EVIDENCE ONLY — NOT ROBERT GEOMETRY",
    "reference": str(REFERENCE),
    "included_source_family": [row["name"] for row in source_rows],
    "excluded_source_families": ["Object001", "Object002"],
    "source_rows": source_rows,
    "selection": {
        "selected_polygons": len(faces),
        "selected_vertices_before_local_remesh": len(vertices),
        "shared_indices_preserved_within_each_chunk": True,
        "per_polygon_vertex_duplication": False,
    },
    "topology": {
        "raw_crop": raw_topology,
        "local_remesh": remeshed_topology,
        "voxel_size_m": 0.00125,
    },
    "renders": render_paths,
    "restrictions": {
        "robert_geometry_modified": False,
        "full_donor_body_transfer_allowed": False,
        "runtime_use_allowed": False,
    },
}
REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(BLEND_PATH)
print(REPORT_PATH)
print(json.dumps(report, indent=2))
