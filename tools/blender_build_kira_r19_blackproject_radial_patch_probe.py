#!/usr/bin/env python3
"""Author a sealed R19 BlackProject adult-surface topology probe.

This Blender worker is intentionally narrow.  It imports the exact enrolled
CC BY 4.0 BlackProject adult-female foundation, reads only the source adult
component's reviewed 34-vertex boundary and boundary weights, discards every
source interior vertex and face, and fills the opening with new concentric
rings plus a pole-free quad strip.  It writes only an append-only private
diagnostic package; it never selects, assigns, activates, publishes, or edits
an earlier candidate or runtime asset.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_author_kira_r7_adult_surface_trial as audit_helpers  # noqa: E402
import blender_build_kira_temporary_functional_body_blackproject as legacy_builder  # noqa: E402
from blender_exact_mesh_intersections import (  # noqa: E402
    exact_nonadjacent_intersection_report,
)


SOURCE_REL = Path(
    "Avatar/avatar_builder/asset_library/base_body_reference/"
    "base_female_character_blackproject_cc_by_4.glb"
)
AUTHORITY_REL = Path(
    "Avatar/avatar_builder/asset_library/base_body_reference/"
    "base_female_character_blackproject_cc_by_4.authority.json"
)
OUTPUT_REL = Path(
    "RecoverySprint/continuation_20260802/"
    "r19_blackproject_radial_patch/attempt_01"
)
SOURCE_SHA256 = "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"
AUTHORITY_SHA256 = "d632a501edb2177aed7299aa257b61784685bdf2d9c88fa280370b640c4b508c"
BOUNDARY_VERTEX_COUNT = 34
RING_SCALES = (1.0, 0.86, 0.72, 0.58, 0.44, 0.30, 0.16)
WELD_TOLERANCE_M = 1.0e-7

PRIMARY_BASE_MESHES = (
    "Ariel_Mesh_Torso_0",
    "Ariel_Mesh_Arms_0",
    "Ariel_Mesh_Legs_0",
    "Ariel_Mesh_Face_0",
    "Ariel_Mesh_Ears_0",
)
SUPPORT_MESHES = (
    "Ariel_Mesh_Lips_0",
    "Ariel_Mesh_Teeth_0",
    "Ariel_Mesh_EyeSocket_0",
    "Ariel_Mesh_Mouth_0",
    "Ariel_Mesh_Pupils_0",
    "Ariel_Mesh_EyeMoisture_0",
    "Ariel_Mesh_Cornea_0",
    "Ariel_Mesh_Irises_0",
    "Ariel_Mesh_Sclera_0",
    "Ariel_Mesh_Fingernails_0",
    "Ariel_Mesh_Toenails_0",
    "Eye_Brows_Brows02_0.001",
    "Eye_Lahes_EyeMoisture_0",
)
SOURCE_PATCH_MESH = "Ariel_Mesh_Genitalia_0"
KEEP_MESHES = set(PRIMARY_BASE_MESHES) | set(SUPPORT_MESHES) | {SOURCE_PATCH_MESH}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def vec_record(value: Vector) -> list[float]:
    return [round(float(component), 9) for component in value]


def normalized_top_four(weights: dict[str, float]) -> dict[str, float]:
    selected = sorted(
        ((name, float(value)) for name, value in weights.items() if value > 1.0e-10),
        key=lambda item: (-item[1], item[0]),
    )[:4]
    total = sum(value for _name, value in selected)
    if total <= 1.0e-12:
        raise ValueError("a radial patch vertex has no transferable boundary weight")
    return {name: value / total for name, value in selected}


def source_vertex_weights(obj: bpy.types.Object, vertex_index: int) -> dict[str, float]:
    result: dict[str, float] = {}
    for assignment in obj.data.vertices[vertex_index].groups:
        value = float(assignment.weight)
        if value > 1.0e-10:
            result[obj.vertex_groups[assignment.group].name] = value
    return normalized_top_four(result)


def weighted_mean(records: list[dict[str, float]]) -> dict[str, float]:
    totals: defaultdict[str, float] = defaultdict(float)
    for record in records:
        for name, value in record.items():
            totals[name] += value
    scale = 1.0 / float(len(records))
    return normalized_top_four({name: value * scale for name, value in totals.items()})


def blended_weights(
    boundary: dict[str, float],
    mean: dict[str, float],
    radial_scale: float,
) -> dict[str, float]:
    names = set(boundary) | set(mean)
    return normalized_top_four(
        {
            name: radial_scale * boundary.get(name, 0.0)
            + (1.0 - radial_scale) * mean.get(name, 0.0)
            for name in names
        }
    )


def gaussian(value: float, center: float, sigma: float) -> float:
    return math.exp(-0.5 * ((value - center) / sigma) ** 2)


def landmark_relief(normalized_x: float, longitudinal: float) -> tuple[float, dict[str, float]]:
    """Return subtle external-landmark relief in metres.

    This is a bounded surface-description probe, not an internal reproductive
    model.  Positive values move along the boundary-derived outward normal;
    negative values create shallow external recess cues.
    """

    terms = {
        "broad_mons": 0.0017
        * gaussian(normalized_x, 0.0, 0.62)
        * gaussian(longitudinal, -0.58, 0.34),
        "paired_labia_majora": 0.0025
        * (
            gaussian(normalized_x, -0.27, 0.15)
            + gaussian(normalized_x, 0.27, 0.15)
        )
        * gaussian(longitudinal, 0.02, 0.46),
        "paired_labia_minora": 0.0011
        * (
            gaussian(normalized_x, -0.105, 0.070)
            + gaussian(normalized_x, 0.105, 0.070)
        )
        * gaussian(longitudinal, 0.01, 0.34),
        "hood_clitoral_transition": 0.0009
        * gaussian(normalized_x, 0.0, 0.13)
        * gaussian(longitudinal, -0.30, 0.13),
        "urethral_cue_recess": -0.00045
        * gaussian(normalized_x, 0.0, 0.080)
        * gaussian(longitudinal, -0.08, 0.075),
        "vestibular_opening_recess": -0.00115
        * gaussian(normalized_x, 0.0, 0.105)
        * gaussian(longitudinal, 0.20, 0.14),
        "posterior_fourchette_transition": 0.00045
        * gaussian(normalized_x, 0.0, 0.18)
        * gaussian(longitudinal, 0.47, 0.11),
        "posterior_anal_recess": -0.00085
        * gaussian(normalized_x, 0.0, 0.12)
        * gaussian(longitudinal, 0.76, 0.095),
    }
    return sum(terms.values()), terms


def boundary_long_axis(boundary: list[Vector]) -> Vector:
    """Compute the principal direction in the source Y/Z plane."""

    mean_y = sum(point.y for point in boundary) / len(boundary)
    mean_z = sum(point.z for point in boundary) / len(boundary)
    var_y = sum((point.y - mean_y) ** 2 for point in boundary)
    var_z = sum((point.z - mean_z) ** 2 for point in boundary)
    cov_yz = sum((point.y - mean_y) * (point.z - mean_z) for point in boundary)
    theta = 0.5 * math.atan2(2.0 * cov_yz, var_y - var_z)
    result = Vector((0.0, math.cos(theta), math.sin(theta))).normalized()
    # Positive longitudinal direction runs toward the posterior/underbody.
    if result.y < 0.0:
        result.negate()
    return result


def make_radial_patch(
    source_patch: bpy.types.Object,
    ordered_cycle: list[int],
    collection: bpy.types.Collection,
) -> tuple[bpy.types.Object, dict[str, object]]:
    boundary = [
        source_patch.matrix_world @ source_patch.data.vertices[index].co
        for index in ordered_cycle
    ]
    boundary_weights = [source_vertex_weights(source_patch, index) for index in ordered_cycle]
    mean_weights = weighted_mean(boundary_weights)
    center = sum(boundary, Vector((0.0, 0.0, 0.0))) / len(boundary)
    lateral_axis = Vector((1.0, 0.0, 0.0))
    long_axis = boundary_long_axis(boundary)
    outward = -(lateral_axis.cross(long_axis)).normalized()
    if outward.y > 0.0:
        outward.negate()

    # Make the cycle orientation agree with the outward surface normal.  This
    # changes only traversal order; every exact boundary coordinate remains.
    newell = Vector((0.0, 0.0, 0.0))
    for current, following in zip(boundary, boundary[1:] + boundary[:1]):
        newell.x += (current.y - following.y) * (current.z + following.z)
        newell.y += (current.z - following.z) * (current.x + following.x)
        newell.z += (current.x - following.x) * (current.y + following.y)
    cycle_reversed = newell.dot(outward) < 0.0
    if cycle_reversed:
        boundary.reverse()
        boundary_weights.reverse()

    lateral_half = max(abs((point - center).dot(lateral_axis)) for point in boundary)
    longitudinal_half = max(abs((point - center).dot(long_axis)) for point in boundary)
    if lateral_half <= 0.04 or longitudinal_half <= 0.04:
        raise ValueError("reviewed boundary dimensions unexpectedly collapsed")

    vertices: list[Vector] = []
    weight_records: list[dict[str, float]] = []
    relief_extrema: list[float] = []
    term_extrema: defaultdict[str, list[float]] = defaultdict(list)
    for radial_scale in RING_SCALES:
        seam_taper = math.sin((1.0 - radial_scale) * math.pi * 0.5) ** 2
        # The base bow is boundary-derived and eliminates a planar central
        # plate without borrowing any rejected source-interior coordinate.
        base_bow = 0.0048 * (1.0 - radial_scale * radial_scale)
        for boundary_index, boundary_point in enumerate(boundary):
            point = center.lerp(boundary_point, radial_scale)
            normalized_x = (point - center).dot(lateral_axis) / lateral_half
            longitudinal = (point - center).dot(long_axis) / longitudinal_half
            relief, terms = landmark_relief(normalized_x, longitudinal)
            displacement = base_bow + seam_taper * relief
            vertices.append(point + outward * displacement)
            weight_records.append(
                blended_weights(
                    boundary_weights[boundary_index],
                    mean_weights,
                    radial_scale,
                )
            )
            relief_extrema.append(displacement)
            for name, value in terms.items():
                term_extrema[name].append(seam_taper * value)

    faces: list[tuple[int, ...]] = []
    n = len(boundary)
    for ring_index in range(len(RING_SCALES) - 1):
        outer_start = ring_index * n
        inner_start = (ring_index + 1) * n
        for index in range(n):
            following = (index + 1) % n
            faces.append(
                (
                    outer_start + index,
                    outer_start + following,
                    inner_start + following,
                    inner_start + index,
                )
            )
    mesh = bpy.data.meshes.new("Kira_R19_New_Radial_Adult_Surface_Mesh")
    mesh.from_pydata([tuple(point) for point in vertices], [], faces)
    # Close the small innermost ring with Blender's structured grid topology.
    # Unlike a triangle fill or poke, grid_fill creates interior vertices and
    # distributes valence rather than sending 34 spokes into one pole.  The
    # six surrounding concentric annuli remain explicitly authored above.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    inner_start = (len(RING_SCALES) - 1) * n
    inner_edges = []
    for index in range(n):
        first = bm.verts[inner_start + index]
        second = bm.verts[inner_start + ((index + 1) % n)]
        edge = bm.edges.get((first, second))
        if edge is None:
            bm.free()
            raise ValueError("innermost radial-ring edge missing before grid fill")
        inner_edges.append(edge)
    grid_result = bmesh.ops.grid_fill(
        bm,
        edges=inner_edges,
        mat_nr=0,
        use_smooth=True,
        use_interp_simple=False,
    )
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.faces.index_update()
    grid_new_vertices = [
        element for element in grid_result.get("geom", []) if isinstance(element, bmesh.types.BMVert)
    ]
    grid_new_faces = [
        element for element in grid_result.get("geom", []) if isinstance(element, bmesh.types.BMFace)
    ]
    generated_vertex_indices = sorted(int(vertex.index) for vertex in grid_new_vertices)
    face_vertex_counts = [len(face.verts) for face in bm.faces]
    maximum_vertex_valence = max(len(vertex.link_edges) for vertex in bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate(verbose=True)
    mesh.update()
    patch = bpy.data.objects.new("Kira_R19_New_Radial_Adult_Surface", mesh)
    collection.objects.link(patch)
    patch["private_review_only"] = True
    patch["owner_approved"] = False
    patch["runtime_assignment_allowed"] = False
    patch["source_interior_vertices_reused"] = 0
    patch["source_interior_faces_reused"] = 0
    patch["topology"] = "seven_concentric_34_vertex_rings_plus_structured_grid_fill"
    for polygon in patch.data.polygons:
        polygon.use_smooth = True

    # Structured-grid vertices receive the normalized boundary-wide mean.  No
    # rejected source-interior weight or coordinate is sampled.
    if len(patch.data.vertices) < len(weight_records):
        raise ValueError("structured grid fill unexpectedly removed authored ring vertices")
    weight_records.extend(
        dict(mean_weights)
        for _index in range(len(patch.data.vertices) - len(weight_records))
    )
    for group_name in sorted({name for record in weight_records for name in record}):
        patch.vertex_groups.new(name=group_name)
    for vertex_index, record in enumerate(weight_records):
        for name, value in record.items():
            patch.vertex_groups[name].add([vertex_index], value, "REPLACE")

    outer_created = vertices[:n]
    boundary_deltas = [
        (created - source).length
        for created, source in zip(outer_created, boundary)
    ]
    if max(boundary_deltas) > 1.0e-12:
        raise ValueError(
            "new outer ring failed exact boundary preservation: "
            f"maximum_delta={max(boundary_deltas):.12g}"
        )
    return patch, {
        "source_boundary_cycle_vertex_count": len(ordered_cycle),
        "cycle_reversed_for_outward_winding": cycle_reversed,
        "source_interior_vertices_reused": 0,
        "source_interior_faces_reused": 0,
        "ring_scales": list(RING_SCALES),
        "new_vertex_count": len(patch.data.vertices),
        "new_face_count": len(patch.data.polygons),
        "annular_quad_count": (len(RING_SCALES) - 1) * n,
        "structured_grid_generated_vertex_count": len(generated_vertex_indices),
        "structured_grid_generated_face_count": len(grid_new_faces),
        "structured_grid_face_vertex_count_histogram": {
            str(size): face_vertex_counts.count(size) for size in sorted(set(face_vertex_counts))
        },
        "maximum_vertex_valence": maximum_vertex_valence,
        "triangle_fan_or_poke_vertex_used": False,
        "maximum_exact_boundary_coordinate_delta_m": max(boundary_deltas),
        "boundary_mean_world_m": vec_record(center),
        "longitudinal_axis_world": vec_record(long_axis),
        "outward_axis_world": vec_record(outward),
        "lateral_half_extent_m": lateral_half,
        "longitudinal_half_extent_m": longitudinal_half,
        "base_bow_maximum_m": 0.0048 * (1.0 - RING_SCALES[-1] ** 2),
        "total_outward_displacement_range_m": [
            min(relief_extrema),
            max(relief_extrema),
        ],
        "landmark_relief_ranges_m": {
            name: [min(values), max(values)]
            for name, values in sorted(term_extrema.items())
        },
        "weight_transfer": {
            "source": "only the exact 34 source-boundary vertices",
            "method": "radial blend of corresponding boundary weights and boundary-wide mean",
            "maximum_influences_per_new_vertex": 4,
            "normalized": True,
            "boundary_mean_weights": mean_weights,
        },
    }


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Roughness"].default_value = roughness
    return material


def replace_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.material_index = 0


def normalize_body_top_four(obj: bpy.types.Object) -> dict[str, int]:
    changed = 0
    unweighted = 0
    maximum_before = 0
    for vertex in obj.data.vertices:
        assignments = [
            (assignment.group, float(assignment.weight))
            for assignment in vertex.groups
            if float(assignment.weight) > 1.0e-10
        ]
        maximum_before = max(maximum_before, len(assignments))
        selected = sorted(assignments, key=lambda item: (-item[1], item[0]))[:4]
        total = sum(value for _group, value in selected)
        if total <= 1.0e-12:
            unweighted += 1
            continue
        selected_indices = {group for group, _value in selected}
        if len(assignments) > 4 or abs(total - 1.0) > 1.0e-6:
            changed += 1
        for group, _value in assignments:
            if group not in selected_indices:
                obj.vertex_groups[group].remove([vertex.index])
        for group, value in selected:
            obj.vertex_groups[group].add([vertex.index], value / total, "REPLACE")
    obj.data.update()
    return {
        "vertices_changed_or_renormalized": changed,
        "unweighted_vertices": unweighted,
        "maximum_influences_before_normalization": maximum_before,
        "maximum_influences_after_normalization": 4,
    }


def join_primary_surface(
    by_mesh_name: dict[str, bpy.types.Object],
    patch: bpy.types.Object,
    armature: bpy.types.Object,
) -> tuple[bpy.types.Object, dict[str, object], set[int]]:
    base_sources = [by_mesh_name[name] for name in PRIMARY_BASE_MESHES]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in base_sources:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.select_set(True)
    body = base_sources[0]
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()

    bm = bmesh.new()
    bm.from_mesh(body.data)
    before_base = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1.0e-7)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    adult_replacement = legacy_builder.remove_base_faces_under_adult_patch(
        body,
        by_mesh_name[SOURCE_PATCH_MESH],
    )

    # Give the patch an identical-looking but distinct slot so exact audit
    # pairs can be classified as patch-related without changing appearance.
    patch_material = patch.data.materials[0]
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    patch.select_set(True)
    bpy.context.view_layer.objects.active = body
    vertices_before_join = len(body.data.vertices) + len(patch.data.vertices)
    bpy.ops.object.join()
    body.name = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface"
    body.data.name = "Kira_R19_BlackProject_Radial_Patch_Primary_Surface_Mesh"
    patch_material_slot = next(
        index for index, material in enumerate(body.data.materials) if material == patch_material
    )
    patch_faces_before_weld = {
        int(polygon.index)
        for polygon in body.data.polygons
        if int(polygon.material_index) == patch_material_slot
    }

    bm = bmesh.new()
    bm.from_mesh(body.data)
    before_weld = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=WELD_TOLERANCE_M)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    for polygon in body.data.polygons:
        polygon.use_smooth = True
    top_four = normalize_body_top_four(body)

    modifier = next((item for item in body.modifiers if item.type == "ARMATURE"), None)
    if modifier is None:
        modifier = body.modifiers.new("KIRA_R19_NATIVE_188_RIG", "ARMATURE")
    modifier.object = armature
    modifier.use_vertex_groups = True
    modifier.use_deform_preserve_volume = True
    body["private_review_only"] = True
    body["owner_approved"] = False
    body["runtime_assignment_allowed"] = False
    body["runtime_activation_allowed"] = False
    body["adult_status"] = "confirmed_adult"
    body["body_class"] = "adult_female"
    body["source_interior_vertices_reused"] = 0
    body["source_interior_faces_reused"] = 0

    patch_faces_after_weld = {
        int(polygon.index)
        for polygon in body.data.polygons
        if int(polygon.material_index) == patch_material_slot
    }
    if len(patch_faces_after_weld) != len(patch_faces_before_weld):
        raise ValueError("weld unexpectedly changed the new radial patch face count")
    return body, {
        "base_vertex_count_before_internal_component_weld": before_base,
        "base_vertex_count_after_internal_component_weld": len(body.data.vertices),
        "joined_vertex_count_before_boundary_weld": vertices_before_join,
        "joined_vertex_count_at_bmesh_weld": before_weld,
        "final_vertex_count": len(body.data.vertices),
        "boundary_vertices_merged": before_weld - len(body.data.vertices),
        "weld_tolerance_m": WELD_TOLERANCE_M,
        "adult_replacement": adult_replacement,
        "patch_material_slot": patch_material_slot,
        "patch_face_count": len(patch_faces_after_weld),
        "top_four_normalization": top_four,
    }, patch_faces_after_weld


def bmesh_exact_audit(obj: bpy.types.Object, include_details: bool) -> dict[str, object]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    report = exact_nonadjacent_intersection_report(
        bm,
        include_pair_details=include_details,
    )
    bm.free()
    return report


def make_camera(scene: bpy.types.Scene) -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("Kira_R19_Probe_Camera_Data")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("Kira_R19_Probe_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


def render_view(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output: Path,
    location: Vector,
    target: Vector,
    scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = scale
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def render_probe_set(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    output_dir: Path,
    body: bpy.types.Object,
    patch_center: Vector,
) -> dict[str, str]:
    points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
    low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    center = (low + high) * 0.5
    height = high.z - low.z
    full_scale = max(height * 1.08, (high.x - low.x) * 1.20)
    views = {
        "full_front": (Vector((center.x, center.y - 3.0, center.z)), center, full_scale),
        "full_three_quarter": (
            Vector((center.x + 2.35, center.y - 2.35, center.z)),
            center,
            full_scale,
        ),
        "full_side": (Vector((center.x + 3.0, center.y, center.z)), center, full_scale),
        "patch_front": (
            Vector((patch_center.x, patch_center.y - 1.6, patch_center.z)),
            patch_center,
            0.27,
        ),
        "patch_three_quarter": (
            Vector((patch_center.x + 1.1, patch_center.y - 1.25, patch_center.z)),
            patch_center,
            0.29,
        ),
        "patch_side": (
            Vector((patch_center.x + 1.6, patch_center.y, patch_center.z)),
            patch_center,
            0.27,
        ),
    }
    result: dict[str, str] = {}
    for name, (location, target, scale) in views.items():
        path = output_dir / f"{name}.png"
        render_view(scene, camera, path, location, target, scale)
        result[name] = path.name
    return result


def main() -> int:
    source_path = PROJECT_ROOT / SOURCE_REL
    authority_path = PROJECT_ROOT / AUTHORITY_REL
    output_dir = PROJECT_ROOT / OUTPUT_REL
    if output_dir.exists():
        raise FileExistsError(
            f"append-only attempt already exists and will not be overwritten: {output_dir}"
        )
    if sha256_file(source_path) != SOURCE_SHA256:
        raise ValueError("exact enrolled BlackProject source hash mismatch")
    if sha256_file(authority_path) != AUTHORITY_SHA256:
        raise ValueError("exact enrolled BlackProject authority hash mismatch")

    audit_helpers.clear_scene()
    scene = bpy.context.scene
    collection = bpy.data.collections.new("KIRA_R19_RADIAL_PATCH_PRIVATE_PROBE")
    scene.collection.children.link(collection)
    imported = audit_helpers.import_glb(source_path)
    for obj in imported:
        audit_helpers.move_to_collection(obj, collection)
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    if len(armatures) != 1 or len(armatures[0].data.bones) != 188:
        raise ValueError("source no longer has the reviewed one 188-joint armature")
    armature = armatures[0]
    armature.name = "Kira_R19_BlackProject_Native_188_Rig"
    armature["private_review_only"] = True
    armature["owner_approved"] = False
    armature["runtime_assignment_allowed"] = False

    by_mesh_name = {obj.data.name: obj for obj in imported if obj.type == "MESH"}
    missing = sorted(KEEP_MESHES - set(by_mesh_name))
    if missing:
        raise ValueError(f"reviewed source meshes missing: {missing}")
    source_patch = by_mesh_name[SOURCE_PATCH_MESH]
    cycles = legacy_builder.ordered_boundary_cycles(source_patch)
    if len(cycles) != 1 or len(cycles[0]) != BOUNDARY_VERTEX_COUNT:
        raise ValueError(
            "source adult component boundary drifted: "
            f"{[len(cycle) for cycle in cycles]}"
        )
    source_patch_stats = {
        "vertices": len(source_patch.data.vertices),
        "faces": len(source_patch.data.polygons),
        "boundary_cycles": [len(cycle) for cycle in cycles],
    }

    # Delete every unneeded mesh before authoring.  In particular, all three
    # source scalp-hair meshes and the cap remain absent rather than hidden.
    excluded_mesh_names: list[str] = []
    for obj in list(imported):
        if obj.type == "MESH" and obj.data.name not in KEEP_MESHES:
            excluded_mesh_names.append(obj.data.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    by_mesh_name = {
        obj.data.name: obj for obj in collection.objects if obj.type == "MESH"
    }

    skin_color = (0.62, 0.40, 0.30, 1.0)
    skin = make_material("Kira_R19_Warm_Natural_Skin", skin_color, 0.54)
    patch_skin = make_material("Kira_R19_Radial_Patch_Skin_Audit_Tag", skin_color, 0.54)
    lips = make_material("Kira_R19_Lips", (0.42, 0.105, 0.10, 1.0), 0.46)
    nails = make_material("Kira_R19_Nails", (0.68, 0.35, 0.33, 1.0), 0.38)
    brow = make_material("Kira_R19_Brows", (0.018, 0.009, 0.006, 1.0), 0.48)
    iris = make_material("Kira_R19_Iris", (0.20, 0.065, 0.02, 1.0), 0.32)
    sclera = make_material("Kira_R19_Sclera", (0.76, 0.70, 0.64, 1.0), 0.46)
    dark = make_material("Kira_R19_Dark_Eye_Mouth", (0.025, 0.007, 0.006, 1.0), 0.42)
    tooth = make_material("Kira_R19_Teeth", (0.82, 0.75, 0.66, 1.0), 0.36)
    clear = make_material("Kira_R19_Clear_Eye", (0.84, 0.91, 1.0, 0.18), 0.10)
    for name in PRIMARY_BASE_MESHES + ("Ariel_Mesh_EyeSocket_0",):
        replace_material(by_mesh_name[name], skin)
    replace_material(by_mesh_name["Ariel_Mesh_Lips_0"], lips)
    replace_material(by_mesh_name["Ariel_Mesh_Fingernails_0"], nails)
    replace_material(by_mesh_name["Ariel_Mesh_Toenails_0"], nails)
    replace_material(by_mesh_name["Eye_Brows_Brows02_0.001"], brow)
    replace_material(by_mesh_name["Ariel_Mesh_Irises_0"], iris)
    replace_material(by_mesh_name["Ariel_Mesh_Sclera_0"], sclera)
    replace_material(by_mesh_name["Ariel_Mesh_Pupils_0"], dark)
    replace_material(by_mesh_name["Ariel_Mesh_Mouth_0"], dark)
    replace_material(by_mesh_name["Ariel_Mesh_Teeth_0"], tooth)
    for name in (
        "Ariel_Mesh_EyeMoisture_0",
        "Ariel_Mesh_Cornea_0",
        "Eye_Lahes_EyeMoisture_0",
    ):
        replace_material(by_mesh_name[name], clear)

    radial_patch, radial_authoring = make_radial_patch(
        source_patch,
        cycles[0],
        collection,
    )
    radial_patch.data.materials.append(patch_skin)
    patch_center = Vector(radial_authoring["boundary_mean_world_m"])
    patch_topology_before_join = audit_helpers.topology_record(radial_patch)
    patch_weights_before_join = audit_helpers.weight_record(
        radial_patch,
        {bone.name for bone in armature.data.bones},
    )
    patch_exact_audit = bmesh_exact_audit(radial_patch, include_details=True)
    if patch_exact_audit["exact_genuine_penetration_pair_count"] != 0:
        raise ValueError(
            "new radial patch self-intersects before joining: "
            f"{patch_exact_audit['exact_genuine_penetration_pair_count']} pairs; "
            f"details={json.dumps([record for record in patch_exact_audit['pairs'] if record['genuine_positive_area_or_segment_penetration']])}"
        )

    body, join_record, patch_face_indices = join_primary_surface(
        by_mesh_name,
        radial_patch,
        armature,
    )
    # The rejected source patch object is now deleted.  Its 702 interior
    # vertices and all 1436 faces never enter the candidate.
    bpy.data.objects.remove(source_patch, do_unlink=True)

    topology = audit_helpers.topology_record(body)
    weights = audit_helpers.weight_record(body, {bone.name for bone in armature.data.bones})
    exact_audit = bmesh_exact_audit(body, include_details=True)
    patch_related_pairs = [
        record
        for record in exact_audit["pairs"]
        if record["genuine_positive_area_or_segment_penetration"]
        and any(index in patch_face_indices for index in record["face_indices"])
    ]
    inherited_elsewhere_pairs = [
        record
        for record in exact_audit["pairs"]
        if record["genuine_positive_area_or_segment_penetration"]
        and not any(index in patch_face_indices for index in record["face_indices"])
    ]

    output_dir.mkdir(parents=True, exist_ok=False)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 760
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.018, 0.024, 0.032)
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.show_specular_highlight = True
    camera = make_camera(scene)
    renders = render_probe_set(scene, camera, output_dir, body, patch_center)

    scene["candidate_kind"] = "R19_BLACKPROJECT_RADIAL_PATCH_PROBE"
    scene["private_review_only"] = True
    scene["owner_approved"] = False
    scene["runtime_assignment_allowed"] = False
    scene["runtime_activation_allowed"] = False
    scene["public_export_allowed"] = False
    scene["no_hair_dependency"] = True
    scene["source_interior_vertices_reused"] = 0
    scene["source_interior_faces_reused"] = 0
    blend_path = output_dir / "kira_r19_blackproject_radial_patch_probe.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    source_hash_after = sha256_file(source_path)
    if source_hash_after != SOURCE_SHA256:
        raise ValueError("source changed during the supposedly read-only import")
    render_bindings = {
        name: {
            "path": str((output_dir / filename).relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(output_dir / filename),
            "size_bytes": (output_dir / filename).stat().st_size,
        }
        for name, filename in renders.items()
    }
    evidence = {
        "schema_version": 1,
        "attempt": "attempt_01",
        "status": "PRIVATE_INACTIVE_GEOMETRY_PROBE_REQUIRES_VISUAL_REVIEW",
        "source": {
            "path": str(SOURCE_REL).replace("\\", "/"),
            "sha256_before": SOURCE_SHA256,
            "sha256_after": source_hash_after,
            "authority_path": str(AUTHORITY_REL).replace("\\", "/"),
            "authority_sha256": AUTHORITY_SHA256,
            "license": "CC BY 4.0",
            "source_patch_stats": source_patch_stats,
        },
        "scope": {
            "private": True,
            "inactive": True,
            "unassigned": True,
            "unpublished": True,
            "runtime_files_modified": False,
            "earlier_candidate_files_modified": False,
            "hair_objects_loaded_in_result": False,
            "source_interior_vertices_reused": 0,
            "source_interior_faces_reused": 0,
        },
        "excluded_source_mesh_names": sorted(excluded_mesh_names),
        "radial_patch_authoring": radial_authoring,
        "patch_topology_before_join": patch_topology_before_join,
        "patch_weights_before_join": patch_weights_before_join,
        "patch_exact_nonadjacent_intersection_audit": patch_exact_audit,
        "primary_surface_join": join_record,
        "primary_surface_topology": topology,
        "primary_surface_weights": weights,
        "primary_surface_exact_nonadjacent_intersection_audit": exact_audit,
        "intersection_localization": {
            "new_patch_related_genuine_pair_count": len(patch_related_pairs),
            "inherited_elsewhere_genuine_pair_count": len(inherited_elsewhere_pairs),
            "patch_related_pairs": patch_related_pairs,
            "inherited_elsewhere_pairs": inherited_elsewhere_pairs,
        },
        "review_renders": render_bindings,
        "blend": {
            "path": str(blend_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(blend_path),
            "size_bytes": blend_path.stat().st_size,
        },
        "worker": {
            "path": str(Path(__file__).resolve().relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "gates": {
            "exact_source_hash_preserved": source_hash_after == SOURCE_SHA256,
            "exact_34_vertex_boundary_preserved": radial_authoring[
                "maximum_exact_boundary_coordinate_delta_m"
            ]
            <= 1.0e-12,
            "zero_source_interior_geometry_reused": True,
            "no_triangle_fan_or_poke": True,
            "new_patch_prejoin_exact_intersection_free": patch_exact_audit[
                "exact_genuine_penetration_pair_count"
            ]
            == 0,
            "new_patch_joined_exact_intersection_free": len(patch_related_pairs) == 0,
            "one_connected_primary_surface": topology["connected_components"] == 1,
            "closed_primary_surface": topology["boundary_edge_count"] == 0,
            "normalized_max_four_weights": (
                weights["unweighted_vertex_count"] == 0
                and weights["maximum_positive_groups_per_vertex"] <= 4
                and weights["weight_sum"]["minimum"] > 0.999
                and weights["weight_sum"]["maximum"] < 1.001
            ),
            "visual_review": "PENDING",
            "owner_approval": "PENDING",
            "runtime_eligibility": False,
        },
        "truth_note": (
            "This is a bounded private geometry probe, not an accepted Kira body. "
            "It proves only the recorded source seam, topology, weight, exact "
            "intersection, and rendered-view facts. It does not prove internal "
            "anatomy, reproductive function, movement, identity likeness, owner "
            "approval, activation, or runtime readiness."
        ),
    }
    evidence_path = output_dir / "BUILD_EVIDENCE.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    report_path = output_dir / "REPORT.md"
    report_path.write_text(
        "\n".join(
            [
                "# R19 BlackProject radial patch probe — attempt 01",
                "",
                f"Status: `{evidence['status']}`",
                "",
                "- The exact 34-vertex source boundary was retained with a maximum coordinate delta of "
                f"`{radial_authoring['maximum_exact_boundary_coordinate_delta_m']:.3g} m`.",
                "- Reused source interior geometry: `0 vertices / 0 faces`.",
                f"- New topology: `{radial_authoring['new_vertex_count']} vertices / "
                f"{radial_authoring['new_face_count']} faces`; concentric annuli plus a "
                "structured center grid, with no central poke or fan.",
                "- New patch exact intersections before join: "
                f"`{patch_exact_audit['exact_genuine_penetration_pair_count']}`.",
                "- New patch-related exact intersections after join: "
                f"`{len(patch_related_pairs)}`.",
                "- Exact intersections elsewhere in inherited source body: "
                f"`{len(inherited_elsewhere_pairs)}`.",
                f"- Primary surface connected components: `{topology['connected_components']}`; "
                f"boundary edges: `{topology['boundary_edge_count']}`.",
                "- Scalp hair objects are excluded, not hidden.",
                "- This is inactive, unassigned, unpublished, and awaits visual review.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest_entries = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file():
            manifest_entries.append(
                {
                    "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    manifest_path = output_dir / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "append_only_attempt": "attempt_01",
                "files_excluding_this_manifest": manifest_entries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "output_dir": str(output_dir),
                "evidence": str(evidence_path),
                "report": str(report_path),
                "manifest": str(manifest_path),
                "new_patch_prejoin_exact_pairs": patch_exact_audit[
                    "exact_genuine_penetration_pair_count"
                ],
                "new_patch_joined_exact_pairs": len(patch_related_pairs),
                "inherited_elsewhere_exact_pairs": len(inherited_elsewhere_pairs),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
