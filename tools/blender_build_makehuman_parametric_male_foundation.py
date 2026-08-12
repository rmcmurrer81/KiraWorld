"""Build a private CC0 MakeHuman adult-male foundation proof in Blender.

This is a reusable-foundation engineering probe, not an owner-approved Robert
body. It reads MakeHuman's CC0 hm08 base OBJ, keeps the visible ``body`` and
``helper-genital`` face groups while discarding unrelated rig/helper geometry,
applies the official parametric target deltas, and renders neutral full-body
and pelvis views. The helper surface remains an engineering input until a
separate topology audit proves whether it is connected cleanly enough for use.

Run with Blender:

    blender --background --python tools/blender_build_makehuman_parametric_male_foundation.py -- \
      --output-dir Avatar/private_owner_review/.../makehuman_parametric_male_probe
"""

from __future__ import annotations

import argparse
import bmesh
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


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
TARGETS = (
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


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--genital-length", type=float, default=0.0)
    parser.add_argument("--genital-circumference", type=float, default=0.0)
    parser.add_argument("--testicle-size", type=float, default=0.0)
    parser.add_argument("--root-inset", type=float, default=0.12)
    parser.add_argument(
        "--extra-target",
        action="append",
        default=[],
        metavar="RELATIVE_PATH=WEIGHT",
        help=(
            "Apply an additional bounded MakeHuman target before topology "
            "integration. The path is relative to data/targets and may be "
            "repeated."
        ),
    )
    parser.add_argument("--skip-renders", action="store_true")
    parser.add_argument("--no-union", action="store_true")
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


RENDER_GROUPS = {"body", "helper-genital"}


def _parse_body_group(path: Path) -> tuple[list[Vector], list[tuple[int, ...]]]:
    vertices: list[Vector] = []
    faces: list[tuple[int, ...]] = []
    group = ""
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                vertices.append(Vector((float(x), float(y), float(z))))
            elif line.startswith("g "):
                group = line[2:].strip()
            elif group in RENDER_GROUPS and line.startswith("f "):
                indices = []
                for token in line.split()[1:]:
                    value = int(token.split("/", 1)[0])
                    indices.append(value - 1 if value > 0 else len(vertices) + value)
                if len(indices) >= 3:
                    faces.append(tuple(indices))
    if not vertices or not faces:
        raise RuntimeError(
            "MakeHuman base OBJ did not yield the requested body/helper-genital groups"
        )
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
            if not 0 <= index < len(vertices):
                raise RuntimeError(f"target vertex {index} outside base mesh")
            vertices[index] += Vector(
                (
                    float(fields[1]) * weight,
                    float(fields[2]) * weight,
                    float(fields[3]) * weight,
                )
            )
            changed += 1
    return changed


def _keep_used_vertices(
    vertices: list[Vector], faces: list[tuple[int, ...]]
) -> tuple[list[tuple[float, float, float]], list[tuple[int, ...]]]:
    used = sorted({index for face in faces for index in face})
    remap = {old: new for new, old in enumerate(used)}
    # MakeHuman is Y-up and uses positive Z toward the face. Rotate +90 degrees
    # around X so the result is Blender Z-up with the face toward -Y.
    converted = [(vertices[i].x, -vertices[i].z, vertices[i].y) for i in used]
    return converted, [tuple(remap[i] for i in face) for face in faces]


def _boundary_components(
    vertices: list[tuple[float, float, float]], faces: list[tuple[int, ...]]
) -> list[dict[str, object]]:
    edge_counts: dict[tuple[int, int], int] = {}
    for face in faces:
        for offset, start in enumerate(face):
            end = face[(offset + 1) % len(face)]
            key = (start, end) if start < end else (end, start)
            edge_counts[key] = edge_counts.get(key, 0) + 1
    boundary_edges = [edge for edge, count in edge_counts.items() if count == 1]
    adjacency: dict[int, set[int]] = {}
    for start, end in boundary_edges:
        adjacency.setdefault(start, set()).add(end)
        adjacency.setdefault(end, set()).add(start)
    unseen = set(adjacency)
    components: list[dict[str, object]] = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        members = {seed}
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor not in members:
                    members.add(neighbor)
                    unseen.discard(neighbor)
                    stack.append(neighbor)
        points = [vertices[index] for index in members]
        components.append(
            {
                "vertex_count": len(members),
                "edge_count": sum(
                    1
                    for start, end in boundary_edges
                    if start in members and end in members
                ),
                "center": [
                    sum(point[axis] for point in points) / len(points)
                    for axis in range(3)
                ],
                "min": [min(point[axis] for point in points) for axis in range(3)],
                "max": [max(point[axis] for point in points) for axis in range(3)],
                "closed_cycle": all(len(adjacency[index]) == 2 for index in members),
            }
        )
    components.sort(key=lambda row: int(row["vertex_count"]), reverse=True)
    return components


def _surface_components(
    vertices: list[tuple[float, float, float]], faces: list[tuple[int, ...]]
) -> list[dict[str, object]]:
    parent = list(range(len(vertices)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    used: set[int] = set()
    for face in faces:
        used.update(face)
        for index in face[1:]:
            union(face[0], index)
    groups: dict[int, set[int]] = {}
    for index in used:
        groups.setdefault(find(index), set()).add(index)
    components: list[dict[str, object]] = []
    for members in groups.values():
        points = [vertices[index] for index in members]
        components.append(
            {
                "vertex_count": len(members),
                "center": [
                    sum(point[axis] for point in points) / len(points)
                    for axis in range(3)
                ],
                "min": [min(point[axis] for point in points) for axis in range(3)],
                "max": [max(point[axis] for point in points) for axis in range(3)],
            }
        )
    components.sort(key=lambda row: int(row["vertex_count"]), reverse=True)
    return components


def _material() -> bpy.types.Material:
    material = bpy.data.materials.new("CC0_MakeHuman_Neutral_Skin")
    material.diffuse_color = (0.56, 0.35, 0.27, 1.0)
    material.use_nodes = True
    node = material.node_tree.nodes.get("Principled BSDF")
    if node is not None:
        node.inputs["Base Color"].default_value = (0.56, 0.35, 0.27, 1.0)
        node.inputs["Roughness"].default_value = 0.52
        node.inputs["Subsurface Weight"].default_value = 0.08
    return material


def _mesh_topology(obj: bpy.types.Object) -> dict[str, object]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary_edges = [edge for edge in bm.edges if edge.is_boundary]
    nonmanifold_edges = [edge for edge in bm.edges if not edge.is_manifold]
    components = 0
    unseen = set(bm.verts)
    while unseen:
        components += 1
        seed = unseen.pop()
        stack = [seed]
        while stack:
            current = stack.pop()
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other in unseen:
                    unseen.remove(other)
                    stack.append(other)
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "surface_components": components,
        "boundary_edges": len(boundary_edges),
        "nonmanifold_edges": len(nonmanifold_edges),
    }
    bm.free()
    return result


def _integrate_loose_components(
    source: bpy.types.Object,
    *,
    root_inset: float,
) -> tuple[bpy.types.Object, dict[str, object]]:
    bpy.context.view_layer.objects.active = source
    source.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = sorted(
        [
            obj
            for obj in bpy.context.selected_objects
            if obj.type == "MESH"
        ],
        key=lambda obj: len(obj.data.vertices),
        reverse=True,
    )
    if len(parts) != 2:
        raise RuntimeError(
            f"expected body plus one genital helper component; found {len(parts)}"
        )
    primary, attachment = parts
    primary.name = "CC0_MakeHuman_Adult_Male_Primary"
    attachment.name = "CC0_MakeHuman_Adult_Male_Anatomy_Helper"

    primary_bm = bmesh.new()
    primary_bm.from_mesh(primary.data)
    bmesh.ops.recalc_face_normals(primary_bm, faces=list(primary_bm.faces))
    primary_volume_before = primary_bm.calc_volume(signed=True)
    if primary_volume_before < 0:
        bmesh.ops.reverse_faces(primary_bm, faces=list(primary_bm.faces))
    primary_volume_after = primary_bm.calc_volume(signed=True)
    primary_bm.to_mesh(primary.data)
    primary_bm.free()
    primary.data.update(calc_edges=True)

    attachment_before = _mesh_topology(attachment)
    bm = bmesh.new()
    bm.from_mesh(attachment.data)
    boundary_edges = [edge for edge in bm.edges if edge.is_boundary]
    if not boundary_edges:
        raise RuntimeError("anatomy helper had no root boundary to close")
    bmesh.ops.holes_fill(bm, edges=boundary_edges)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    attachment_volume_before = bm.calc_volume(signed=True)
    if attachment_volume_before < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    attachment_volume_after = bm.calc_volume(signed=True)
    bm.to_mesh(attachment.data)
    bm.free()
    attachment.data.update(calc_edges=True)
    attachment_after_cap = _mesh_topology(attachment)

    # The MakeHuman helper root is tangent to the neutral body surface. Give
    # the closed root a bounded posterior inset so the exact union has a real
    # overlap volume instead of a coplanar/tangent contact.
    attachment.location.y += root_inset
    bpy.context.view_layer.objects.active = attachment
    attachment.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

    bpy.ops.object.select_all(action="DESELECT")
    primary.select_set(True)
    bpy.context.view_layer.objects.active = primary
    modifier = primary.modifiers.new("IntegrateAdultMaleAnatomy", "BOOLEAN")
    modifier.operation = "UNION"
    modifier.solver = "EXACT"
    modifier.object = attachment
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    bpy.data.objects.remove(attachment, do_unlink=True)
    bm = bmesh.new()
    bm.from_mesh(primary.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.00001)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(primary.data)
    bm.free()
    primary.data.update(calc_edges=True)
    primary.name = "CC0_MakeHuman_Adult_Male_Foundation"
    return primary, {
        "method": "close_official_helper_root_then_exact_boolean_union",
        "root_inset": root_inset,
        "primary_signed_volume_before": primary_volume_before,
        "primary_signed_volume_after": primary_volume_after,
        "attachment_signed_volume_before": attachment_volume_before,
        "attachment_signed_volume_after": attachment_volume_after,
        "attachment_before": attachment_before,
        "attachment_after_cap": attachment_after_cap,
        "integrated_result": _mesh_topology(primary),
    }


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


def main() -> None:
    args = _arguments()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    vertices, faces = _parse_body_group(BASE_OBJ)
    applied = []
    for path, weight in TARGETS:
        applied.append(
            {
                "path": str(path),
                "sha256": _sha256(path),
                "weight": weight,
                "changed_vertices": _apply_target(vertices, path, weight),
            }
        )
    genital_targets = (
        ("penis-length", args.genital_length),
        ("penis-circ", args.genital_circumference),
        ("penis-testicles", args.testicle_size),
    )
    for stem, value in genital_targets:
        if value == 0:
            continue
        suffix = "incr" if value > 0 else "decr"
        path = MAKEHUMAN_DATA / "targets" / "genitals" / f"{stem}-{suffix}.target"
        applied.append(
            {
                "path": str(path),
                "sha256": _sha256(path),
                "weight": abs(value),
                "changed_vertices": _apply_target(vertices, path, abs(value)),
            }
        )
    for target_spec in args.extra_target:
        try:
            relative, raw_weight = target_spec.rsplit("=", 1)
            weight = float(raw_weight)
        except (ValueError, TypeError) as exc:
            raise RuntimeError(
                f"invalid --extra-target {target_spec!r}; expected RELATIVE_PATH=WEIGHT"
            ) from exc
        path = (MAKEHUMAN_DATA / "targets" / relative).resolve()
        target_root = (MAKEHUMAN_DATA / "targets").resolve()
        if target_root not in path.parents or path.suffix.lower() != ".target":
            raise RuntimeError(
                f"extra target must remain inside {target_root}: {target_spec!r}"
            )
        if not path.is_file():
            raise RuntimeError(f"extra target does not exist: {path}")
        if not -1.0 <= weight <= 1.0:
            raise RuntimeError(
                f"extra target weight must remain within [-1, 1]: {target_spec!r}"
            )
        applied.append(
            {
                "path": str(path),
                "sha256": _sha256(path),
                "weight": weight,
                "changed_vertices": _apply_target(vertices, path, weight),
                "source": "bounded_extra_target",
            }
        )

    compact_vertices, compact_faces = _keep_used_vertices(vertices, faces)
    boundary_components = _boundary_components(compact_vertices, compact_faces)
    surface_components = _surface_components(compact_vertices, compact_faces)
    mesh = bpy.data.meshes.new("CC0_MakeHuman_Adult_Male_Foundation")
    mesh.from_pydata(compact_vertices, [], compact_faces)
    mesh.update(calc_edges=True)
    body = bpy.data.objects.new("CC0_MakeHuman_Adult_Male_Foundation", mesh)
    bpy.context.collection.objects.link(body)
    body.data.materials.append(_material())
    for polygon in mesh.polygons:
        polygon.use_smooth = True

    integration = {
        "method": "not_run",
        "reason": "--no-union explicitly selected",
        "integrated_result": _mesh_topology(body),
    }
    if not args.no_union:
        body, integration = _integrate_loose_components(
            body, root_inset=args.root_inset
        )
        for polygon in body.data.polygons:
            polygon.use_smooth = True

    subdivision = body.modifiers.new("ReviewSubdivision", "SUBSURF")
    subdivision.levels = 1
    subdivision.render_levels = 2

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
    if not args.skip_renders:
        for filename, (location, target, scale) in views.items():
            _render(
                scene,
                camera,
                output_dir / filename,
                location=location,
                target=target,
                ortho_scale=scale,
            )

    blend_path = output_dir / "MAKEHUMAN_CC0_PARAMETRIC_MALE_FOUNDATION.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report = {
        "schema": "kira.avatar.makehuman_parametric_foundation_probe.v1",
        "status": "ENGINEERING_PROBE_AWAITING_VISUAL_AND_TOPOLOGY_REVIEW",
        "not_owner_approved": True,
        "not_robert_identity_complete": True,
        "not_runtime_assigned": True,
        "license": "CC0-1.0",
        "base_obj": str(BASE_OBJ),
        "base_obj_sha256": _sha256(BASE_OBJ),
        "source_face_groups": sorted(RENDER_GROUPS),
        "source_vertex_count": len(vertices),
        "candidate_vertex_count": len(compact_vertices),
        "candidate_face_count": len(compact_faces),
        "surface_component_count": len(surface_components),
        "surface_components": surface_components,
        "boundary_component_count": len(boundary_components),
        "boundary_components": boundary_components,
        "integration": integration,
        "targets": applied,
        "estimate_label": "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE",
        "blend": str(blend_path),
        "blend_sha256": _sha256(blend_path),
        "renders": (
            {name: str(output_dir / name) for name in views}
            if not args.skip_renders
            else {}
        ),
    }
    report_path = output_dir / "FOUNDATION_PROBE_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
