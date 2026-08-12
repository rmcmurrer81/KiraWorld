"""Build one compact connected anatomy volume on the clean V24C foundation.

R1-R6 used two separately rooted appendage branches.  Even when their seams
were topologically closed, encoded side views read as floating pieces.  R7
instead opens one bounded pubic window and grows one nested, hand-authored
volume from that single boundary.  Its shallow contours carry the integrated
pubic/perineal/scrotal envelope while its deeper contours narrow into a short
neutral shaft and glans.  This is a static engineering trial, not approval.

The authorized adult reference informs only structural relationships.  Robert
placement and scale remain private person-specific parameters.  No Boolean,
metaball, donor identity surface, or voxel-remeshed donor patch is used.
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
    "biological_static_likeness_v24c_r7_unified_anatomy_volume"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_NAME = (
    "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V24C_"
    "R7_UNIFIED_ANATOMY_VOLUME"
)
BLEND_PATH = OUT / f"{BODY_NAME}.blend"
REPORT_PATH = OUT / "V24C_R7_UNIFIED_ANATOMY_VOLUME_REPORT.json"

PATCH_SUBDIVISION_CUTS = 5
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
    result = []
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
        result.append(component)
    return result


def ordered_cycle(component):
    adjacency = {}
    for edge in component:
        first, second = edge.verts
        adjacency.setdefault(first, []).append(second)
        adjacency.setdefault(second, []).append(first)
    if not adjacency or set(len(values) for values in adjacency.values()) != {2}:
        raise RuntimeError("root boundary is not one degree-two cycle")
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
            raise RuntimeError("root boundary repeats before closure")
        result.append(following)
        previous, current = current, following
    return result


def cycle_center(cycle):
    return sum((vertex.co for vertex in cycle), Vector()) / len(cycle)


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


def perimeter_angles(cycle):
    """Return a monotone full turn following the boundary perimeter."""

    lengths = [
        (cycle[(index + 1) % len(cycle)].co - cycle[index].co).length
        for index in range(len(cycle))
    ]
    total = sum(lengths)
    values = [math.pi / 2.0]
    travelled = 0.0
    for index in range(1, len(cycle)):
        travelled += lengths[index - 1]
        values.append(math.pi / 2.0 - math.tau * travelled / total)
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


def connect_cycles(
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
        raise RuntimeError("cycle counts differ")
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


def contour_point(spec, angle):
    """Create one point on a nested anatomical silhouette.

    A lower lateral width bias creates a compact bilateral pouch in the
    shallower contours.  The deeper contours lift and narrow so the pouch caps
    behind a short shaft instead of becoming a second detached tube.
    """

    sine = math.sin(angle)
    cosine = math.cos(angle)
    center_z = spec["center_z"]
    half_height = spec["half_height"]
    z = center_z + half_height * sine
    lower = max(0.0, -sine)
    upper = max(0.0, sine)
    width_scale = (
        1.0
        + spec.get("lower_bulge", 0.0) * lower * lower
        - spec.get("upper_taper", 0.0) * upper * upper
    )
    x = spec["half_width"] * width_scale * cosine
    # Mild bilateral shaping: lateral lower points hang slightly lower than
    # the midline, while the superior central bridge remains high and narrow.
    lateral = abs(cosine)
    z -= spec.get("bilateral_drop", 0.0) * lower * lateral
    if x > 0.0:
        z -= spec.get("right_asymmetry", 0.0) * lower
    return Vector((x, spec["y"], z))


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
            for pair in sorted(self_pairs)[:40]
        ],
        "first_patch_retained_pairs": [
            {
                "faces": list(pair),
                "patch_center": patch_centers[pair[0]],
                "retained_center": retained_centers[pair[1]],
            }
            for pair in sorted(retained_pairs)[:40]
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
authored_layer = bm.verts.layers.int.get("V24C_R7_Unified_Volume")
if authored_layer is None:
    authored_layer = bm.verts.layers.int.new("V24C_R7_Unified_Volume")
mix_layer = bm.verts.layers.float.get("V24C_R7_Regional_Mix")
if mix_layer is None:
    mix_layer = bm.verts.layers.float.new("V24C_R7_Regional_Mix")

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

# One contiguous window replaces the two detached-looking R1-R6 roots.
cut_faces = [
    face
    for face in bm.faces
    if face.normal.y < -0.65
    and all(
        abs(vertex.co.x) <= 0.0360
        and -0.125 <= vertex.co.y <= -0.090
        and 0.7230 <= vertex.co.z <= 0.8200
        for vertex in face.verts
    )
]
if len(cut_faces) < 20:
    raise RuntimeError(f"unified root window too small: {len(cut_faces)}")
bmesh.ops.delete(bm, geom=cut_faces, context="FACES")
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

new_boundary_edges = [
    edge
    for edge in bm.edges
    if len(edge.link_faces) == 1
    and edge_key(edge) not in baseline_boundaries
    and all(
        abs(vertex.co.x) <= 0.040
        and -0.130 <= vertex.co.y <= -0.085
        and 0.715 <= vertex.co.z <= 0.825
        for vertex in edge.verts
    )
]
components = edge_components(new_boundary_edges)
if len(components) != 1:
    raise RuntimeError(
        "expected one unified root cycle, found "
        f"{[len(component) for component in components]}"
    )
root = ordered_cycle(components[0])
root_center = cycle_center(root)
root_coordinates = [list(vertex.co) for vertex in root]
angles = perimeter_angles(root)
uv_value = average_uv(root, uv_layer)

specs = [
    {
        "name": "integrated_skin_transition",
        "y": -0.1180,
        "center_z": 0.769,
        "half_height": 0.047,
        "half_width": 0.032,
        "lower_bulge": 0.08,
        "upper_taper": 0.18,
        "bilateral_drop": 0.0010,
        "right_asymmetry": 0.0005,
        "zone": 10,
    },
    {
        "name": "perineal_scrotal_envelope_1",
        "y": -0.1225,
        "center_z": 0.764,
        "half_height": 0.043,
        "half_width": 0.026,
        "lower_bulge": 0.22,
        "upper_taper": 0.32,
        "bilateral_drop": 0.0020,
        "right_asymmetry": 0.0007,
        "zone": 11,
    },
    {
        "name": "perineal_scrotal_envelope_2",
        "y": -0.1270,
        "center_z": 0.760,
        "half_height": 0.038,
        "half_width": 0.022,
        "lower_bulge": 0.30,
        "upper_taper": 0.36,
        "bilateral_drop": 0.0028,
        "right_asymmetry": 0.0008,
        "zone": 11,
    },
    {
        "name": "shaft_transition",
        "y": -0.1310,
        "center_z": 0.766,
        "half_height": 0.031,
        "half_width": 0.017,
        "lower_bulge": 0.20,
        "upper_taper": 0.30,
        "bilateral_drop": 0.0015,
        "right_asymmetry": 0.0005,
        "zone": 12,
    },
    {
        "name": "short_shaft",
        "y": -0.1350,
        "center_z": 0.767,
        "half_height": 0.025,
        "half_width": 0.0142,
        "lower_bulge": 0.08,
        "upper_taper": 0.12,
        "bilateral_drop": 0.0006,
        "right_asymmetry": 0.0003,
        "zone": 12,
    },
    {
        "name": "glans_shoulder",
        "y": -0.1380,
        "center_z": 0.765,
        "half_height": 0.020,
        "half_width": 0.0148,
        "lower_bulge": 0.04,
        "upper_taper": 0.06,
        "bilateral_drop": 0.0002,
        "right_asymmetry": 0.0002,
        "zone": 13,
    },
    {
        "name": "glans_front",
        "y": -0.1400,
        "center_z": 0.764,
        "half_height": 0.015,
        "half_width": 0.0120,
        "lower_bulge": 0.0,
        "upper_taper": 0.0,
        "bilateral_drop": 0.0,
        "right_asymmetry": 0.0,
        "zone": 13,
    },
]

new_faces = []
first_ideal = [
    contour_point(specs[0], angle)
    for angle in angles
]
previous = root
transition_rows = []
for factor in (0.08, 0.20, 0.42, 0.68, 0.88):
    eased = factor * factor * (3.0 - 2.0 * factor)
    row = []
    for root_vertex, ideal in zip(root, first_ideal):
        preserved = root_vertex.co + Vector((0.0, -0.0020 * factor, 0.0))
        coordinate = preserved.lerp(ideal, eased)
        vertex = bm.verts.new(coordinate)
        vertex[zone_layer] = 10
        vertex[authored_layer] = 1
        vertex[mix_layer] = 0.16 + 0.12 * eased
        row.append(vertex)
    connect_cycles(
        bm,
        previous,
        row,
        material_index=central_material,
        uv_layer=uv_layer,
        uv_value=uv_value,
        new_faces=new_faces,
    )
    previous = row
    transition_rows.append([list(vertex.co) for vertex in row])

ring_reports = []
for ring_index, spec in enumerate(specs):
    ring = []
    for angle in angles:
        vertex = bm.verts.new(contour_point(spec, angle))
        vertex[zone_layer] = spec["zone"]
        vertex[authored_layer] = 1
        vertex[mix_layer] = min(1.0, 0.28 + 0.11 * ring_index)
        ring.append(vertex)
    connect_cycles(
        bm,
        previous,
        ring,
        material_index=central_material,
        uv_layer=uv_layer,
        uv_value=uv_value,
        new_faces=new_faces,
    )
    previous = ring
    ring_reports.append(
        {
            "name": spec["name"],
            "y": spec["y"],
            "z_min": min(vertex.co.z for vertex in ring),
            "z_max": max(vertex.co.z for vertex in ring),
            "x_min": min(vertex.co.x for vertex in ring),
            "x_max": max(vertex.co.x for vertex in ring),
            "zone": ZONE_NAMES[spec["zone"]],
        }
    )

terminal = bm.verts.new(Vector((0.0, -0.1420, specs[-1]["center_z"])))
terminal[zone_layer] = 13
terminal[authored_layer] = 1
terminal[mix_layer] = 1.0
for index in range(len(previous)):
    following = (index + 1) % len(previous)
    make_face(
        bm,
        (previous[index], previous[following], terminal),
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
body["status"] = "ENGINEERING TRIAL - VISUAL REVIEW REQUIRED"
body["source_authority"] = "V24C CLEAN CONTINUOUS PUBIC BRIDGE"
body["method"] = "ONE ROOT + ONE NESTED AUTHORED ANATOMY VOLUME"
body["boolean_used"] = False
body["metaball_used"] = False
body["voxel_remesh_used"] = False
body["donor_identity_surface_used"] = False
body["owner_approved"] = False
body["movement_started"] = False
body["runtime_activation_allowed"] = False
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema": "kira.avatar.biological_robert.v24c.r7.unified_volume.v1",
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
        "single_contiguous_root_window": True,
        "single_connected_authored_volume": True,
        "boolean": False,
        "metaballs": False,
        "voxel_remesh": False,
        "donor_identity_surface": False,
        "global_body_change": False,
        "r5_and_r6_rejected_reason": (
            "two separately rooted branches encoded as floating shaft/pouch "
            "pieces even when their local seams were topologically closed"
        ),
    },
    "root": {
        "cut_face_count": len(cut_faces),
        "boundary_vertices": len(root),
        "center": list(root_center),
        "coordinates": root_coordinates,
    },
    "transition_rows": transition_rows,
    "contours": ring_reports,
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
            "surface reads as one generic blob rather than anatomy",
            "root looks pasted or leaves a gap",
            "side view reads as floating geometry",
            "shaft is too long or thick",
            "glans is spherical or oversized",
            "scrotal envelope is toy-like instead of compact and bilateral",
        ],
    },
    "reusability_boundary": {
        "candidate_reusable_method_only_after_owner_approval": [
            "single bounded root window",
            "nested authored contour volume",
            "encoded neutral-view and intersection gates",
        ],
        "robert_private_person_specific_data": [
            "root position and proportions inferred from protected photos",
            "Robert likeness body mesh and materials",
            "Robert-specific body parameters",
        ],
        "avatar_builder_promotion": (
            "BLOCKED until Biological Robert static owner approval and "
            "separate proof that a generalized method works on other adults"
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
