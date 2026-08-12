"""Build an isolated MakeHuman-based Kira temporary functional-body candidate.

The candidate is a private, inactive Avatar Builder proof.  It deliberately
uses only the bundled CC0 MakeHuman hm08 female-neutral foundation, official
female macro deltas, default skeleton, and CC0 skeleton weights.  It does not
read Robert photographs, measurements, morphs, candidates, or private-review
folders.

The MakeHuman ``helper-genital`` group is explicitly excluded because it is a
male attachment.  A small bounded set of vertices on the already-closed female
body surface is instead reshaped to remove the deep triangular void while
retaining one connected manifold surface.  A licensed adult-female asset is
listed as reference-only structural guidance; no vertices, faces, materials,
identity, or proportions are copied from it.
"""

from __future__ import annotations

import argparse
import bmesh
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector
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
RIG_PATH = MAKEHUMAN_DATA / "rigs" / "default.mhskel"
WEIGHTS_PATH = MAKEHUMAN_DATA / "rigs" / "default_weights.mhw"
HAIR_PATH = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "asset_library"
    / "hair_reference"
    / "beautiful_hair_1_6e5776fa64.glb"
)
HAIR_PACK_PATH = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "asset_library"
    / "hair_reference"
    / "hair_pack_part_1_592f1bcc9b.glb"
)
R13_HAIR_OBJECT = "Object_134"
ADULT_REFERENCE_PATH = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "asset_library"
    / "adult_anatomy_reference"
    / "female_anatomy_study_progress_2_b0577836d8.glb"
)
GENERIC_BUILDER = ROOT / "tools" / "blender_build_makehuman_parametric_male_foundation.py"

TARGETS = (
    (
        MAKEHUMAN_DATA
        / "targets"
        / "macrodetails"
        / "universal-female-young-averagemuscle-averageweight.target",
        1.0,
    ),
    (
        MAKEHUMAN_DATA
        / "targets"
        / "macrodetails"
        / "caucasian-female-young.target",
        1.0,
    ),
)

TARGET_HEIGHT_METERS = 1.651


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--candidate-id",
        default="kira_temporary_functional_body_makehuman_r11",
    )
    parser.add_argument(
        "--knee-engineering-only",
        action="store_true",
        help=(
            "Build only the clean female body/rig, solve the bilateral knee "
            "axes from evaluated joint motion, and emit two focused rejected "
            "engineering previews."
        ),
    )
    parser.add_argument(
        "--face-hair-engineering-only",
        action="store_true",
        help=(
            "Build only the clean female body/rig plus fitted helper eyes and "
            "one removable black-hair mesh, then emit four focused rejected "
            "face/hair engineering previews."
        ),
    )
    parser.add_argument(
        "--hair-groom-crown-rear-only",
        action="store_true",
        help=(
            "Build a dense removable procedural strand groom and render only "
            "crown/rear fit-space views. No GLB or full candidate is emitted."
        ),
    )
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_generic():
    spec = importlib.util.spec_from_file_location(
        "makehuman_foundation_methodology",
        GENERIC_BUILDER,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load generic MakeHuman methodology: {GENERIC_BUILDER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _converted(point: Vector) -> Vector:
    # MakeHuman is Y-up and faces positive Z.  Blender is Z-up; the result
    # faces negative Y.
    return Vector((point.x, -point.z, point.y))


def _topology(obj: bpy.types.Object) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary = [edge for edge in bm.edges if edge.is_boundary]
    nonmanifold = [edge for edge in bm.edges if not edge.is_manifold]
    unseen = set(bm.verts)
    components = 0
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
        "boundary_edges": len(boundary),
        "nonmanifold_edges": len(nonmanifold),
    }
    bm.free()
    return result


def _world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def _body_source() -> tuple[
    list[Vector],
    list[tuple[int, ...]],
    dict[int, int],
    list[dict[str, object]],
    dict[str, object],
]:
    generic = _load_generic()
    generic.RENDER_GROUPS = {"body"}
    vertices, faces = generic._parse_body_group(BASE_OBJ)
    applied: list[dict[str, object]] = []
    for path, weight in TARGETS:
        changed = generic._apply_target(vertices, path, weight)
        applied.append(
            {
                "path": str(path),
                "sha256": _sha256(path),
                "weight": weight,
                "changed_vertices": changed,
                "note": (
                    "intentional neutral hm08 baseline; comments-only delta"
                    if changed == 0
                    else "official female macro delta"
                ),
            }
        )
    used = sorted({index for face in faces for index in face})
    old_to_new = {old: new for new, old in enumerate(used)}
    compact = [_converted(vertices[index]) for index in used]
    compact_faces = [tuple(old_to_new[index] for index in face) for face in faces]

    # Bounded local authored repair on the existing connected female surface.
    # These indices are stable hm08 body vertices.  The paired left/right
    # anchors form shallow external labial folds and a continuous perineal
    # transition instead of the source's deep triangular recess.  No faces are
    # added or transferred from the adult reference asset.
    authored = {
        4370: (0.0000, -0.7700, -0.7452),
        4372: (0.0000, -0.7050, -0.7709),
        6335: (-0.0400, -0.7000, -0.7850),
        12932: (0.0400, -0.7000, -0.7850),
        6392: (-0.0500, -0.6750, -0.8750),
        12989: (0.0500, -0.6750, -0.8750),
        6393: (-0.0580, -0.6450, -0.9950),
        12990: (0.0580, -0.6450, -0.9950),
        6394: (-0.0720, -0.6000, -1.1150),
        12991: (0.0720, -0.6000, -1.1150),
        6395: (-0.0950, -0.5550, -1.3000),
        12992: (0.0950, -0.5550, -1.3000),
    }
    before_after: list[dict[str, object]] = []
    for source_index, desired in authored.items():
        compact_index = old_to_new.get(source_index)
        if compact_index is None:
            raise RuntimeError(f"authored hm08 vertex missing from body group: {source_index}")
        before = compact[compact_index].copy()
        compact[compact_index] = Vector(desired)
        before_after.append(
            {
                "source_vertex": source_index,
                "compact_vertex": compact_index,
                "before": [round(float(value), 6) for value in before],
                "after": [round(float(value), 6) for value in desired],
            }
        )

    low_z = min(point.z for point in compact)
    high_z = max(point.z for point in compact)
    source_height = high_z - low_z
    scale = TARGET_HEIGHT_METERS / source_height
    for index, point in enumerate(compact):
        compact[index] = Vector(
            (
                point.x * scale,
                point.y * scale,
                (point.z - low_z) * scale,
            )
        )
    transform = {
        "source_height_units": source_height,
        "target_height_m": TARGET_HEIGHT_METERS,
        "uniform_scale": scale,
        "source_floor_z": low_z,
    }
    surface_note = {
        "method": "bounded_hm08_local_vertex_surface_authoring",
        "body_face_group_only": True,
        "male_helper_genital_excluded": True,
        "copied_reference_geometry": False,
        "estimate_label": "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE",
        "reference_only_asset": str(ADULT_REFERENCE_PATH),
        "reference_only_sha256": _sha256(ADULT_REFERENCE_PATH),
        "authored_vertices": before_after,
    }
    return compact, compact_faces, old_to_new, applied, {
        "transform": transform,
        "surface": surface_note,
        "all_deformed_source_vertices": vertices,
        "source_low_z": low_z,
        "scale": scale,
    }


def _skin_material() -> bpy.types.Material:
    material = bpy.data.materials.new("Kira_Temporary_Light_Skin")
    material.use_nodes = True
    material.diffuse_color = (0.64, 0.43, 0.35, 1.0)
    node = material.node_tree.nodes.get("Principled BSDF")
    if node is not None:
        node.inputs["Base Color"].default_value = (0.64, 0.43, 0.35, 1.0)
        node.inputs["Roughness"].default_value = 0.47
        node.inputs["Subsurface Weight"].default_value = 0.09
        node.inputs["Subsurface Radius"].default_value = (1.0, 0.42, 0.24)
    return material


def _simple_material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    roughness: float = 0.45,
    metallic: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color
    node = material.node_tree.nodes.get("Principled BSDF")
    if node is not None:
        node.inputs["Base Color"].default_value = color
        node.inputs["Roughness"].default_value = roughness
        node.inputs["Metallic"].default_value = metallic
    return material


def _build_body(
    vertices: list[Vector],
    faces: list[tuple[int, ...]],
    candidate_id: str,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{candidate_id}_primary_surface")
    mesh.from_pydata([tuple(point) for point in vertices], [], faces)
    mesh.update(calc_edges=True)
    body = bpy.data.objects.new(f"{candidate_id}_primary_surface", mesh)
    bpy.context.collection.objects.link(body)
    body.data.materials.append(_skin_material())
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    body["rapid_body_primary_surface"] = True
    body["candidate_id"] = candidate_id
    body["private_review_only"] = True
    body["runtime_activation_allowed"] = False
    body["roster_registration_allowed"] = False
    body["anatomical_forward_axis"] = "-Y"
    body["body_class"] = "adult_female"
    body["adult_surface_body_class"] = "adult_female"
    body["wrong_body_class_helper_or_surface_excluded"] = True
    body["left_knee_upper_bone"] = "upperleg02.L"
    body["left_knee_lower_bone"] = "lowerleg01.L"
    body["left_ankle_bone"] = "lowerleg02.L"
    body["right_knee_upper_bone"] = "upperleg02.R"
    body["right_knee_lower_bone"] = "lowerleg01.R"
    body["right_ankle_bone"] = "lowerleg02.R"
    return body


def _joint_positions(
    rig_data: dict[str, object],
    source_vertices: list[Vector],
    *,
    source_low_z: float,
    scale: float,
) -> dict[str, Vector]:
    positions: dict[str, Vector] = {}
    for name, indices in rig_data["joints"].items():
        source = Vector((0.0, 0.0, 0.0))
        for index in indices:
            source += _converted(source_vertices[int(index)])
        source /= len(indices)
        positions[name] = Vector(
            (
                source.x * scale,
                source.y * scale,
                (source.z - source_low_z) * scale,
            )
        )
    return positions


def _plane_normal(
    plane_name: str,
    rig_data: dict[str, object],
    joint_positions: dict[str, Vector],
) -> Vector | None:
    names = rig_data.get("planes", {}).get(plane_name)
    if not names or any(name not in joint_positions for name in names):
        return None
    p1, p2, p3 = (joint_positions[name] for name in names)
    first = (p2 - p1).normalized()
    second = (p3 - p2).normalized()
    normal = second.cross(first)
    return normal.normalized() if normal.length > 1e-8 else None


def _build_armature(
    body: bpy.types.Object,
    old_to_new: dict[int, int],
    source_vertices: list[Vector],
    *,
    source_low_z: float,
    scale: float,
    candidate_id: str,
) -> tuple[bpy.types.Object, dict[str, object]]:
    rig_data = json.loads(RIG_PATH.read_text(encoding="utf-8"))
    weight_data = json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))
    joints = _joint_positions(
        rig_data,
        source_vertices,
        source_low_z=source_low_z,
        scale=scale,
    )
    armature_data = bpy.data.armatures.new(f"{candidate_id}_skeleton")
    armature = bpy.data.objects.new(f"{candidate_id}_rig", armature_data)
    bpy.context.collection.objects.link(armature)
    armature.show_in_front = True
    armature["candidate_id"] = candidate_id
    armature["private_review_only"] = True
    armature["runtime_activation_allowed"] = False
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    remaining = dict(rig_data["bones"])
    built: set[str] = set()
    while remaining:
        progressed = False
        for name, definition in list(remaining.items()):
            parent = definition.get("parent")
            if parent and parent not in built:
                continue
            head = joints[definition["head"]]
            tail = joints[definition["tail"]]
            if (tail - head).length < 1e-5:
                tail = head + Vector((0.0, 0.0, 0.01))
            edit = armature_data.edit_bones.new(name)
            edit.head = head
            edit.tail = tail
            edit.use_deform = name in weight_data["weights"]
            if parent:
                edit.parent = armature_data.edit_bones[parent]
                edit.use_connect = (edit.head - edit.parent.tail).length < 0.0005
            rotation_plane = definition.get("rotation_plane")
            normals = []
            for plane_name in (
                rotation_plane
                if isinstance(rotation_plane, list)
                else [rotation_plane]
            ):
                if isinstance(plane_name, str):
                    normal = _plane_normal(plane_name, rig_data, joints)
                    if normal is not None:
                        normals.append(normal)
            if normals:
                normal = sum(normals, Vector((0.0, 0.0, 0.0))).normalized()
                try:
                    edit.align_roll(normal)
                except ValueError:
                    pass
            built.add(name)
            del remaining[name]
            progressed = True
        if not progressed:
            raise RuntimeError(f"could not resolve rig parents: {sorted(remaining)}")
    bpy.ops.object.mode_set(mode="OBJECT")

    group_count = 0
    assignment_count = 0
    vertex_weight_sums = [0.0] * len(body.data.vertices)
    for bone_name, assignments in weight_data["weights"].items():
        mapped = [
            (old_to_new[int(source_index)], float(weight))
            for source_index, weight in assignments
            if int(source_index) in old_to_new and float(weight) > 0.0
        ]
        if not mapped:
            continue
        group = body.vertex_groups.new(name=bone_name)
        group_count += 1
        for compact_index, weight in mapped:
            group.add([compact_index], weight, "REPLACE")
            vertex_weight_sums[compact_index] += weight
            assignment_count += 1
    root_group = body.vertex_groups.get("root")
    if root_group is None:
        root_group = body.vertex_groups.new(name="root")
        group_count += 1
    unweighted = []
    for index, total in enumerate(vertex_weight_sums):
        if total <= 1e-8:
            root_group.add([index], 1.0, "REPLACE")
            unweighted.append(index)
    modifier = body.modifiers.new("Kira_Official_MakeHuman_Rig", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    subdivision = body.modifiers.new("Kira_Review_Subdivision", "SUBSURF")
    subdivision.levels = 1
    subdivision.render_levels = 1
    return armature, {
        "rig_path": str(RIG_PATH),
        "rig_sha256": _sha256(RIG_PATH),
        "weights_path": str(WEIGHTS_PATH),
        "weights_sha256": _sha256(WEIGHTS_PATH),
        "bone_count": len(armature.data.bones),
        "deform_bone_count": sum(1 for bone in armature.data.bones if bone.use_deform),
        "vertex_group_count": group_count,
        "weight_assignment_count": assignment_count,
        "fallback_root_weight_vertex_count": len(unweighted),
        "weighted_vertex_count": len(body.data.vertices),
        "weight_coverage": 1.0,
    }


def _assign_rigid_bone(
    obj: bpy.types.Object,
    armature: bpy.types.Object,
    bone_name: str,
) -> None:
    group = obj.vertex_groups.new(name=bone_name)
    group.add([vertex.index for vertex in obj.data.vertices], 1.0, "REPLACE")
    modifier = obj.modifiers.new("Kira_Rigid_Bone_Deform", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True


def _obj_group_faces(path: Path, requested_group: str) -> list[tuple[int, ...]]:
    """Read one exact OBJ face group while preserving source vertex indices."""

    faces: list[tuple[int, ...]] = []
    vertex_count = 0
    group = ""
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith("v "):
                vertex_count += 1
            elif line.startswith("g "):
                group = line[2:].strip()
            elif group == requested_group and line.startswith("f "):
                indices = []
                for token in line.split()[1:]:
                    value = int(token.split("/", 1)[0])
                    indices.append(value - 1 if value > 0 else vertex_count + value)
                if len(indices) >= 3:
                    faces.append(tuple(indices))
    if not faces:
        raise RuntimeError(
            f"MakeHuman base OBJ contains no faces for {requested_group!r}"
        )
    return faces


def _makehuman_group_object(
    *,
    name: str,
    group: str,
    source_vertices: list[Vector],
    source_low_z: float,
    scale: float,
    material: bpy.types.Material,
) -> tuple[bpy.types.Object, dict[str, object]]:
    faces = _obj_group_faces(BASE_OBJ, group)
    used = sorted({index for face in faces for index in face})
    old_to_new = {old: new for new, old in enumerate(used)}
    points = []
    for source_index in used:
        point = _converted(source_vertices[source_index])
        points.append(
            Vector(
                (
                    point.x * scale,
                    point.y * scale,
                    (point.z - source_low_z) * scale,
                )
            )
        )
    compact_faces = [tuple(old_to_new[index] for index in face) for face in faces]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(point) for point in points], [], compact_faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    low, high = _world_bounds([obj])
    return obj, {
        "source_group": group,
        "source_vertex_count": len(used),
        "source_face_count": len(faces),
        "bounds_low_before_fit": [round(float(value), 6) for value in low],
        "bounds_high_before_fit": [round(float(value), 6) for value in high],
    }


def _add_r13_helper_eyes(
    body: bpy.types.Object,
    armature: bpy.types.Object,
    source: dict[str, object],
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    """Seat official CC0 helper-eye geometry inside the hm08 eyelids.

    The official helper groups begin aligned to this exact base head.  They
    are uniformly reduced to a human-scale visible globe and moved 2.2 mm
    posteriorly so the upper/lower body eyelids occlude the sclera instead of
    producing the R11 protruding-eye failure.
    """

    sclera_material = _simple_material(
        "Kira_R13_Natural_Sclera",
        (0.78, 0.75, 0.70, 1.0),
        roughness=0.26,
    )
    iris_material = _simple_material(
        "Kira_R13_Natural_Brown_Iris",
        (0.16, 0.052, 0.014, 1.0),
        roughness=0.31,
    )
    pupil_material = _simple_material(
        "Kira_R13_Pupil",
        (0.0025, 0.0018, 0.0015, 1.0),
        roughness=0.20,
    )
    source_vertices = source["all_deformed_source_vertices"]
    source_low_z = float(source["source_low_z"])
    source_scale = float(source["scale"])
    objects: list[bpy.types.Object] = []
    records: dict[str, object] = {}
    for side, group in (("L", "helper-l-eye"), ("R", "helper-r-eye")):
        sclera, record = _makehuman_group_object(
            name=f"Kira_R13_Official_Helper_Eye_Sclera_{side}",
            group=group,
            source_vertices=source_vertices,
            source_low_z=source_low_z,
            scale=source_scale,
            material=sclera_material,
        )
        low, high = _world_bounds([sclera])
        center = (low + high) * 0.5
        fit_scale = 0.855
        for vertex in sclera.data.vertices:
            vertex.co = center + (vertex.co - center) * fit_scale
            vertex.co.y += 0.0022
        sclera.data.update()
        low, high = _world_bounds([sclera])
        center = (low + high) * 0.5
        radii = (high - low) * 0.5
        iris_center = Vector((center.x, low.y - 0.00010, center.z))
        iris = _add_uv_sphere(
            f"Kira_R13_Brown_Iris_{side}",
            iris_center,
            (radii.x * 0.43, 0.00072, radii.z * 0.43),
            iris_material,
            segments=32,
            ring_count=16,
        )
        pupil = _add_uv_sphere(
            f"Kira_R13_Pupil_{side}",
            Vector((center.x, low.y - 0.00065, center.z)),
            (radii.x * 0.17, 0.00044, radii.z * 0.17),
            pupil_material,
            segments=24,
            ring_count=12,
        )
        for obj in (sclera, iris, pupil):
            obj["eye_component"] = True
            obj["private_review_only"] = True
            obj["opaque_eyelash_card"] = False
            obj["black_eye_band"] = False
            _assign_rigid_bone(obj, armature, f"eye.{side}")
            objects.append(obj)
        record.update(
            {
                "fit_scale": fit_scale,
                "posterior_inset_m": 0.0022,
                "center": [round(float(value), 6) for value in center],
                "fitted_diameter_m": [
                    round(float(value), 6) for value in (high - low)
                ],
                "bounds_low_after_fit": [
                    round(float(value), 6) for value in low
                ],
                "bounds_high_after_fit": [
                    round(float(value), 6) for value in high
                ],
            }
        )
        records[side] = record
    return objects, {
        "method": "official_cc0_hm08_helper_eye_groups_bounded_socket_fit",
        "color": "natural brown",
        "helper_group_count": 2,
        "component_count": len(objects),
        "opaque_eyelash_card_count": 0,
        "black_eye_band_object_count": 0,
        "records": records,
        "visual_fit_requires_render_review": True,
    }


def _add_r13_hair(
    body: bpy.types.Object,
    armature: bpy.types.Object,
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    """Fit one real removable hair mesh; exclude all caps/underlays."""

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(HAIR_PACK_PATH))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    candidates = [
        obj
        for obj in imported
        if obj.type == "MESH" and obj.name.split(".", 1)[0] == R13_HAIR_OBJECT
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected one {R13_HAIR_OBJECT} mesh in the licensed hair pack, found "
            f"{[obj.name for obj in candidates]}"
        )
    hair = candidates[0]
    source_object_name = hair.name
    # Preserve the evaluated world transform before deleting pack hierarchy.
    world_matrix = hair.matrix_world.copy()
    hair.parent = None
    hair.matrix_world = world_matrix
    bpy.context.view_layer.objects.active = hair
    bpy.ops.object.select_all(action="DESELECT")
    hair.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for obj in imported:
        if obj is not hair:
            bpy.data.objects.remove(obj, do_unlink=True)
    # Strip the source pack's skeleton binding before fitting to Kira's head.
    # Leaving that modifier in place made the R13 authoring coordinates and
    # rendered/evaluated coordinates disagree, producing detached hair.
    for modifier in list(hair.modifiers):
        hair.modifiers.remove(modifier)
    for group in list(hair.vertex_groups):
        hair.vertex_groups.remove(group)

    body_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    maximum_z = max(point.z for point in body_points)
    head_points = [point for point in body_points if point.z >= maximum_z - 0.270]
    head_low = Vector(
        tuple(min(point[axis] for point in head_points) for axis in range(3))
    )
    head_high = Vector(
        tuple(max(point[axis] for point in head_points) for axis in range(3))
    )
    source_low, source_high = _world_bounds([hair])
    source_center = (source_low + source_high) * 0.5
    source_size = source_high - source_low
    desired_width = (head_high.x - head_low.x) * 1.18
    desired_depth = (head_high.y - head_low.y) * 1.22
    desired_height = (head_high.z - head_low.z) * 1.20
    fit_scale = Vector(
        (
            desired_width / max(source_size.x, 1e-8),
            desired_depth / max(source_size.y, 1e-8),
            desired_height / max(source_size.z, 1e-8),
        )
    )
    desired_center = Vector(
        (
            (head_low.x + head_high.x) * 0.5,
            (head_low.y + head_high.y) * 0.5 + 0.002,
            maximum_z + 0.025 - desired_height * 0.5,
        )
    )
    hair.scale = fit_scale
    hair.location = desired_center - Vector(
        (
            source_center.x * fit_scale.x,
            source_center.y * fit_scale.y,
            source_center.z * fit_scale.z,
        )
    )
    bpy.context.view_layer.objects.active = hair
    bpy.ops.object.select_all(action="DESELECT")
    hair.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    hair.data.update()
    hair.name = "Kira_R13_Removable_Straight_Black_Hair"
    hair["removable_review_hair"] = True
    hair["runtime_hair_complete"] = False
    hair["private_review_only"] = True
    hair["source_object"] = source_object_name
    hair["scalp_cap_or_underlay"] = False
    _darken_hair_materials([hair])
    _assign_rigid_bone(hair, armature, "head")
    final_low, final_high = _world_bounds([hair])
    head_center = (head_low + head_high) * 0.5
    return [hair], {
        "path": str(HAIR_PACK_PATH),
        "sha256": _sha256(HAIR_PACK_PATH),
        "source_object": source_object_name,
        "method": "single_licensed_hair_mesh_world_space_head_fit",
        "imported_component_object_count": len(imported),
        "retained_hair_mesh_count": 1,
        "deleted_nonselected_component_object_count": len(imported) - 1,
        "scalp_cap_or_underlay_object_count": 0,
        "opaque_eyelash_card_count": 0,
        "fit_scale_xyz": [round(float(value), 8) for value in fit_scale],
        "desired_size_m": [
            round(float(value), 6)
            for value in (desired_width, desired_depth, desired_height)
        ],
        "head_bounds_low": [round(float(value), 6) for value in head_low],
        "head_bounds_high": [round(float(value), 6) for value in head_high],
        "head_center": [round(float(value), 6) for value in head_center],
        "hair_bounds_low": [round(float(value), 6) for value in final_low],
        "hair_bounds_high": [round(float(value), 6) for value in final_high],
        "removable": True,
        "runtime_hair_complete": False,
        "visual_fit_requires_front_profile_crown_rear_review": True,
    }


def _add_procedural_straight_black_groom(
    body: bpy.types.Object,
    armature: bpy.types.Object,
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    """Author a dense actual-strand static groom around the target scalp.

    Every visible element is a bevelled curve converted to mesh.  There is no
    scalp cap, opaque underlay, helmet shell, or painted-on hair.  The front
    root envelope stops at the upper forehead; side/rear roots continue over
    crown and occiput, and strand endpoints fall toward the neck/shoulders.
    """

    body_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    maximum_z = max(point.z for point in body_points)
    head_points = [point for point in body_points if point.z >= maximum_z - 0.270]
    head_low = Vector(
        tuple(min(point[axis] for point in head_points) for axis in range(3))
    )
    head_high = Vector(
        tuple(max(point[axis] for point in head_points) for axis in range(3))
    )
    upper = [point for point in head_points if point.z >= maximum_z - 0.135]
    upper_low = Vector(tuple(min(point[axis] for point in upper) for axis in range(3)))
    upper_high = Vector(tuple(max(point[axis] for point in upper) for axis in range(3)))
    center = Vector(
        (
            (upper_low.x + upper_high.x) * 0.5,
            (upper_low.y + upper_high.y) * 0.5,
            maximum_z - 0.132,
        )
    )
    radii = Vector(
        (
            (upper_high.x - upper_low.x) * 0.5 + 0.006,
            (upper_high.y - upper_low.y) * 0.5 + 0.008,
            0.137,
        )
    )

    # R13h/R13i proved that an analytic ellipsoid is not a safe final
    # attachment surface: curve controls could lie behind the real scalp even
    # though their coordinates were outside the ellipsoid.  Build an actual
    # head-surface BVH and project every root and scalp-following control to
    # that mesh.  The ellipsoid below is now only a sampling envelope.
    head_face_floor = maximum_z - 0.305
    head_faces = []
    for polygon in body.data.polygons:
        face_points = [body_points[index] for index in polygon.vertices]
        if min(point.z for point in face_points) >= head_face_floor:
            head_faces.append(tuple(int(index) for index in polygon.vertices))
    head_bvh = BVHTree.FromPolygons(body_points, head_faces, all_triangles=False)
    if head_bvh is None:
        raise RuntimeError("could not build actual-head BVH for strand groom")
    body_bvh = BVHTree.FromPolygons(
        body_points,
        [tuple(int(index) for index in polygon.vertices) for polygon in body.data.polygons],
        all_triangles=False,
    )
    if body_bvh is None:
        raise RuntimeError("could not build body BVH for hair/body collision")

    def project_to_head(point: Vector):
        result = head_bvh.find_nearest(point, 0.090)
        if result is None or result[0] is None or result[1] is None:
            return None
        location, normal, polygon_index, distance = result
        normal = normal.normalized()
        # Preserve an outward offset even if an imported face winding happens
        # to be reversed.
        if normal.dot(location - center) < 0.0:
            normal.negate()
        return location, normal, polygon_index, float(distance)

    def distribution(values: list[float]) -> dict[str, float | int | None]:
        if not values:
            return {
                "count": 0,
                "minimum_m": None,
                "median_m": None,
                "maximum_m": None,
            }
        ordered = sorted(values)
        midpoint = len(ordered) // 2
        if len(ordered) % 2:
            median = ordered[midpoint]
        else:
            median = (ordered[midpoint - 1] + ordered[midpoint]) * 0.5
        return {
            "count": len(ordered),
            "minimum_m": round(float(ordered[0]), 8),
            "median_m": round(float(median), 8),
            "maximum_m": round(float(ordered[-1]), 8),
        }

    def safe_scalp_offset(
        surface: Vector,
        normal: Vector,
        clearance: float,
    ):
        """Return a point verified outside the nearest actual scalp faces."""

        point = surface + normal * clearance
        for _attempt in range(5):
            nearest = project_to_head(point)
            if nearest is None:
                return None
            nearest_location, nearest_normal, polygon_index, nearest_distance = nearest
            signed = (point - nearest_location).dot(nearest_normal)
            if signed > 0.0 and nearest_distance >= clearance * 0.70:
                return (
                    point,
                    nearest_location,
                    nearest_normal,
                    polygon_index,
                    nearest_distance,
                    signed,
                )
            corrected_normal = normal + nearest_normal
            if corrected_normal.length < 1e-8:
                corrected_normal = nearest_normal
            corrected_normal.normalize()
            point = nearest_location + corrected_normal * (clearance * 1.12)
            normal = corrected_normal
        return None

    def body_collision_correct(point: Vector, clearance: float = 0.0040):
        nearest = body_bvh.find_nearest(point, 0.040)
        if nearest is None or nearest[0] is None or nearest[1] is None:
            return point, False
        location, normal, _polygon_index, distance = nearest
        normal = normal.normalized()
        # The MakeHuman body has outward winding.  Correct only points on the
        # inward side or points closer than the requested hair/body spacing.
        signed = (point - location).dot(normal)
        if signed >= clearance and float(distance) >= clearance:
            return point, False
        return location + normal * clearance, True

    material = _simple_material(
        "Kira_Static_Straight_Black_Strand_Groom",
        (0.0045, 0.0035, 0.007, 1.0),
        roughness=0.58,
    )
    hair_principled = material.node_tree.nodes.get("Principled BSDF")
    if hair_principled is not None:
        specular = hair_principled.inputs.get("Specular IOR Level")
        if specular is not None:
            specular.default_value = 0.18
    curve_data = bpy.data.curves.new("Kira_R13G_Actual_Hair_Strands", "CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 1
    curve_data.bevel_depth = 0.00019
    curve_data.bevel_resolution = 0
    curve_data.resolution_u = 1
    curve_data.materials.append(material)
    center_bridge_diagnostic = "bridge_diagnostic" in body.name.lower()
    if center_bridge_diagnostic:
        curve_data.materials.append(
            _simple_material(
                "Kira_Center_Bridge_DIAGNOSTIC_RED",
                (0.8, 0.005, 0.005, 1.0),
                roughness=0.52,
            )
        )
        curve_data.materials.append(
            _simple_material(
                "Kira_Center_ROI_Base_Paths_DIAGNOSTIC_GREEN",
                (0.005, 0.72, 0.04, 1.0),
                roughness=0.52,
            )
        )
    fibonacci_candidate_count = 160000
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    strand_count = 0
    root_clearance = 0.00090
    root_clearances: list[float] = []
    scalp_follow_clearances: list[float] = []
    outward_clearance_failures = 0
    duplicate_root_rejections = 0
    envelope_rejections = 0
    projection_rejections = 0
    unsafe_offset_rejections = 0
    body_collision_corrections = 0
    center_bridge_strand_count = 0
    center_bridge_clearances: list[float] = []
    center_bridge_outward_failures = 0
    center_roi_diagnostic_strand_count = 0
    fall_envelope_clamp_count = 0
    fall_envelope_margin_x = 0.003
    fall_envelope_front_margin_y = 0.003
    fall_envelope_rear_margin_y = 0.003
    fall_envelope_soft_limit = 0.004
    front_neck_route_count = 0

    def soft_limit(value: float, low: float, high: float) -> tuple[float, bool]:
        if value < low:
            return (
                low
                - fall_envelope_soft_limit
                * math.tanh((low - value) / fall_envelope_soft_limit),
                True,
            )
        if value > high:
            return (
                high
                + fall_envelope_soft_limit
                * math.tanh((value - high) / fall_envelope_soft_limit),
                True,
            )
        return value, False
    used_root_cells: set[tuple[int, int, int]] = set()
    sampling_radii = Vector(
        (
            radii.x + 0.020,
            radii.y + 0.026,
            radii.z + 0.018,
        )
    )
    for sample_index in range(fibonacci_candidate_count):
        unit_z = 1.0 - 1.72 * (sample_index + 0.5) / fibonacci_candidate_count
        radial = math.sqrt(max(0.0, 1.0 - unit_z * unit_z))
        phi = sample_index * golden_angle
        planned = center + Vector(
            (
                sampling_radii.x * radial * math.cos(phi),
                sampling_radii.y * radial * math.sin(phi),
                sampling_radii.z * unit_z,
            )
        )
        projected = project_to_head(planned)
        if projected is None:
            projection_rejections += 1
            continue
        root_surface, root_normal, _polygon_index, _distance = projected
        relative_y = root_surface.y - center.y
        # Stop roots at the upper forehead; continue lower only around sides
        # and rear/occiput.  These are actual projected surface coordinates,
        # not a synthetic shell.
        if relative_y < -0.018:
            minimum_root_z = maximum_z - 0.118
        elif relative_y < 0.014:
            minimum_root_z = maximum_z - 0.192
        else:
            minimum_root_z = maximum_z - 0.238
        if (
            root_surface.z < minimum_root_z
            or root_surface.z > maximum_z + 0.002
            or abs(root_surface.x - center.x) > 0.101
            or root_normal.z < -0.42
        ):
            envelope_rejections += 1
            continue
        root_cell = tuple(round(float(value) / 0.00038) for value in root_surface)
        if root_cell in used_root_cells:
            duplicate_root_rejections += 1
            continue
        used_root_cells.add(root_cell)

        deterministic = math.sin((sample_index + 1) * 1.731)
        side = (
            -1.0
            if root_surface.x < center.x
            else 1.0
        )
        if abs(root_surface.x - center.x) < 0.009:
            side = -1.0 if sample_index % 2 else 1.0
        front_origin = relative_y < -0.018
        points: list[Vector] = []
        surface = root_surface
        normal = root_normal
        previous_tangent: Vector | None = None
        scalp_sample_count = 11 + (sample_index % 6)
        scalp_step_m = 0.0086
        for step in range(scalp_sample_count):
            clearance = root_clearance + 0.00013 * (
                0.5 + 0.5 * math.sin(sample_index * 0.419 + step * 0.271)
            )
            safe_point = safe_scalp_offset(surface, normal, clearance)
            if safe_point is None:
                unsafe_offset_rejections += 1
                break
            (
                point,
                nearest_location,
                nearest_normal,
                _nearest_index,
                nearest_distance,
                outward,
            ) = safe_point
            if step == 0:
                root_clearances.append(nearest_distance)
            else:
                scalp_follow_clearances.append(nearest_distance)
            points.append(point)
            if step == scalp_sample_count - 1:
                break

            # Gravity is projected onto the *actual* scalp tangent.  At the
            # near-horizontal crown the groom is deliberately combed toward
            # the rear with only a tiny asymmetric lateral drift.  This gives
            # overlapping lay instead of a radial crown singularity or a wide
            # artificial center-part zipper.
            desired = Vector((0.0, 0.0, -1.0))
            if normal.y < -0.30:
                # The face points toward -Y.  Gravity projected at the
                # near-vertical forehead drove the old front-root subset down
                # into one hairline convergence/star.  Guide only this subset
                # upward over the forehead toward crown; once the local normal
                # becomes crown-like, the normal combed-back rule takes over.
                desired = Vector(
                    (
                        side * (0.16 + 0.025 * deterministic),
                        0.30,
                        0.92,
                    )
                )
            elif normal.z > 0.50:
                crown_weight = min(1.0, (normal.z - 0.50) / 0.45)
                crown_lateral = (
                    side * (0.032 + 0.008 * deterministic)
                    if front_origin
                    else 0.0025 * deterministic
                )
                desired += Vector(
                    (
                        crown_lateral * crown_weight,
                        (0.30 + 0.025 * deterministic) * crown_weight,
                        0.0,
                    )
                )
            center_lane_proximity = max(
                0.0,
                1.0 - abs(surface.x - center.x) / 0.012,
            )
            if center_lane_proximity > 0.0:
                # Prevent any path from sharing the old centerline fall pole.
                # Alternating lane assignment near x=0 produces bounded
                # diagonal overlap rather than a single wedge/tear.
                desired += Vector(
                    (
                        side * 0.075 * center_lane_proximity,
                        0.0,
                        0.0,
                    )
                )
            tangent = desired - normal * desired.dot(normal)
            if tangent.length < 1e-8:
                tangent = Vector((0.002 * deterministic, 0.24, 0.0))
                tangent -= normal * tangent.dot(normal)
            if tangent.length < 1e-8:
                break
            tangent.normalize()
            if previous_tangent is not None:
                tangent = previous_tangent * 0.58 + tangent * 0.42
                tangent -= normal * tangent.dot(normal)
                if tangent.length < 1e-8:
                    break
                tangent.normalize()
            previous_tangent = tangent.copy()
            next_projected = project_to_head(surface + tangent * scalp_step_m)
            if next_projected is None:
                projection_rejections += 1
                break
            next_surface, next_normal, _next_index, _next_distance = next_projected
            if (next_surface - surface).length < 0.001:
                break
            surface = next_surface
            normal = next_normal
            if step >= 7 and surface.z < maximum_z - 0.248:
                break
        if len(points) < 3:
            continue

        scalp_point_count = len(points)
        tangent_end = points[-1]
        end_projected = project_to_head(tangent_end)
        end_normal = end_projected[1] if end_projected is not None else normal
        horizontal = Vector((end_normal.x, end_normal.y, 0.0))
        if horizontal.length < 1e-8:
            horizontal = Vector((0.0, 1.0, 0.0))
        horizontal.normalize()
        front_root = front_origin
        if front_root:
            horizontal = Vector((0.015 * deterministic, 1.0, 0.0)).normalized()
            fall_length = 0.090 + 0.018 * (0.5 + 0.5 * deterministic)
        else:
            horizontal = Vector(
                (
                    max(-0.12, min(0.12, horizontal.x)),
                    max(0.35, horizontal.y),
                    0.0,
                )
            ).normalized()
            fall_length = 0.112 + 0.044 * (
                0.5 + 0.5 * math.sin(sample_index * 0.731)
            )
        fall_end = tangent_end + horizontal * (
            0.00070 + 0.00045 * (0.5 + 0.5 * deterministic)
        )
        # A softly stratified shoulder/nape hem avoids the ruler-straight
        # rectangular panel produced by R13j/R13k while remaining straight,
        # not curly.  Center/rear strands are only modestly longer.
        normalized_side = min(
            1.0,
            abs(tangent_end.x - center.x) / max(radii.x, 1e-8),
        )
        hem_noise = 0.5 + 0.5 * math.sin(sample_index * 0.347)
        hem_z = 1.327 + 0.028 * normalized_side + 0.008 * hem_noise
        fall_end.z = max(hem_z, tangent_end.z - fall_length)
        for step in range(1, 6):
            t = step / 5.0
            point = tangent_end.lerp(fall_end, t)
            point += horizontal * (0.0030 * t * t)
            point += Vector(
                (
                    0.00024 * deterministic * math.sin(math.pi * t),
                    0.00020
                    * math.sin(sample_index * 0.313)
                    * math.sin(math.pi * t),
                    0.0,
                )
            )
            if (
                point.z < maximum_z - 0.110
                and point.y < center.y + 0.008
                and abs(point.x - center.x) < 0.045
            ):
                route_progress = min(
                    1.0,
                    (maximum_z - 0.110 - point.z) / 0.055,
                )
                route_strength = route_progress * route_progress * (
                    3.0 - 2.0 * route_progress
                )
                target_x = center.x + side * (
                    0.041 + 0.0012 * deterministic
                )
                point.x = (
                    point.x * (1.0 - 0.94 * route_strength)
                    + target_x * (0.94 * route_strength)
                )
                front_neck_route_count += 1
            point, corrected = body_collision_correct(point)
            if corrected:
                body_collision_corrections += 1
            clamped_x, clamped_x_changed = soft_limit(
                point.x,
                head_low.x - fall_envelope_margin_x,
                head_high.x + fall_envelope_margin_x,
            )
            if clamped_x_changed:
                point.x = clamped_x
                fall_envelope_clamp_count += 1
            points.append(point)
        spline = curve_data.splines.new("POLY")
        if (
            center_bridge_diagnostic
            and any(
                abs(point.x - center.x) < 0.0055
                and point.z > maximum_z - 0.225
                for point in points[:scalp_point_count]
            )
        ):
            spline.material_index = 2
            center_roi_diagnostic_strand_count += 1
        spline.points.add(len(points) - 1)
        for index, point in enumerate(points):
            spline.points[index].co = (*point, 1.0)
        strand_count += 1

    # R13l's remaining defect was a narrow, coordinate-stable center seam and
    # rear wedge.  Fill only that exact path with a tiny set of longitudinal
    # actual strands.  This is deliberately not a broad overlap layer and is
    # not a cap/shell: thirteen individual fibers follow the real scalp BVH
    # from upper forehead over crown and down the rear occiput.
    center_bridge_offsets = [
        -0.0018 + index * (0.0036 / 12.0)
        for index in range(13)
    ]
    center_bridge_clearance = 0.00175
    for bridge_offset in center_bridge_offsets:
        bridge_points: list[Vector] = []
        bridge_valid = True
        # Upper-forehead to rear-crown arc.
        for sample in range(22):
            t = sample / 21.0
            planned = Vector(
                (
                    center.x + bridge_offset,
                    -0.103 + 0.142 * t,
                    maximum_z + 0.050,
                )
            )
            projected = project_to_head(planned)
            if projected is None:
                bridge_valid = False
                break
            surface, normal, _polygon_index, _distance = projected
            safe_point = safe_scalp_offset(
                surface,
                normal,
                center_bridge_clearance,
            )
            if safe_point is None:
                bridge_valid = False
                break
            point = safe_point[0]
            if bridge_points and (point - bridge_points[-1]).length < 0.0012:
                continue
            center_bridge_clearances.append(float(safe_point[4]))
            if float(safe_point[5]) <= 0.0:
                center_bridge_outward_failures += 1
                bridge_valid = False
                break
            bridge_points.append(point)
        # Rear crown down through the dark wedge area.
        if bridge_valid:
            for sample in range(1, 17):
                t = sample / 16.0
                planned = Vector(
                    (
                        center.x + bridge_offset,
                        head_high.y + 0.050,
                        (maximum_z - 0.018) * (1.0 - t)
                        + (maximum_z - 0.225) * t,
                    )
                )
                projected = project_to_head(planned)
                if projected is None:
                    bridge_valid = False
                    break
                surface, normal, _polygon_index, _distance = projected
                safe_point = safe_scalp_offset(
                    surface,
                    normal,
                    center_bridge_clearance,
                )
                if safe_point is None:
                    bridge_valid = False
                    break
                point = safe_point[0]
                if bridge_points and (point - bridge_points[-1]).length < 0.0012:
                    continue
                center_bridge_clearances.append(float(safe_point[4]))
                if float(safe_point[5]) <= 0.0:
                    center_bridge_outward_failures += 1
                    bridge_valid = False
                    break
                bridge_points.append(point)
        if not bridge_valid or len(bridge_points) < 8:
            continue
        bridge_end = bridge_points[-1]
        bridge_fall_end = bridge_end + Vector((0.0, 0.004, 0.0))
        bridge_fall_end.z = max(1.335, bridge_end.z - 0.105)
        for sample in range(1, 6):
            t = sample / 5.0
            point = bridge_end.lerp(bridge_fall_end, t)
            point, corrected = body_collision_correct(point)
            if corrected:
                body_collision_corrections += 1
            clamped_x, clamped_x_changed = soft_limit(
                point.x,
                head_low.x - fall_envelope_margin_x,
                head_high.x + fall_envelope_margin_x,
            )
            if clamped_x_changed:
                point.x = clamped_x
                fall_envelope_clamp_count += 1
            bridge_points.append(point)
        bridge_spline = curve_data.splines.new("POLY")
        if center_bridge_diagnostic:
            bridge_spline.material_index = 1
        bridge_spline.points.add(len(bridge_points) - 1)
        for index, point in enumerate(bridge_points):
            bridge_spline.points[index].co = (*point, 1.0)
        strand_count += 1
        center_bridge_strand_count += 1
    groom = bpy.data.objects.new(
        "Kira_R13G_Removable_Straight_Black_Strand_Groom",
        curve_data,
    )
    bpy.context.collection.objects.link(groom)
    groom["removable_review_hair"] = True
    groom["static_review_groom"] = True
    groom["runtime_hair_complete"] = False
    groom["private_review_only"] = True
    groom["scalp_cap_or_underlay"] = False
    groom["actual_strand_geometry"] = True
    optimized_native_curves = "optimized" in body.name.lower()
    curve_control_point_count = sum(
        len(spline.points) for spline in curve_data.splines
    )
    bpy.context.view_layer.objects.active = groom
    if optimized_native_curves:
        groom.name = "Kira_R13_Optimized_Native_Strand_Groom"
        groom["optimized_native_poly_curves"] = True
        groom["head_binding_deferred_until_integration"] = True
    else:
        bpy.ops.object.select_all(action="DESELECT")
        groom.select_set(True)
        bpy.ops.object.convert(target="MESH")
        groom = bpy.context.object
        groom.name = "Kira_R13G_Removable_Straight_Black_Strand_Groom"
        for polygon in groom.data.polygons:
            polygon.use_smooth = True
        _assign_rigid_bone(groom, armature, "head")
    low, high = _world_bounds([groom])
    return [groom], {
        "method": "dense_bevelled_curve_strands_converted_to_mesh",
        "static_review_style": "straight_black_combed_back_shoulder_lob",
        "runtime_hair_system_complete": False,
        "strand_count": strand_count,
        "root_distribution": "golden_angle_fibonacci_sampling_projected_to_actual_head_bvh",
        "fibonacci_candidate_count": fibonacci_candidate_count,
        "accepted_unique_root_count": len(used_root_cells),
        "duplicate_root_rejections": duplicate_root_rejections,
        "envelope_rejections": envelope_rejections,
        "projection_rejections": projection_rejections,
        "unsafe_offset_rejections": unsafe_offset_rejections,
        "root_clearance_m": root_clearance,
        "root_to_actual_scalp_clearance": distribution(root_clearances),
        "scalp_follow_to_actual_scalp_clearance": distribution(
            scalp_follow_clearances
        ),
        "outward_clearance_failures": outward_clearance_failures,
        "body_collision_corrections": body_collision_corrections,
        "body_collision_clearance_m": 0.004,
        "fall_envelope_clamp_count": fall_envelope_clamp_count,
        "fall_envelope_margin_x_m": fall_envelope_margin_x,
        "fall_envelope_front_margin_y_m": fall_envelope_front_margin_y,
        "fall_envelope_rear_margin_y_m": fall_envelope_rear_margin_y,
        "fall_envelope_y_limit_applied": False,
        "fall_envelope_soft_limit_m": fall_envelope_soft_limit,
        "front_neck_route_count": front_neck_route_count,
        "front_neck_center_clearance_half_width_m": 0.041,
        "front_neck_route_start_below_crown_m": 0.110,
        "front_neck_route_full_below_crown_m": 0.165,
        "center_bridge_strand_count": center_bridge_strand_count,
        "center_bridge_clearance_m": center_bridge_clearance,
        "center_bridge_to_actual_scalp_clearance": distribution(
            center_bridge_clearances
        ),
        "center_bridge_outward_failures": center_bridge_outward_failures,
        "center_bridge_is_actual_strands_not_cap_or_shell": True,
        "center_bridge_diagnostic_color_enabled": center_bridge_diagnostic,
        "center_roi_diagnostic_strand_count": (
            center_roi_diagnostic_strand_count
        ),
        "actual_head_bvh_face_count": len(head_faces),
        "scalp_follow_surface": "actual_body_head_mesh_bvh",
        "analytic_ellipsoid_used_as_final_surface": False,
        "bevel_radius_m": curve_data.bevel_depth,
        "scalp_cap_or_underlay_object_count": 0,
        "opaque_shell_object_count": 0,
        "actual_strand_geometry": True,
        "optimized_native_poly_curves": optimized_native_curves,
        "curve_spline_count": len(curve_data.splines),
        "curve_control_point_count": curve_control_point_count,
        "mesh_conversion_performed": not optimized_native_curves,
        "head_binding_deferred_until_integration": optimized_native_curves,
        "removable": True,
        "runtime_hair_complete": False,
        "head_bounds_low": [round(float(value), 6) for value in head_low],
        "head_bounds_high": [round(float(value), 6) for value in head_high],
        "scalp_ellipsoid_center": [
            round(float(value), 6) for value in center
        ],
        "scalp_ellipsoid_radii": [
            round(float(value), 6) for value in radii
        ],
        "sampling_envelope_radii": [
            round(float(value), 6) for value in sampling_radii
        ],
        "groom_bounds_low": [round(float(value), 6) for value in low],
        "groom_bounds_high": [round(float(value), 6) for value in high],
    }


def _darken_hair_materials(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        for material in obj.data.materials:
            if material is None:
                continue
            material.diffuse_color = (0.006, 0.004, 0.008, 1.0)
            if not material.use_nodes:
                material.use_nodes = True
            principled = material.node_tree.nodes.get("Principled BSDF")
            if principled is None:
                continue
            base_input = principled.inputs.get("Base Color")
            if base_input is not None:
                for link in list(base_input.links):
                    material.node_tree.links.remove(link)
                base_input.default_value = (0.006, 0.004, 0.008, 1.0)
            principled.inputs["Roughness"].default_value = 0.38


def _add_hair(
    body: bpy.types.Object,
    armature: bpy.types.Object,
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(HAIR_PATH))
    imported = [
        obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"
    ]
    if not imported:
        raise RuntimeError("hair asset import produced no mesh")
    source_low, source_high = _world_bounds(imported)
    source_size = source_high - source_low
    body_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    maximum_z = max(point.z for point in body_points)
    head_points = [point for point in body_points if point.z >= maximum_z - 0.255]
    head_low = Vector(
        tuple(min(point[axis] for point in head_points) for axis in range(3))
    )
    head_high = Vector(
        tuple(max(point[axis] for point in head_points) for axis in range(3))
    )
    desired_width = (head_high.x - head_low.x) * 1.28
    factor = desired_width / max(source_size.x, 1e-6)
    for obj in imported:
        obj.scale *= factor
    bpy.context.view_layer.update()
    scaled_low, scaled_high = _world_bounds(imported)
    scaled_center = (scaled_low + scaled_high) * 0.5
    head_center = (head_low + head_high) * 0.5
    desired_center = Vector(
        (
            head_center.x,
            head_center.y + 0.012,
            maximum_z + 0.008 - (scaled_high.z - scaled_low.z) * 0.5,
        )
    )
    offset = desired_center - scaled_center
    for obj in imported:
        obj.location += offset
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        obj.name = f"Kira_Removable_Straight_Black_Hair_{obj.name}"
        obj["removable_review_hair"] = True
        obj["runtime_hair_complete"] = False
        obj["private_review_only"] = True
        _assign_rigid_bone(obj, armature, "head")
    _darken_hair_materials(imported)
    final_low, final_high = _world_bounds(imported)
    return imported, {
        "path": str(HAIR_PATH),
        "sha256": _sha256(HAIR_PATH),
        "method": "licensed_local_hair_component_uniformly_fitted_to_makehuman_head",
        "removable": True,
        "runtime_hair_complete": False,
        "object_count": len(imported),
        "bounds_low": [round(float(value), 6) for value in final_low],
        "bounds_high": [round(float(value), 6) for value in final_high],
    }


def _add_uv_sphere(
    name: str,
    location: Vector,
    scale: tuple[float, float, float],
    material: bpy.types.Material,
    *,
    segments: int = 24,
    ring_count: int = 12,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=ring_count,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def _add_eyes(
    armature: bpy.types.Object,
    rig_data: dict[str, object],
    joints: dict[str, Vector],
    height: float,
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    sclera_material = _simple_material(
        "Kira_Sclera",
        (0.82, 0.82, 0.78, 1.0),
        roughness=0.22,
    )
    iris_material = _simple_material(
        "Kira_Brown_Iris",
        (0.20, 0.075, 0.022, 1.0),
        roughness=0.34,
    )
    pupil_material = _simple_material(
        "Kira_Pupil",
        (0.003, 0.002, 0.002, 1.0),
        roughness=0.18,
    )
    radius = height * 0.0103
    objects: list[bpy.types.Object] = []
    centers: dict[str, list[float]] = {}
    for side in ("L", "R"):
        center = joints[f"eye.{side}____head"]
        centers[side] = [round(float(value), 6) for value in center]
        sclera = _add_uv_sphere(
            f"Kira_Eye_Sclera_{side}",
            center,
            (radius, radius, radius),
            sclera_material,
        )
        iris_center = center + Vector((0.0, -radius * 0.94, 0.0))
        iris = _add_uv_sphere(
            f"Kira_Eye_Brown_Iris_{side}",
            iris_center,
            (radius * 0.47, radius * 0.09, radius * 0.47),
            iris_material,
        )
        pupil = _add_uv_sphere(
            f"Kira_Eye_Pupil_{side}",
            center + Vector((0.0, -radius * 1.00, 0.0)),
            (radius * 0.19, radius * 0.055, radius * 0.19),
            pupil_material,
            segments=20,
            ring_count=10,
        )
        for obj in (sclera, iris, pupil):
            obj["eye_component"] = True
            obj["private_review_only"] = True
            _assign_rigid_bone(obj, armature, f"eye.{side}")
            objects.append(obj)
    return objects, {
        "color": "natural brown",
        "procedural_component_count": len(objects),
        "centers": centers,
        "hard_black_eye_bands_created": False,
    }


def _add_nails(
    armature: bpy.types.Object,
    height: float,
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    nail_material = _simple_material(
        "Kira_Natural_Nails",
        (0.76, 0.52, 0.47, 1.0),
        roughness=0.38,
    )
    objects: list[bpy.types.Object] = []
    records = []
    for side in ("L", "R"):
        for digit in range(1, 6):
            bone_name = f"finger{digit}-3.{side}"
            bone = armature.data.bones[bone_name]
            direction = (bone.tail_local - bone.head_local).normalized()
            center = bone.tail_local - direction * (height * 0.0031)
            center += Vector((0.0, -height * 0.00075, 0.0))
            nail = _add_uv_sphere(
                f"Kira_Fingernail_{digit}_{side}",
                center,
                (
                    height * (0.0027 if digit == 1 else 0.00235),
                    height * 0.00055,
                    height * (0.0036 if digit == 1 else 0.0031),
                ),
                nail_material,
                segments=16,
                ring_count=8,
            )
            nail.rotation_mode = "QUATERNION"
            nail.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(direction)
            bpy.context.view_layer.objects.active = nail
            nail.select_set(True)
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            nail["nail_component"] = True
            nail["penetration_design"] = "slight_surface_overlap_no_floating_free_edge"
            _assign_rigid_bone(nail, armature, bone_name)
            objects.append(nail)
            records.append({"object": nail.name, "bone": bone_name})
        for digit in range(1, 6):
            bone_name = f"toe{digit}-{'2' if digit == 1 else '3'}.{side}"
            bone = armature.data.bones[bone_name]
            direction = (bone.tail_local - bone.head_local).normalized()
            center = bone.tail_local - direction * (height * 0.0025)
            center += Vector((0.0, -height * 0.0007, height * 0.0012))
            nail = _add_uv_sphere(
                f"Kira_Toenail_{digit}_{side}",
                center,
                (
                    height * (0.0034 if digit == 1 else 0.0020),
                    height * (0.0037 if digit == 1 else 0.0025),
                    height * 0.0006,
                ),
                nail_material,
                segments=16,
                ring_count=8,
            )
            nail["nail_component"] = True
            nail["penetration_design"] = "slight_surface_overlap_no_floating_free_edge"
            _assign_rigid_bone(nail, armature, bone_name)
            objects.append(nail)
            records.append({"object": nail.name, "bone": bone_name})
    return objects, {
        "component_count": len(objects),
        "fingernail_count": 10,
        "toenail_count": 10,
        "records": records,
    }


def _reset_pose(armature: bpy.types.Object) -> None:
    for bone in armature.pose.bones:
        # Preserve the channel that an action actually keys.  The knee
        # engineering actions use quaternion channels; forcing those bones
        # back to Euler mode before GLTF export makes the exporter sample the
        # unkeyed Euler values and silently drops the solved knee motion.
        rotation_mode = bone.rotation_mode
        bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
        bone.rotation_mode = rotation_mode
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def _pose_chain_coordinates(
    armature: bpy.types.Object,
    side: str,
) -> dict[str, Vector]:
    """Return exact evaluated armature-space landmarks for one leg.

    The anatomical knee is the upperleg02 tail/lowerleg01 head.  The ankle is
    the lowerleg02 tail/foot head.  Coordinates are transformed to world space
    before scoring, so posterior always means +Y and never camera space.
    """

    upper = armature.pose.bones[f"upperleg02.{side}"]
    lower = armature.pose.bones[f"lowerleg01.{side}"]
    ankle_bone = armature.pose.bones[f"lowerleg02.{side}"]
    return {
        "upper_head": armature.matrix_world @ upper.head,
        "knee_upper_tail": armature.matrix_world @ upper.tail,
        "knee_lower_head": armature.matrix_world @ lower.head,
        "ankle": armature.matrix_world @ ankle_bone.tail,
    }


def _flexion_degrees(points: dict[str, Vector]) -> float:
    upper = points["knee_upper_tail"] - points["upper_head"]
    lower = points["ankle"] - points["knee_lower_head"]
    if upper.length <= 1e-8 or lower.length <= 1e-8:
        return 0.0
    cosine = max(-1.0, min(1.0, upper.normalized().dot(lower.normalized())))
    return math.degrees(math.acos(cosine))


def _solve_knee_axis(
    armature: bpy.types.Object,
    side: str,
) -> dict[str, object]:
    """Search each local cardinal axis/sign and score actual ankle motion."""

    lower_name = f"lowerleg01.{side}"
    _reset_pose(armature)
    rest = _pose_chain_coordinates(armature, side)
    candidates: list[dict[str, object]] = []
    axes = {
        "LOCAL_X": Vector((1.0, 0.0, 0.0)),
        "LOCAL_Y": Vector((0.0, 1.0, 0.0)),
        "LOCAL_Z": Vector((0.0, 0.0, 1.0)),
    }
    for axis_name, axis in axes.items():
        for sign in (-1, 1):
            for angle_degrees in range(20, 156, 5):
                _reset_pose(armature)
                lower = armature.pose.bones[lower_name]
                lower.rotation_mode = "QUATERNION"
                lower.rotation_quaternion = Quaternion(
                    axis,
                    math.radians(float(sign * angle_degrees)),
                )
                bpy.context.view_layer.update()
                posed = _pose_chain_coordinates(armature, side)
                displacement = posed["ankle"] - rest["ankle"]
                posterior = float(displacement.y)
                lateral = abs(float(displacement.x))
                flexion = _flexion_degrees(posed)
                vertical = float(displacement.z)
                valid = (
                    posterior > 0.015
                    and lateral <= max(0.018, posterior * 0.55)
                    and 20.0 <= flexion <= 155.0
                )
                # Positive posterior +Y is the main objective.  Lateral motion
                # is strongly penalized; vertical rise is expected in flexion.
                score = posterior - lateral * 2.75
                candidates.append(
                    {
                        "axis": axis_name,
                        "axis_vector": [float(value) for value in axis],
                        "sign": sign,
                        "signed_angle_degrees": sign * angle_degrees,
                        "angle_degrees": angle_degrees,
                        "posterior_displacement_m": posterior,
                        "lateral_displacement_m": lateral,
                        "vertical_displacement_m": vertical,
                        "flexion_degrees": flexion,
                        "valid": valid,
                        "score": score,
                        "posed": posed,
                    }
                )
    valid_candidates = [candidate for candidate in candidates if candidate["valid"]]
    if not valid_candidates:
        ranked = sorted(candidates, key=lambda item: float(item["score"]), reverse=True)
        compact = [
            {
                key: value
                for key, value in candidate.items()
                if key != "posed"
            }
            for candidate in ranked[:10]
        ]
        raise RuntimeError(
            f"no posterior knee solution for {side}; top candidates={compact}"
        )
    selected = max(valid_candidates, key=lambda item: float(item["score"]))
    _reset_pose(armature)
    lower = armature.pose.bones[lower_name]
    lower.rotation_mode = "QUATERNION"
    lower.rotation_quaternion = Quaternion(
        Vector(tuple(selected["axis_vector"])),
        math.radians(float(selected["signed_angle_degrees"])),
    )
    bpy.context.view_layer.update()
    verified = _pose_chain_coordinates(armature, side)
    verified_displacement = verified["ankle"] - rest["ankle"]
    result = {
        "side": "left" if side == "L" else "right",
        "upper_bone": f"upperleg02.{side}",
        "lower_bone": lower_name,
        "ankle_bone": f"lowerleg02.{side}",
        "anatomical_forward_axis": "-Y",
        "posterior_world_axis": "+Y",
        "selected_local_axis": selected["axis"],
        "selected_axis_vector": selected["axis_vector"],
        "selected_sign": selected["sign"],
        "selected_signed_angle_degrees": selected["signed_angle_degrees"],
        "flexion_degrees": _flexion_degrees(verified),
        "rest": {
            name: [round(float(value), 9) for value in point]
            for name, point in rest.items()
        },
        "posed": {
            name: [round(float(value), 9) for value in point]
            for name, point in verified.items()
        },
        "ankle_displacement_m": [
            round(float(value), 9) for value in verified_displacement
        ],
        "posterior_displacement_m": round(float(verified_displacement.y), 9),
        "lateral_displacement_m": round(abs(float(verified_displacement.x)), 9),
        "vertical_displacement_m": round(float(verified_displacement.z), 9),
        "search_candidate_count": len(candidates),
        "valid_candidate_count": len(valid_candidates),
        "objective_gate": {
            "positive_posterior_y": bool(verified_displacement.y > 0.015),
            "low_lateral": bool(
                abs(verified_displacement.x)
                <= max(0.018, verified_displacement.y * 0.55)
            ),
            "flexion_in_range_20_to_155": bool(
                20.0 <= _flexion_degrees(verified) <= 155.0
            ),
        },
    }
    result["objective_pass"] = all(result["objective_gate"].values())
    _reset_pose(armature)
    return result


def _apply_knee_solution(
    armature: bpy.types.Object,
    solution: dict[str, object],
) -> None:
    _reset_pose(armature)
    lower = armature.pose.bones[str(solution["lower_bone"])]
    lower.rotation_mode = "QUATERNION"
    lower.rotation_quaternion = Quaternion(
        Vector(tuple(solution["selected_axis_vector"])),
        math.radians(float(solution["selected_signed_angle_degrees"])),
    )
    bpy.context.view_layer.update()


def _create_knee_engineering_actions(
    armature: bpy.types.Object,
    solutions: dict[str, dict[str, object]],
) -> list[str]:
    armature.animation_data_create()
    names = []
    for side in ("left", "right"):
        solution = solutions[side]
        action_name = f"kira_private_knee_flex_{side}_axis_solved"
        action = bpy.data.actions.new(action_name)
        action.use_fake_user = True
        armature.animation_data.action = action
        _reset_pose(armature)
        lower = armature.pose.bones[str(solution["lower_bone"])]
        lower.rotation_mode = "QUATERNION"
        lower.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        lower.keyframe_insert("rotation_quaternion", frame=1, group=lower.name)
        lower.rotation_quaternion = Quaternion(
            Vector(tuple(solution["selected_axis_vector"])),
            math.radians(float(solution["selected_signed_angle_degrees"])),
        )
        lower.keyframe_insert("rotation_quaternion", frame=30, group=lower.name)
        names.append(action_name)
    armature.animation_data.action = None
    _reset_pose(armature)
    return names


POSES = {
    "standing": {},
    "left_knee_flex": {
        "upperleg01.L": (math.radians(-18.0), 0.0, 0.0),
        "lowerleg01.L": (math.radians(68.0), 0.0, 0.0),
    },
    "right_knee_flex": {
        "upperleg01.R": (math.radians(-18.0), 0.0, 0.0),
        "lowerleg01.R": (math.radians(68.0), 0.0, 0.0),
    },
    "seated": {
        "upperleg01.L": (math.radians(-78.0), 0.0, 0.0),
        "upperleg01.R": (math.radians(-78.0), 0.0, 0.0),
        "lowerleg01.L": (math.radians(76.0), 0.0, 0.0),
        "lowerleg01.R": (math.radians(76.0), 0.0, 0.0),
        "spine05": (math.radians(4.0), 0.0, 0.0),
    },
}


def _apply_pose(
    armature: bpy.types.Object,
    name: str,
    *,
    root_location: tuple[float, float, float] | None = None,
) -> None:
    _reset_pose(armature)
    for bone_name, rotation in POSES[name].items():
        bone = armature.pose.bones.get(bone_name)
        if bone is None:
            raise RuntimeError(f"pose bone missing: {bone_name}")
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = rotation
    if root_location is not None:
        armature.pose.bones["root"].location = root_location
    bpy.context.view_layer.update()


def _create_actions(armature: bpy.types.Object, height: float) -> list[str]:
    specs = {
        "kira_private_idle": [
            (1, "standing", (0.0, 0.0, 0.0)),
            (60, "standing", (0.0, 0.0, 0.0)),
        ],
        "kira_private_knee_flex_left": [
            (1, "standing", (0.0, 0.0, 0.0)),
            (30, "left_knee_flex", (0.0, 0.0, 0.0)),
        ],
        "kira_private_knee_flex_right": [
            (1, "standing", (0.0, 0.0, 0.0)),
            (30, "right_knee_flex", (0.0, 0.0, 0.0)),
        ],
        "kira_private_sit": [
            (1, "standing", (0.0, 0.0, 0.0)),
            (40, "seated", (0.0, 0.0, -height * 0.19)),
        ],
    }
    armature.animation_data_create()
    created = []
    for action_name, frames in specs.items():
        action = bpy.data.actions.new(action_name)
        action.use_fake_user = True
        armature.animation_data.action = action
        for frame, pose_name, root_location in frames:
            _apply_pose(armature, pose_name, root_location=root_location)
            for bone in armature.pose.bones:
                bone.keyframe_insert("rotation_euler", frame=frame, group=bone.name)
                bone.keyframe_insert("location", frame=frame, group=bone.name)
        created.append(action_name)
    armature.animation_data.action = None
    _reset_pose(armature)
    return created


def _look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def _camera() -> bpy.types.Object:
    data = bpy.data.cameras.new("Kira_Private_Review_Camera")
    data.type = "ORTHO"
    camera = bpy.data.objects.new("Kira_Private_Review_Camera", data)
    bpy.context.collection.objects.link(camera)
    return camera


def _render(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output: Path,
    *,
    location: Vector,
    target: Vector,
    scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = scale
    _look_at(camera, target)
    scene.camera = camera
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def _add_seat(height: float) -> bpy.types.Object:
    material = _simple_material(
        "Kira_Seat_Contact_Diagnostic",
        (0.09, 0.13, 0.17, 1.0),
        roughness=0.55,
    )
    bpy.ops.mesh.primitive_cube_add(
        location=(0.0, 0.075, height * 0.269),
        scale=(height * 0.255, height * 0.19, height * 0.018),
    )
    seat = bpy.context.object
    seat.name = "Kira_Seat_Contact_Diagnostic"
    seat.data.materials.append(material)
    seat.hide_render = True
    return seat


def _render_evidence(
    output_dir: Path,
    body: bpy.types.Object,
    armature: bpy.types.Object,
    hair: list[bpy.types.Object],
    scene: bpy.types.Scene,
) -> dict[str, str]:
    body_low, body_high = _world_bounds([body])
    height = body_high.z - body_low.z
    center = (body_low + body_high) * 0.5
    distance = height * 1.9
    camera = _camera()
    seat = _add_seat(height)
    renders: dict[str, str] = {}

    def shot(
        filename: str,
        pose_name: str,
        location: Vector,
        target: Vector,
        scale: float,
        *,
        seated: bool = False,
    ) -> None:
        _apply_pose(
            armature,
            pose_name,
            root_location=(0.0, 0.0, -height * 0.19) if seated else None,
        )
        seat.hide_render = not seated
        path = output_dir / filename
        _render(
            scene,
            camera,
            path,
            location=location,
            target=target,
            scale=scale,
        )
        renders[filename] = str(path)

    full_scale = height * 1.08
    shot(
        "standing_front.png",
        "standing",
        Vector((center.x, body_low.y - distance, center.z)),
        center,
        full_scale,
    )
    shot(
        "standing_rear.png",
        "standing",
        Vector((center.x, body_high.y + distance, center.z)),
        center,
        full_scale,
    )
    shot(
        "standing_left_profile.png",
        "standing",
        Vector((body_low.x - distance, center.y, center.z)),
        center,
        full_scale,
    )
    shot(
        "standing_right_profile.png",
        "standing",
        Vector((body_high.x + distance, center.y, center.z)),
        center,
        full_scale,
    )
    shot(
        "standing_left_three_quarter.png",
        "standing",
        Vector((center.x - distance * 0.70, body_low.y - distance * 0.70, center.z)),
        center,
        full_scale,
    )
    shot(
        "standing_right_three_quarter.png",
        "standing",
        Vector((center.x + distance * 0.70, body_low.y - distance * 0.70, center.z)),
        center,
        full_scale,
    )
    face_target = Vector((center.x, center.y, body_high.z - height * 0.085))
    shot(
        "face_neutral_close.png",
        "standing",
        Vector((center.x, body_low.y - distance, face_target.z)),
        face_target,
        height * 0.30,
    )
    shot(
        "hair_rear_hairline.png",
        "standing",
        Vector((center.x, body_high.y + distance, face_target.z)),
        face_target,
        height * 0.34,
    )
    shot(
        "hair_crown_top.png",
        "standing",
        Vector((center.x, center.y, body_high.z + distance)),
        Vector((center.x, center.y, body_high.z - height * 0.10)),
        height * 0.34,
    )
    knee_target = Vector((center.x, center.y, body_low.z + height * 0.28))
    shot(
        "left_knee_posterior_flex.png",
        "left_knee_flex",
        Vector((body_low.x - distance, center.y, knee_target.z)),
        knee_target,
        height * 0.72,
    )
    shot(
        "right_knee_posterior_flex.png",
        "right_knee_flex",
        Vector((body_high.x + distance, center.y, knee_target.z)),
        knee_target,
        height * 0.72,
    )
    shot(
        "seated_contact_left_profile.png",
        "seated",
        Vector((body_low.x - distance, center.y, body_low.z + height * 0.47)),
        Vector((center.x, center.y, body_low.z + height * 0.47)),
        height * 0.92,
        seated=True,
    )
    adult_target = Vector((center.x, body_low.y, body_low.z + height * 0.47))
    shot(
        "adult_surface_front.png",
        "standing",
        Vector((center.x, body_low.y - distance, adult_target.z)),
        adult_target,
        height * 0.38,
    )
    shot(
        "adult_surface_three_quarter.png",
        "standing",
        Vector((center.x - distance * 0.70, body_low.y - distance * 0.70, adult_target.z)),
        adult_target,
        height * 0.38,
    )
    _reset_pose(armature)
    seat.hide_render = True
    return renders


def _setup_scene() -> bpy.types.Scene:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.085, 0.095, 0.115)
    for name, energy, location, size in (
        ("Kira_Key", 950.0, (3.6, -4.6, 4.8), 4.0),
        ("Kira_Fill", 850.0, (-4.2, -2.5, 3.8), 5.0),
        ("Kira_RearFill", 700.0, (2.2, 4.4, 4.5), 4.0),
        ("Kira_TopFill", 500.0, (0.0, 0.0, 6.0), 3.5),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        light.location = location
        bpy.context.collection.objects.link(light)
        light.rotation_euler = (
            Vector((0.0, 0.0, 0.85)) - light.location
        ).to_track_quat("-Z", "Y").to_euler()
    return scene


def _render_knee_engineering_previews(
    output_dir: Path,
    body: bpy.types.Object,
    armature: bpy.types.Object,
    scene: bpy.types.Scene,
    solutions: dict[str, dict[str, object]],
) -> dict[str, str]:
    """Render only the isolated L/R side views used by the knee gate."""

    body_low, body_high = _world_bounds([body])
    height = body_high.z - body_low.z
    center = (body_low + body_high) * 0.5
    knee_z = (
        float(solutions["left"]["rest"]["knee_upper_tail"][2])
        + float(solutions["right"]["rest"]["knee_upper_tail"][2])
    ) * 0.5
    target = Vector((center.x, center.y, knee_z))
    camera = _camera()
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    distance = height * 1.8
    scale = height * 0.70
    renders: dict[str, str] = {}
    for side, camera_x, filename in (
        ("left", body_low.x - distance, "left_knee_axis_solved_side.png"),
        ("right", body_high.x + distance, "right_knee_axis_solved_side.png"),
    ):
        _apply_knee_solution(armature, solutions[side])
        path = output_dir / filename
        _render(
            scene,
            camera,
            path,
            location=Vector((camera_x, center.y, knee_z)),
            target=target,
            scale=scale,
        )
        renders[side] = str(path)
    _reset_pose(armature)
    return renders


def _render_face_hair_engineering_previews(
    output_dir: Path,
    body: bpy.types.Object,
    armature: bpy.types.Object,
    scene: bpy.types.Scene,
) -> dict[str, str]:
    """Render only the four views required by the R13 face/hair gate."""

    _reset_pose(armature)
    body_low, body_high = _world_bounds([body])
    height = body_high.z - body_low.z
    center = (body_low + body_high) * 0.5
    face_target = Vector((center.x, center.y, body_high.z - height * 0.105))
    distance = height * 1.35
    camera = _camera()
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    renders: dict[str, str] = {}
    shots = (
        (
            "face_front.png",
            Vector((center.x, body_low.y - distance, face_target.z)),
            face_target,
            height * 0.31,
        ),
        (
            "face_left_three_quarter.png",
            Vector(
                (
                    center.x - distance * 0.56,
                    body_low.y - distance * 0.83,
                    face_target.z + height * 0.012,
                )
            ),
            face_target,
            height * 0.33,
        ),
        (
            "hair_crown.png",
            Vector((center.x, center.y, body_high.z + distance)),
            Vector((center.x, center.y, body_high.z - height * 0.075)),
            height * 0.32,
        ),
        (
            "hair_rear_hairline.png",
            Vector((center.x, body_high.y + distance, face_target.z)),
            face_target,
            height * 0.38,
        ),
    )
    for filename, location, target, scale in shots:
        path = output_dir / filename
        _render(
            scene,
            camera,
            path,
            location=location,
            target=target,
            scale=scale,
        )
        renders[filename] = str(path)
    return renders


def _render_groom_crown_rear_previews(
    output_dir: Path,
    body: bpy.types.Object,
    armature: bpy.types.Object,
    scene: bpy.types.Scene,
) -> dict[str, str]:
    """Render only crown/rear for the procedural strand-groom gate."""

    _reset_pose(armature)
    body_low, body_high = _world_bounds([body])
    height = body_high.z - body_low.z
    center = (body_low + body_high) * 0.5
    head_target = Vector((center.x, center.y, body_high.z - height * 0.095))
    distance = height * 1.35
    camera = _camera()
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    renders: dict[str, str] = {}
    for filename, location, target, scale in (
        (
            "groom_crown_first_gate.png",
            Vector((center.x, center.y, body_high.z + distance)),
            Vector((center.x, center.y, body_high.z - height * 0.080)),
            height * 0.33,
        ),
        (
            "groom_rear_first_gate.png",
            Vector((center.x, body_high.y + distance, head_target.z)),
            head_target,
            height * 0.39,
        ),
    ):
        path = output_dir / filename
        _render(
            scene,
            camera,
            path,
            location=location,
            target=target,
            scale=scale,
        )
        renders[filename] = str(path)
    return renders


def _export_glb(
    path: Path,
    objects: list[bpy.types.Object],
) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_def_bones=True,
        export_yup=True,
        export_morph=False,
        export_extras=True,
    )


def main() -> None:
    args = _arguments()
    engineering_modes = (
        args.knee_engineering_only,
        args.face_hair_engineering_only,
        args.hair_groom_crown_rear_only,
    )
    if sum(bool(value) for value in engineering_modes) > 1:
        raise RuntimeError("engineering-only modes are mutually exclusive")
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_id = args.candidate_id
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    vertices, faces, old_to_new, applied, source = _body_source()
    body = _build_body(vertices, faces, candidate_id)
    topology = _topology(body)
    if (
        topology["surface_components"] != 1
        or topology["boundary_edges"] != 0
        or topology["nonmanifold_edges"] != 0
    ):
        raise RuntimeError(f"female primary surface failed topology gate: {topology}")
    armature, rig_report = _build_armature(
        body,
        old_to_new,
        source["all_deformed_source_vertices"],
        source_low_z=source["source_low_z"],
        scale=source["scale"],
        candidate_id=candidate_id,
    )
    if args.hair_groom_crown_rear_only:
        hair, hair_report = _add_procedural_straight_black_groom(body, armature)
        optimized_review = bool(hair_report["optimized_native_poly_curves"])
        eye_report = None
        if optimized_review:
            _eyes, eye_report = _add_r13_helper_eyes(body, armature, source)
        scene = _setup_scene()
        if optimized_review:
            renders = _render_face_hair_engineering_previews(
                output_dir,
                body,
                armature,
                scene,
            )
            blend_path = (
                output_dir
                / "KIRA_TFB_R13_OPTIMIZED_NATIVE_GROOM_FACE_GATE.blend"
            )
        else:
            renders = _render_groom_crown_rear_previews(
                output_dir,
                body,
                armature,
                scene,
            )
            blend_path = (
                output_dir
                / "KIRA_TFB_R13G_STRAND_GROOM_CROWN_REAR_ONLY.blend"
            )
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        render_bindings = {}
        for label, raw_path in renders.items():
            path = Path(raw_path)
            render_bindings[label] = {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        evidence = {
            "schema_version": 1,
            "run_id": candidate_id,
            "candidate_id": candidate_id,
            "status": "REJECTED_ENGINEERING_EVIDENCE",
            "scope": (
                "optimized_native_strand_groom_crown_rear_face_gate"
                if optimized_review
                else "procedural_strand_groom_crown_rear_first_gate_only"
            ),
            "not_a_full_candidate": True,
            "owner_approved": False,
            "runtime_assignment_allowed": False,
            "runtime_activation_allowed": False,
            "roster_registration_allowed": False,
            "runtime_files_read_or_written_by_worker": False,
            "privacy": {
                "robert_private_photos_used": False,
                "robert_measurements_used": False,
                "robert_morphs_or_surface_used": False,
                "identifiable_person_likeness_used": False,
                "private_local_review_only": True,
            },
            "knee_solution_modified": False,
            "protected_surface_modified_for_groom": False,
            "hair": hair_report,
            "eyes": eye_report,
            "excluded_visual_defects": {
                "opaque_eyelash_card_count": 0,
                "black_eye_band_object_count": 0,
                "scalp_cap_or_underlay_object_count": 0,
                "opaque_hair_shell_object_count": 0,
            },
            "visual_gate": {
                "crown_has_no_large_exposed_region": False,
                "rear_has_no_large_exposed_region": False,
                "no_face_or_neck_intersection_reviewed": False,
                "passed": False,
                "note": (
                    (
                        "Optimized crown/rear/front/three-quarter views were "
                        "rendered; pixel inspection is required before any "
                        "integration or export."
                    )
                    if optimized_review
                    else (
                        "Only crown/rear were rendered. Pixel inspection is "
                        "required before any front/three-quarter view or export."
                    )
                ),
            },
            "review_renders": render_bindings,
            "topology": topology,
            "rig": rig_report,
            "candidate_export": {
                "created": False,
                "reason": (
                    "Root required crown/rear source-on-head approval before "
                    "any full engineering GLB or candidate export."
                ),
            },
            "review_blend": {
                "path": str(blend_path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": blend_path.stat().st_size,
                "sha256": _sha256(blend_path),
            },
            "truth_note": (
                "This is a private inactive crown/rear strand-groom "
                "engineering gate. Runtime dynamics remain unimplemented, "
                "and this is not a body candidate."
            ),
        }
        evidence_path = output_dir / "BUILD_EVIDENCE.json"
        evidence_path.write_text(
            json.dumps(evidence, indent=2) + "\n",
            encoding="utf-8",
        )
        return
    if args.face_hair_engineering_only:
        eyes, eye_report = _add_r13_helper_eyes(body, armature, source)
        hair, hair_report = _add_r13_hair(body, armature)
        scene = _setup_scene()
        renders = _render_face_hair_engineering_previews(
            output_dir,
            body,
            armature,
            scene,
        )
        glb_path = output_dir / "KIRA_TFB_R13_FACE_HAIR_ENGINEERING.glb"
        _export_glb(glb_path, [body, armature, *eyes, *hair])
        blend_path = output_dir / "KIRA_TFB_R13_FACE_HAIR_ENGINEERING.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        render_bindings = {}
        for label, raw_path in renders.items():
            path = Path(raw_path)
            render_bindings[label] = {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        evidence = {
            "schema_version": 1,
            "run_id": candidate_id,
            "candidate_id": candidate_id,
            "status": "REJECTED_ENGINEERING_EVIDENCE",
            "scope": "face_eye_hair_visual_fit_only",
            "not_a_full_candidate": True,
            "owner_approved": False,
            "runtime_assignment_allowed": False,
            "runtime_activation_allowed": False,
            "roster_registration_allowed": False,
            "runtime_files_read_or_written_by_worker": False,
            "privacy": {
                "robert_private_photos_used": False,
                "robert_measurements_used": False,
                "robert_morphs_or_surface_used": False,
                "identifiable_person_likeness_used": False,
                "private_local_review_only": True,
            },
            "owner_visual_direction": (
                "Preserve the natural feminine R4 face/long-black-hair "
                "direction only; no R4 geometry, eye bands, scalp underlay, "
                "or defective topology copied."
            ),
            "body_class": "adult_female",
            "adult_surface_matches_requested_body_class": False,
            "requested_body_class_visually_reviewed": False,
            "adult_surface_note": (
                "This engineering run tests only face, eyes, and removable "
                "hair. The protected adult surface and all motion gates are "
                "unchanged and explicitly out of scope."
            ),
            "knee_solution_modified": False,
            "protected_surface_modified_for_r13": False,
            "eyes": eye_report,
            "hair": hair_report,
            "excluded_visual_defects": {
                "opaque_eyelash_card_count": 0,
                "black_eye_band_object_count": 0,
                "scalp_cap_or_underlay_object_count": 0,
                "non_hair_black_scalp_object_count": 0,
            },
            "self_rejection_required_if_visible_defect": True,
            "visual_gate": {
                "natural_brown_irises": False,
                "credible_upper_lower_lid_occlusion": False,
                "no_black_eye_bands": False,
                "no_exposed_crown": False,
                "no_non_hair_black_scalp_patch": False,
                "no_detached_hair_aabb": False,
                "front_three_quarter_crown_rear_review_complete": False,
                "passed": False,
                "note": (
                    "The authoring worker must inspect all four original "
                    "renders before any visual gate can be marked true."
                ),
            },
            "review_renders": render_bindings,
            "topology": topology,
            "rig": rig_report,
            "candidate": {
                "path": str(glb_path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": glb_path.stat().st_size,
                "sha256": _sha256(glb_path),
                "owner_approved": False,
                "runtime_assignment_allowed": False,
                "runtime_activation_allowed": False,
                "public_export_allowed": False,
            },
            "review_blend": {
                "path": str(blend_path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": blend_path.stat().st_size,
                "sha256": _sha256(blend_path),
            },
            "truth_note": (
                "This is intentionally rejected engineering evidence for "
                "face/eye/hair fit only. It cannot be selected, attached, "
                "rostered, activated, or approved."
            ),
        }
        evidence_path = output_dir / "BUILD_EVIDENCE.json"
        evidence_path.write_text(
            json.dumps(evidence, indent=2) + "\n",
            encoding="utf-8",
        )
        return
    if args.knee_engineering_only:
        solutions = {
            "left": _solve_knee_axis(armature, "L"),
            "right": _solve_knee_axis(armature, "R"),
        }
        if not all(solution["objective_pass"] for solution in solutions.values()):
            raise RuntimeError(f"axis-solved knee objective failed: {solutions}")
        actions = _create_knee_engineering_actions(armature, solutions)
        scene = _setup_scene()
        renders = _render_knee_engineering_previews(
            output_dir,
            body,
            armature,
            scene,
            solutions,
        )
        engineering_stem = (
            "KIRA_TFB_R12B_KNEE_EXPORT_ENGINEERING"
            if "r12b" in candidate_id.lower()
            else "KIRA_TFB_R12_KNEE_ENGINEERING_ONLY"
        )
        glb_path = output_dir / f"{engineering_stem}.glb"
        _export_glb(glb_path, [body, armature])
        blend_path = output_dir / f"{engineering_stem}.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        render_bindings = {}
        for side, raw_path in renders.items():
            path = Path(raw_path)
            render_bindings[f"{side}_knee_flexion"] = {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        evidence = {
            "schema_version": 1,
            "run_id": candidate_id,
            "candidate_id": candidate_id,
            "status": "REJECTED_ENGINEERING_EVIDENCE",
            "scope": "bilateral_axis_solved_knee_preview_only",
            "not_a_full_candidate": True,
            "owner_approved": False,
            "runtime_assignment_allowed": False,
            "runtime_activation_allowed": False,
            "roster_registration_allowed": False,
            "runtime_files_read_or_written_by_worker": False,
            "privacy": {
                "robert_private_photos_used": False,
                "robert_measurements_used": False,
                "robert_morphs_or_surface_used": False,
                "identifiable_person_likeness_used": False,
                "private_local_review_only": True,
            },
            "body_class": "adult_female",
            "adult_surface_body_class": "adult_female",
            "wrong_body_class_helper_or_surface_excluded": True,
            "adult_surface_matches_requested_body_class": False,
            "requested_body_class_visually_reviewed": False,
            "adult_surface_note": (
                "This engineering run tests only knees. The prior shallow "
                "female external surface remains rejected and is not being "
                "passed or reviewed here."
            ),
            "anatomical_forward_axis": "-Y",
            "knee_bone_bindings": {
                "left_knee_upper_bone": "upperleg02.L",
                "left_knee_lower_bone": "lowerleg01.L",
                "left_ankle_bone": "lowerleg02.L",
                "right_knee_upper_bone": "upperleg02.R",
                "right_knee_lower_bone": "lowerleg01.R",
                "right_ankle_bone": "lowerleg02.R",
            },
            "axis_search": {
                "coordinate_space": "world/armature space",
                "posterior_axis": "+Y",
                "camera_space_used_for_scoring": False,
                "left": solutions["left"],
                "right": solutions["right"],
            },
            "actions": {
                "knee_flexion": actions[0],
                "knee_flexion_right": actions[1],
            },
            "deformation_author_passes": {
                "knee_flexion": True,
                "knee_flexion_right": True,
            },
            "review_renders": {
                "pose_knee_flexion": Path(renders["left"]).name,
                "pose_knee_flexion_right": Path(renders["right"]).name,
            },
            "render_bindings": render_bindings,
            "topology": topology,
            "rig": rig_report,
            "candidate": {
                "path": str(glb_path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": glb_path.stat().st_size,
                "sha256": _sha256(glb_path),
                "primary_surface_property": "rapid_body_primary_surface=true",
                "owner_approved": False,
                "runtime_assignment_allowed": False,
                "runtime_activation_allowed": False,
                "public_export_allowed": False,
            },
            "review_blend": {
                "path": str(blend_path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": blend_path.stat().st_size,
                "sha256": _sha256(blend_path),
            },
            "truth_note": (
                "This is intentionally rejected engineering evidence for the "
                "bilateral knee-axis repair only. It is not a complete Kira "
                "body candidate and cannot be selected, attached, rostered, "
                "activated, or approved."
            ),
        }
        evidence_path = output_dir / "BUILD_EVIDENCE.json"
        evidence_path.write_text(
            json.dumps(evidence, indent=2) + "\n",
            encoding="utf-8",
        )
        return
    rig_data = json.loads(RIG_PATH.read_text(encoding="utf-8"))
    joints = _joint_positions(
        rig_data,
        source["all_deformed_source_vertices"],
        source_low_z=source["source_low_z"],
        scale=source["scale"],
    )
    hair, hair_report = _add_hair(body, armature)
    eyes, eye_report = _add_eyes(
        armature,
        rig_data,
        joints,
        TARGET_HEIGHT_METERS,
    )
    nails, nail_report = _add_nails(armature, TARGET_HEIGHT_METERS)
    actions = _create_actions(armature, TARGET_HEIGHT_METERS)
    scene = _setup_scene()
    renders = _render_evidence(output_dir, body, armature, hair, scene)

    glb_path = output_dir / "KIRA_TEMPORARY_FUNCTIONAL_BODY_PRIVATE_CANDIDATE.glb"
    export_objects = [body, armature, *hair, *eyes, *nails]
    _export_glb(glb_path, export_objects)
    blend_path = output_dir / "KIRA_TEMPORARY_FUNCTIONAL_BODY_PRIVATE_CANDIDATE.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report = {
        "schema": "kira.avatar.temporary_functional_body.makehuman_candidate.v1",
        "candidate_id": candidate_id,
        "status": "PRIVATE_INACTIVE_CANDIDATE_AWAITING_INDEPENDENT_VISUAL_AND_DEFORMATION_REVIEW",
        "owner_approved": False,
        "selectable": False,
        "attached": False,
        "rostered": False,
        "runtime_activation_allowed": False,
        "runtime_modified": False,
        "identity": "Kira Hart",
        "body_class": "TEMPORARY_FUNCTIONAL_BODY",
        "adult": True,
        "height_m": TARGET_HEIGHT_METERS,
        "target_description": {
            "sex": "adult woman",
            "build": "natural-athletic and proportionate",
            "skin": "light",
            "eyes": "brown",
            "hair": "black removable review hair",
        },
        "privacy_and_identity_isolation": {
            "robert_private_data_read": False,
            "robert_identity_or_morph_reused": False,
            "source_is_generic_cc0_makehuman": True,
            "adult_reference_is_structural_guidance_only": True,
        },
        "base_obj": str(BASE_OBJ),
        "base_obj_sha256": _sha256(BASE_OBJ),
        "source_face_groups": ["body"],
        "explicitly_excluded_source_groups": ["helper-genital"],
        "targets": applied,
        "topology": topology,
        "adult_surface_authoring": source["surface"],
        "height_transform": source["transform"],
        "rig": rig_report,
        "hair": hair_report,
        "eyes": eye_report,
        "nails": nail_report,
        "actions": actions,
        "required_visual_evidence": renders,
        "self_review_pending": [
            "bilateral knees visibly flex posteriorly",
            "seated body has believable seat contact",
            "no hard black bands above or below eyes",
            "no non-hair black scalp or cap",
            "front, side, rear, crown hair coverage",
            "no nail penetration, floating, or protrusion",
            "adult external surface reads as continuous rather than a void",
            "hair reads as straight rather than wavy or curled",
        ],
        "glb": str(glb_path),
        "glb_sha256": _sha256(glb_path),
        "blend": str(blend_path),
        "blend_sha256": _sha256(blend_path),
    }
    report_path = output_dir / "CANDIDATE_BUILD_REPORT.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
