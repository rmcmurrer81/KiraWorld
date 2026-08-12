"""Build and audit a connected CC0 MakeHuman adult-male foundation.

This engineering builder uses only MakeHuman's bundled CC0 hm08 base and
official CC0 morph targets.  The visible body and the parametric
``helper-genital`` surface are created as separate source objects.  The open
helper boundary is capped *inside* the body, then an exact Boolean union removes
the overlapping doll-safe surface and the hidden cap.  The result is accepted
only if the encoded mesh is one connected, closed, manifold component.

This is a reusable generic Avatar Builder foundation, not Robert's identity
surface and not an owner-approved or runtime-ready body.

Run with Blender:

    blender --background --python \
      tools/blender_build_makehuman_connected_male_foundation.py -- \
      --output-dir Avatar/private_owner_review/.../makehuman_connected_probe
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import deque
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
MAKEHUMAN_DATA = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "tooling"
    / "makehuman_official"
    / "makehuman"
    / "data"
)
BASE_OBJ = MAKEHUMAN_DATA / "3dobjs" / "base.obj"
BASE_TARGETS = (
    (
        MAKEHUMAN_DATA
        / "targets"
        / "macrodetails"
        / "universal-male-young-averagemuscle-averageweight.target",
        1.0,
    ),
    (
        MAKEHUMAN_DATA
        / "targets"
        / "macrodetails"
        / "caucasian-male-young.target",
        1.0,
    ),
)
VISIBLE_GROUPS = ("body", "helper-genital")


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--genital-length", type=float, default=0.0)
    parser.add_argument("--genital-circumference", type=float, default=0.0)
    parser.add_argument("--testicle-size", type=float, default=0.0)
    parser.add_argument(
        "--union-method", choices=("exact", "voxel"), default="exact"
    )
    parser.add_argument("--voxel-size", type=float, default=0.02)
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_groups(
    path: Path,
) -> tuple[list[Vector], dict[str, list[tuple[int, ...]]]]:
    vertices: list[Vector] = []
    faces = {name: [] for name in VISIBLE_GROUPS}
    group = ""
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                vertices.append(Vector((float(x), float(y), float(z))))
            elif line.startswith("g "):
                group = line[2:].strip()
            elif group in faces and line.startswith("f "):
                indices = []
                for token in line.split()[1:]:
                    value = int(token.split("/", 1)[0])
                    indices.append(value - 1 if value > 0 else len(vertices) + value)
                if len(indices) >= 3:
                    faces[group].append(tuple(indices))
    for name in VISIBLE_GROUPS:
        if not faces[name]:
            raise RuntimeError(f"MakeHuman base OBJ did not yield group {name!r}")
    return vertices, faces


def _apply_target(vertices: list[Vector], path: Path, weight: float) -> int:
    if not weight:
        return 0
    changed = 0
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) != 4:
                continue
            index = int(fields[0])
            vertices[index] += Vector(
                (
                    float(fields[1]) * weight,
                    float(fields[2]) * weight,
                    float(fields[3]) * weight,
                )
            )
            changed += 1
    return changed


def _compact_group(
    vertices: list[Vector], faces: list[tuple[int, ...]]
) -> tuple[list[tuple[float, float, float]], list[tuple[int, ...]]]:
    used = sorted({index for face in faces for index in face})
    remap = {old: new for new, old in enumerate(used)}
    # MakeHuman is Y-up and uses positive Z toward the face. Rotate +90 degrees
    # around X so the result is Blender Z-up with the face toward -Y.
    converted = [(vertices[i].x, -vertices[i].z, vertices[i].y) for i in used]
    return converted, [tuple(remap[i] for i in face) for face in faces]


def _object(
    name: str,
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.validate(verbose=False)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def _topology(obj: bpy.types.Object) -> dict[str, int | float | list[int]]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    boundary = [edge for edge in bm.edges if edge.is_boundary]
    nonmanifold_internal = [
        edge for edge in bm.edges if not edge.is_manifold and not edge.is_boundary
    ]
    unseen = set(bm.verts)
    component_sizes: list[int] = []
    while unseen:
        start = unseen.pop()
        queue = deque([start])
        size = 0
        while queue:
            vertex = queue.popleft()
            size += 1
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in unseen:
                    unseen.remove(other)
                    queue.append(other)
        component_sizes.append(size)
    component_sizes.sort(reverse=True)
    signed_volume = 0.0
    volume = 0.0
    if not boundary and not nonmanifold_internal:
        try:
            signed_volume = float(bm.calc_volume(signed=True))
            volume = abs(signed_volume)
        except Exception:
            signed_volume = 0.0
            volume = 0.0
    result: dict[str, int | float | list[int]] = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": len(boundary),
        "nonmanifold_internal_edges": len(nonmanifold_internal),
        "connected_components": len(component_sizes),
        "component_vertex_counts": component_sizes,
        "signed_volume": signed_volume,
        "signed_volume_absolute": volume,
    }
    bm.free()
    return result


def _ensure_positive_closed_volume(
    obj: bpy.types.Object,
) -> dict[str, bool | float]:
    """Orient a closed source surface so Boolean inside/outside is unambiguous."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if any(edge.is_boundary for edge in bm.edges):
        bm.free()
        raise RuntimeError(f"{obj.name} is open; cannot orient as a closed volume")
    before = float(bm.calc_volume(signed=True))
    reversed_faces = before < 0.0
    if reversed_faces:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.normal_update()
        bm.to_mesh(obj.data)
        obj.data.update(calc_edges=True)
    after = float(bm.calc_volume(signed=True))
    bm.free()
    return {
        "signed_volume_before": before,
        "reversed_faces": reversed_faces,
        "signed_volume_after": after,
    }


def _cap_open_boundary(obj: bpy.types.Object) -> dict[str, int | float | list[int]]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary = [edge for edge in bm.edges if edge.is_boundary]
    if not boundary:
        raise RuntimeError("helper-genital source unexpectedly has no open boundary")
    result = bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    obj.data.update(calc_edges=True)
    bm.free()
    orientation = _ensure_positive_closed_volume(obj)
    audit = _topology(obj)
    audit["cap_faces_created"] = len(result.get("faces", []))
    audit["orientation"] = orientation
    return audit


def _bvh(obj: bpy.types.Object) -> BVHTree:
    vertices = [vertex.co.copy() for vertex in obj.data.vertices]
    polygons = [tuple(poly.vertices) for poly in obj.data.polygons]
    return BVHTree.FromPolygons(vertices, polygons, all_triangles=False, epsilon=0.0)


def _material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    node = material.node_tree.nodes.get("Principled BSDF")
    if node is not None:
        node.inputs["Base Color"].default_value = color
        node.inputs["Roughness"].default_value = 0.52
        node.inputs["Subsurface Weight"].default_value = 0.06
    return material


def _look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def _world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[i] for point in points) for i in range(3))),
        Vector(tuple(max(point[i] for point in points) for i in range(3))),
    )


def _camera(name: str) -> bpy.types.Object:
    data = bpy.data.cameras.new(name)
    data.type = "ORTHO"
    camera = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(camera)
    return camera


def _render(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output: Path,
    *,
    location: Vector,
    target: Vector,
    ortho_scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    _look_at(camera, target)
    scene.camera = camera
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def _configure_scene() -> bpy.types.Scene:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.025, 0.03, 0.04)
    for name, energy, location, size in (
        ("Key", 1200.0, (3.5, -5.0, 6.5), 4.0),
        ("Fill", 750.0, (-4.0, -2.0, 4.0), 5.0),
        ("Rim", 900.0, (2.0, 4.0, 5.5), 3.0),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        light.location = location
        bpy.context.collection.objects.link(light)
        light.rotation_euler = (
            Vector((0.0, 0.0, 3.0)) - light.location
        ).to_track_quat("-Z", "Y").to_euler()
    return scene


def main() -> None:
    args = _arguments()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    vertices, group_faces = _parse_groups(BASE_OBJ)
    applied = []
    for path, weight in BASE_TARGETS:
        applied.append(
            {
                "path": str(path),
                "sha256": _sha256(path),
                "weight": weight,
                "changed_vertices": _apply_target(vertices, path, weight),
            }
        )
    for stem, value in (
        ("penis-length", args.genital_length),
        ("penis-circ", args.genital_circumference),
        ("penis-testicles", args.testicle_size),
    ):
        if value == 0.0:
            continue
        suffix = "incr" if value > 0.0 else "decr"
        path = MAKEHUMAN_DATA / "targets" / "genitals" / f"{stem}-{suffix}.target"
        applied.append(
            {
                "path": str(path),
                "sha256": _sha256(path),
                "weight": abs(value),
                "changed_vertices": _apply_target(vertices, path, abs(value)),
            }
        )

    body_vertices, body_faces = _compact_group(vertices, group_faces["body"])
    helper_vertices, helper_faces = _compact_group(
        vertices, group_faces["helper-genital"]
    )
    body = _object("CC0_MakeHuman_Body", body_vertices, body_faces)
    helper = _object(
        "CC0_MakeHuman_Parametric_Male_Helper", helper_vertices, helper_faces
    )
    body.data.materials.append(
        _material("CC0_MakeHuman_Neutral_Skin", (0.56, 0.35, 0.27, 1.0))
    )
    helper.data.materials.append(
        _material("CC0_MakeHuman_Male_Helper_Debug", (0.18, 0.44, 0.72, 1.0))
    )

    body_before = _topology(body)
    body_orientation = _ensure_positive_closed_volume(body)
    body_before_oriented = _topology(body)
    helper_before = _topology(helper)
    helper_after_cap = _cap_open_boundary(helper)
    source_overlap_pairs = len(_bvh(body).overlap(_bvh(helper)))

    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    if args.union_method == "exact":
        helper.select_set(False)
        boolean = body.modifiers.new("ConnectedMaleExactUnion", "BOOLEAN")
        boolean.operation = "UNION"
        boolean.solver = "EXACT"
        boolean.use_self = True
        boolean.use_hole_tolerant = True
        boolean.object = helper
        bpy.ops.object.modifier_apply(modifier=boolean.name)
        bpy.data.objects.remove(helper, do_unlink=True)
    else:
        if args.voxel_size <= 0.0:
            raise RuntimeError("--voxel-size must be positive")
        helper.select_set(True)
        bpy.ops.object.join()
        body = bpy.context.view_layer.objects.active
        body.data.remesh_voxel_size = args.voxel_size
        body.data.remesh_voxel_adaptivity = 0.0
        bpy.ops.object.voxel_remesh()
    body.name = "CC0_MakeHuman_Connected_Adult_Male_Foundation"
    body.data.name = body.name
    body.data.materials.clear()
    body.data.materials.append(
        _material("CC0_MakeHuman_Connected_Skin", (0.56, 0.35, 0.27, 1.0))
    )
    for polygon in body.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    body.data.validate(verbose=False)
    body.data.update(calc_edges=True)
    union_topology = _topology(body)

    subdivision = body.modifiers.new("ReviewSubdivision", "SUBSURF")
    subdivision.levels = 1
    subdivision.render_levels = 2

    scene = _configure_scene()
    minimum, maximum = _world_bounds(body)
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    depth = maximum.y - minimum.y
    width = maximum.x - minimum.x
    full_scale = max(height * 1.08, width * 1.55)
    distance = max(height, width, depth) * 1.9
    pelvis_target = Vector((center.x, center.y, minimum.z + height * 0.47))
    pelvis_scale = height * 0.38
    camera = _camera("ReviewCamera")
    views = {
        "full_front.png": (
            Vector((center.x, minimum.y - distance, center.z)),
            center,
            full_scale,
        ),
        "full_side.png": (
            Vector((minimum.x - distance, center.y, center.z)),
            center,
            full_scale,
        ),
        "full_three_quarter.png": (
            Vector((center.x - distance * 0.70, minimum.y - distance * 0.70, center.z)),
            center,
            full_scale,
        ),
        "pelvis_front.png": (
            Vector((center.x, minimum.y - distance, pelvis_target.z)),
            pelvis_target,
            pelvis_scale,
        ),
        "pelvis_side.png": (
            Vector((minimum.x - distance, center.y, pelvis_target.z)),
            pelvis_target,
            pelvis_scale,
        ),
        "pelvis_three_quarter.png": (
            Vector(
                (
                    center.x - distance * 0.70,
                    minimum.y - distance * 0.70,
                    pelvis_target.z,
                )
            ),
            pelvis_target,
            pelvis_scale,
        ),
    }
    for filename, (location, target, scale) in views.items():
        _render(
            scene,
            camera,
            output_dir / filename,
            location=location,
            target=target,
            ortho_scale=scale,
        )

    blend_path = output_dir / "MAKEHUMAN_CC0_CONNECTED_MALE_FOUNDATION.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    plausible_scale_pass = (
        union_topology["vertices"] >= int(body_before_oriented["vertices"] * 0.90)
        and union_topology["faces"] >= int(body_before_oriented["faces"] * 0.90)
        and union_topology["signed_volume_absolute"]
        >= body_before_oriented["signed_volume_absolute"] * 0.90
        and union_topology["signed_volume_absolute"]
        <= (
            body_before_oriented["signed_volume_absolute"]
            + helper_after_cap["signed_volume_absolute"]
        )
        * 1.10
    )
    topology_pass = (
        union_topology["connected_components"] == 1
        and union_topology["boundary_edges"] == 0
        and union_topology["nonmanifold_internal_edges"] == 0
        and union_topology["signed_volume_absolute"] > 0.0
        and plausible_scale_pass
    )
    report = {
        "schema": "kira.avatar.makehuman_connected_male_foundation_probe.v1",
        "status": (
            "ENGINEERING_PROBE_AWAITING_VISUAL_REVIEW"
            if topology_pass
            else "BLOCKED — CONNECTED MANIFOLD TOPOLOGY NOT PROVEN"
        ),
        "not_owner_approved": True,
        "not_robert_identity_complete": True,
        "not_runtime_assigned": True,
        "generic_reusable_foundation_only": True,
        "license": "CC0-1.0",
        "base_obj": str(BASE_OBJ),
        "base_obj_sha256": _sha256(BASE_OBJ),
        "source_face_groups": list(VISIBLE_GROUPS),
        "targets": applied,
        "parameters": {
            "genital_length": args.genital_length,
            "genital_circumference": args.genital_circumference,
            "testicle_size": args.testicle_size,
        },
        "method": {
            "open_helper_boundary_capped_inside_body": True,
            "exact_boolean_union": args.union_method == "exact",
            "voxel_remesh": args.union_method == "voxel",
            "voxel_size": args.voxel_size if args.union_method == "voxel" else None,
            "donor_geometry": False,
            "donor_identity_surface": False,
        },
        "source_topology": {
            "body": body_before,
            "body_orientation": body_orientation,
            "body_after_orientation": body_before_oriented,
            "helper_before_cap": helper_before,
            "helper_after_cap": helper_after_cap,
            "body_helper_surface_overlap_pairs_before_union": source_overlap_pairs,
        },
        "encoded_union_topology": union_topology,
        "plausible_scale_pass": plausible_scale_pass,
        "topology_pass": topology_pass,
        "estimate_label": "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE",
        "visual_acceptance_rule": (
            "Must read as recognizable, anatomically plausible adult male anatomy "
            "from ordinary front, profile, and three-quarter views; topology alone "
            "cannot pass the candidate."
        ),
        "blend": str(blend_path),
        "blend_sha256": _sha256(blend_path),
        "renders": {name: str(output_dir / name) for name in views},
    }
    report_path = output_dir / "CONNECTED_FOUNDATION_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
