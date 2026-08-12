"""Probe one authorized adult-reference object as a local anatomy source.

Earlier V16 code combined every imported object and duplicated vertices per
polygon, producing overlapping scan layers and ring artifacts.  This probe
uses only the body object that contains the lower torso, preserves shared
indices, crops a bounded external region after the known scale transform,
adds one inward construction shell, and voxel-remeshes only that local patch.

The output is reference evidence, not Robert geometry and not an approval
candidate.  It exists to decide whether this source can guide a cleaner
hand-authored graft on the V24C body.
"""

from __future__ import annotations

import json
import math
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
    "anatomy_reference_audit/male_nude_2_single_object_local_crop_probe"
)
OUT.mkdir(parents=True, exist_ok=True)
REPORT_PATH = OUT / "SINGLE_OBJECT_LOCAL_CROP_REPORT.json"
BLEND_PATH = OUT / "AUTHORIZED_REFERENCE_LOCAL_CROP_PROBE.blend"

SOURCE_OBJECT = "Object003_Object003_mtl_0"
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
    seen: set[bmesh.types.BMVert] = set()
    components = []
    for vertex in bm.verts:
        if vertex in seen:
            continue
        stack = [vertex]
        seen.add(vertex)
        count = 0
        while stack:
            current = stack.pop()
            count += 1
            for edge in current.link_edges:
                neighbor = edge.other_vert(current)
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
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
    direction = point - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(REFERENCE))
source = bpy.data.objects.get(SOURCE_OBJECT)
if source is None:
    raise RuntimeError(f"authorized reference object missing: {SOURCE_OBJECT}")
source_polygon_count = len(source.data.polygons)

world_points = [
    target_point(source.matrix_world @ vertex.co)
    for vertex in source.data.vertices
]
selected_polygons = []
selected_indices: set[int] = set()
for polygon in source.data.polygons:
    points = [world_points[index] for index in polygon.vertices]
    center = sum(points, Vector()) / len(points)
    if (
        abs(center.x) <= 0.085
        and -0.255 <= center.y <= -0.045
        and 0.640 <= center.z <= 0.845
        and all(abs(point.x) <= 0.105 for point in points)
    ):
        selected_polygons.append(tuple(polygon.vertices))
        selected_indices.update(polygon.vertices)
if len(selected_polygons) < 80:
    raise RuntimeError(
        f"single-object crop too small: {len(selected_polygons)} faces"
    )

ordered_indices = sorted(selected_indices)
index_map = {old: new for new, old in enumerate(ordered_indices)}
vertices = [world_points[index] for index in ordered_indices]
faces = [
    tuple(index_map[index] for index in polygon)
    for polygon in selected_polygons
]
mesh = bpy.data.meshes.new("AuthorizedReferenceLocalCropRaw")
mesh.from_pydata(vertices, [], faces)
mesh.update()
patch = bpy.data.objects.new("AuthorizedReferenceLocalCropRaw", mesh)
bpy.context.collection.objects.link(patch)
raw_topology = topology(patch)

for obj in list(bpy.data.objects):
    if obj is not patch:
        bpy.data.objects.remove(obj, do_unlink=True)

# Make the open crop into one bounded volume and remesh only this reference
# evidence.  This is not applied to Robert.
bpy.context.view_layer.objects.active = patch
patch.select_set(True)
solidify = patch.modifiers.new("ReferenceCropInwardShell", "SOLIDIFY")
solidify.thickness = 0.010
solidify.offset = -1.0
solidify.use_rim = True
bpy.ops.object.modifier_apply(modifier=solidify.name)
patch.data.remesh_voxel_size = 0.00125
patch.data.remesh_voxel_adaptivity = 0.0
bpy.ops.object.voxel_remesh()
patch.name = "AUTHORIZED_REFERENCE_LOCAL_CROP_REMESH"
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
scene.render.film_transparent = False
world = bpy.data.worlds.new("ReferenceProbeWorld")
world.color = (0.035, 0.038, 0.045)
scene.world = world

camera_data = bpy.data.cameras.new("ReferenceProbeCamera")
camera_data.type = "ORTHO"
camera_data.ortho_scale = 0.30
camera = bpy.data.objects.new("ReferenceProbeCamera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera

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
    look_at(light, Vector((0.0, -0.13, 0.74)))
    bpy.context.collection.objects.link(light)

target = Vector((0.0, -0.13, 0.742))
views = {
    "front": Vector((0.0, -0.62, 0.742)),
    "side": Vector((0.48, -0.13, 0.742)),
    "three_quarter": Vector((0.38, -0.48, 0.755)),
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
    "schema": "kira.avatar.authorized_reference.local_crop_probe.v1",
    "status": "REFERENCE EVIDENCE ONLY — NOT ROBERT GEOMETRY",
    "reference": str(REFERENCE),
    "single_source_object": SOURCE_OBJECT,
    "selection": {
        "source_polygons": source_polygon_count,
        "selected_polygons": len(selected_polygons),
        "selected_vertices": len(selected_indices),
        "target_crop_bounds": {
            "x": [-0.085, 0.085],
            "y": [-0.255, -0.045],
            "z": [0.640, 0.845],
        },
        "vertices_preserved_by_shared_index": True,
        "all_imported_objects_combined": False,
    },
    "topology": {
        "raw_crop": raw_topology,
        "after_inward_shell_and_local_voxel_remesh": remeshed_topology,
        "voxel_size_m": 0.00125,
    },
    "renders": render_paths,
    "restrictions": {
        "another_identity_or_body_transfer_allowed": False,
        "robert_geometry_modified": False,
        "runtime_use_allowed": False,
    },
}
REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(BLEND_PATH)
print(REPORT_PATH)
print(json.dumps(report, indent=2))
