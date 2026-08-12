"""Build a direct continuous anatomy surface cage on the clean V24C bridge.

R8 and R9 proved the local graft plumbing but visually failed as cylinders,
beads, hanging lobes, and hard panels.  R10 removes the implicit-volume graft
entirely.  It fills the V24C body opening with one dense radial surface whose
continuous depth field encodes a high root, tapered neutral shaft/distal
relationship, posterior-inferior pouch, and perineal continuity.

This is a private static engineering trial.  It is not approved, activated,
rigged, or reusable as a generic Avatar Builder template.  No donor body,
donor topology, or donor identity surface enters Biological Robert.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
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
    "biological_static_likeness_v24c_r10_direct_surface_cage"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_NAME = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_"
    "R10_DIRECT_SURFACE_CAGE"
)
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24C_R10_DIRECT_SURFACE_CAGE_REPORT.json"
PATCH_SUBDIVISION_CUTS = 5
RADIAL_RING_COUNT = 18

ZONE_NAMES = {
    1: "pubic_bridge",
    10: "integrated_root",
    11: "perineal_scrotal_envelope",
    12: "shaft_body",
    13: "distal_form",
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


def connect_cycles(
    bm,
    outer,
    inner,
    *,
    material_index,
    uv_layer,
    uv_value,
    new_faces,
):
    if len(outer) != len(inner):
        raise RuntimeError("surface cage cycles have different counts")
    for index in range(len(outer)):
        following = (index + 1) % len(outer)
        make_face(
            bm,
            (
                outer[index],
                outer[following],
                inner[following],
                inner[index],
            ),
            material_index=material_index,
            uv_layer=uv_layer,
            uv_value=uv_value,
            new_faces=new_faces,
        )


def interpolate_control(z, controls):
    if z <= controls[0][0]:
        return controls[0][1]
    if z >= controls[-1][0]:
        return controls[-1][1]
    for (first_z, first_value), (next_z, next_value) in zip(
        controls,
        controls[1:],
    ):
        if first_z <= z <= next_z:
            factor = (z - first_z) / (next_z - first_z)
            eased = factor * factor * (3.0 - 2.0 * factor)
            return first_value + (next_value - first_value) * eased
    return 0.0


def elliptical_bump(x, z, *, center_x, center_z, radius_x, radius_z, depth):
    radial = (
        ((x - center_x) / radius_x) ** 2
        + ((z - center_z) / radius_z) ** 2
    )
    if radial >= 1.0:
        return 0.0
    return depth * max(0.0, 1.0 - radial) ** 0.72


def anatomy_projection(x, z):
    """Return anterior depth and the dominant authored anatomy zone."""

    # Broad shallow root/apron.  It gives the smaller high structures a
    # continuous transition to the V24C pubic surface without a hard panel.
    root = elliptical_bump(
        x,
        z,
        center_x=0.0,
        center_z=0.779,
        radius_x=0.0245,
        radius_z=0.0390,
        depth=0.0070,
    )
    perineal = elliptical_bump(
        x,
        z,
        center_x=0.0005,
        center_z=0.738,
        radius_x=0.0205,
        radius_z=0.0320,
        depth=0.0100,
    )

    # One smooth longitudinal profile replaces the former cylinder and bead
    # chain.  Width and anterior depth change continuously from high root
    # through shaft to a subtly broader distal relationship.
    width = interpolate_control(
        z,
        [
            (0.724, 0.0),
            (0.733, 0.0060),
            (0.740, 0.0098),
            (0.748, 0.0108),
            (0.756, 0.0097),
            (0.770, 0.0088),
            (0.785, 0.0091),
            (0.798, 0.0097),
            (0.807, 0.0),
        ],
    )
    shaft_depth = interpolate_control(
        z,
        [
            (0.724, 0.0),
            (0.733, 0.0110),
            (0.740, 0.0270),
            (0.748, 0.0315),
            (0.756, 0.0290),
            (0.770, 0.0265),
            (0.785, 0.0220),
            (0.798, 0.0120),
            (0.807, 0.0),
        ],
    )
    shaft = 0.0
    if width > 0.0 and abs(x) < width:
        cross_section = math.sqrt(max(0.0, 1.0 - (x / width) ** 2))
        shaft = shaft_depth * cross_section ** 0.82

    # One pouch behind and below the shaft.  Small bounded asymmetry avoids
    # perfect toy symmetry while a shallow raphe does not split the surface.
    scrotal_center_z = 0.7145 - 0.0008 * math.tanh(-x / 0.004)
    scrotal = elliptical_bump(
        x,
        z,
        center_x=0.0010,
        center_z=scrotal_center_z,
        radius_x=0.0188,
        radius_z=0.0255,
        depth=0.0185,
    )
    if scrotal > 0.0 and abs(x) < 0.0035:
        raphe = (
            0.00055
            * (1.0 - abs(x) / 0.0035)
            * max(0.0, 1.0 - abs(z - 0.714) / 0.022)
        )
        scrotal = max(0.0, scrotal - raphe)

    values = {
        10: root,
        11: max(perineal, scrotal),
        12: shaft,
        13: shaft if 0.733 <= z <= 0.755 else 0.0,
    }
    positive = [value for value in values.values() if value > 0.0]
    if not positive:
        return 0.0, 10
    # A high-order norm blends overlapping structures without adding the
    # obvious stacked shoulders produced by summing primitive volumes.
    projection = sum(value**7 for value in positive) ** (1.0 / 7.0)
    dominant = max(values, key=values.get)
    return projection, dominant


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

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
uv_layer = bm.loops.layers.uv.active
zone_layer = bm.verts.layers.int.get("Adult_Anatomy_Zone")
if zone_layer is None:
    zone_layer = bm.verts.layers.int.new("Adult_Anatomy_Zone")
authored_layer = bm.verts.layers.int.get("V24C_R10_Direct_Surface_Cage")
if authored_layer is None:
    authored_layer = bm.verts.layers.int.new(
        "V24C_R10_Direct_Surface_Cage"
    )
mix_layer = bm.verts.layers.float.get("V24C_R10_Regional_Mix")
if mix_layer is None:
    mix_layer = bm.verts.layers.float.new("V24C_R10_Regional_Mix")

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

center = sum((vertex.co for vertex in body_root), Vector()) / len(body_root)
center.x = 0.0
center.z = 0.759
new_faces = []
new_vertices = []
previous_cycle = body_root
for ring_number in range(RADIAL_RING_COUNT - 1, 0, -1):
    radial = ring_number / RADIAL_RING_COUNT
    ring = []
    for boundary_vertex in body_root:
        coordinate = center.lerp(boundary_vertex.co, radial)
        projection, zone = anatomy_projection(coordinate.x, coordinate.z)
        boundary_fade = (1.0 - radial * radial) ** 2
        coordinate.y -= projection * boundary_fade
        vertex = bm.verts.new(coordinate)
        vertex[zone_layer] = zone
        vertex[authored_layer] = 1
        vertex[mix_layer] = 1.0 - radial
        ring.append(vertex)
        new_vertices.append(vertex)
    connect_cycles(
        bm,
        previous_cycle,
        ring,
        material_index=central_material,
        uv_layer=uv_layer,
        uv_value=uv_value,
        new_faces=new_faces,
    )
    previous_cycle = ring

center_projection, center_zone = anatomy_projection(center.x, center.z)
center.y -= center_projection
center_vertex = bm.verts.new(center)
center_vertex[zone_layer] = center_zone
center_vertex[authored_layer] = 1
center_vertex[mix_layer] = 1.0
new_vertices.append(center_vertex)
for index in range(len(previous_cycle)):
    following = (index + 1) % len(previous_cycle)
    make_face(
        bm,
        (
            previous_cycle[index],
            previous_cycle[following],
            center_vertex,
        ),
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
body["method"] = "DIRECT CONTINUOUS RADIAL SURFACE CAGE"
body["donor_identity_surface_used"] = False
body["owner_approved"] = False
body["movement_started"] = False
body["runtime_activation_allowed"] = False
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema": "kira.avatar.biological_robert.v24c.r10.direct_surface_cage.v1",
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
            "shaft/body/distal relationship",
            "scrotum behind and below the shaft",
            "perineal continuity",
        ],
        "estimated_detail_label": (
            "ESTIMATED FROM AUTHORIZED ADULT ANATOMY REFERENCE"
        ),
        "private_local_only": True,
        "delete_only_after_explicit_owner_approval": True,
    },
    "method_truth": {
        "v24c_clean_bridge_used": True,
        "single_contiguous_body_root": True,
        "single_connected_local_surface": True,
        "direct_surface_cage": True,
        "radial_rings": RADIAL_RING_COUNT,
        "implicit_volume": False,
        "voxel_remesh": False,
        "boolean": False,
        "metaballs": False,
        "donor_geometry": False,
        "donor_identity_surface": False,
        "global_body_change": False,
        "r8_r9_rejected_reason": (
            "implicit guides encoded piston, beads, hanging pouch, and panel"
        ),
    },
    "roots": {
        "body_cut_face_count": len(cut_faces),
        "body_root_vertices": body_root_count,
        "directly_shared_body_boundary": True,
        "separate_bridge_or_panel": False,
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
            "side view reads as a flat relief or floating geometry",
            "shaft reads as a cylinder or bead chain",
            "distal relationship is spherical or ring-like",
            "pouch is toy-like instead of compact and posterior-inferior",
            "normal views do not read as plausible adult male anatomy",
        ],
    },
    "reusability_boundary": {
        "candidate_reusable_method_only_after_owner_approval": [
            "direct bounded body-opening surface cage",
            "continuous normalized profile controls",
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
print(str(BLEND_PATH))
print(json.dumps(report, indent=2))
