"""Create the protected Biological Robert V25 static review candidate.

This script personalizes the clean CC0 MakeHuman R8-derived topology without
changing the generic reusable foundation.  It adds bounded Robert-specific
shape targets (already baked into the source blend), neutral skin variation,
real blue iris materials, a removable layered dark-blond static-review groom,
and explicit static fingernails.  It remains a static owner-review artifact:
no rig, movement, runtime attachment, activation, clothing, Kira body work, or
Synthetic Robert duplication is performed.

Run with Blender 5.1:

    blender --background --python \
      tools/blender_personalize_biological_robert_makehuman_v25.py
"""

from __future__ import annotations

from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path
import random

import bmesh
import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = (
    ROOT
    / "Avatar"
    / "private_owner_review"
    / "dual_robert_20260729"
    / "biological_static_likeness_v25_r7_makehuman_cc0_private_fit"
)
SOURCE_BLEND = SOURCE_DIR / "MAKEHUMAN_CC0_PARAMETRIC_MALE_FOUNDATION.blend"
SOURCE_REPORT = SOURCE_DIR / "FOUNDATION_PROBE_REPORT.json"
FACE_LANDMARK_COMPARISON = SOURCE_DIR / "PRIVATE_FACE_LANDMARK_COMPARISON.json"
OUT = SOURCE_DIR / "private_review"
FINAL_BLEND = SOURCE_DIR / "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V25_R7.blend"
MAKEHUMAN_BASE = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "tooling"
    / "makehuman_official"
    / "makehuman"
    / "data"
    / "3dobjs"
    / "base.obj"
)
HAIR_REFERENCE = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "asset_library"
    / "hair_reference"
    / "short_hair_cut_in_layers_with_bones_90fd798a2e.glb"
)
HAIR_PACK_REFERENCE = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "asset_library"
    / "hair_reference"
    / "hair_pack_part_1_592f1bcc9b.glb"
)
HAIR_PACK_CANDIDATE_OBJECTS = ("Object_134", "Object_136")
PRIVATE_NEW_REFERENCE = Path(r"C:\Users\robmc\Desktop\reference")
PRIVATE_BASE_REFERENCE = Path(r"C:\Users\robmc\Desktop\robert avatar base")

STATUS = "REJECTED_ENGINEERING_EVIDENCE_ONLY"
REJECTED_STATUS = "REJECTED_ENGINEERING_EVIDENCE_ONLY"
ESTIMATE_LABEL = "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
PREVIEW_ONLY = os.environ.get("ROBERT_STATIC_PREVIEW_ONLY") == "1"
HAIR_FROZEN_FOR_FACE_REPAIR = True
STATIC_LID_OVERLAYS_ENABLED = False

PRIVATE_FACE_LANDMARK_TARGETS: tuple[
    tuple[str, float, str], ...
] = (
    ("head/head-rectangular.target", 0.10, "retain Robert's broad rectangular head"),
    ("head/head-square.target", 0.07, "strengthen bounded square lower-face direction"),
    (
        "head/head-scale-horiz-incr.target",
        0.025,
        "bounded reference-supported head width",
    ),
    (
        "head/head-scale-vert-decr.target",
        0.025,
        "reduce remaining generic long-head appearance",
    ),
    ("cheek/l-cheek-volume-incr.target", 0.18, "left cheek fullness"),
    ("cheek/r-cheek-volume-incr.target", 0.18, "right cheek fullness"),
    ("chin/chin-width-incr.target", 0.14, "broad adult chin"),
    ("chin/chin-height-decr.target", 0.12, "reduce generic long-chin appearance"),
    ("nose/nose-scale-horiz-incr.target", 0.15, "broader reference-supported nose"),
    ("nose/nose-point-width-incr.target", 0.14, "broader rounded nasal tip"),
    ("nose/nose-nostrils-width-incr.target", 0.12, "nostril width"),
    (
        "nose/nose-scale-depth-decr.target",
        0.08,
        "moderate private-profile nose projection",
    ),
    (
        "nose/nose-scale-vert-decr.target",
        0.04,
        "bounded private-profile nose length",
    ),
    ("nose/nose-width1-incr.target", 0.05, "upper nose width"),
    ("nose/nose-width2-incr.target", 0.06, "middle nose width"),
    ("mouth/mouth-scale-horiz-incr.target", 0.24, "reference-supported mouth width"),
    ("mouth/mouth-lowerlip-width-incr.target", 0.08, "lower-lip width"),
    ("mouth/mouth-upperlip-width-incr.target", 0.06, "upper-lip width"),
    ("mouth/mouth-lowerlip-volume-incr.target", 0.23, "lower-lip volume"),
    ("mouth/mouth-upperlip-volume-incr.target", 0.13, "upper-lip volume"),
    ("mouth/mouth-scale-vert-incr.target", 0.08, "natural lip aperture height"),
    (
        "mouth/mouth-trans-forward.target",
        0.025,
        "bounded natural lip projection in profile",
    ),
    (
        "eyes/l-eye-scale-incr.target",
        0.04,
        "partially restore left aperture after inherited reduction",
    ),
    (
        "eyes/r-eye-scale-incr.target",
        0.04,
        "partially restore right aperture after inherited reduction",
    ),
    (
        "eyes/l-eye-height1-incr.target",
        0.12,
        "restore natural left outer aperture height",
    ),
    (
        "eyes/l-eye-height2-incr.target",
        0.12,
        "restore natural left middle aperture height",
    ),
    (
        "eyes/l-eye-height3-incr.target",
        0.12,
        "restore natural left inner aperture height",
    ),
    (
        "eyes/r-eye-height1-incr.target",
        0.12,
        "restore natural right outer aperture height",
    ),
    (
        "eyes/r-eye-height2-incr.target",
        0.12,
        "restore natural right middle aperture height",
    ),
    (
        "eyes/r-eye-height3-incr.target",
        0.12,
        "restore natural right inner aperture height",
    ),
    ("eyes/l-eye-trans-out.target", 0.025, "left eye spacing"),
    ("eyes/r-eye-trans-out.target", 0.025, "right eye spacing"),
    ("eyes/l-eye-eyefold-down.target", 0.025, "left natural upper lid fold"),
    ("eyes/r-eye-eyefold-down.target", 0.025, "right natural upper lid fold"),
    ("eyes/l-eye-bag-incr.target", 0.055, "left adult lower-eye structure"),
    ("eyes/r-eye-bag-incr.target", 0.055, "right adult lower-eye structure"),
    ("eyes/l-eye-push1-in.target", 0.04, "seat left outer socket"),
    ("eyes/l-eye-push2-in.target", 0.04, "seat left inner socket"),
    ("eyes/r-eye-push1-in.target", 0.04, "seat right outer socket"),
    ("eyes/r-eye-push2-in.target", 0.04, "seat right inner socket"),
)

PRIVATE_FACE_LANDMARK_GOALS = {
    "authority": "ESTIMATED/MEASURED FROM AUTHORIZED PRIVATE REFERENCE",
    "method": (
        "manual bounded normalized measurements from an authorized neutral "
        "front reference, cross-checked against the V1/V15 identity direction"
    ),
    "not_photogrammetry": True,
    "normalized_goals": {
        "face_height_over_bizygomatic_width": [1.46, 1.62],
        "jaw_width_over_cheek_width": [0.82, 0.90],
        "chin_width_over_face_width": [0.52, 0.62],
        "nose_width_over_face_width": [0.27, 0.32],
        "mouth_width_over_face_width": [0.42, 0.48],
        "interpupillary_distance_over_face_width": [0.39, 0.44],
        "eye_aperture_height_over_width": [0.30, 0.40],
        "iris_diameter_over_visible_eye_height": [0.72, 0.90],
    },
    "qualitative_landmarks": [
        "broad rectangular adult head",
        "full but bounded cheeks",
        "broad square chin without an elongated point",
        "rounded wider nose and nostril base",
        "wider natural lips with fuller lower lip",
        "small blue-gray eyes with heavy natural upper lids",
    ],
}


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
    component_sizes: list[int] = []
    while unseen:
        seed = unseen.pop()
        queue = deque([seed])
        size = 0
        while queue:
            current = queue.popleft()
            size += 1
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other in unseen:
                    unseen.remove(other)
                    queue.append(other)
        component_sizes.append(size)
    component_sizes.sort(reverse=True)
    boundary = sum(edge.is_boundary for edge in bm.edges)
    internal_nonmanifold = sum(
        not edge.is_manifold and not edge.is_boundary for edge in bm.edges
    )
    signed_volume = (
        float(bm.calc_volume(signed=True))
        if boundary == 0 and internal_nonmanifold == 0
        else 0.0
    )
    result: dict[str, int | float | list[int]] = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "connected_components": len(component_sizes),
        "component_vertex_counts": component_sizes,
        "boundary_edges": boundary,
        "nonmanifold_internal_edges": internal_nonmanifold,
        "signed_volume": signed_volume,
    }
    bm.free()
    return result


def material_principled(
    name: str,
    color: tuple[float, float, float, float],
    *,
    roughness: float,
    subsurface: float = 0.0,
    metallic: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Subsurface Weight"].default_value = subsurface
    return material


def skin_material() -> bpy.types.Material:
    material = bpy.data.materials.new("Robert_Natural_Regional_Skin_V25")
    material.diffuse_color = (0.63, 0.40, 0.32, 1.0)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.name = "Subtle_Skin_Albedo_Variation"
    noise.inputs["Scale"].default_value = 4.2
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.58
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.name = "Natural_Skin_Color_Range"
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (0.34, 0.17, 0.12, 1.0)
    ramp.color_ramp.elements[1].position = 0.76
    ramp.color_ramp.elements[1].color = (0.60, 0.35, 0.26, 1.0)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    if bsdf is not None:
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.54
        bsdf.inputs["Subsurface Weight"].default_value = 0.07
        if "Subsurface Radius" in bsdf.inputs:
            bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.48, 0.28)
    return material


def hair_material() -> bpy.types.Material:
    material = bpy.data.materials.new("Robert_Dark_Blond_Static_Groom_V25")
    material.diffuse_color = (0.40, 0.25, 0.10, 1.0)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 7.5
    noise.inputs["Detail"].default_value = 2.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.12, 0.065, 0.022, 1.0)
    ramp.color_ramp.elements[1].color = (0.48, 0.30, 0.115, 1.0)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    if bsdf is not None:
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.57
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.24
        if "Coat Weight" in bsdf.inputs:
            bsdf.inputs["Coat Weight"].default_value = 0.0
    return material


def parse_obj_groups(
    path: Path,
) -> tuple[list[Vector], dict[str, list[tuple[int, ...]]]]:
    vertices: list[Vector] = []
    groups: dict[str, list[tuple[int, ...]]] = {}
    current = ""
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                vertices.append(Vector((float(x), float(y), float(z))))
            elif line.startswith("g "):
                current = line[2:].strip()
            elif line.startswith("f ") and current:
                indices = []
                for token in line.split()[1:]:
                    raw_index = int(token.split("/", 1)[0])
                    indices.append(
                        raw_index - 1
                        if raw_index > 0
                        else len(vertices) + raw_index
                    )
                if len(indices) >= 3:
                    groups.setdefault(current, []).append(tuple(indices))
    return vertices, groups


def apply_target(vertices: list[Vector], path: Path, weight: float) -> None:
    if not weight:
        return
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            fields = raw.split()
            if len(fields) != 4 or fields[0].startswith("#"):
                continue
            index = int(fields[0])
            vertices[index] += Vector(
                (
                    float(fields[1]) * weight,
                    float(fields[2]) * weight,
                    float(fields[3]) * weight,
                )
            )


def _coordinate_key(point: Vector, digits: int) -> tuple[float, float, float]:
    return tuple(round(float(value), digits) for value in point)


def _point_signature(points: list[Vector]) -> str:
    digest = hashlib.sha256()
    for point in points:
        digest.update(
            (
                f"{point.x:.7f},{point.y:.7f},{point.z:.7f}\n"
            ).encode("ascii")
        )
    return digest.hexdigest()


def apply_private_face_geometry_fit(
    body: bpy.types.Object,
    source_vertices: list[Vector],
) -> dict[str, object]:
    """Apply measured, bounded Robert-specific face deltas to the clean head.

    The body was compacted and pelvis-unioned after MakeHuman target
    application, so source indices are no longer a safe direct map. Head
    coordinates remain unchanged by that local pelvis operation. We therefore
    replay the private face targets on a copy of the source vertices and map
    the resulting coordinate deltas back onto exact/quantized pre-morph head
    coordinates. Lower-body coordinates are hashed before and after and must
    remain byte-for-byte identical at the chosen precision.
    """

    before_source = [point.copy() for point in source_vertices]
    target_root = MAKEHUMAN_BASE.parents[1] / "targets"
    target_rows: list[dict[str, object]] = []
    for relative_path, weight, purpose in PRIVATE_FACE_LANDMARK_TARGETS:
        path = target_root / relative_path
        if not path.is_file():
            raise RuntimeError(f"required private face target missing: {relative_path}")
        apply_target(source_vertices, path, weight)
        target_rows.append(
            {
                "target": relative_path,
                "weight": weight,
                "purpose": purpose,
                "source_sha256": sha256(path),
            }
        )

    delta_maps: dict[
        int, dict[tuple[float, float, float], list[Vector]]
    ] = {5: {}, 4: {}}
    nonzero_source_vertices = 0
    for before, after in zip(before_source, source_vertices):
        before_blender = blender_point(before)
        delta = blender_point(after) - before_blender
        if delta.length <= 1e-9:
            continue
        nonzero_source_vertices += 1
        for digits in (5, 4):
            delta_maps[digits].setdefault(
                _coordinate_key(before_blender, digits), []
            ).append(delta)

    averaged_maps: dict[int, dict[tuple[float, float, float], Vector]] = {}
    for digits, rows in delta_maps.items():
        averaged_maps[digits] = {
            key: sum(values, Vector()) / len(values)
            for key, values in rows.items()
        }

    lower_before = [
        vertex.co.copy() for vertex in body.data.vertices if vertex.co.z < 6.45
    ]
    lower_signature_before = _point_signature(lower_before)
    matched_indices: list[int] = []
    displacements: list[float] = []
    matched_by_precision = {5: 0, 4: 0}
    matched_before: list[Vector] = []
    for vertex in body.data.vertices:
        if vertex.co.z < 6.45:
            continue
        delta = averaged_maps[5].get(_coordinate_key(vertex.co, 5))
        digits = 5
        if delta is None:
            delta = averaged_maps[4].get(_coordinate_key(vertex.co, 4))
            digits = 4
        if delta is None:
            continue
        matched_before.append(vertex.co.copy())
        vertex.co += delta
        matched_indices.append(vertex.index)
        displacements.append(delta.length)
        matched_by_precision[digits] += 1
    body.data.update()
    if not matched_indices or max(displacements, default=0.0) <= 1e-7:
        raise RuntimeError(
            "private face landmark fit changed no body head vertices; fail closed"
        )

    fit_group = body.vertex_groups.get("Robert_Private_Face_Landmark_Fit_V25")
    if fit_group is None:
        fit_group = body.vertex_groups.new(
            name="Robert_Private_Face_Landmark_Fit_V25"
        )
    fit_group.add(matched_indices, 1.0, "REPLACE")

    lower_after = [
        vertex.co.copy() for vertex in body.data.vertices if vertex.co.z < 6.45
    ]
    lower_signature_after = _point_signature(lower_after)
    lower_invariant = (
        len(lower_before) == len(lower_after)
        and lower_signature_before == lower_signature_after
    )
    if not lower_invariant:
        raise RuntimeError("face-only fit altered lower body/pelvis/anatomy vertices")

    matched_after = [body.data.vertices[index].co.copy() for index in matched_indices]
    before_min = [
        min(point[axis] for point in matched_before) for axis in range(3)
    ]
    before_max = [
        max(point[axis] for point in matched_before) for axis in range(3)
    ]
    after_min = [
        min(point[axis] for point in matched_after) for axis in range(3)
    ]
    after_max = [
        max(point[axis] for point in matched_after) for axis in range(3)
    ]
    return {
        "status": "BOUNDED_GEOMETRY_CHANGE_APPLIED_NOT_OWNER_APPROVED",
        "landmark_goals": PRIVATE_FACE_LANDMARK_GOALS,
        "target_deltas": target_rows,
        "source_vertices_with_nonzero_face_delta": nonzero_source_vertices,
        "matched_body_head_vertices": len(matched_indices),
        "matched_by_coordinate_precision": matched_by_precision,
        "maximum_vertex_displacement": max(displacements),
        "mean_vertex_displacement": sum(displacements) / len(displacements),
        "matched_region_bounds_before": {
            "minimum": before_min,
            "maximum": before_max,
        },
        "matched_region_bounds_after": {
            "minimum": after_min,
            "maximum": after_max,
        },
        "lower_body_pelvis_anatomy_invariant": {
            "cutoff_z": 6.45,
            "vertex_count": len(lower_before),
            "signature_before": lower_signature_before,
            "signature_after": lower_signature_after,
            "unchanged": lower_invariant,
        },
        "truth_limit": (
            "manual reference-guided parametric landmark fit; not "
            "photogrammetry and not final likeness approval"
        ),
    }


def blender_point(point: Vector) -> Vector:
    return Vector((point.x, -point.z, point.y))


def compact_group(
    vertices: list[Vector], faces: list[tuple[int, ...]]
) -> tuple[list[tuple[float, float, float]], list[tuple[int, ...]]]:
    used = sorted({index for face in faces for index in face})
    remap = {old: new for new, old in enumerate(used)}
    points = [tuple(blender_point(vertices[index])) for index in used]
    compact_faces = [tuple(remap[index] for index in face) for face in faces]
    return points, compact_faces


def create_eye_group(
    name: str,
    vertices: list[Vector],
    faces: list[tuple[int, ...]],
    sclera: bpy.types.Material,
    iris: bpy.types.Material,
    pupil: bpy.types.Material,
    lid_material: bpy.types.Material,
) -> tuple[bpy.types.Object, list[bpy.types.Object], dict[str, object]]:
    points, compact_faces = compact_group(vertices, faces)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], compact_faces)
    mesh.update(calc_edges=True)
    eye = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(eye)
    eye.data.materials.append(sclera)
    for polygon in eye.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True
    modifier = eye.modifiers.new("EyeReviewSubdivision", "SUBSURF")
    modifier.levels = 1
    modifier.render_levels = 2

    minimum, maximum = object_bounds(eye)
    center = (minimum + maximum) * 0.5
    radius = max(maximum.x - minimum.x, maximum.z - minimum.z) * 0.5
    front_y = minimum.y + 0.010
    # Retain the official helper sphere as non-rendered placement evidence.
    # A shallow sclera surface avoids the under-eye disk/intersection artifact
    # produced when the full helper sphere protrudes through the eyelid mesh.
    eye.hide_render = True
    additions: list[bpy.types.Object] = []
    # Fit a smaller eye surface behind the body's actual eyelid opening. The
    # earlier large white ellipse plus separate lid strips looked pasted on.
    # The face targets now own the aperture geometry; these surfaces provide
    # only sclera, blue iris, and pupil behind it.
    sclera_half_width = radius * 0.68
    sclera_half_height = radius * 0.28
    sclera_depth = radius * 0.55
    for suffix, material, scale, front_offset in (
        (
            "Sclera_Review_Surface",
            sclera,
            (sclera_half_width, sclera_depth, sclera_half_height),
            0.0,
        ),
        (
            "Iris",
            iris,
            (radius * 0.17, radius * 0.13, radius * 0.17),
            -0.004,
        ),
        (
            "Pupil",
            pupil,
            (radius * 0.064, radius * 0.08, radius * 0.064),
            -0.007,
        ),
    ):
        depth = scale[1]
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=40,
            ring_count=20,
            # Put the front of each curved ellipsoid at the recorded eye
            # plane while its volume extends backward into the socket. This
            # retains curvature in three-quarter views instead of rendering
            # the eye as a flat pasted-in ellipse.
            location=(center.x, front_y + depth + front_offset, center.z),
        )
        overlay = bpy.context.object
        overlay.name = f"{name}_{suffix}"
        overlay.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        overlay.data.materials.append(material)
        for polygon in overlay.data.polygons:
            polygon.use_smooth = True
        additions.append(overlay)

    # Explicit static upper/lower lid strips cover the flat white-oval edges.
    # These are review geometry only; facial animation/shape keys remain
    # deferred until the static likeness is accepted.
    lid_names: list[str] = []
    for upper in ((True, False) if STATIC_LID_OVERLAYS_ENABLED else ()):
        segments = 32
        start_angle = 0.0 if upper else math.pi
        end_angle = math.pi if upper else 2.0 * math.pi
        outer_points: list[tuple[float, float, float]] = []
        inner_points: list[tuple[float, float, float]] = []
        for index in range(segments + 1):
            angle = start_angle + (end_angle - start_angle) * (
                index / segments
            )
            cosine = math.cos(angle)
            sine = math.sin(angle)
            outer_points.append(
                (
                    center.x + sclera_half_width * 1.05 * cosine,
                    front_y - 0.011,
                    center.z + sclera_half_height * 1.12 * sine,
                )
            )
            # The prior 0.34/0.60 factors over-covered the blue eye and read
            # as a black horizontal slit.  These factors leave a bounded,
            # asymmetric human aperture while still hiding the flat sclera
            # ellipse edges.
            inner_height_factor = 0.60 if upper else 0.78
            inner_points.append(
                (
                    center.x + sclera_half_width * 0.96 * cosine,
                    front_y - 0.012,
                    center.z
                    + sclera_half_height * inner_height_factor * sine,
                )
            )
        lid_vertices = outer_points + inner_points
        lid_faces: list[tuple[int, int, int, int]] = []
        inner_offset = len(outer_points)
        for index in range(segments):
            lid_faces.append(
                (
                    index,
                    index + 1,
                    inner_offset + index + 1,
                    inner_offset + index,
                )
            )
        lid_mesh = bpy.data.meshes.new(
            f"{name}_{'Upper' if upper else 'Lower'}_Lid_Mesh"
        )
        lid_mesh.from_pydata(lid_vertices, [], lid_faces)
        lid_mesh.update(calc_edges=True)
        lid = bpy.data.objects.new(
            f"{name}_{'Upper' if upper else 'Lower'}_Static_Lid", lid_mesh
        )
        bpy.context.collection.objects.link(lid)
        lid.data.materials.append(lid_material)
        for polygon in lid.data.polygons:
            polygon.use_smooth = True
        solidify = lid.modifiers.new("StaticLidThickness", "SOLIDIFY")
        solidify.thickness = 0.004
        solidify.offset = 0.0
        additions.append(lid)
        lid_names.append(lid.name)
    return eye, additions, {
        "minimum": [float(value) for value in minimum],
        "maximum": [float(value) for value in maximum],
        "center": [float(value) for value in center],
        "seated_front_y": front_y,
        "visible_sclera_half_width": sclera_half_width,
        "visible_sclera_half_height": sclera_half_height,
        "visible_sclera_depth": sclera_depth,
        "sclera_front_plane_y": front_y,
        "iris_radius": radius * 0.17,
        "pupil_radius": radius * 0.064,
        "static_lid_overlays_enabled": STATIC_LID_OVERLAYS_ENABLED,
        "nominal_sclera_surface_height_over_width": (
            2.0 * sclera_half_height
        )
        / (2.0 * sclera_half_width),
        "static_lid_meshes": lid_names,
        "runtime_face_rig_complete": False,
    }


def add_reference_static_hair(
    body: bpy.types.Object, material: bpy.types.Material
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    """Fit the licensed layered short-hair mesh as removable static hair.

    The source armature deformation is intentionally removed for this static
    fit. Retaining it during R7's first fit twisted the layers across the face.
    """

    if not HAIR_REFERENCE.is_file():
        raise RuntimeError(f"approved static hair reference missing: {HAIR_REFERENCE}")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(HAIR_REFERENCE))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    meshes = [
        obj
        for obj in imported
        if obj.type == "MESH" and obj.name.lower() != "icosphere"
    ]
    if not meshes:
        raise RuntimeError("approved static hair reference imported no visible meshes")
    for obj in imported:
        if obj.type == "MESH" and obj not in meshes:
            obj.hide_render = True
    for obj in meshes:
        # Match the proven V15 adaptation: use the coherent authored rest mesh
        # directly instead of evaluating its unrelated source armature.
        obj.parent = None
        for modifier in list(obj.modifiers):
            obj.modifiers.remove(modifier)
        obj.location = (0.0, 0.0, 0.0)
        obj.rotation_euler = (0.0, 0.0, 0.0)
        obj.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()

    body_points = [vertex.co.copy() for vertex in body.data.vertices]
    top = max(point.z for point in body_points)
    head_points = [point for point in body_points if point.z > top - 2.35]
    # Fit depth and fore/aft placement against the upper skull rather than the
    # complete head bounds.  The nose is the front-most head point and biased
    # the previous fit forward, leaving the occipital scalp exposed while the
    # fringe crossed Robert's eyes.
    crown_points = [point for point in body_points if point.z > top - 0.85]
    if not crown_points:
        raise RuntimeError("upper-crown landmark selection produced no points")
    target_min = Vector(
        tuple(min(point[axis] for point in head_points) for axis in range(3))
    )
    target_max = Vector(
        tuple(max(point[axis] for point in head_points) for axis in range(3))
    )
    crown_min = Vector(
        tuple(min(point[axis] for point in crown_points) for axis in range(3))
    )
    crown_max = Vector(
        tuple(max(point[axis] for point in crown_points) for axis in range(3))
    )
    source_min, source_max = world_bounds(meshes)
    source_extent = source_max - source_min
    target_extent = target_max - target_min
    crown_extent = crown_max - crown_min
    scale_x = target_extent.x * 1.10 / source_extent.x
    raw_scale_y = crown_extent.y * 1.24 / source_extent.y
    scale_y = max(
        scale_x * 0.94,
        min(scale_x * 1.18, raw_scale_y),
    )
    # The licensed groom is intentionally longer in front than Robert's short
    # layered reference style. Preserve more authored length over the sides
    # and occipital scalp instead of compressing the entire groom into a cap.
    # Both source meshes receive exactly the same smooth front-to-rear haircut.
    front_vertical_factor = 0.58
    rear_vertical_factor = 0.90
    for obj in meshes:
        for vertex in obj.data.vertices:
            depth = (
                (vertex.co.y - source_min.y) / source_extent.y
                if source_extent.y > 1e-8
                else 0.5
            )
            depth = max(0.0, min(1.0, depth))
            smooth_depth = depth * depth * (3.0 - 2.0 * depth)
            vertical_factor = (
                front_vertical_factor
                + (rear_vertical_factor - front_vertical_factor) * smooth_depth
            )
            vertex.co.z = source_max.z + (
                vertex.co.z - source_max.z
            ) * vertical_factor
        obj.data.update()
    bpy.context.view_layer.update()
    deformed_min, deformed_max = world_bounds(meshes)
    deformed_extent = deformed_max - deformed_min
    deformed_center = (deformed_min + deformed_max) * 0.5
    upper_crown_y_center = (crown_min.y + crown_max.y) * 0.5
    target_top = target_max.z + 0.04
    target_center = Vector(
        (
            (target_min.x + target_max.x) * 0.5,
            upper_crown_y_center + 0.02,
            target_top - deformed_extent.z * scale_x * 0.5,
        )
    )
    translation = target_center - Vector(
        (
            deformed_center.x * scale_x,
            deformed_center.y * scale_y,
            deformed_center.z * scale_x,
        )
    )
    root = bpy.data.objects.new("Robert_Removable_Layered_Hair_Root_V25_R7", None)
    bpy.context.collection.objects.link(root)

    for obj in meshes:
        obj.scale = (scale_x, scale_y, scale_x)
        obj.location = translation
    bpy.context.view_layer.update()
    for obj in meshes:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix
        obj.data.materials.clear()
        obj.data.materials.append(material)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        obj["static_review_component"] = True
        obj["runtime_hair_system_complete"] = False
    root["component_type"] = "REMOVABLE_LAYERED_HAIR_WITH_BONES_STATIC_REVIEW"
    root["runtime_approved"] = False
    root["runtime_hair_system_complete"] = False
    root["component_meshes"] = [obj.name for obj in meshes]
    return [root, *imported], {
        "method": (
            "licensed layered short-hair rest meshes detached from unrelated "
            "source armature, jointly fitted to Robert upper-skull/crown "
            "landmarks with one shared smooth region-aware haircut, and "
            "recolored"
        ),
        "source_asset_id": "APPROVED_LAYERED_SHORT_HAIR_REFERENCE",
        "source_sha256": sha256(HAIR_REFERENCE),
        "attribution": {
            "title": "Short Hair Cut In Layers (With Bones)",
            "author": "zHairezt",
            "author_url": "https://sketchfab.com/zHairezt",
            "source_url": (
                "https://sketchfab.com/3d-models/"
                "short-hair-cut-in-layers-with-bones-60f13e9fa15941409654483c51add79e"
            ),
            "license": "CC-BY-4.0",
            "license_url": "http://creativecommons.org/licenses/by/4.0/",
            "adaptation_notice": (
                "rest meshes detached from source armature for static review; "
                "both authored meshes retain one shared fit transform, with "
                "the same bounded front-to-rear length adaptation and "
                "dark-blond recoloring; no runtime-rig claim"
            ),
        },
        "visible_mesh_count": len(meshes),
        "shared_fit_scale_xz": scale_x,
        "shared_fit_scale_y": scale_y,
        "raw_depth_scale": raw_scale_y,
        "front_vertical_factor": front_vertical_factor,
        "rear_vertical_factor": rear_vertical_factor,
        "region_aware_haircut": True,
        "upper_crown_y_center": upper_crown_y_center,
        "target_top": target_top,
        "runtime_hair_complete": False,
        "review_scope": "STATIC_LIKENESS_ONLY",
    }


def add_static_hair_root_underlay(
    body: bpy.types.Object, material: bpy.types.Material
) -> tuple[bpy.types.Object, dict[str, object]]:
    """Create a removable scalp-root underlay beneath the licensed hair mesh.

    The authored hair has an intentional crown opening. This underlay prevents
    that opening from reading as bald skin in static review. It is not a
    helmet, final groom, or runtime hair system.
    """

    coordinates = [vertex.co.copy() for vertex in body.data.vertices]
    normals = [vertex.normal.copy() for vertex in body.data.vertices]
    top = max(point.z for point in coordinates)
    selected = {
        index for index, point in enumerate(coordinates) if point.z > top - 0.58
    }
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    remap: dict[int, int] = {}
    for polygon in body.data.polygons:
        polygon_indices = list(polygon.vertices)
        if not all(index in selected for index in polygon_indices):
            continue
        face: list[int] = []
        for index in polygon_indices:
            if index not in remap:
                remap[index] = len(vertices)
                point = coordinates[index] + normals[index] * 0.022
                vertices.append(tuple(point))
            face.append(remap[index])
        faces.append(tuple(face))
    mesh = bpy.data.meshes.new("Robert_Static_Hair_Root_Underlay_Mesh_V25")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    underlay = bpy.data.objects.new(
        "Robert_Removable_Static_Hair_Root_Underlay_V25", mesh
    )
    bpy.context.collection.objects.link(underlay)
    underlay.data.materials.append(material)
    for polygon in underlay.data.polygons:
        polygon.use_smooth = True
    solidify = underlay.modifiers.new("StaticHairRootUnderlayThickness", "SOLIDIFY")
    solidify.thickness = 0.012
    solidify.offset = 1.0
    underlay["static_review_component"] = True
    underlay["runtime_hair_system_complete"] = False
    return underlay, {
        "method": (
            "removable scalp-surface root underlay beneath licensed hair mesh"
        ),
        "vertices": len(vertices),
        "faces": len(faces),
        "purpose": "prevent authored crown opening from reading as bald skin",
        "runtime_hair_complete": False,
    }


def add_hair_pack_static_hair(
    body: bpy.types.Object, material: bpy.types.Material
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    """Fit one licensed, full-coverage short hairstyle to Robert's skull.

    The earlier two-mesh layered reference remained a chunky circular shag even
    after its placement and coverage were corrected.  This bounded static-only
    adapter evaluates one cleaner short hairstyle from the existing CC-BY Hair
    Pack, bakes its rest shape, discards the unrelated source rig, and fits it
    against upper-skull/crown landmarks.  It is removable and is not represented
    as the future runtime groom.
    """

    if not HAIR_PACK_REFERENCE.is_file():
        raise RuntimeError(f"licensed hair pack missing: {HAIR_PACK_REFERENCE}")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(HAIR_PACK_REFERENCE))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    source_candidates: list[bpy.types.Object] = []
    for expected_name in HAIR_PACK_CANDIDATE_OBJECTS:
        matches = [
            obj
            for obj in imported
            if obj.type == "MESH"
            and (
                obj.name == expected_name
                or obj.name.startswith(f"{expected_name}.")
            )
        ]
        if len(matches) != 1:
            raise RuntimeError(
                "expected one authored Hair Pack mesh "
                f"{expected_name}, found {[obj.name for obj in matches]}"
            )
        source_candidates.append(matches[0])
    if len(source_candidates) != len(HAIR_PACK_CANDIDATE_OBJECTS):
        raise RuntimeError(
            "incomplete licensed short-hair sibling set "
            f"{HAIR_PACK_CANDIDATE_OBJECTS}, found "
            f"{[obj.name for obj in source_candidates]}"
        )
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    hair_meshes: list[bpy.types.Object] = []
    for index, source in enumerate(source_candidates):
        evaluated = source.evaluated_get(depsgraph)
        baked_mesh = bpy.data.meshes.new_from_object(
            evaluated,
            preserve_all_data_layers=True,
            depsgraph=depsgraph,
        )
        hair = bpy.data.objects.new(
            f"Robert_Removable_Clean_Short_Hair_V25_R7_{index:02d}",
            baked_mesh,
        )
        bpy.context.collection.objects.link(hair)
        hair.matrix_world = source.matrix_world.copy()
        # Bake the source hierarchy transform into each sibling mesh so one
        # shared removable object transform owns all later Robert-specific fit.
        baked_mesh.transform(hair.matrix_world)
        hair.matrix_world = Matrix.Identity(4)
        # Preserve the source alpha/strand structure. Replacing these materials
        # with an opaque shader exposed raw hair-card polygons in the prior
        # rejected probe. Tint only the authored Base Color path.
        if not baked_mesh.materials:
            baked_mesh.materials.append(material)
        else:
            for material_index, source_material in enumerate(
                list(baked_mesh.materials)
            ):
                if source_material is None:
                    baked_mesh.materials[material_index] = material
                    continue
                adapted = source_material.copy()
                adapted.name = (
                    f"Robert_Dark_Blond_Authored_Alpha_{index:02d}_"
                    f"{material_index:02d}"
                )
                if adapted.use_nodes:
                    nodes = adapted.node_tree.nodes
                    links = adapted.node_tree.links
                    for bsdf in [
                        node
                        for node in nodes
                        if node.type == "BSDF_PRINCIPLED"
                    ]:
                        base = bsdf.inputs.get("Base Color")
                        if base is not None and base.is_linked:
                            old_link = base.links[0]
                            source_socket = old_link.from_socket
                            links.remove(old_link)
                            tint = nodes.new("ShaderNodeMixRGB")
                            tint.name = "Robert_Natural_Dark_Blond_Tint"
                            tint.blend_type = "MULTIPLY"
                            tint.inputs[0].default_value = 0.82
                            tint.inputs[2].default_value = (
                                0.34,
                                0.245,
                                0.135,
                                1.0,
                            )
                            links.new(source_socket, tint.inputs[1])
                            links.new(tint.outputs["Color"], base)
                        elif base is not None:
                            base.default_value = (0.30, 0.21, 0.115, 1.0)
                        bsdf.inputs["Roughness"].default_value = 0.56
                        if "Specular IOR Level" in bsdf.inputs:
                            bsdf.inputs["Specular IOR Level"].default_value = 0.24
                        if "Coat Weight" in bsdf.inputs:
                            bsdf.inputs["Coat Weight"].default_value = 0.0
                baked_mesh.materials[material_index] = adapted
        for polygon in baked_mesh.polygons:
            polygon.use_smooth = True
        hair_meshes.append(hair)
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)

    body_points = [vertex.co.copy() for vertex in body.data.vertices]
    top = max(point.z for point in body_points)
    head_points = [point for point in body_points if point.z > top - 2.35]
    crown_points = [point for point in body_points if point.z > top - 0.90]
    if not head_points or not crown_points:
        raise RuntimeError("Robert skull landmark selection produced no points")
    target_min = Vector(
        tuple(min(point[axis] for point in head_points) for axis in range(3))
    )
    target_max = Vector(
        tuple(max(point[axis] for point in head_points) for axis in range(3))
    )
    crown_min = Vector(
        tuple(min(point[axis] for point in crown_points) for axis in range(3))
    )
    crown_max = Vector(
        tuple(max(point[axis] for point in crown_points) for axis in range(3))
    )
    source_min, source_max = world_bounds(hair_meshes)
    source_extent = source_max - source_min
    source_center = (source_min + source_max) * 0.5
    target_extent = target_max - target_min
    crown_extent = crown_max - crown_min

    scale_x = target_extent.x * 1.08 / source_extent.x
    raw_scale_y = crown_extent.y * 1.14 / source_extent.y
    scale_y = max(scale_x * 0.92, min(scale_x * 1.16, raw_scale_y))
    scale_z = scale_x * 0.92
    target_top = target_max.z + 0.045
    target_center = Vector(
        (
            (target_min.x + target_max.x) * 0.5,
            (crown_min.y + crown_max.y) * 0.5 + 0.025,
            target_top - source_extent.z * scale_z * 0.5,
        )
    )
    translation = target_center - Vector(
        (
            source_center.x * scale_x,
            source_center.y * scale_y,
            source_center.z * scale_z,
        )
    )
    for hair in hair_meshes:
        hair.scale = (scale_x, scale_y, scale_z)
        hair.location = translation
    bpy.context.view_layer.update()

    root = bpy.data.objects.new("Robert_Removable_Static_Hair_Root_V25_R7", None)
    bpy.context.collection.objects.link(root)
    for hair in hair_meshes:
        matrix_world = hair.matrix_world.copy()
        hair.parent = root
        hair.matrix_world = matrix_world
        hair["static_review_component"] = True
        hair["runtime_hair_system_complete"] = False
    root["component_type"] = "REMOVABLE_LICENSED_SHORT_HAIR_STATIC_REVIEW"
    root["runtime_approved"] = False
    root["runtime_hair_system_complete"] = False
    root["component_meshes"] = [hair.name for hair in hair_meshes]
    return [root, *hair_meshes], {
        "method": (
            "evaluated licensed Hair Pack short-hair candidate baked away from "
            "its unrelated source rig and fitted to Robert upper-skull/crown "
            "landmarks with one bounded removable transform"
        ),
        "source_asset_id": "LICENSED_HAIR_PACK_PART_1",
        "source_candidate_objects": list(HAIR_PACK_CANDIDATE_OBJECTS),
        "source_sha256": sha256(HAIR_PACK_REFERENCE),
        "attribution": {
            "title": "Hair Pack (part 1)",
            "author": "rendysix",
            "author_url": "https://sketchfab.com/rendysix",
            "source_url": (
                "https://sketchfab.com/3d-models/"
                "hair-pack-part-1-41f1709e39e24a3fafdbcd2c2aac72a1"
            ),
            "license": "CC-BY-4.0",
            "license_url": "http://creativecommons.org/licenses/by/4.0/",
            "adaptation_notice": (
                "authored hair and companion coverage meshes evaluated together "
                "in their rest pose with alpha materials preserved, source rig "
                "removed, jointly fitted to Robert skull landmarks, and tinted "
                "natural dark blond; no runtime-groom claim"
            ),
        },
        "visible_mesh_count": len(hair_meshes),
        "fit_scale_x": scale_x,
        "fit_scale_y": scale_y,
        "fit_scale_z": scale_z,
        "raw_depth_scale": raw_scale_y,
        "target_top": target_top,
        "root_underlay": None,
        "runtime_hair_complete": False,
        "review_scope": "STATIC_LIKENESS_ONLY",
    }


def add_static_eyebrows(
    eye_bounds: dict[str, dict[str, list[float]]],
    material: bpy.types.Material,
) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []
    for eye_name, row in eye_bounds.items():
        center = Vector(row["center"])
        sign = 1.0 if center.x > 0 else -1.0
        data = bpy.data.curves.new(f"{eye_name}_Eyebrow_Data", "CURVE")
        data.dimensions = "3D"
        data.bevel_depth = 0.018
        data.bevel_resolution = 3
        spline = data.splines.new("BEZIER")
        spline.bezier_points.add(2)
        for point, position in zip(
            spline.bezier_points,
            (
                Vector((center.x - sign * 0.17, center.y - 0.20, center.z + 0.23)),
                Vector((center.x, center.y - 0.225, center.z + 0.27)),
                Vector((center.x + sign * 0.18, center.y - 0.19, center.z + 0.22)),
            ),
        ):
            point.co = position
            point.handle_left_type = "AUTO"
            point.handle_right_type = "AUTO"
        eyebrow = bpy.data.objects.new(f"{eye_name}_Natural_Dark_Blond_Eyebrow", data)
        bpy.context.collection.objects.link(eyebrow)
        eyebrow.data.materials.append(material)
        objects.append(eyebrow)
    return objects


def object_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[axis] for point in points) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in points) for axis in range(3))),
    )


def world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    corners: list[Vector] = []
    for obj in objects:
        corners.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    return (
        Vector(tuple(min(point[axis] for point in corners) for axis in range(3))),
        Vector(tuple(max(point[axis] for point in corners) for axis in range(3))),
    )


def add_static_hair(
    body: bpy.types.Object, material: bpy.types.Material
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    """Add a removable layered static groom, explicitly not runtime hair."""

    coordinates = [vertex.co.copy() for vertex in body.data.vertices]
    normals = [vertex.normal.copy() for vertex in body.data.vertices]
    top = max(point.z for point in coordinates)
    selected_indices = [
        index
        for index, point in enumerate(coordinates)
        if (
            point.z > top - 0.65
            or (point.z > top - 1.45 and point.y > -0.35)
            or (
                point.z > top - 1.25
                and abs(point.x) > 0.65
                and point.y > -0.90
            )
        )
    ]
    selected_set = set(selected_indices)

    scalp_mesh = bpy.data.meshes.new("Robert_Removable_Static_Scalp_Base_V25")
    scalp_vertices: list[tuple[float, float, float]] = []
    scalp_faces: list[tuple[int, ...]] = []
    remap: dict[int, int] = {}
    for polygon in body.data.polygons:
        indices = list(polygon.vertices)
        if all(index in selected_set for index in indices):
            face: list[int] = []
            for index in indices:
                if index not in remap:
                    remap[index] = len(scalp_vertices)
                    point = coordinates[index] + normals[index] * 0.055
                    scalp_vertices.append(tuple(point))
                face.append(remap[index])
            scalp_faces.append(tuple(face))
    scalp_mesh.from_pydata(scalp_vertices, [], scalp_faces)
    scalp_mesh.update(calc_edges=True)
    scalp = bpy.data.objects.new("Robert_Removable_Static_Scalp_Base_V25", scalp_mesh)
    bpy.context.collection.objects.link(scalp)
    scalp.data.materials.append(material)
    for polygon in scalp.data.polygons:
        polygon.use_smooth = True
    solidify = scalp.modifiers.new("StaticScalpLayerThickness", "SOLIDIFY")
    solidify.thickness = 0.014
    solidify.offset = 1.0
    subdivision = scalp.modifiers.new("StaticScalpSmooth", "SUBSURF")
    subdivision.levels = 1
    subdivision.render_levels = 1

    # Deterministic strand sampling across crown, temple, sides, and rear.
    randomizer = random.Random(20260730)
    candidates = selected_indices[:]
    randomizer.shuffle(candidates)
    roots = candidates[: min(72, len(candidates))]
    curve_data = bpy.data.curves.new("Robert_Dark_Blond_Layered_Strands_V25", "CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 1
    curve_data.bevel_depth = 0.0035
    curve_data.bevel_resolution = 2
    curve_data.resolution_u = 2
    for index in roots:
        root = coordinates[index] + normals[index] * 0.05
        relative_top = max(0.0, min(1.0, (root.z - (top - 1.70)) / 1.70))
        side = abs(root.x)
        if root.y < -2.25:
            # Front hairline and fringe flow down and slightly forward.
            flow = Vector((0.12 * math.copysign(1.0, root.x or 1.0), -0.20, -0.62))
        elif side > 0.78:
            # Temple/side coverage prevents a bald side silhouette.
            flow = Vector((0.08 * math.copysign(1.0, root.x), 0.03, -0.72))
        elif root.y > -1.05:
            # Rear coverage follows the skull downward.
            flow = Vector((0.05 * math.copysign(1.0, root.x or 1.0), 0.18, -0.70))
        else:
            # Crown is brushed primarily forward with a soft side part.
            flow = Vector((0.20 * math.copysign(1.0, root.x or 1.0), -0.46, -0.25))
        flow.normalize()
        length = 0.075 + 0.105 * relative_top + randomizer.uniform(-0.012, 0.018)
        spline = curve_data.splines.new("BEZIER")
        spline.bezier_points.add(2)
        positions = (
            root,
            root + normals[index] * 0.035 + flow * (length * 0.48),
            root + normals[index] * 0.025 + flow * length,
        )
        for point, position in zip(spline.bezier_points, positions):
            point.co = position
            point.handle_left_type = "AUTO"
            point.handle_right_type = "AUTO"
        spline.resolution_u = 2
    strands = bpy.data.objects.new("Robert_Dark_Blond_Layered_Strands_V25", curve_data)
    bpy.context.collection.objects.link(strands)
    strands.data.materials.append(material)
    return [scalp, strands], {
        "method": "removable_layered_static_scalp_plus_curve_strands",
        "strand_count": len(roots),
        "scalp_vertices": len(scalp_vertices),
        "scalp_faces": len(scalp_faces),
        "runtime_hair_complete": False,
        "review_scope": "STATIC_LIKENESS_ONLY",
    }


def create_nail(
    name: str,
    center: Vector,
    finger_direction: Vector,
    surface_normal: Vector,
    material: bpy.types.Material,
    *,
    thumb: bool,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        location=center,
    )
    nail = bpy.context.object
    nail.name = name
    tangent_long = finger_direction - surface_normal * finger_direction.dot(
        surface_normal
    )
    if tangent_long.length < 1e-6:
        tangent_long = Vector((0.0, 0.0, 1.0))
    tangent_long.normalize()
    tangent_width = surface_normal.cross(tangent_long).normalized()
    nail.rotation_euler = Matrix(
        (tangent_width, surface_normal, tangent_long)
    ).transposed().to_euler()
    nail.scale = (0.050 if thumb else 0.042, 0.0045, 0.092 if thumb else 0.080)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    nail.data.materials.append(material)
    for polygon in nail.data.polygons:
        polygon.use_smooth = True
    return nail


def add_static_nails(
    body: bpy.types.Object,
    vertices: list[Vector],
    groups: dict[str, list[tuple[int, ...]]],
    material: bpy.types.Material,
) -> tuple[list[bpy.types.Object], dict[str, object]]:
    nails: list[bpy.types.Object] = []
    centers: dict[str, list[float]] = {}
    for side in ("l", "r"):
        for finger in range(1, 6):
            group_name = f"joint-{side}-finger-{finger}-4"
            previous_group_name = f"joint-{side}-finger-{finger}-3"
            faces = groups.get(group_name)
            previous_faces = groups.get(previous_group_name)
            if not faces or not previous_faces:
                continue
            indices = sorted({index for face in faces for index in face})
            center_source = sum((vertices[index] for index in indices), Vector()) / len(indices)
            previous_indices = sorted(
                {index for face in previous_faces for index in face}
            )
            previous_source = (
                sum((vertices[index] for index in previous_indices), Vector())
                / len(previous_indices)
            )
            tip = blender_point(center_source)
            previous = blender_point(previous_source)
            finger_direction = (tip - previous).normalized()
            # Locate the actual dorsal distal-phalanx surface rather than
            # floating a cap at the joint landmark.
            dorsal_axis = tip - finger_direction * (
                0.145 if finger == 1 else 0.120
            )
            local_candidates = [
                vertex
                for vertex in body.data.vertices
                if (vertex.co - dorsal_axis).length <= (
                    0.230 if finger == 1 else 0.185
                )
            ]
            if not local_candidates:
                continue
            # In the MakeHuman rest pose +Y is the dorsal surface visible in
            # the dedicated rear-hand review camera.
            nearest = max(local_candidates, key=lambda vertex: vertex.co.y)
            surface_normal = nearest.normal.normalized()
            if surface_normal.y < 0.0:
                surface_normal.negate()
            center = nearest.co + surface_normal * 0.003
            nail = create_nail(
                f"Robert_{side.upper()}_Finger_{finger}_Static_Nail_V25",
                center,
                finger_direction,
                surface_normal,
                material,
                thumb=finger == 1,
            )
            nails.append(nail)
            centers[group_name] = [float(value) for value in center]
    return nails, {
        "method": "static_review_nails_at_makehuman_distal_finger_landmarks",
        "count": len(nails),
        "landmark_centers": centers,
        "motion_validated": False,
    }


def assign_regional_materials(
    body: bpy.types.Object,
    skin: bpy.types.Material,
    transformed_source_vertices: list[Vector],
    source_report: dict[str, object],
) -> dict[str, object]:
    body.data.materials.clear()
    body.data.materials.append(skin)

    lip_indices: set[int] = set()
    for row in source_report.get("targets", []):
        target_path = Path(str(row["path"]))
        if target_path.name not in {
            "mouth-lowerlip-volume-incr.target",
            "mouth-upperlip-volume-incr.target",
        }:
            continue
        with target_path.open("r", encoding="utf-8") as stream:
            for raw in stream:
                fields = raw.split()
                if len(fields) == 4 and not fields[0].startswith("#"):
                    lip_indices.add(int(fields[0]))
    lip_points = [blender_point(transformed_source_vertices[index]) for index in lip_indices]
    lip_min = Vector(
        tuple(min(point[axis] for point in lip_points) for axis in range(3))
    )
    lip_max = Vector(
        tuple(max(point[axis] for point in lip_points) for axis in range(3))
    )
    lip_min -= Vector((0.025, 0.025, 0.025))
    lip_max += Vector((0.025, 0.025, 0.025))

    coordinates = [vertex.co for vertex in body.data.vertices]
    top = max(point.z for point in coordinates)
    bottom = min(point.z for point in coordinates)
    height = top - bottom
    chest_low = bottom + height * 0.665
    chest_high = bottom + height * 0.755
    side_points: dict[int, Vector] = {}
    for sign in (-1, 1):
        candidates = [
            point
            for point in coordinates
            if chest_low <= point.z <= chest_high
            and 0.45 <= abs(point.x) <= 2.0
            and math.copysign(1.0, point.x) == sign
        ]
        side_points[sign] = min(candidates, key=lambda point: point.y).copy()

    for polygon in body.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True

    genital_indices: set[int] = set()
    for row in source_report.get("targets", []):
        target_path = Path(str(row["path"]))
        if target_path.parent.name != "genitals":
            continue
        with target_path.open("r", encoding="utf-8") as stream:
            for raw in stream:
                fields = raw.split()
                if len(fields) == 4 and not fields[0].startswith("#"):
                    genital_indices.add(int(fields[0]))
    genital_points = [
        blender_point(transformed_source_vertices[index])
        for index in genital_indices
    ]
    genital_min = Vector(
        tuple(min(point[axis] for point in genital_points) for axis in range(3))
    )
    genital_max = Vector(
        tuple(max(point[axis] for point in genital_points) for axis in range(3))
    )

    local_min, local_max = object_bounds(body)
    local_extent = local_max - local_min

    def generated(point: Vector) -> Vector:
        return Vector(
            tuple(
                (point[axis] - local_min[axis]) / local_extent[axis]
                for axis in range(3)
            )
        )

    nodes = skin.node_tree.nodes
    links = skin.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    base_ramp = nodes.get("Natural_Skin_Color_Range")
    if bsdf is None or base_ramp is None:
        raise RuntimeError("skin material did not expose expected nodes")
    for link in list(bsdf.inputs["Base Color"].links):
        links.remove(link)
    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.name = "Regional_Mask_Generated_Coordinates"
    color_output = base_ramp.outputs["Color"]

    def distance_mask(
        name: str,
        center: Vector,
        radius: float,
    ) -> bpy.types.NodeSocket:
        distance = nodes.new("ShaderNodeVectorMath")
        distance.name = f"{name}_Distance"
        distance.operation = "DISTANCE"
        distance.inputs[1].default_value = center
        links.new(texcoord.outputs["Generated"], distance.inputs[0])
        mapping = nodes.new("ShaderNodeMapRange")
        mapping.name = f"{name}_Soft_Mask"
        mapping.clamp = True
        mapping.inputs["From Min"].default_value = 0.0
        mapping.inputs["From Max"].default_value = radius
        mapping.inputs["To Min"].default_value = 1.0
        mapping.inputs["To Max"].default_value = 0.0
        links.new(distance.outputs["Value"], mapping.inputs["Value"])
        return mapping.outputs["Result"]

    def mix_region(
        name: str,
        mask: bpy.types.NodeSocket,
        color: tuple[float, float, float, float],
    ) -> None:
        nonlocal color_output
        mix = nodes.new("ShaderNodeMixRGB")
        mix.name = f"{name}_Smooth_Color_Mix"
        mix.blend_type = "MIX"
        mix.inputs["Color2"].default_value = color
        links.new(mask, mix.inputs["Fac"])
        links.new(color_output, mix.inputs["Color1"])
        color_output = mix.outputs["Color"]

    lip_center = generated((lip_min + lip_max) * 0.5)
    mix_region(
        "Natural_Lips",
        distance_mask("Natural_Lips", lip_center, 0.030),
        (0.40, 0.17, 0.145, 1.0),
    )
    nipple_masks = []
    for side, nipple_center in side_points.items():
        nipple_masks.append(
            distance_mask(
                f"Natural_Nipple_{side}",
                generated(nipple_center),
                0.022,
            )
        )
    nipple_max = nodes.new("ShaderNodeMath")
    nipple_max.name = "Natural_Nipples_Combined_Mask"
    nipple_max.operation = "MAXIMUM"
    links.new(nipple_masks[0], nipple_max.inputs[0])
    links.new(nipple_masks[1], nipple_max.inputs[1])
    mix_region(
        "Natural_Nipples",
        nipple_max.outputs["Value"],
        (0.41, 0.205, 0.165, 1.0),
    )
    genital_center = generated((genital_min + genital_max) * 0.5)
    genital_extent_generated = generated(genital_max) - generated(genital_min)
    genital_radius = max(genital_extent_generated) * 0.62
    mix_region(
        "Natural_Genital_Region",
        distance_mask(
            "Natural_Genital_Region",
            genital_center,
            genital_radius,
        ),
        (0.46, 0.235, 0.195, 1.0),
    )
    links.new(color_output, bsdf.inputs["Base Color"])
    return {
        "assignment_method": (
            "single continuous skin material with smooth generated-coordinate "
            "regional masks; no polygon color patches"
        ),
        "body_material_slots": 1,
        "lip_bbox_min": [float(value) for value in lip_min],
        "lip_bbox_max": [float(value) for value in lip_max],
        "left_nipple_center": [float(value) for value in side_points[-1]],
        "right_nipple_center": [float(value) for value in side_points[1]],
        "genital_bbox_min": [float(value) for value in genital_min],
        "genital_bbox_max": [float(value) for value in genital_max],
        "smooth_mask_radii_generated": {
            "lips": 0.030,
            "nipples": 0.022,
            "genital_region": genital_radius,
        },
    }


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def render(
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
    look_at(camera, target)
    scene.camera = camera
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def rendered_subject_fraction(path: Path, *, stride: int = 24) -> float:
    """Measure whether a rendered frame contains content beyond the background.

    This is deliberately a coarse fail-closed delivery check. It catches
    camera/bounds failures that otherwise create valid but blank PNG files.
    It is not a visual-likeness approval.
    """

    image = bpy.data.images.load(str(path), check_existing=False)
    width, height = image.size
    pixels = image.pixels[:]
    corner_index = ((height - 1) * width) * 4
    background = (
        pixels[corner_index],
        pixels[corner_index + 1],
        pixels[corner_index + 2],
    )
    sampled = 0
    changed = 0
    for y in range(0, height, stride):
        for x in range(0, width, stride):
            index = (y * width + x) * 4
            delta = max(
                abs(pixels[index + channel] - background[channel])
                for channel in range(3)
            )
            sampled += 1
            if delta > 0.035:
                changed += 1
    bpy.data.images.remove(image)
    return changed / max(sampled, 1)


def setup_scene() -> tuple[bpy.types.Scene, bpy.types.Object]:
    for obj in list(bpy.context.scene.objects):
        if obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.055, 0.060, 0.070)
    scene.view_settings.look = "AgX - Medium Low Contrast"
    for name, energy, direction, angle in (
        ("NeutralFrontSun", 2.0, (0.0, -1.0, 0.45), 0.45),
        ("NeutralLeftSun", 1.1, (-0.8, -0.35, 0.35), 0.55),
        ("NeutralRightSun", 0.85, (0.8, -0.25, 0.25), 0.55),
        ("NeutralRearSun", 0.65, (0.0, 0.9, 0.30), 0.60),
    ):
        light_data = bpy.data.lights.new(name, "SUN")
        light_data.energy = energy
        light_data.angle = angle
        light = bpy.data.objects.new(name, light_data)
        bpy.context.collection.objects.link(light)
        light.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    camera_data = bpy.data.cameras.new("ProtectedStaticReviewCamera_V25")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("ProtectedStaticReviewCamera_V25", camera_data)
    bpy.context.collection.objects.link(camera)
    return scene, camera


def private_reference_manifest() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for directory, id_prefix, purpose in (
        (
            PRIVATE_NEW_REFERENCE,
            "ROBERT_PRIVATE_PLACEMENT_REF",
            "Robert-specific placement and local likeness guidance",
        ),
        (
            PRIVATE_BASE_REFERENCE,
            "ROBERT_PRIVATE_BASE_REF",
            "Robert-specific face, body, hair, hand, and skin guidance",
        ),
    ):
        if not directory.is_dir():
            continue
        accepted = [
            path
            for path in sorted(directory.iterdir())
            if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
        ]
        for number, path in enumerate(accepted, start=1):
            rows.append(
                {
                    "opaque_reference_id": f"{id_prefix}_{number:03d}",
                    "sha256": sha256(path),
                    "purpose": purpose,
                    "copied_into_project": False,
                    "deletion_state": (
                        "PRESERVED UNTIL EXPLICIT OWNER APPROVAL; DO NOT DELETE YET"
                    ),
                }
            )
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source_report = json.loads(SOURCE_REPORT.read_text(encoding="utf-8"))
    face_landmark_comparison = json.loads(
        FACE_LANDMARK_COMPARISON.read_text(encoding="utf-8")
    )
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))
    bodies = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and "MakeHuman" in obj.name
    ]
    if len(bodies) != 1:
        raise RuntimeError(f"expected one clean MakeHuman body, found {[obj.name for obj in bodies]}")
    body = bodies[0]
    body.name = "Biological_Robert_Static_V25_R7_Body"

    source_vertices, source_groups = parse_obj_groups(MAKEHUMAN_BASE)
    for row in source_report["targets"]:
        apply_target(source_vertices, Path(row["path"]), float(row["weight"]))
    face_fit_report = apply_private_face_geometry_fit(body, source_vertices)

    skin = skin_material()
    regional_report = assign_regional_materials(
        body, skin, source_vertices, source_report
    )

    sclera = material_principled(
        "Robert_Natural_Sclera_V25", (0.48, 0.455, 0.43, 1.0), roughness=0.42
    )
    iris = material_principled(
        "Robert_Actual_Natural_Blue_Iris_V25",
        (0.018, 0.040, 0.065, 1.0),
        roughness=0.38,
    )
    pupil = material_principled(
        "Robert_Natural_Pupil_V25", (0.003, 0.004, 0.006, 1.0), roughness=0.22
    )
    # Use a stable local skin material for the tiny review-only lid meshes.
    # Reusing the full-body Generated-coordinate noise shader made each small
    # lid sample a different part of the ramp and rendered both as muddy dark
    # bands.  This is a bounded presentation fix, not a separate facial skin.
    eyelid_skin = material_principled(
        "Robert_Static_Eyelid_Skin_V25",
        (0.43, 0.235, 0.175, 1.0),
        roughness=0.56,
        subsurface=0.07,
    )
    eye_objects: list[bpy.types.Object] = []
    eye_report: dict[str, object] = {
        "iris_color_source": "protected Robert reference photographs",
        "actual_iris_material": iris.name,
        "lighting_only_color": False,
        "eyes": {},
    }
    for group_name, public_name in (
        ("helper-l-eye", "Robert_Left_Eye_V25"),
        ("helper-r-eye", "Robert_Right_Eye_V25"),
    ):
        eye, overlays, bounds_report = create_eye_group(
            public_name,
            source_vertices,
            source_groups[group_name],
            sclera,
            iris,
            pupil,
            eyelid_skin,
        )
        eye_objects.extend([eye, *overlays])
        eye_report["eyes"][public_name] = bounds_report

    static_hair_material = hair_material()
    if HAIR_FROZEN_FOR_FACE_REPAIR:
        hair_objects: list[bpy.types.Object] = []
        hair_report: dict[str, object] = {
            "status": "FROZEN_AFTER_INCOMPATIBLE_ASSET_REJECTION",
            "rendered_in_face_repair_preview": False,
            "reason": (
                "licensed layered cut read as chunky helmet/shag; Hair Pack "
                "candidate and authored companion produced an opaque bald dome"
            ),
            "next_action": (
                "select or build a clean removable static style only after "
                "face geometry and eye seating pass focused review"
            ),
            "runtime_hair_complete": False,
        }
    else:
        hair_objects, hair_report = add_hair_pack_static_hair(
            body, static_hair_material
        )
    eyebrow_objects = add_static_eyebrows(
        eye_report["eyes"], static_hair_material
    )
    nail_material = material_principled(
        "Robert_Natural_Fingernail_V25",
        (0.48, 0.285, 0.255, 1.0),
        roughness=0.38,
        subsurface=0.035,
    )
    nail_objects, nail_report = add_static_nails(
        body, source_vertices, source_groups, nail_material
    )

    scene, camera = setup_scene()
    review_objects = [
        body,
        *eye_objects,
        *hair_objects,
        *eyebrow_objects,
        *nail_objects,
    ]
    # Imported hair packages can contain armatures, roots, and other
    # non-renderable objects with very large default bound boxes. Those
    # objects must remain in the saved hair component but must never influence
    # review-camera framing.
    review_objects = [
        obj
        for obj in review_objects
        if obj.type in {"MESH", "CURVE"} and not obj.hide_render
    ]
    minimum, maximum = world_bounds(review_objects)
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    width = maximum.x - minimum.x
    depth = maximum.y - minimum.y
    distance = max(height, width, depth) * 2.0
    full_scale = max(height * 1.08, width * 1.55)
    face_target = Vector((0.0, center.y - 0.35, maximum.z - height * 0.075))
    hair_target = Vector((0.0, center.y, maximum.z - height * 0.055))
    pelvis_target = Vector((0.0, center.y - 0.05, minimum.z + height * 0.485))
    left_hand = Vector((minimum.x + width * 0.06, center.y, minimum.z + height * 0.57))
    right_hand = Vector((maximum.x - width * 0.06, center.y, minimum.z + height * 0.57))

    views = {
        "full_front.png": (
            Vector((center.x, minimum.y - distance, center.z)),
            center,
            full_scale,
        ),
        "full_rear.png": (
            Vector((center.x, maximum.y + distance, center.z)),
            center,
            full_scale,
        ),
        "left_profile.png": (
            Vector((minimum.x - distance, center.y, center.z)),
            center,
            full_scale,
        ),
        "right_profile.png": (
            Vector((maximum.x + distance, center.y, center.z)),
            center,
            full_scale,
        ),
        "left_three_quarter.png": (
            Vector((center.x - distance * 0.72, minimum.y - distance * 0.72, center.z)),
            center,
            full_scale,
        ),
        "right_three_quarter.png": (
            Vector((center.x + distance * 0.72, minimum.y - distance * 0.72, center.z)),
            center,
            full_scale,
        ),
        "face_front_close.png": (
            Vector((face_target.x, minimum.y - distance, face_target.z)),
            face_target,
            height * 0.245,
        ),
        "face_left_three_quarter_close.png": (
            Vector(
                (
                    face_target.x - distance * 0.70,
                    minimum.y - distance * 0.70,
                    face_target.z,
                )
            ),
            face_target,
            height * 0.245,
        ),
        "hair_front_close.png": (
            Vector((hair_target.x, minimum.y - distance, hair_target.z)),
            hair_target,
            height * 0.255,
        ),
        "hair_left_profile_close.png": (
            Vector((minimum.x - distance, hair_target.y, hair_target.z)),
            hair_target,
            height * 0.255,
        ),
        "hair_rear_close.png": (
            Vector((hair_target.x, maximum.y + distance, hair_target.z)),
            hair_target,
            height * 0.255,
        ),
        "hair_crown_close.png": (
            Vector((hair_target.x, hair_target.y, maximum.z + distance)),
            hair_target,
            height * 0.255,
        ),
        "pelvis_front_protected.png": (
            Vector((pelvis_target.x, minimum.y - distance, pelvis_target.z)),
            pelvis_target,
            height * 0.29,
        ),
        "pelvis_side_protected.png": (
            Vector((minimum.x - distance, pelvis_target.y, pelvis_target.z)),
            pelvis_target,
            height * 0.29,
        ),
        "pelvis_three_quarter_protected.png": (
            Vector(
                (
                    pelvis_target.x - distance * 0.72,
                    minimum.y - distance * 0.72,
                    pelvis_target.z,
                )
            ),
            pelvis_target,
            height * 0.29,
        ),
        "left_hand_dorsal_close.png": (
            Vector((left_hand.x, maximum.y + distance, left_hand.z)),
            left_hand,
            height * 0.13,
        ),
        "right_hand_dorsal_close.png": (
            Vector((right_hand.x, maximum.y + distance, right_hand.z)),
            right_hand,
            height * 0.13,
        ),
    }
    if PREVIEW_ONLY:
        preview_names = {
            "face_front_close.png",
            "face_left_three_quarter_close.png",
        }
        views = {
            name: parameters
            for name, parameters in views.items()
            if name in preview_names
        }
    for filename, (location, target, scale) in views.items():
        render(
            scene,
            camera,
            OUT / filename,
            location=location,
            target=target,
            scale=scale,
        )
    subject_fractions = {
        filename: rendered_subject_fraction(OUT / filename)
        for filename in views
    }
    render_delivery_pass = all(
        fraction >= 0.01 for fraction in subject_fractions.values()
    )

    wireframe_views: dict[str, str] = {}
    if not PREVIEW_ONLY:
        # A separate wireframe overlay corroborates that the protected local
        # region is one connected surface; it is evidence, not a substitute
        # for the ordinary-view visual gate.
        wire = body.copy()
        wire.data = body.data.copy()
        wire.name = "Biological_Robert_V25_R7_Topology_Wire_Overlay"
        bpy.context.collection.objects.link(wire)
        for modifier in list(wire.modifiers):
            wire.modifiers.remove(modifier)
        wire.data.materials.clear()
        wire_material = material_principled(
            "Robert_Topology_Diagnostic_Cyan_V25",
            (0.01, 0.30, 0.38, 1.0),
            roughness=0.35,
        )
        wire.data.materials.append(wire_material)
        wire_modifier = wire.modifiers.new("ProtectedTopologyWire", "WIREFRAME")
        wire_modifier.thickness = 0.004
        wire_modifier.offset = 1.0
        wire_modifier.use_replace = True
        for filename, location in (
            (
                "pelvis_front_wireframe.png",
                Vector((pelvis_target.x, minimum.y - distance, pelvis_target.z)),
            ),
            (
                "pelvis_side_wireframe.png",
                Vector((minimum.x - distance, pelvis_target.y, pelvis_target.z)),
            ),
        ):
            render(
                scene,
                camera,
                OUT / filename,
                location=location,
                target=pelvis_target,
                scale=height * 0.29,
            )
            wireframe_views[filename] = str(OUT / filename)
        bpy.data.objects.remove(wire, do_unlink=True)

    body_topology = topology(body)
    topology_pass = (
        body_topology["connected_components"] == 1
        and body_topology["boundary_edges"] == 0
        and body_topology["nonmanifold_internal_edges"] == 0
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(FINAL_BLEND))
    reference_manifest = private_reference_manifest()
    report = {
        "schema": "kira.avatar.biological_robert.static_review.v25.r7",
        "status": STATUS if render_delivery_pass else REJECTED_STATUS,
        "owner_approved": False,
        "static_review_only": True,
        "runtime_ready": False,
        "movement_validated": False,
        "activation_allowed": False,
        "source_foundation": str(SOURCE_BLEND),
        "source_foundation_sha256": sha256(SOURCE_BLEND),
        "final_blend": str(FINAL_BLEND),
        "final_blend_sha256": sha256(FINAL_BLEND),
        "generic_method_separated_from_private_parameters": True,
        "estimate_label": ESTIMATE_LABEL,
        "private_reference_policy": {
            "used_for": (
                "Robert-specific placement, likeness, body proportion, hair, "
                "hand, skin, and color guidance only"
            ),
            "copied_into_candidate": False,
            "delete_now": False,
            "deletion_gate": "EXPLICIT OWNER APPROVAL AFTER BODY ACCEPTANCE",
            "files": reference_manifest,
        },
        "shape_targets": source_report["targets"],
        "face_landmark_comparison": {
            "path": str(FACE_LANDMARK_COMPARISON),
            "sha256": sha256(FACE_LANDMARK_COMPARISON),
            "status": face_landmark_comparison["status"],
            "method": face_landmark_comparison["method"],
            "inputs": face_landmark_comparison["inputs"],
            "bounded_front_landmark_goals": face_landmark_comparison[
                "bounded_front_landmark_goals"
            ],
            "profile_constraints": face_landmark_comparison[
                "profile_constraints"
            ],
        },
        "private_face_geometry_fit": face_fit_report,
        "body_direction": (
            "bounded medium-heavy fit, deliberately somewhat thinner than the "
            "protected biological references, not athletic or skinny"
        ),
        "topology": body_topology,
        "topology_gate": "PASS" if topology_pass else "FAIL",
        "render_delivery_gate": {
            "decision": "PASS" if render_delivery_pass else "FAIL",
            "minimum_non_background_fraction": 0.01,
            "measured_non_background_fractions": subject_fractions,
            "meaning": (
                "delivery/camera sanity only; this does not approve visual "
                "likeness or anatomy"
            ),
        },
        "regional_material_assignment": regional_report,
        "eyes": eye_report,
        "hair": hair_report,
        "eyebrows": {
            "method": "separate removable static curve components",
            "count": len(eyebrow_objects),
            "runtime_approved": False,
        },
        "hands_and_nails": nail_report,
        "review_views": {name: str(OUT / name) for name in views},
        "wireframe_views": wireframe_views,
        "engineering_preview_only": PREVIEW_ONLY,
        "scope_blocks": [
            "movement",
            "runtime attachment",
            "activation",
            "Synthetic Robert duplication",
            "Kira body work",
            "clothing",
            "Kira World integration",
        ],
        "honest_limitations": [
            "The face uses measured/manual authorized-reference goals and explicit bounded geometry deltas; it is not a photogrammetry reconstruction or final likeness approval.",
            "Hair is frozen after incompatible static-asset failures and is intentionally absent from the focused face-repair preview.",
            "Nails are static review components and require later rig/contact validation after static approval.",
            "Adult anatomy form and root continuity are static-only; soft-tissue behavior is deferred to Stage B after owner approval.",
        ],
    }
    (SOURCE_DIR / "BIOLOGICAL_ROBERT_V25_R7_STATIC_REVIEW_REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
