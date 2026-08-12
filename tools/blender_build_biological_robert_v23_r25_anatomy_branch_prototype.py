"""Build a static-only R25 anatomy-branch prototype on the R24 body surface.

The prototype removes only the R24 vertices tagged as authored anatomy, keeps
the owner-derived body surface and attachment boundaries unchanged, and builds
new compact branches with:

* a high, short shaft path;
* continuous phrase-like curvature rather than stacked vertical cylinders;
* a distinct neck, restrained coronal flare, glans body, and rounded tip;
* a connected scrotal pouch behind the shaft with subtle bilateral form; and
* root support rings that follow the existing body-surface normals.

This is private static engineering evidence.  It does not use Boolean union,
voxel/global remeshing, or donor identity/body surface transfer.  It does not
authorize movement, runtime attachment, activation, Synthetic Robert, Kira,
clothing, or Kira World work.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_preserved_surface_trial_r24_raised_branches/"
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "PRESERVED_SURFACE_TRIAL_R24_RAISED_BRANCHES.blend"
)
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v23_r25b_anatomy_branch_prototype"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_OUTPUT_NAME = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_"
    "R25B_ANATOMY_BRANCH_PROTOTYPE"
)
BLEND_PATH = OUT / f"{BODY_OUTPUT_NAME}.blend"
REPORT_PATH = OUT / "R25B_ANATOMY_BRANCH_PROTOTYPE_REPORT.json"

ADULT_ANATOMY_ZONES = {
    10: "shaft_root",
    11: "shaft_body",
    12: "glans",
    20: "scrotal_root",
    21: "scrotal_envelope",
    22: "perineal_transition",
}


def edge_components(
    edges: list[bmesh.types.BMEdge],
) -> list[list[bmesh.types.BMEdge]]:
    vertex_edges: dict[bmesh.types.BMVert, list[bmesh.types.BMEdge]] = {}
    for edge in edges:
        for vertex in edge.verts:
            vertex_edges.setdefault(vertex, []).append(edge)
    unseen = set(edges)
    components = []
    while unseen:
        seed = unseen.pop()
        component = [seed]
        stack = [seed]
        while stack:
            current = stack.pop()
            for vertex in current.verts:
                for neighbor in vertex_edges.get(vertex, []):
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        component.append(neighbor)
                        stack.append(neighbor)
        components.append(component)
    return components


def ordered_cycle(
    edges: list[bmesh.types.BMEdge],
) -> list[bmesh.types.BMVert]:
    adjacency: dict[bmesh.types.BMVert, list[bmesh.types.BMVert]] = {}
    for edge in edges:
        first, second = edge.verts
        adjacency.setdefault(first, []).append(second)
        adjacency.setdefault(second, []).append(first)
    if {len(neighbors) for neighbors in adjacency.values()} != {2}:
        raise RuntimeError("attachment boundary is not a simple closed cycle")
    start = max(
        adjacency,
        key=lambda vertex: (
            vertex.co.z,
            -abs(vertex.co.x),
            -vertex.co.y,
        ),
    )
    # Travel from the superior point toward the anatomical left side.  This
    # gives stable top/left/bottom/right correspondence on every ideal ring.
    candidates = adjacency[start]
    first = min(candidates, key=lambda vertex: vertex.co.x)
    cycle = [start, first]
    previous = start
    current = first
    while True:
        following = next(
            vertex for vertex in adjacency[current] if vertex is not previous
        )
        if following is start:
            break
        if following in cycle:
            raise RuntimeError("attachment cycle repeats before closure")
        cycle.append(following)
        previous, current = current, following
    return cycle


def arc_angles(cycle: list[bmesh.types.BMVert]) -> list[float]:
    lengths = []
    total = 0.0
    for index in range(len(cycle)):
        following = (index + 1) % len(cycle)
        length = (cycle[following].co - cycle[index].co).length
        lengths.append(length)
        total += length
    if total <= 1.0e-9:
        raise RuntimeError("attachment cycle has zero perimeter")
    values = []
    traversed = 0.0
    for index in range(len(cycle)):
        values.append(math.pi / 2.0 + math.tau * traversed / total)
        traversed += lengths[index]
    return values


def topology_counts(obj: bpy.types.Object) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in bm.edges),
        "wire_edges": sum(len(edge.link_faces) == 0 for edge in bm.edges),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in bm.edges
        ),
    }
    bm.free()
    return result


def bounds_for_vertices(
    vertices: list[bmesh.types.BMVert],
) -> dict[str, object]:
    center = sum((vertex.co for vertex in vertices), Vector()) / len(vertices)
    bounds = {
        "min_x": min(vertex.co.x for vertex in vertices),
        "max_x": max(vertex.co.x for vertex in vertices),
        "min_y": min(vertex.co.y for vertex in vertices),
        "max_y": max(vertex.co.y for vertex in vertices),
        "min_z": min(vertex.co.z for vertex in vertices),
        "max_z": max(vertex.co.z for vertex in vertices),
    }
    return {
        "vertex_count": len(vertices),
        "center": list(center),
        "bounds": bounds,
        "width_x_m": bounds["max_x"] - bounds["min_x"],
        "depth_y_m": bounds["max_y"] - bounds["min_y"],
        "height_z_m": bounds["max_z"] - bounds["min_z"],
    }


def connectivity_evidence(
    bm: bmesh.types.BMesh,
    anatomy_zone_layer: bmesh.types.BMLayerItem,
) -> dict[str, object]:
    """Measure connected-component membership without inferring approval."""

    bm.verts.ensure_lookup_table()
    parent = list(range(len(bm.verts)))
    size = [1] * len(bm.verts)

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        first_root = find(first)
        second_root = find(second)
        if first_root == second_root:
            return
        if size[first_root] < size[second_root]:
            first_root, second_root = second_root, first_root
        parent[second_root] = first_root
        size[first_root] += size[second_root]

    for edge in bm.edges:
        union(edge.verts[0].index, edge.verts[1].index)
    component_sizes: dict[int, int] = {}
    for vertex in bm.verts:
        root = find(vertex.index)
        component_sizes[root] = component_sizes.get(root, 0) + 1
    primary_root = max(component_sizes, key=component_sizes.get)
    anatomy_vertices = [
        vertex for vertex in bm.verts if vertex[anatomy_zone_layer] > 0
    ]
    anatomy_roots = {find(vertex.index) for vertex in anatomy_vertices}
    main_boundary_edges = sum(
        len(edge.link_faces) == 1
        and all(find(vertex.index) == primary_root for vertex in edge.verts)
        for edge in bm.edges
    )
    main_nonmanifold_edges = sum(
        len(edge.link_faces) > 2
        and all(find(vertex.index) == primary_root for vertex in edge.verts)
        for edge in bm.edges
    )
    return {
        "mesh_connected_component_count": len(component_sizes),
        "largest_component_vertex_count": component_sizes[primary_root],
        "largest_component_fraction": (
            component_sizes[primary_root] / max(1, len(bm.verts))
        ),
        "primary_skin_component_count": 1,
        "anatomy_primary_skin_same_component": anatomy_roots == {primary_root},
        "separate_anatomy_mesh_count": sum(
            root != primary_root for root in anatomy_roots
        ),
        "main_skin_boundary_edges": main_boundary_edges,
        "main_skin_nonmanifold_edges": main_nonmanifold_edges,
    }


def cycle_bounds(cycle: list[bmesh.types.BMVert]) -> dict[str, float]:
    return {
        "min_x": min(vertex.co.x for vertex in cycle),
        "max_x": max(vertex.co.x for vertex in cycle),
        "min_y": min(vertex.co.y for vertex in cycle),
        "max_y": max(vertex.co.y for vertex in cycle),
        "min_z": min(vertex.co.z for vertex in cycle),
        "max_z": max(vertex.co.z for vertex in cycle),
    }


def cycle_center(cycle: list[bmesh.types.BMVert]) -> Vector:
    return sum((vertex.co for vertex in cycle), Vector()) / len(cycle)


def average_boundary_uv(
    cycle: list[bmesh.types.BMVert],
    uv_layer: bmesh.types.BMLayerItem | None,
) -> Vector:
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


def boundary_normal(vertex: bmesh.types.BMVert) -> Vector:
    normal = sum(
        (face.normal for face in vertex.link_faces),
        Vector((0.0, 0.0, 0.0)),
    )
    if normal.length <= 1.0e-9:
        return Vector((0.0, -1.0, 0.0))
    normal.normalize()
    # The anterior body surface faces negative Y in this asset.  Restrain any
    # inherited side-facing outlier so the support ring cannot fold backward.
    if normal.y > -0.25:
        normal = Vector((normal.x * 0.20, -1.0, normal.z * 0.20))
        normal.normalize()
    return normal


def tangent_cross_axis(tangent: Vector) -> Vector:
    tangent = tangent.normalized()
    cross_axis = Vector((0.0, -tangent.z, tangent.y))
    if cross_axis.length <= 1.0e-9:
        return Vector((0.0, 1.0, 0.0))
    return cross_axis.normalized()


def connect_rings(
    bm: bmesh.types.BMesh,
    first: list[bmesh.types.BMVert],
    second: list[bmesh.types.BMVert],
    *,
    material_index: int,
    new_faces: list[bmesh.types.BMFace],
) -> None:
    if len(first) != len(second):
        raise RuntimeError("ring vertex counts differ")
    for index in range(len(first)):
        following = (index + 1) % len(first)
        face = bm.faces.new(
            (
                first[index],
                first[following],
                second[following],
                second[index],
            )
        )
        face.material_index = material_index
        face.smooth = True
        new_faces.append(face)


def create_support_ring(
    bm: bmesh.types.BMesh,
    root: list[bmesh.types.BMVert],
    *,
    surface_class_value: int,
    surface_class_layer: bmesh.types.BMLayerItem,
    anatomy_class_layer: bmesh.types.BMLayerItem,
    anatomy_zone_layer: bmesh.types.BMLayerItem,
    anatomy_zone_value: int,
    regional_mix_layer: bmesh.types.BMLayerItem,
    uv_center: Vector,
    vertex_uv: dict[bmesh.types.BMVert, Vector],
    new_vertices: list[bmesh.types.BMVert],
    outward: float,
    vertical_offset: float,
) -> list[bmesh.types.BMVert]:
    support = []
    for root_vertex in root:
        coordinate = (
            root_vertex.co
            + boundary_normal(root_vertex) * outward
            + Vector((0.0, 0.0, vertical_offset))
        )
        vertex = bm.verts.new(coordinate)
        vertex[surface_class_layer] = surface_class_value
        vertex[anatomy_class_layer] = surface_class_value
        vertex[anatomy_zone_layer] = anatomy_zone_value
        vertex[regional_mix_layer] = 0.18
        vertex_uv[vertex] = uv_center.copy()
        support.append(vertex)
        new_vertices.append(vertex)
    return support


def create_ideal_ring(
    bm: bmesh.types.BMesh,
    *,
    center: Vector,
    tangent: Vector,
    angles: list[float],
    radius_x: float,
    radius_cross: float,
    surface_class_value: int,
    surface_class_layer: bmesh.types.BMLayerItem,
    anatomy_class_layer: bmesh.types.BMLayerItem,
    anatomy_zone_layer: bmesh.types.BMLayerItem,
    anatomy_zone_value: int,
    regional_mix_layer: bmesh.types.BMLayerItem,
    uv_center: Vector,
    vertex_uv: dict[bmesh.types.BMVert, Vector],
    new_vertices: list[bmesh.types.BMVert],
    progress: float,
    scrotal_pouch: bool,
) -> list[bmesh.types.BMVert]:
    cross_axis = tangent_cross_axis(tangent)
    ring = []
    for theta in angles:
        cosine = math.cos(theta)
        sine = math.sin(theta)
        coordinate = (
            center
            + Vector((1.0, 0.0, 0.0)) * (radius_x * cosine)
            + cross_axis * (radius_cross * sine)
        )
        if scrotal_pouch:
            # Shape one connected pouch.  The center receives a restrained
            # shallow raphe groove while the bilateral lobes descend slightly.
            normalized_x = coordinate.x / max(radius_x, 1.0e-6)
            medial = math.exp(-((normalized_x / 0.27) ** 2))
            bilateral = 1.0 - medial
            coordinate.y += 0.0014 * medial * progress
            coordinate.z -= 0.0023 * bilateral * progress
            if coordinate.x < 0.0:
                coordinate.z -= 0.0010 * progress
            else:
                coordinate.z += 0.0004 * progress
        vertex = bm.verts.new(coordinate)
        vertex[surface_class_layer] = surface_class_value
        vertex[anatomy_class_layer] = surface_class_value
        vertex[anatomy_zone_layer] = anatomy_zone_value
        vertex[regional_mix_layer] = min(1.0, 0.22 + 0.78 * progress)
        vertex_uv[vertex] = uv_center + Vector(
            (0.010 * cosine, 0.009 * sine)
        )
        ring.append(vertex)
        new_vertices.append(vertex)
    return ring


def create_transition_ring(
    bm: bmesh.types.BMesh,
    *,
    first: list[bmesh.types.BMVert],
    second: list[bmesh.types.BMVert],
    factor: float,
    surface_class_value: int,
    surface_class_layer: bmesh.types.BMLayerItem,
    anatomy_class_layer: bmesh.types.BMLayerItem,
    anatomy_zone_layer: bmesh.types.BMLayerItem,
    anatomy_zone_value: int,
    regional_mix_layer: bmesh.types.BMLayerItem,
    uv_center: Vector,
    vertex_uv: dict[bmesh.types.BMVert, Vector],
    new_vertices: list[bmesh.types.BMVert],
) -> list[bmesh.types.BMVert]:
    """Interpolate owner-boundary support into the first authored ring.

    Two intermediate rows prevent the irregular inherited root cycle from
    collapsing directly into an ideal ellipse and forming visible radial
    spikes at the attachment.
    """

    if len(first) != len(second):
        raise RuntimeError("transition ring vertex counts differ")
    eased = factor * factor * (3.0 - 2.0 * factor)
    ring = []
    for first_vertex, second_vertex in zip(first, second):
        vertex = bm.verts.new(
            first_vertex.co.lerp(second_vertex.co, eased)
        )
        vertex[surface_class_layer] = surface_class_value
        vertex[anatomy_class_layer] = surface_class_value
        vertex[anatomy_zone_layer] = anatomy_zone_value
        vertex[regional_mix_layer] = 0.18 + 0.08 * eased
        vertex_uv[vertex] = uv_center.copy()
        ring.append(vertex)
        new_vertices.append(vertex)
    return ring


def densify_path(
    keyframes: list[tuple[Vector, float, float]],
    *,
    steps_per_segment: int,
) -> list[tuple[Vector, float, float]]:
    """Add longitudinal support rows without changing authored endpoints."""

    if steps_per_segment < 1:
        raise ValueError("steps_per_segment must be positive")
    dense: list[tuple[Vector, float, float]] = []
    for index in range(len(keyframes) - 1):
        first_center, first_x, first_cross = keyframes[index]
        second_center, second_x, second_cross = keyframes[index + 1]
        for step in range(steps_per_segment):
            factor = step / steps_per_segment
            eased = factor * factor * (3.0 - 2.0 * factor)
            dense.append(
                (
                    first_center.lerp(second_center, eased),
                    first_x + (second_x - first_x) * eased,
                    first_cross + (second_cross - first_cross) * eased,
                )
            )
    dense.append(keyframes[-1])
    return dense


def build_branch(
    bm: bmesh.types.BMesh,
    *,
    root: list[bmesh.types.BMVert],
    path: list[tuple[Vector, float, float]],
    surface_class_value: int,
    surface_class_layer: bmesh.types.BMLayerItem,
    anatomy_class_layer: bmesh.types.BMLayerItem,
    anatomy_zone_layer: bmesh.types.BMLayerItem,
    regional_mix_layer: bmesh.types.BMLayerItem,
    uv_layer: bmesh.types.BMLayerItem | None,
    material_index: int,
    new_vertices: list[bmesh.types.BMVert],
    new_faces: list[bmesh.types.BMFace],
    scrotal_pouch: bool,
    root_zone: int,
    body_zone: int,
    distal_zone: int,
    distal_start_fraction: float,
) -> dict[str, object]:
    root_center = cycle_center(root)
    angles = arc_angles(root)
    uv_center = average_boundary_uv(root, uv_layer)
    vertex_uv: dict[bmesh.types.BMVert, Vector] = {}
    for vertex in root:
        vertex[anatomy_zone_layer] = root_zone
    support = create_support_ring(
        bm,
        root,
        surface_class_value=surface_class_value,
        surface_class_layer=surface_class_layer,
        anatomy_class_layer=anatomy_class_layer,
        anatomy_zone_layer=anatomy_zone_layer,
        anatomy_zone_value=root_zone,
        regional_mix_layer=regional_mix_layer,
        uv_center=uv_center,
        vertex_uv=vertex_uv,
        new_vertices=new_vertices,
        outward=0.0020 if not scrotal_pouch else 0.0016,
        vertical_offset=-0.0003 if not scrotal_pouch else -0.0007,
    )
    connect_rings(
        bm,
        root,
        support,
        material_index=material_index,
        new_faces=new_faces,
    )
    centers = [item[0] for item in path]
    first_center, first_radius_x, first_radius_cross = path[0]
    first_tangent = centers[1] - root_center
    first_ring = create_ideal_ring(
        bm,
        center=first_center,
        tangent=first_tangent,
        angles=angles,
        radius_x=first_radius_x,
        radius_cross=first_radius_cross,
        surface_class_value=surface_class_value,
        surface_class_layer=surface_class_layer,
        anatomy_class_layer=anatomy_class_layer,
        anatomy_zone_layer=anatomy_zone_layer,
        anatomy_zone_value=body_zone,
        regional_mix_layer=regional_mix_layer,
        uv_center=uv_center,
        vertex_uv=vertex_uv,
        new_vertices=new_vertices,
        progress=1.0 / len(path),
        scrotal_pouch=scrotal_pouch,
    )
    previous_ring = support
    for factor in (0.33, 0.66):
        transition = create_transition_ring(
            bm,
            first=support,
            second=first_ring,
            factor=factor,
            surface_class_value=surface_class_value,
            surface_class_layer=surface_class_layer,
            anatomy_class_layer=anatomy_class_layer,
            anatomy_zone_layer=anatomy_zone_layer,
            anatomy_zone_value=root_zone,
            regional_mix_layer=regional_mix_layer,
            uv_center=uv_center,
            vertex_uv=vertex_uv,
            new_vertices=new_vertices,
        )
        connect_rings(
            bm,
            previous_ring,
            transition,
            material_index=material_index,
            new_faces=new_faces,
        )
        previous_ring = transition
    connect_rings(
        bm,
        previous_ring,
        first_ring,
        material_index=material_index,
        new_faces=new_faces,
    )
    previous_ring = first_ring

    ring_measurements = [
        {
            "index": 0,
            "zone": body_zone,
            "center": list(
                sum((vertex.co for vertex in first_ring), Vector())
                / len(first_ring)
            ),
            "width_x_m": (
                max(vertex.co.x for vertex in first_ring)
                - min(vertex.co.x for vertex in first_ring)
            ),
        }
    ]
    for index, (center, radius_x, radius_cross) in enumerate(path[1:], start=1):
        previous_center = centers[index - 1]
        next_center = (
            centers[index + 1] if index + 1 < len(centers) else center
        )
        tangent = next_center - previous_center
        if tangent.length <= 1.0e-9:
            tangent = Vector((0.0, -1.0, -0.2))
        progress = (index + 1) / len(path)
        zone_value = (
            distal_zone
            if progress >= distal_start_fraction
            else body_zone
        )
        ring = create_ideal_ring(
            bm,
            center=center,
            tangent=tangent,
            angles=angles,
            radius_x=radius_x,
            radius_cross=radius_cross,
            surface_class_value=surface_class_value,
            surface_class_layer=surface_class_layer,
            anatomy_class_layer=anatomy_class_layer,
            anatomy_zone_layer=anatomy_zone_layer,
            anatomy_zone_value=zone_value,
            regional_mix_layer=regional_mix_layer,
            uv_center=uv_center,
            vertex_uv=vertex_uv,
            new_vertices=new_vertices,
            progress=progress,
            scrotal_pouch=scrotal_pouch,
        )
        connect_rings(
            bm,
            previous_ring,
            ring,
            material_index=material_index,
            new_faces=new_faces,
        )
        previous_ring = ring
        ring_measurements.append(
            {
                "index": index,
                "zone": zone_value,
                "center": list(
                    sum((vertex.co for vertex in ring), Vector()) / len(ring)
                ),
                "width_x_m": (
                    max(vertex.co.x for vertex in ring)
                    - min(vertex.co.x for vertex in ring)
                ),
            }
        )

    terminal_tangent = centers[-1] - centers[-2]
    terminal = centers[-1] + terminal_tangent.normalized() * (
        0.0012 if not scrotal_pouch else 0.0015
    )
    tip = bm.verts.new(terminal)
    tip[surface_class_layer] = surface_class_value
    tip[anatomy_class_layer] = surface_class_value
    tip[anatomy_zone_layer] = distal_zone
    tip[regional_mix_layer] = 1.0
    vertex_uv[tip] = uv_center.copy()
    new_vertices.append(tip)
    for index in range(len(previous_ring)):
        following = (index + 1) % len(previous_ring)
        face = bm.faces.new(
            (previous_ring[index], previous_ring[following], tip)
        )
        face.material_index = material_index
        face.smooth = True
        new_faces.append(face)

    if uv_layer is not None:
        for face in new_faces:
            for loop in face.loops:
                if loop.vert in vertex_uv:
                    loop[uv_layer].uv = vertex_uv[loop.vert]

    return {
        "root_center": list(root_center),
        "root_bounds": cycle_bounds(root),
        "root_vertex_count": len(root),
        "path": [
            {
                "center": list(center),
                "radius_x": radius_x,
                "radius_cross": radius_cross,
            }
            for center, radius_x, radius_cross in path
        ],
        "ring_measurements": ring_measurements,
        "terminal": list(terminal),
    }


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
body = next(
    obj
    for obj in bpy.context.scene.objects
    if obj.type == "MESH" and "BIOLOGICAL_ROBERT_STATIC_LIKENESS" in obj.name
)
source_sha256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
baseline_topology = topology_counts(body)
skin_index = next(
    index
    for index, material in enumerate(body.data.materials)
    if material and material.name == "MBLab_skin3"
)

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
uv_layer = bm.loops.layers.uv.active
surface_class_layer = bm.verts.layers.int.get("V23_Surface_Class")
if surface_class_layer is None:
    raise RuntimeError("R24 body is missing V23_Surface_Class")
regional_mix_layer = bm.verts.layers.float.get("V23_Regional_Mix")
if regional_mix_layer is None:
    regional_mix_layer = bm.verts.layers.float.new("V23_Regional_Mix")
anatomy_class_layer = bm.verts.layers.int.get("V25_Anatomy_Class")
if anatomy_class_layer is None:
    anatomy_class_layer = bm.verts.layers.int.new("V25_Anatomy_Class")
anatomy_zone_layer = bm.verts.layers.int.get("Adult_Anatomy_Zone")
if anatomy_zone_layer is None:
    anatomy_zone_layer = bm.verts.layers.int.new("Adult_Anatomy_Zone")

old_authored = [
    vertex for vertex in bm.verts if vertex[surface_class_layer] in {1, 2}
]
old_authored_counts = {
    "scrotal": sum(
        vertex[surface_class_layer] == 1 for vertex in old_authored
    ),
    "shaft": sum(
        vertex[surface_class_layer] == 2 for vertex in old_authored
    ),
}
bmesh.ops.delete(bm, geom=old_authored, context="VERTS")
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

attachment_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and all(
        abs(vertex.co.x) < 0.055
        and -0.180 < vertex.co.y < -0.005
        and 0.640 < vertex.co.z < 0.825
        for vertex in edge.verts
    )
]
attachment_components = [
    component
    for component in edge_components(attachment_edges)
    if len(component) >= 32
]
if len(attachment_components) != 2:
    raise RuntimeError(
        "expected two authored attachment cycles after branch removal, found "
        f"{[len(component) for component in attachment_components]}"
    )
attachment_cycles = [ordered_cycle(component) for component in attachment_components]
attachment_cycles.sort(key=lambda cycle: cycle_center(cycle).z, reverse=True)
shaft_root, scrotal_root = attachment_cycles
shaft_center = cycle_center(shaft_root)
scrotal_center = cycle_center(scrotal_root)

new_vertices: list[bmesh.types.BMVert] = []
new_faces: list[bmesh.types.BMFace] = []

# Compact high-root flaccid shaft.  The path and cross-sections are authored
# as a single continuous branch; the public/static appearance remains the
# normal spelling/body form and no donor identity surface is transferred.
shaft_keyframes = [
    (
        Vector((0.0, shaft_center.y - 0.0045, shaft_center.z - 0.0010)),
        0.0144,
        0.0152,
    ),
    (Vector((0.0, -0.097, 0.782)), 0.0152, 0.0142),
    (Vector((0.0, -0.105, 0.774)), 0.0158, 0.0138),
    (Vector((0.0, -0.111, 0.763)), 0.0161, 0.0136),
    (Vector((0.0, -0.116, 0.752)), 0.0159, 0.0133),
    (Vector((0.0, -0.120, 0.741)), 0.0140, 0.0117),
    # Distinct neck and restrained coronal flare.
    (Vector((0.0, -0.122, 0.734)), 0.0135, 0.0112),
    (Vector((0.0, -0.123, 0.729)), 0.0171, 0.0141),
    (Vector((0.0, -0.124, 0.723)), 0.0177, 0.0147),
    (Vector((0.0, -0.124, 0.718)), 0.0164, 0.0136),
    (Vector((0.0, -0.124, 0.714)), 0.0120, 0.0097),
    (Vector((0.0, -0.123, 0.711)), 0.0063, 0.0048),
]
shaft_path = densify_path(shaft_keyframes, steps_per_segment=3)
shaft_report = build_branch(
    bm,
    root=shaft_root,
    path=shaft_path,
    surface_class_value=2,
    surface_class_layer=surface_class_layer,
    anatomy_class_layer=anatomy_class_layer,
    anatomy_zone_layer=anatomy_zone_layer,
    regional_mix_layer=regional_mix_layer,
    uv_layer=uv_layer,
    material_index=skin_index,
    new_vertices=new_vertices,
    new_faces=new_faces,
    scrotal_pouch=False,
    root_zone=10,
    body_zone=11,
    distal_zone=12,
    distal_start_fraction=0.62,
)

# One connected scrotal/perineal pouch behind the shaft.  The root stays on
# the inherited owner-body boundary; subtle bilateral shaping is applied only
# after the support ring so the perineal transition remains continuous.
scrotal_keyframes = [
    (
        Vector(
            (
                0.0,
                scrotal_center.y - 0.0035,
                scrotal_center.z - 0.0015,
            )
        ),
        0.0210,
        0.0290,
    ),
    (Vector((0.0, -0.076, 0.721)), 0.0250, 0.0300),
    (Vector((0.0, -0.084, 0.710)), 0.0310, 0.0290),
    (Vector((0.0, -0.089, 0.698)), 0.0335, 0.0265),
    (Vector((0.0, -0.089, 0.688)), 0.0300, 0.0220),
    (Vector((0.0, -0.086, 0.681)), 0.0210, 0.0150),
    (Vector((0.0, -0.083, 0.677)), 0.0100, 0.0070),
]
scrotal_path = densify_path(scrotal_keyframes, steps_per_segment=3)
scrotal_report = build_branch(
    bm,
    root=scrotal_root,
    path=scrotal_path,
    surface_class_value=1,
    surface_class_layer=surface_class_layer,
    anatomy_class_layer=anatomy_class_layer,
    anatomy_zone_layer=anatomy_zone_layer,
    regional_mix_layer=regional_mix_layer,
    uv_layer=uv_layer,
    material_index=skin_index,
    new_vertices=new_vertices,
    new_faces=new_faces,
    scrotal_pouch=True,
    root_zone=22,
    body_zone=20,
    distal_zone=21,
    distal_start_fraction=0.24,
)

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
zone_metrics = {}
for code, name in ADULT_ANATOMY_ZONES.items():
    vertices = [
        vertex for vertex in bm.verts if vertex[anatomy_zone_layer] == code
    ]
    zone_metrics[name] = (
        bounds_for_vertices(vertices)
        if vertices
        else {"vertex_count": 0}
    )
connectivity = connectivity_evidence(bm, anatomy_zone_layer)
body_min_z = min(vertex.co.z for vertex in bm.verts)
body_max_z = max(vertex.co.z for vertex in bm.verts)
body_height_m = body_max_z - body_min_z

# All relationship values below are calculated from the constructed vertices.
# Rendered-ray measurements remain null until the dedicated visual-gap audit
# runs; this prototype must not claim that the inherited superior gap passed.
shaft_ring_measurements = shaft_report["ring_measurements"]
scrotal_ring_measurements = scrotal_report["ring_measurements"]
shaft_body_width_m = max(
    item["width_x_m"]
    for item in shaft_ring_measurements
    if item["zone"] == 11
)
glans_max_width_m = max(
    item["width_x_m"]
    for item in shaft_ring_measurements
    if item["zone"] == 12
)
glans_neck_width_m = min(
    item["width_x_m"]
    for item in shaft_ring_measurements
    if item["zone"] == 11
)
shaft_distal_center = zone_metrics["glans"]["center"]
scrotal_lowest_vertex = min(
    (
        vertex
        for vertex in bm.verts
        if vertex[anatomy_zone_layer] == 21
    ),
    key=lambda vertex: vertex.co.z,
)
scrotal_lowest_center = list(scrotal_lowest_vertex.co)
scrotal_bilateral_envelope_present = (
    zone_metrics["scrotal_envelope"]["bounds"]["min_x"] < -0.020
    and zone_metrics["scrotal_envelope"]["bounds"]["max_x"] > 0.020
)
raphe_midline_vertices = sum(
    abs(vertex.co.x) <= 0.0008
    for vertex in bm.verts
    if vertex[anatomy_zone_layer] == 21
)
scrotal_raphe_continuity_present = (
    raphe_midline_vertices >= len(scrotal_ring_measurements)
)
shaft_root_shared = all(
    any(
        any(neighbor[anatomy_zone_layer] == 0 for neighbor in face.verts)
        for face in vertex.link_faces
    )
    for vertex in shaft_root
)
scrotal_root_shared = all(
    any(
        any(neighbor[anatomy_zone_layer] == 0 for neighbor in face.verts)
        for face in vertex.link_faces
    )
    for vertex in scrotal_root
)
bm.to_mesh(body.data)
bm.free()
body.data.update()
for polygon in body.data.polygons:
    polygon.use_smooth = True
body.name = BODY_OUTPUT_NAME
body["status"] = "REJECTED ENGINEERING EVIDENCE — VISUAL REVIEW REQUIRED"
body["source_r24_sha256"] = source_sha256
body["method"] = (
    "R24 OWNER-DERIVED SURFACE + TAGGED-BRANCH REPLACEMENT + "
    "HIGH COMPACT SHAFT + CONNECTED BILOBED SCROTAL POUCH"
)
body["boolean_used"] = False
body["global_remesh_used"] = False
body["donor_surface_transferred"] = False
body["static_review_only"] = True
body["runtime_activation_allowed"] = False
body["movement_started"] = False
body["anatomy_estimation_label"] = (
    "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
)
body["adult_anatomy_zone_attribute"] = "Adult_Anatomy_Zone"
body["adult_anatomy_zone_codes"] = json.dumps(ADULT_ANATOMY_ZONES)

final_topology = topology_counts(body)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
report = {
    "schema_version": 1,
    "status": body["status"],
    "source": str(SOURCE),
    "source_sha256": source_sha256,
    "output": str(BLEND_PATH),
    "method": body["method"],
    "old_authored_vertex_counts": old_authored_counts,
    "attachment_cycle_count": len(attachment_cycles),
    "semantic_zone_attribute": "Adult_Anatomy_Zone",
    "semantic_zone_codes": ADULT_ANATOMY_ZONES,
    "semantic_zone_metrics": zone_metrics,
    "shaft": shaft_report,
    "scrotal_pouch": scrotal_report,
    "new_vertices": len(new_vertices),
    "new_faces": len(new_faces),
    "baseline_topology": baseline_topology,
    "final_topology": final_topology,
    "boolean_operations": 0,
    "global_remesh_operations": 0,
    "donor_surface_transferred": False,
    "coordinate_convention": "z_up_negative_y_front",
    "body_height_m": body_height_m,
    "primary_skin_component_count": connectivity[
        "primary_skin_component_count"
    ],
    "anatomy_primary_skin_same_component": connectivity[
        "anatomy_primary_skin_same_component"
    ],
    "main_skin_boundary_edges": connectivity["main_skin_boundary_edges"],
    "main_skin_nonmanifold_edges": connectivity[
        "main_skin_nonmanifold_edges"
    ],
    "separate_anatomy_mesh_count": connectivity[
        "separate_anatomy_mesh_count"
    ],
    "connectivity_evidence": connectivity,
    "front_superior_gap_rays": None,
    "side_root_gap_rays": None,
    "three_quarter_root_gap_rays": None,
    "side_silhouette_self_intersections": None,
    "shaft_root_surface_distance_m": 0.0 if shaft_root_shared else None,
    "scrotal_root_surface_distance_m": (
        0.0 if scrotal_root_shared else None
    ),
    "shaft_root_center": shaft_report["root_center"],
    "shaft_distal_center": shaft_distal_center,
    "scrotal_root_center": scrotal_report["root_center"],
    "scrotal_lowest_center": scrotal_lowest_center,
    "shaft_body_width_m": shaft_body_width_m,
    "glans_max_width_m": glans_max_width_m,
    "glans_neck_width_m": glans_neck_width_m,
    "scrotal_bilateral_envelope_present": (
        scrotal_bilateral_envelope_present
    ),
    "scrotal_raphe_continuity_present": (
        scrotal_raphe_continuity_present
    ),
    "perineal_transition_continuous": (
        scrotal_root_shared
        and connectivity["anatomy_primary_skin_same_component"]
    ),
    "landmark_measurement_truth": (
        "Coordinates, widths, and component membership are measured from "
        "constructed mesh vertices. Rendered gap rays are intentionally "
        "unmeasured/null for this branch-only prototype."
    ),
    "known_external_dependency": (
        "R24 superior pubic bridge/gap is outside this branch prototype and "
        "must be repaired and revalidated separately before any owner review."
    ),
    "scope": {
        "static_review_only": True,
        "movement": False,
        "activation": False,
        "runtime_attachment": False,
        "synthetic_robert": False,
        "kira": False,
        "clothing": False,
    },
}
REPORT_PATH.write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
print(BLEND_PATH)
print(json.dumps(report, indent=2))
