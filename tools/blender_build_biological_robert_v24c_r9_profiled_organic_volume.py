"""Build a profiled organic connected anatomy volume on the clean V24C bridge.

R7 proved that a single body root eliminates the detached two-branch
silhouette, but its concentric contour loft encoded as an onion-like blob.
R8 proved the local implicit-volume plumbing but visually failed as a
cylinder/piston, ring-like distal end, paired beads, and a hard panel.  R9
keeps the valid single-root method while replacing those primitives with
overlapping curved profile guides, one asymmetric pouch, a shorter neutral
projection, and a smaller blended root.

This is a private static engineering trial.  It is not approved, activated,
rigged, or reusable as a generic Avatar Builder template.  No donor body or
identity surface enters Biological Robert.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24c_superior_bridge_refinement/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v24c_r9_profiled_organic_volume"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_NAME = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_"
    "R9_PROFILED_ORGANIC_VOLUME"
)
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24C_R9_PROFILED_ORGANIC_VOLUME_REPORT.json"
PATCH_SUBDIVISION_CUTS = 5
ROOT_PLANE_Y = -0.1190
VOXEL_SIZE = 0.00072

ZONE_NAMES = {
    1: "pubic_bridge",
    10: "integrated_root",
    11: "perineal_scrotal_envelope",
    12: "shaft_body",
    13: "glans",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def coordinate_key(vertex):
    return tuple(round(float(value), 7) for value in vertex.co)


def edge_key(edge):
    return tuple(sorted(coordinate_key(vertex) for vertex in edge.verts))


def topology_counts(bm):
    return {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in bm.edges),
        "wire_edges": sum(len(edge.link_faces) == 0 for edge in bm.edges),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in bm.edges
        ),
        "local_boundary_edges": sum(
            len(edge.link_faces) == 1
            and all(
                abs(vertex.co.x) <= 0.095
                and -0.190 <= vertex.co.y <= 0.080
                and 0.620 <= vertex.co.z <= 0.860
                for vertex in edge.verts
            )
            for edge in bm.edges
        ),
    }


def edge_components(edges):
    by_vertex = {}
    for edge in edges:
        for vertex in edge.verts:
            by_vertex.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    components = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        component = [seed]
        while stack:
            edge = stack.pop()
            for vertex in edge.verts:
                for neighbor in by_vertex[vertex]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        component.append(neighbor)
                        stack.append(neighbor)
        components.append(component)
    return components


def ordered_cycle(component):
    adjacency = {}
    for edge in component:
        first, second = edge.verts
        adjacency.setdefault(first, []).append(second)
        adjacency.setdefault(second, []).append(first)
    if not adjacency or set(len(values) for values in adjacency.values()) != {2}:
        raise RuntimeError("boundary is not one simple degree-two cycle")
    start = max(
        adjacency,
        key=lambda vertex: (vertex.co.z, -abs(vertex.co.x), -vertex.co.y),
    )
    first = min(adjacency[start], key=lambda vertex: vertex.co.x)
    result = [start, first]
    previous = start
    current = first
    while True:
        following = next(
            vertex for vertex in adjacency[current] if vertex is not previous
        )
        if following is start:
            break
        if following in result:
            raise RuntimeError("boundary repeats before closure")
        result.append(following)
        previous, current = current, following
    return result


def cycle_signed_area(cycle):
    area = 0.0
    for index, vertex in enumerate(cycle):
        following = cycle[(index + 1) % len(cycle)]
        area += vertex.co.x * following.co.z - following.co.x * vertex.co.z
    return area * 0.5


def rotate_to_top(cycle):
    start = max(
        range(len(cycle)),
        key=lambda index: (
            cycle[index].co.z,
            -abs(cycle[index].co.x),
        ),
    )
    return cycle[start:] + cycle[:start]


def average_uv(cycle, uv_layer):
    if uv_layer is None:
        return Vector((0.52, 0.38))
    values = [
        loop[uv_layer].uv.copy()
        for vertex in cycle
        for face in vertex.link_faces
        for loop in face.loops
        if loop.vert is vertex
    ]
    if not values:
        return Vector((0.52, 0.38))
    return sum(values, Vector((0.0, 0.0))) / len(values)


def normalized_perimeter(cycle):
    lengths = [
        (cycle[(index + 1) % len(cycle)].co - cycle[index].co).length
        for index in range(len(cycle))
    ]
    total = sum(lengths)
    values = [0.0]
    walked = 0.0
    for index in range(1, len(cycle)):
        walked += lengths[index - 1]
        values.append(walked / total)
    values.append(1.0)
    return values


def make_face(
    bm,
    vertices,
    *,
    material_index,
    uv_layer,
    uv_value,
    new_faces,
):
    face = bm.faces.new(tuple(vertices))
    face.material_index = material_index
    face.smooth = True
    if uv_layer is not None:
        for loop in face.loops:
            loop[uv_layer].uv = uv_value
    new_faces.append(face)
    return face


def bridge_unequal_cycles(
    bm,
    body_cycle,
    patch_cycle,
    *,
    material_index,
    uv_layer,
    uv_value,
    new_faces,
):
    """Zipper two simple, similarly oriented cycles with unequal counts."""

    body_cycle = rotate_to_top(body_cycle)
    patch_cycle = rotate_to_top(patch_cycle)
    if cycle_signed_area(body_cycle) * cycle_signed_area(patch_cycle) < 0.0:
        patch_cycle = [patch_cycle[0]] + list(reversed(patch_cycle[1:]))
    body_t = normalized_perimeter(body_cycle)
    patch_t = normalized_perimeter(patch_cycle)
    i = 0
    j = 0
    body_count = len(body_cycle)
    patch_count = len(patch_cycle)
    created = 0
    while i < body_count or j < patch_count:
        body_next = body_t[i + 1] if i < body_count else 1.0
        patch_next = patch_t[j + 1] if j < patch_count else 1.0
        a = body_cycle[i % body_count]
        b = patch_cycle[j % patch_count]
        if i < body_count and j < patch_count and abs(body_next - patch_next) < 1e-8:
            an = body_cycle[(i + 1) % body_count]
            bn = patch_cycle[(j + 1) % patch_count]
            make_face(
                bm,
                (a, an, bn, b),
                material_index=material_index,
                uv_layer=uv_layer,
                uv_value=uv_value,
                new_faces=new_faces,
            )
            i += 1
            j += 1
        elif i < body_count and (j >= patch_count or body_next < patch_next):
            an = body_cycle[(i + 1) % body_count]
            make_face(
                bm,
                (a, an, b),
                material_index=material_index,
                uv_layer=uv_layer,
                uv_value=uv_value,
                new_faces=new_faces,
            )
            i += 1
        else:
            bn = patch_cycle[(j + 1) % patch_count]
            make_face(
                bm,
                (a, bn, b),
                material_index=material_index,
                uv_layer=uv_layer,
                uv_value=uv_value,
                new_faces=new_faces,
            )
            j += 1
        created += 1
        if created > body_count + patch_count + 4:
            raise RuntimeError("unequal-cycle zipper did not terminate")
    return {
        "body_cycle_vertices": body_count,
        "patch_cycle_vertices": patch_count,
        "bridge_faces": created,
    }


def connect_equal_cycles(
    bm,
    first,
    second,
    *,
    material_index,
    uv_layer,
    uv_value,
    new_faces,
):
    if len(first) != len(second):
        raise RuntimeError("equal-cycle bridge received different counts")
    for index in range(len(first)):
        following = (index + 1) % len(first)
        make_face(
            bm,
            (
                first[index],
                first[following],
                second[following],
                second[index],
            ),
            material_index=material_index,
            uv_layer=uv_layer,
            uv_value=uv_value,
            new_faces=new_faces,
        )


def bridge_matching_cycles_with_transitions(
    bm,
    body_cycle,
    patch_cycle,
    *,
    zone_layer,
    authored_layer,
    mix_layer,
    material_index,
    uv_layer,
    uv_value,
    new_faces,
):
    """Bridge matched roots through smooth quad-only transition rows."""

    body_cycle = rotate_to_top(body_cycle)
    patch_cycle = rotate_to_top(patch_cycle)
    if cycle_signed_area(body_cycle) * cycle_signed_area(patch_cycle) < 0.0:
        patch_cycle = [patch_cycle[0]] + list(reversed(patch_cycle[1:]))
    if len(body_cycle) != len(patch_cycle):
        raise RuntimeError("matched transition cycles have different counts")
    previous = body_cycle
    rows = []
    for factor in (0.25, 0.52, 0.78):
        eased = factor * factor * (3.0 - 2.0 * factor)
        row = []
        for body_vertex, patch_vertex in zip(body_cycle, patch_cycle):
            coordinate = body_vertex.co.lerp(patch_vertex.co, eased)
            # Keep each transition monotonically anterior to its body point.
            coordinate.y = min(
                coordinate.y,
                body_vertex.co.y - 0.0008 * factor,
            )
            vertex = bm.verts.new(coordinate)
            vertex[zone_layer] = 10
            vertex[authored_layer] = 1
            vertex[mix_layer] = 0.18 + 0.20 * eased
            row.append(vertex)
        connect_equal_cycles(
            bm,
            previous,
            row,
            material_index=material_index,
            uv_layer=uv_layer,
            uv_value=uv_value,
            new_faces=new_faces,
        )
        previous = row
        rows.append(row)
    connect_equal_cycles(
        bm,
        previous,
        patch_cycle,
        material_index=material_index,
        uv_layer=uv_layer,
        uv_value=uv_value,
        new_faces=new_faces,
    )
    return {
        "body_cycle_vertices": len(body_cycle),
        "patch_cycle_vertices": len(patch_cycle),
        "transition_rows": len(rows),
        "bridge_faces": len(body_cycle) * (len(rows) + 1),
        "quad_only": True,
    }


def add_ellipsoid(name, center, scale, segments=40, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=1.0,
        location=center,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def add_profile_ellipsoid(
    name,
    start,
    end,
    *,
    radius_x,
    radius_y,
    end_extension=1.10,
):
    """Add one overlapping organic profile segment along a curved centreline."""

    start = Vector(start)
    end = Vector(end)
    direction = end - start
    if direction.length <= 1.0e-8:
        raise ValueError(f"{name} has a zero-length profile")
    center = (start + end) * 0.5
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=48,
        ring_count=28,
        radius=1.0,
        location=center,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(
        direction.normalized()
    )
    obj.scale = (
        radius_x,
        radius_y,
        direction.length * 0.5 * end_extension,
    )
    bpy.ops.object.transform_apply(
        location=False,
        rotation=True,
        scale=True,
    )
    return obj


def add_rounded_cylinder(name, center, radius_x, radius_y, depth):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48,
        radius=1.0,
        depth=depth,
        location=center,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = (radius_x, radius_y, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new(f"{name}_RoundedEnds", "BEVEL")
    bevel.width = min(radius_x, radius_y) * 0.72
    bevel.segments = 4
    bevel.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    return obj


def add_rounded_cone(
    name,
    center,
    *,
    radius_bottom,
    radius_top,
    depth,
    y_scale,
):
    """Create a tapered rounded distal form with a broader proximal shoulder."""

    bpy.ops.mesh.primitive_cone_add(
        vertices=48,
        radius1=radius_bottom,
        radius2=radius_top,
        depth=depth,
        location=center,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = (1.0, y_scale, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new(f"{name}_RoundedProfile", "BEVEL")
    bevel.width = min(radius_bottom, radius_top) * 0.42
    bevel.segments = 4
    bevel.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    return obj


def simplify_planar_boundary(patch_bm, cycle, target_count):
    """Reduce a dense remesh cut to an evenly sampled bridge boundary."""

    if len(cycle) <= target_count:
        return cycle
    count = len(cycle)
    keep_indices = {
        min(count - 1, round(index * count / target_count))
        for index in range(target_count)
    }
    dissolve = [
        vertex
        for index, vertex in enumerate(cycle)
        if index not in keep_indices
    ]
    bmesh.ops.dissolve_verts(
        patch_bm,
        verts=dissolve,
        use_face_split=False,
        use_boundary_tear=False,
    )
    patch_bm.verts.ensure_lookup_table()
    patch_bm.edges.ensure_lookup_table()
    patch_bm.faces.ensure_lookup_table()
    patch_bm.normal_update()
    boundaries = [
        edge
        for edge in patch_bm.edges
        if len(edge.link_faces) == 1
        and all(
            abs(vertex.co.y - ROOT_PLANE_Y) <= 2.0e-4
            for vertex in edge.verts
        )
    ]
    components = edge_components(boundaries)
    if len(components) != 1:
        raise RuntimeError(
            "simplified organic root lost its single cycle: "
            f"{[len(component) for component in components]}"
        )
    result = ordered_cycle(components[0])
    if len(result) != target_count:
        raise RuntimeError(
            f"organic root simplification produced {len(result)}, "
            f"expected {target_count}"
        )
    return result


def create_organic_patch_object():
    """Create one local volume from overlapping profiled form guides."""

    guides = [
        # Compact high root and superior apron.  Both remain shallow at the
        # body plane so the stitched transition does not read as a hard panel.
        add_ellipsoid(
            "R9_HighIntegratedRoot",
            (0.0, -0.1168, 0.783),
            (0.0235, 0.0090, 0.0310),
        ),
        add_ellipsoid(
            "R9_SuperiorApron",
            (0.0, -0.1160, 0.803),
            (0.0175, 0.0075, 0.0215),
        ),
        # A broad perineal bridge makes the pouch and shaft emerge from one
        # continuous surface instead of from independent sockets.
        add_ellipsoid(
            "R9_PerinealBridge",
            (0.0, -0.1195, 0.751),
            (0.0195, 0.0100, 0.0300),
        ),
        # The neutral shaft is a curved, tapered chain of heavily overlapping
        # ellipsoidal profiles.  No cylinder, ring, or separately spliced
        # distal bead is used.
        add_profile_ellipsoid(
            "R9_ShaftProximal",
            (0.0, -0.1260, 0.790),
            (0.0004, -0.1360, 0.772),
            radius_x=0.0096,
            radius_y=0.0100,
            end_extension=1.55,
        ),
        add_profile_ellipsoid(
            "R9_ShaftMiddle",
            (0.0004, -0.1350, 0.776),
            (0.0008, -0.1410, 0.756),
            radius_x=0.0089,
            radius_y=0.0096,
            end_extension=1.62,
        ),
        add_profile_ellipsoid(
            "R9_ShaftDistal",
            (0.0008, -0.1400, 0.760),
            (0.0003, -0.1435, 0.744),
            radius_x=0.0092,
            radius_y=0.0102,
            end_extension=1.58,
        ),
        # A subtly broader, vertically elongated distal form overlaps the
        # shaft enough that the remeshed result has no ring-like joint.
        add_ellipsoid(
            "R9_DistalContinuousForm",
            (0.0002, -0.1435, 0.7365),
            (0.0103, 0.0112, 0.0136),
            segments=48,
            rings=28,
        ),
        # One connected asymmetric scrotal envelope sits behind and below the
        # shaft.  A later bounded surface displacement supplies a shallow
        # midline raphe without splitting it into two bead-like lobes.
        add_ellipsoid(
            "R9_ScrotalEnvelope",
            (0.0012, -0.1235, 0.7160),
            (0.0188, 0.0133, 0.0272),
            segments=48,
            rings=28,
        ),
        add_ellipsoid(
            "R9_ScrotalSuperiorContinuity",
            (0.0, -0.1200, 0.7370),
            (0.0178, 0.0107, 0.0220),
            segments=48,
            rings=28,
        ),
    ]
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    for obj in guides:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = guides[0]
    bpy.ops.object.join()
    patch = bpy.context.object
    patch.name = "R9_PROFILED_ORGANIC_VOLUME_RAW"
    # Bake the active guide's object translation so the local mesh uses the
    # same Biological Robert coordinate frame as the retained body BMesh.
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    patch.data.remesh_voxel_size = VOXEL_SIZE
    patch.data.remesh_voxel_adaptivity = 0.0
    bpy.ops.object.voxel_remesh()
    # A bounded smoothing pass removes voxel stair-stepping while retaining
    # the shaft/glans shoulder and bilateral lower silhouette.
    modifier = patch.modifiers.new("R9_BoundedSurfaceRelax", "SMOOTH")
    modifier.factor = 0.38
    modifier.iterations = 5
    bpy.context.view_layer.objects.active = patch
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return patch


def copy_patch_to_body(
    target_bm,
    patch_bm,
    patch_cycle,
    *,
    zone_layer,
    authored_layer,
    mix_layer,
    material_index,
    uv_layer,
    uv_value,
    new_faces,
):
    mapping = {}
    for vertex in patch_bm.verts:
        copied = target_bm.verts.new(vertex.co)
        if vertex.co.z >= 0.785:
            zone = 12
        elif vertex.co.z <= 0.745:
            zone = 11
        else:
            zone = 13 if vertex.co.y <= -0.129 else 10
        copied[zone_layer] = zone
        copied[authored_layer] = 1
        copied[mix_layer] = 1.0
        mapping[vertex] = copied
    for face in patch_bm.faces:
        copied_face = make_face(
            target_bm,
            [mapping[vertex] for vertex in face.verts],
            material_index=material_index,
            uv_layer=uv_layer,
            uv_value=uv_value,
            new_faces=new_faces,
        )
        copied_face.smooth = True
    return [mapping[vertex] for vertex in patch_cycle]


def mesh_bvh(faces):
    vertices = []
    vertex_map = {}
    polygons = []
    keys = []
    centers = []
    for face in faces:
        polygon = []
        face_keys = set()
        for vertex in face.verts:
            key = coordinate_key(vertex)
            if key not in vertex_map:
                vertex_map[key] = len(vertices)
                vertices.append(vertex.co.copy())
            polygon.append(vertex_map[key])
            face_keys.add(key)
        polygons.append(polygon)
        keys.append(face_keys)
        centers.append(list(face.calc_center_median()))
    if not polygons:
        return None, keys, centers
    return (
        BVHTree.FromPolygons(vertices, polygons, all_triangles=False),
        keys,
        centers,
    )


def intersection_report(patch_faces, retained_faces):
    patch_bvh, patch_keys, patch_centers = mesh_bvh(patch_faces)
    retained_bvh, retained_keys, retained_centers = mesh_bvh(retained_faces)
    self_pairs = set()
    for first, second in patch_bvh.overlap(patch_bvh):
        if first >= second or patch_keys[first] & patch_keys[second]:
            continue
        self_pairs.add((first, second))
    retained_pairs = set()
    for first, second in patch_bvh.overlap(retained_bvh):
        if patch_keys[first] & retained_keys[second]:
            continue
        retained_pairs.add((first, second))
    return {
        "nonadjacent_patch_self_intersections": len(self_pairs),
        "nonadjacent_patch_retained_intersections": len(retained_pairs),
        "first_patch_self_pairs": [
            {
                "patch_faces": list(pair),
                "centers": [
                    patch_centers[pair[0]],
                    patch_centers[pair[1]],
                ],
            }
            for pair in sorted(self_pairs)[:30]
        ],
        "first_patch_retained_pairs": [
            {
                "faces": list(pair),
                "patch_center": patch_centers[pair[0]],
                "retained_center": retained_centers[pair[1]],
            }
            for pair in sorted(retained_pairs)[:30]
        ],
    }


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = bpy.data.objects[
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_SUPERIOR_BRIDGE_REFINEMENT"
]
source_sha = sha256(SOURCE)

# Build the organic surface as a separate closed object before touching the
# retained body mesh.
patch_object = create_organic_patch_object()
patch_bm = bmesh.new()
patch_bm.from_mesh(patch_object.data)
patch_bm.verts.ensure_lookup_table()
patch_bm.edges.ensure_lookup_table()
patch_bm.faces.ensure_lookup_table()
bmesh.ops.bisect_plane(
    patch_bm,
    geom=list(patch_bm.verts) + list(patch_bm.edges) + list(patch_bm.faces),
    dist=1.0e-6,
    plane_co=Vector((0.0, ROOT_PLANE_Y, 0.0)),
    plane_no=Vector((0.0, 1.0, 0.0)),
    clear_outer=False,
    clear_inner=False,
    use_snap_center=False,
)
posterior_faces = [
    face
    for face in patch_bm.faces
    if face.calc_center_median().y > ROOT_PLANE_Y + 1.0e-7
]
bmesh.ops.delete(patch_bm, geom=posterior_faces, context="FACES")
loose_vertices = [
    vertex for vertex in patch_bm.verts if not vertex.link_faces
]
if loose_vertices:
    bmesh.ops.delete(patch_bm, geom=loose_vertices, context="VERTS")
patch_bm.verts.ensure_lookup_table()
patch_bm.edges.ensure_lookup_table()
patch_bm.faces.ensure_lookup_table()
patch_bm.normal_update()
all_patch_boundaries = [
    edge for edge in patch_bm.edges if len(edge.link_faces) == 1
]
patch_boundaries = [
    edge
    for edge in all_patch_boundaries
    if all(abs(vertex.co.y - ROOT_PLANE_Y) <= 2.0e-4 for vertex in edge.verts)
]
patch_components = edge_components(patch_boundaries)
if len(patch_components) != 1:
    raise RuntimeError(
        "organic patch root is not one boundary cycle: "
        f"plane_components={[len(component) for component in patch_components]} "
        f"all_boundary_edges={len(all_patch_boundaries)} "
        f"mesh_bounds_y=("
        f"{min(vertex.co.y for vertex in patch_bm.verts):.6f},"
        f"{max(vertex.co.y for vertex in patch_bm.verts):.6f})"
    )
patch_root = ordered_cycle(patch_components[0])
patch_root_count = len(patch_root)

# Subtle midline recession and mild left/right height asymmetry give the one
# pouch ordinary form without cutting a hole or creating two objects.
for vertex in patch_bm.verts:
    if (
        abs(vertex.co.x) < 0.0043
        and 0.694 < vertex.co.z < 0.731
        and vertex.co.y < ROOT_PLANE_Y - 0.001
    ):
        x_factor = 1.0 - abs(vertex.co.x) / 0.0043
        z_factor = max(0.0, 1.0 - abs(vertex.co.z - 0.714) / 0.019)
        vertex.co.y += 0.00048 * x_factor * z_factor
    if (
        vertex.co.x < 0.0
        and 0.692 < vertex.co.z < 0.730
        and vertex.co.y < ROOT_PLANE_Y - 0.001
    ):
        lateral = min(1.0, abs(vertex.co.x) / 0.018)
        lower = max(0.0, 1.0 - abs(vertex.co.z - 0.710) / 0.020)
        vertex.co.z -= 0.0014 * lateral * lower
patch_bm.normal_update()

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
uv_layer = bm.loops.layers.uv.active
zone_layer = bm.verts.layers.int.get("Adult_Anatomy_Zone")
if zone_layer is None:
    zone_layer = bm.verts.layers.int.new("Adult_Anatomy_Zone")
authored_layer = bm.verts.layers.int.get("V24C_R9_Profiled_Organic_Volume")
if authored_layer is None:
    authored_layer = bm.verts.layers.int.new("V24C_R9_Profiled_Organic_Volume")
mix_layer = bm.verts.layers.float.get("V24C_R9_Regional_Mix")
if mix_layer is None:
    mix_layer = bm.verts.layers.float.new("V24C_R9_Regional_Mix")

baseline = topology_counts(bm)
baseline_boundaries = {
    edge_key(edge) for edge in bm.edges if len(edge.link_faces) == 1
}
central_faces = [
    face
    for face in bm.faces
    if face.normal.y < -0.75
    and min(vertex.co.x for vertex in face.verts) < -0.030
    and max(vertex.co.x for vertex in face.verts) > 0.030
    and all(
        -0.135 < vertex.co.y < -0.060
        and 0.670 < vertex.co.z < 0.840
        for vertex in face.verts
    )
]
if len(central_faces) != 4:
    raise RuntimeError(f"expected four V24C bridge faces, got {len(central_faces)}")
central_material = max(
    set(face.material_index for face in central_faces),
    key=[face.material_index for face in central_faces].count,
)
central_edges = list({edge for face in central_faces for edge in face.edges})
bmesh.ops.subdivide_edges(
    bm,
    edges=central_edges,
    cuts=PATCH_SUBDIVISION_CUTS,
    use_grid_fill=True,
)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
bm.normal_update()

cut_faces = [
    face
    for face in bm.faces
    if face.normal.y < -0.65
    and all(
        abs(vertex.co.x) <= 0.0360
        and -0.125 <= vertex.co.y <= -0.090
        and 0.6950 <= vertex.co.z <= 0.8320
        for vertex in face.verts
    )
]
if len(cut_faces) < 20:
    raise RuntimeError(f"body root window too small: {len(cut_faces)}")
bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
body_boundary_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and edge_key(edge) not in baseline_boundaries
    and all(
        abs(vertex.co.x) <= 0.040
        and -0.130 <= vertex.co.y <= -0.085
        and 0.685 <= vertex.co.z <= 0.838
        for vertex in edge.verts
    )
]
body_components = edge_components(body_boundary_edges)
if len(body_components) != 1:
    raise RuntimeError(
        "body root is not one cycle: "
        f"{[len(component) for component in body_components]}"
    )
body_root = ordered_cycle(body_components[0])
body_root_count = len(body_root)
uv_value = average_uv(body_root, uv_layer)

# Match the dense remeshed cut to the authored body boundary before bridging.
# This removes the hundreds of needle triangles that made the first R8 root
# look pleated despite a closed topology.
patch_root = simplify_planar_boundary(
    patch_bm,
    patch_root,
    body_root_count,
)
patch_root_count = len(patch_root)

new_faces = []
copied_patch_root = copy_patch_to_body(
    bm,
    patch_bm,
    patch_root,
    zone_layer=zone_layer,
    authored_layer=authored_layer,
    mix_layer=mix_layer,
    material_index=central_material,
    uv_layer=uv_layer,
    uv_value=uv_value,
    new_faces=new_faces,
)
patch_bm.free()
bridge_report = bridge_matching_cycles_with_transitions(
    bm,
    body_root,
    copied_patch_root,
    zone_layer=zone_layer,
    authored_layer=authored_layer,
    mix_layer=mix_layer,
    material_index=central_material,
    uv_layer=uv_layer,
    uv_value=uv_value,
    new_faces=new_faces,
)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.normal_update()

final = topology_counts(bm)
patch_set = set(new_faces)
retained_local_faces = [
    face
    for face in bm.faces
    if face not in patch_set
    and max(abs(vertex.co.x) for vertex in face.verts) <= 0.095
    and max(vertex.co.y for vertex in face.verts) >= -0.190
    and min(vertex.co.y for vertex in face.verts) <= 0.050
    and max(vertex.co.z for vertex in face.verts) >= 0.630
    and min(vertex.co.z for vertex in face.verts) <= 0.850
]
intersections = intersection_report(new_faces, retained_local_faces)
topology_gate = (
    final["boundary_edges"] == baseline["boundary_edges"]
    and final["wire_edges"] == baseline["wire_edges"]
    and final["nonmanifold_gt2_edges"]
    == baseline["nonmanifold_gt2_edges"]
    and final["local_boundary_edges"] == baseline["local_boundary_edges"]
)
intersection_gate = (
    intersections["nonadjacent_patch_self_intersections"] == 0
    and intersections["nonadjacent_patch_retained_intersections"] == 0
)
zone_counts = {
    name: sum(vertex[zone_layer] == code for vertex in bm.verts)
    for code, name in ZONE_NAMES.items()
}

bm.to_mesh(body.data)
bm.free()
body.data.update()
mesh_validate_changed = body.data.validate(clean_customdata=False)
for polygon in body.data.polygons:
    polygon.use_smooth = True
body.name = BODY_NAME
body["status"] = (
    "ENGINEERING TRIAL - FRONT/SIDE/THREE-QUARTER VISUAL REVIEW REQUIRED"
)
body["source_authority"] = "V24C CLEAN CONTINUOUS PUBIC BRIDGE"
body["method"] = "ONE ROOT + ONE ORGANIC CONNECTED LOCAL VOLUME"
body["local_implicit_form_guides_used"] = True
body["local_voxel_remesh_used"] = True
body["donor_identity_surface_used"] = False
body["owner_approved"] = False
body["movement_started"] = False
body["runtime_activation_allowed"] = False
bpy.data.objects.remove(patch_object, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema": "kira.avatar.biological_robert.v24c.r9.profiled_organic_volume.v1",
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": source_sha,
    "output": str(BLEND_PATH),
    "output_sha256": sha256(BLEND_PATH),
    "reference_handling": {
        "private_owner_reference_directory": r"C:\Users\robmc\Desktop\reference",
        "used_for": [
            "Robert-specific placement",
            "compact neutral projection",
            "relationship to Robert's upper thighs",
        ],
        "authorized_adult_reference_used_for": [
            "high continuous root relationship",
            "shaft/body/glans distinction",
            "scrotum behind and below the shaft",
            "bilateral pouch and perineal continuity",
        ],
        "private_local_only": True,
        "delete_only_after_explicit_owner_approval": True,
    },
    "method_truth": {
        "v24c_clean_bridge_used": True,
        "single_contiguous_body_root": True,
        "single_connected_local_volume": True,
        "form_guides": "overlapping hand-authored ellipsoids",
        "local_voxel_remesh": True,
        "voxel_size_m": VOXEL_SIZE,
        "boolean": False,
        "metaballs": False,
        "donor_identity_surface": False,
        "global_body_change": False,
        "r7_rejected_reason": (
            "nested concentric contours encoded as an onion-like generic blob"
        ),
    },
    "roots": {
        "body_cut_face_count": len(cut_faces),
        "body_root_vertices": body_root_count,
        "patch_root_plane_y": ROOT_PLANE_Y,
        "patch_root_vertices": patch_root_count,
        "bridge": bridge_report,
    },
    "zone_vertex_counts": zone_counts,
    "baseline_topology": baseline,
    "final_topology": final,
    "topology_gate": topology_gate,
    "intersection_report": intersections,
    "intersection_gate": intersection_gate,
    "mesh_validate_changed_data": bool(mesh_validate_changed),
    "truthful_gate": {
        "static_owner_review_candidate": False,
        "visual_promotion": (
            "BLOCKED UNTIL ENCODED NEUTRAL FRONT/SIDE/THREE-QUARTER "
            "REVIEW AND INTERSECTION GATES PASS"
        ),
        "reject_if": [
            "root looks pasted or leaves a gap",
            "side view reads as floating geometry",
            "shaft is too long or thick",
            "glans is spherical or oversized",
            "scrotal envelope is toy-like instead of compact and bilateral",
            "voxel remesh erased anatomical distinctions",
        ],
    },
    "reusability_boundary": {
        "candidate_reusable_method_only_after_owner_approval": [
            "single bounded body root",
            "profiled organic local connected volume",
            "encoded neutral-view and intersection gates",
        ],
        "robert_private_person_specific_data": [
            "root position and proportions inferred from protected photos",
            "Robert likeness body mesh and materials",
            "Robert-specific anatomy parameters",
        ],
        "avatar_builder_promotion": (
            "BLOCKED until Biological Robert static owner approval and "
            "independent generalization proof on other authorized adults"
        ),
    },
    "scope": {
        "private_static_engineering_only": True,
        "movement": False,
        "activation": False,
        "runtime_attachment": False,
        "synthetic_robert": False,
        "kira": False,
        "clothing": False,
    },
}
REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(BLEND_PATH)
print(json.dumps(report, indent=2))
