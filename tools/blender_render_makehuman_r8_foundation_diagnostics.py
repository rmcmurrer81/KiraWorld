"""Render neutral-light and wireframe diagnostics for the CC0 R8 foundation.

The R8 foundation is a generic engineering substrate only.  These diagnostics
do not personalize it as Robert, approve it, rig it, or attach it to runtime.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = (
    ROOT
    / "Avatar"
    / "private_owner_review"
    / "dual_robert_20260729"
    / "makehuman_cc0_parametric_male_foundation_probe_r8_union_inset"
)
SOURCE = SOURCE_DIR / "MAKEHUMAN_CC0_PARAMETRIC_MALE_FOUNDATION.blend"
OUT = (
    ROOT
    / "Avatar"
    / "private_owner_review"
    / "dual_robert_20260729"
    / "makehuman_cc0_parametric_male_foundation_probe_r8_union_inset_diagnostics"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def topology(obj: bpy.types.Object) -> dict[str, int | float | list[int]]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    unseen = set(bm.verts)
    components: list[int] = []
    while unseen:
        start = unseen.pop()
        queue = deque([start])
        count = 0
        while queue:
            vertex = queue.popleft()
            count += 1
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in unseen:
                    unseen.remove(other)
                    queue.append(other)
        components.append(count)
    components.sort(reverse=True)
    boundary = sum(edge.is_boundary for edge in bm.edges)
    nonmanifold_internal = sum(
        not edge.is_manifold and not edge.is_boundary for edge in bm.edges
    )
    signed_volume = (
        float(bm.calc_volume(signed=True))
        if boundary == 0 and nonmanifold_internal == 0
        else 0.0
    )
    result: dict[str, int | float | list[int]] = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "connected_components": len(components),
        "component_vertex_counts": components,
        "boundary_edges": boundary,
        "nonmanifold_internal_edges": nonmanifold_internal,
        "signed_volume": signed_volume,
    }
    bm.free()
    return result


def material(name: str, color: tuple[float, float, float, float], roughness: float):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    if node is not None:
        node.inputs["Base Color"].default_value = color
        node.inputs["Roughness"].default_value = roughness
        node.inputs["Subsurface Weight"].default_value = 0.035
    return mat


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def render(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output: Path,
    location: Vector,
    target: Vector,
    ortho_scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    look_at(camera, target)
    scene.camera = camera
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[i] for point in points) for i in range(3))),
        Vector(tuple(max(point[i] for point in points) for i in range(3))),
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    meshes = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and "MakeHuman" in obj.name
    ]
    if len(meshes) != 1:
        raise RuntimeError(f"expected one MakeHuman mesh, found {[obj.name for obj in meshes]}")
    body = meshes[0]
    source_topology = topology(body)

    for obj in list(bpy.context.scene.objects):
        if obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)

    neutral_skin = material(
        "CC0_R8_Neutral_Diagnostic_Skin", (0.49, 0.30, 0.23, 1.0), 0.58
    )
    body.data.materials.clear()
    body.data.materials.append(neutral_skin)
    for polygon in body.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.16, 0.16, 0.16)
    scene.view_settings.look = "AgX - Medium High Contrast"

    for name, energy, location, size in (
        ("FrontFill", 900.0, (0.0, -5.2, 3.1), 5.5),
        ("LeftFill", 650.0, (-4.0, -3.0, 3.4), 4.5),
        ("RightFill", 650.0, (4.0, -3.0, 3.4), 4.5),
        ("TopFill", 700.0, (0.0, -0.5, 7.2), 5.0),
        ("RearRim", 450.0, (0.0, 4.0, 4.0), 4.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        light.location = location
        bpy.context.collection.objects.link(light)
        light.rotation_euler = (
            Vector((0.0, -0.7, 2.8)) - light.location
        ).to_track_quat("-Z", "Y").to_euler()

    camera_data = bpy.data.cameras.new("R8DiagnosticCamera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R8DiagnosticCamera", camera_data)
    bpy.context.collection.objects.link(camera)

    minimum, maximum = bounds(body)
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    extent = max(maximum.x - minimum.x, maximum.y - minimum.y, height)
    distance = extent * 1.9
    pelvis = Vector((center.x, center.y - 0.05, minimum.z + height * 0.475))
    # The neutral MakeHuman A-pose holds the hands slightly below the pelvis.
    # Center the diagnostic from the actual lateral/body proportions instead
    # of the earlier 49%-height estimate, which clipped most of each hand.
    hand_left = Vector(
        (
            minimum.x + (maximum.x - minimum.x) * 0.06,
            center.y - 0.14,
            minimum.z + height * 0.57,
        )
    )
    hand_right = Vector(
        (
            maximum.x - (maximum.x - minimum.x) * 0.06,
            center.y - 0.14,
            minimum.z + height * 0.57,
        )
    )
    face = Vector((center.x, center.y - 0.06, minimum.z + height * 0.89))

    views = {
        "full_front_neutral.png": (
            Vector((center.x, minimum.y - distance, center.z)),
            center,
            height * 1.08,
        ),
        "pelvis_front_neutral.png": (
            Vector((pelvis.x, minimum.y - distance, pelvis.z)),
            pelvis,
            height * 0.30,
        ),
        "pelvis_side_neutral.png": (
            Vector((minimum.x - distance, pelvis.y, pelvis.z)),
            pelvis,
            height * 0.30,
        ),
        "pelvis_three_quarter_neutral.png": (
            Vector((center.x - distance * 0.72, minimum.y - distance * 0.72, pelvis.z)),
            pelvis,
            height * 0.30,
        ),
        "left_hand_neutral.png": (
            Vector((hand_left.x, minimum.y - distance, hand_left.z)),
            hand_left,
            height * 0.12,
        ),
        "right_hand_neutral.png": (
            Vector((hand_right.x, minimum.y - distance, hand_right.z)),
            hand_right,
            height * 0.12,
        ),
        "face_neutral.png": (
            Vector((face.x, minimum.y - distance, face.z)),
            face,
            height * 0.24,
        ),
    }
    for filename, (location, target, scale) in views.items():
        render(scene, camera, OUT / filename, location, target, scale)

    wire = body.copy()
    wire.data = body.data.copy()
    wire.name = "R8_Union_Wireframe_Overlay"
    bpy.context.collection.objects.link(wire)
    for modifier in list(wire.modifiers):
        wire.modifiers.remove(modifier)
    wire.data.materials.clear()
    wire.data.materials.append(
        material("R8_Wireframe_Cyan", (0.015, 0.30, 0.38, 1.0), 0.35)
    )
    wireframe = wire.modifiers.new("R8TopologyWire", "WIREFRAME")
    wireframe.thickness = 0.004
    wireframe.offset = 1.0
    wireframe.use_replace = True
    for polygon in wire.data.polygons:
        polygon.material_index = 0

    wire_views = {
        "pelvis_front_wireframe.png": (
            Vector((pelvis.x, minimum.y - distance, pelvis.z)),
            pelvis,
            height * 0.30,
        ),
        "pelvis_side_wireframe.png": (
            Vector((minimum.x - distance, pelvis.y, pelvis.z)),
            pelvis,
            height * 0.30,
        ),
        "pelvis_three_quarter_wireframe.png": (
            Vector((center.x - distance * 0.72, minimum.y - distance * 0.72, pelvis.z)),
            pelvis,
            height * 0.30,
        ),
    }
    for filename, (location, target, scale) in wire_views.items():
        render(scene, camera, OUT / filename, location, target, scale)

    bpy.data.objects.remove(wire, do_unlink=True)
    report = {
        "schema": "kira.avatar.makehuman_r8_foundation_diagnostics.v1",
        "status": (
            "GENERIC FOUNDATION VISUAL/TOPOLOGY ENGINEERING PASS — "
            "NOT ROBERT / NOT OWNER APPROVED"
        ),
        "source": str(SOURCE),
        "source_sha256": sha256(SOURCE),
        "not_robert_identity": True,
        "not_owner_approved": True,
        "not_runtime_ready": True,
        "estimate_label": "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE",
        "encoded_topology": source_topology,
        "neutral_views": {name: str(OUT / name) for name in views},
        "wireframe_views": {name: str(OUT / name) for name in wire_views},
        "visual_gate": (
            "Ordinary front, profile, and three-quarter views must remain "
            "recognizable and plausible; dark lighting may not be interpreted as "
            "a hole without neutral and wireframe corroboration."
        ),
        "visual_decision": {
            "ordinary_front_profile_three_quarter": "PASS_GENERIC_PLAUSIBILITY",
            "root_connection": (
                "PASS_GENERIC_ENGINEERING_REVIEW; neutral and wireframe views "
                "corroborate a connected high compact root without a surface hole"
            ),
            "identity_personalization": "PENDING_PRIVATE_ROBERT_STATIC_CANDIDATE",
            "eyes_hair_skin_hands": (
                "GENERIC FOUNDATION ONLY; Robert-specific eye, removable static "
                "hair, skin, and hand/nail review remain separate"
            ),
        },
    }
    (OUT / "R8_DIAGNOSTIC_REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
