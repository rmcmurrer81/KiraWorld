"""Build a private static anatomy trial from the clean V1 Robert substrate.

This branch deliberately starts before the V14 exact-union lineage.  It keeps
the V1 Robert skin/face surface, removes the four old separate anatomy objects,
and constructs one compact high-rooted external-anatomy volume.  The volume is
voxel-unified *before* it touches Robert, then unioned only with the largest
connected V1 skin component.  All other V1 mesh components are kept outside
the Boolean and rejoined afterward.

This is an engineering candidate, not an owner-approved body.  It cannot be
used for movement, activation, Synthetic Robert, Kira, clothing, or runtime.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    "biological_static_likeness_v1/BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
)
TRIAL = os.environ.get("KIRA_CLEAN_V1_TRIAL", "r27a")
OUT = (
    ROOT
    / "Avatar/private_owner_review/dual_robert_20260729/"
    f"biological_static_likeness_v23_{TRIAL}_clean_v1_implicit_trial"
)
OUT.mkdir(parents=True, exist_ok=True)
BODY_OUTPUT_NAME = (
    f"BIOLOGICAL_ROBERT_STATIC_LIKENESS_V23_{TRIAL.upper()}_"
    "CLEAN_V1_IMPLICIT_TRIAL"
)
BLEND_PATH = OUT / f"{BODY_OUTPUT_NAME}.blend"
REPORT_PATH = OUT / f"{TRIAL.upper()}_CLEAN_V1_IMPLICIT_BUILD_REPORT.json"

# Parameters remain explicit in the report so subsequent trials can be
# compared honestly.  World units are metres in this Robert branch.
Z_OFFSET = float(os.environ.get("KIRA_ANATOMY_Z_OFFSET", "0.000"))
Y_OFFSET = float(os.environ.get("KIRA_ANATOMY_Y_OFFSET", "0.000"))
VOXEL_SIZE = float(os.environ.get("KIRA_ANATOMY_VOXEL", "0.0022"))
BOOLEAN_SOLVER = os.environ.get("KIRA_BOOLEAN_SOLVER", "MANIFOLD").upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def topology_counts(mesh) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(len(edge.link_faces) == 1 for edge in bm.edges),
        "wire_edges": sum(len(edge.link_faces) == 0 for edge in bm.edges),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in bm.edges
        ),
        "degenerate_faces": sum(face.calc_area() < 1.0e-11 for face in bm.faces),
    }
    bm.free()
    return result


def connected_components(mesh) -> list[set[int]]:
    adjacency = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        first, second = edge.vertices
        adjacency[first].add(second)
        adjacency[second].add(first)
    remaining = set(range(len(mesh.vertices)))
    result = []
    while remaining:
        seed = remaining.pop()
        members = {seed}
        stack = [seed]
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    members.add(neighbor)
                    stack.append(neighbor)
        result.append(members)
    return sorted(result, key=len, reverse=True)


def keep_vertex_component(obj, keep_indices: set[int], invert: bool = False):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    doomed = [
        vertex
        for vertex in bm.verts
        if ((vertex.index in keep_indices) == invert)
    ]
    if doomed:
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def active_only(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def add_uv_ellipsoid(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    *,
    segments: int = 32,
    rings: int = 20,
):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=(
            location[0],
            location[1] + Y_OFFSET,
            location[2] + Z_OFFSET,
        ),
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def add_curved_capsule_chain(
    prefix: str,
    centers: list[tuple[float, float, float]],
    radii: list[tuple[float, float, float]],
):
    parts = []
    for index, (center, radius) in enumerate(zip(centers, radii)):
        parts.append(
            add_uv_ellipsoid(
                f"{prefix}_{index:02d}",
                center,
                radius,
                segments=32,
                rings=20,
            )
        )
    return parts


def add_swept_shaft(
    name: str,
    samples: list[
        tuple[
            tuple[float, float, float],
            tuple[float, float],
        ]
    ],
    *,
    radial_segments: int = 36,
):
    """Create one smooth curved root/shaft/glans surface.

    Each sample contains a center and the horizontal/depth radii.  A zero-radius
    final sample closes the distal tip.  The proximal end is capped but sits
    deeply inside the authored pubic-root transition before union.
    """

    centers = [
        Vector((center[0], center[1] + Y_OFFSET, center[2] + Z_OFFSET))
        for center, _radii in samples
    ]
    radii = [pair for _center, pair in samples]
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    ring_indices: list[list[int]] = []
    side = Vector((1.0, 0.0, 0.0))
    for index, (center, (radius_x, radius_depth)) in enumerate(
        zip(centers, radii)
    ):
        if radius_x <= 1.0e-8 or radius_depth <= 1.0e-8:
            ring_indices.append([len(vertices)])
            vertices.append(tuple(center))
            continue
        previous = centers[max(0, index - 1)]
        following = centers[min(len(centers) - 1, index + 1)]
        tangent = (following - previous).normalized()
        depth_axis = tangent.cross(side).normalized()
        ring = []
        for radial in range(radial_segments):
            angle = 2.0 * math.pi * radial / radial_segments
            point = (
                center
                + side * (math.cos(angle) * radius_x)
                + depth_axis * (math.sin(angle) * radius_depth)
            )
            ring.append(len(vertices))
            vertices.append(tuple(point))
        ring_indices.append(ring)
    for first, second in zip(ring_indices, ring_indices[1:]):
        if len(second) == 1:
            tip = second[0]
            for radial in range(radial_segments):
                faces.append(
                    (
                        first[radial],
                        first[(radial + 1) % radial_segments],
                        tip,
                    )
                )
        else:
            for radial in range(radial_segments):
                following = (radial + 1) % radial_segments
                faces.append(
                    (
                        first[radial],
                        first[following],
                        second[following],
                        second[radial],
                    )
                )
    faces.append(tuple(reversed(ring_indices[0])))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def local_topology_report(mesh) -> dict[str, object]:
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    roi_verts = {
        vertex
        for vertex in bm.verts
        if (
            abs(vertex.co.x) <= 0.125
            and -0.255 <= vertex.co.y <= 0.125
            and 0.610 <= vertex.co.z <= 0.875
        )
    }
    roi_edges = [
        edge for edge in bm.edges if any(vertex in roi_verts for vertex in edge.verts)
    ]
    roi_faces = [
        face for face in bm.faces if any(vertex in roi_verts for vertex in face.verts)
    ]
    result = {
        "roi_vertices": len(roi_verts),
        "roi_edges": len(roi_edges),
        "roi_faces": len(roi_faces),
        "roi_boundary_edges": sum(
            len(edge.link_faces) == 1 for edge in roi_edges
        ),
        "roi_wire_edges": sum(len(edge.link_faces) == 0 for edge in roi_edges),
        "roi_nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2 for edge in roi_edges
        ),
        "roi_degenerate_faces": sum(
            face.calc_area() < 1.0e-11 for face in roi_faces
        ),
        "bounds": {
            "x": [
                min((vertex.co.x for vertex in roi_verts), default=None),
                max((vertex.co.x for vertex in roi_verts), default=None),
            ],
            "y": [
                min((vertex.co.y for vertex in roi_verts), default=None),
                max((vertex.co.y for vertex in roi_verts), default=None),
            ],
            "z": [
                min((vertex.co.z for vertex in roi_verts), default=None),
                max((vertex.co.z for vertex in roi_verts), default=None),
            ],
        },
    }
    bm.free()
    return result


def create_review_skin_material(source_skin):
    material = bpy.data.materials.new("Robert_Integrated_Anatomy_Review_Skin")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    # A neutral pale warm skin match for the inherited V1 review material.
    # Blender stores this node color in linear space.  The previous value
    # converted to a much lighter display color than the adjacent V1 skin and
    # made the authored surface look pasted on.  This lower linear value
    # targets the neutral-lit V1 pelvis while retaining subtle regional
    # warmth; it does not alter Robert's preserved body material.
    shader.inputs["Base Color"].default_value = (0.135, 0.052, 0.038, 1.0)
    shader.inputs["Roughness"].default_value = 0.47
    if shader.inputs.get("Subsurface Weight"):
        shader.inputs["Subsurface Weight"].default_value = 0.065
    if shader.inputs.get("Subsurface Radius"):
        shader.inputs["Subsurface Radius"].default_value = (1.0, 0.42, 0.22)
    material.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    material.diffuse_color = (0.38, 0.215, 0.175, 1.0)
    material["purpose"] = "LOCAL INTEGRATED STATIC REVIEW SKIN"
    material["v1_skin_preserved_elsewhere"] = source_skin is not None
    return material


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
source_sha256 = sha256_file(SOURCE)
body = bpy.data.objects.get("BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1")
if body is None:
    raise RuntimeError("final V1 body object is missing")

# V1 intentionally stores the same MBLab skin datablock in two material slots,
# with the exterior body using the later slot.  BMesh/Boolean can collapse
# duplicate datablock slots and shift exterior skin faces onto the tongue
# material.  Give the exterior slot an identical-but-distinct datablock before
# any topology operation so its numeric material semantics remain stable.
v1_surface_skin_slot = 6
if (
    len(body.data.materials) <= v1_surface_skin_slot
    or body.data.materials[v1_surface_skin_slot] is None
):
    raise RuntimeError("V1 exterior skin material slot 6 is missing")
v1_surface_skin_material = body.data.materials[v1_surface_skin_slot].copy()
v1_surface_skin_material.name = "MBLab_skin3_V1_Exterior_Surface_Preserved"
body.data.materials[v1_surface_skin_slot] = v1_surface_skin_material

# Freeze only the rest-pose geometry necessary for a static topology trial.
active_only(body)
for modifier in list(body.modifiers):
    if modifier.type in {"ARMATURE", "CORRECTIVE_SMOOTH"}:
        bpy.ops.object.modifier_apply(modifier=modifier.name)

source_body_topology = topology_counts(body.data)
source_components = connected_components(body.data)
if not source_components:
    raise RuntimeError("V1 body has no connected components")
largest_component = source_components[0]
if len(largest_component) < 10000:
    raise RuntimeError(
        f"unexpected V1 dominant component size: {len(largest_component)}"
    )

# Delete the four old estimated separate pieces and every other external
# anatomy object.  They are neither retained nor used as hidden render assets.
removed_external_anatomy = []
for obj in list(bpy.data.objects):
    if "External_Anatomy" in obj.name:
        removed_external_anatomy.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)
if len(removed_external_anatomy) != 4:
    raise RuntimeError(
        "expected exactly four V1 separate external-anatomy objects; "
        f"removed {removed_external_anatomy}"
    )

# Bounded slimming on the untouched V1 coordinates.  The head/face, hands,
# central pelvis/root, and feet are explicitly outside every changed region.
slimmed_vertices = []
for vertex in body.data.vertices:
    co = vertex.co
    before = co.copy()
    # Torso only, fading out before the neck and excluding the pubic/root zone.
    if abs(co.x) < 0.39 and 0.92 <= co.z < 1.56:
        neck_fade = 1.0 - max(0.0, min(1.0, (co.z - 1.43) / 0.13))
        waist_weight = max(0.0, min(1.0, (1.30 - co.z) / 0.38))
        co.x *= 1.0 - neck_fade * (0.025 + 0.020 * waist_weight)
        co.y *= 1.0 - neck_fade * (0.032 + 0.020 * waist_weight)
    # Upper thighs only; central pubic/root vertices and lower legs are fixed.
    if 0.43 <= co.z <= 0.655 and 0.105 <= abs(co.x) <= 0.34:
        side_center = 0.19 if co.x > 0 else -0.19
        co.x = side_center + (co.x - side_center) * 0.970
        co.y *= 0.978
    # Upper arms only; hand/finger vertices are below this bounded band.
    if 1.00 <= co.z <= 1.43 and abs(co.x) >= 0.33:
        side_center = 0.315 if co.x > 0 else -0.315
        co.x = side_center + (co.x - side_center) * 0.975
        co.y *= 0.982
    if (co - before).length > 1.0e-10:
        slimmed_vertices.append(vertex.index)
body.data.update()

# Split only for the Boolean.  The largest V1 component is Robert's continuous
# exterior skin.  Eyes, teeth, lashes, nails, and other disconnected V1
# components stay in a separate untouched object until final rejoin.
skin = body.copy()
skin.data = body.data.copy()
skin.name = "Robert_V1_Primary_Skin_For_Local_Union"
bpy.context.collection.objects.link(skin)
keep_vertex_component(skin, largest_component, invert=False)

other_components = body.copy()
other_components.data = body.data.copy()
other_components.name = "Robert_V1_Untouched_NonSkin_Components"
bpy.context.collection.objects.link(other_components)
keep_vertex_component(other_components, largest_component, invert=True)

bpy.data.objects.remove(body, do_unlink=True)
body = None
skin_topology_before_union = topology_counts(skin.data)
other_topology = topology_counts(other_components.data)

source_skin = bpy.data.materials.get("MBLab_skin3")
review_skin = create_review_skin_material(source_skin)
skin.data.materials.append(review_skin)
review_skin_index = len(skin.data.materials) - 1

# Blender's manifold Boolean expects closed operands.  The V1 primary skin is
# locally closed at the pelvis but intentionally has three remote boundary
# loops at the mouth and eyes.  Cap those loops temporarily, tag the cap faces
# with a sentinel material, perform the pelvis Boolean, then remove the remote
# caps to restore V1's original openings exactly.
temporary_cap_material = bpy.data.materials.new("TEMP_BOOLEAN_CLOSURE_DO_NOT_RENDER")
temporary_cap_material.diffuse_color = (1.0, 0.0, 1.0, 1.0)
skin.data.materials.append(temporary_cap_material)
temporary_cap_material_index = len(skin.data.materials) - 1
cap_bm = bmesh.new()
cap_bm.from_mesh(skin.data)
cap_bm.verts.ensure_lookup_table()
cap_bm.edges.ensure_lookup_table()
cap_bm.faces.ensure_lookup_table()
remote_boundary_edges = [
    edge for edge in cap_bm.edges if len(edge.link_faces) == 1
]
cap_result = bmesh.ops.holes_fill(
    cap_bm, edges=remote_boundary_edges, sides=0
)
temporary_cap_faces = list(cap_result.get("faces", []))
for face in temporary_cap_faces:
    face.material_index = temporary_cap_material_index
bmesh.ops.recalc_face_normals(cap_bm, faces=cap_bm.faces)
cap_bm.to_mesh(skin.data)
skin_closed_signed_volume = cap_bm.calc_volume(signed=True)
cap_bm.free()
skin.data.update()
skin_topology_temporarily_closed = topology_counts(skin.data)

# The anatomical donor is authored as an overlapping family of smooth closed
# volumes.  It is compact and high-rooted: the root/pubic saddle is centered
# around z 0.79 and overlaps the unmodified V1 pubic surface deeply enough to
# avoid the old detached low-hanging construction.
parts = []
parts += add_curved_capsule_chain(
    "Robert_Implicit_Pubic_Root",
    [
        (0.000, -0.004, 0.808),
        (0.000, -0.024, 0.800),
    ],
    [
        (0.023, 0.037, 0.019),
        (0.021, 0.032, 0.019),
    ],
)
parts.append(
    add_uv_ellipsoid(
        "Robert_Implicit_Deep_Root_Junction",
        (0.000, -0.038, 0.790),
        (0.021, 0.036, 0.025),
        segments=36,
        rings=24,
    )
)
parts.append(
    add_swept_shaft(
        "Robert_Implicit_Swept_Shaft_Glans",
        [
            ((0.000, -0.054, 0.804), (0.0200, 0.0180)),
            ((0.000, -0.070, 0.795), (0.0205, 0.0185)),
            ((0.000, -0.084, 0.783), (0.0200, 0.0180)),
            ((0.000, -0.094, 0.770), (0.0195, 0.0175)),
            ((0.000, -0.101, 0.756), (0.0190, 0.0170)),
            ((0.000, -0.105, 0.744), (0.0185, 0.0165)),
            ((0.000, -0.106, 0.735), (0.0175, 0.0155)),
            ((0.000, -0.106, 0.731), (0.000, 0.000)),
        ],
        radial_segments=40,
    )
)
# A short rotationally swept glans provides a modest coronal shoulder and a
# tapered rounded distal dome.  A UV sphere produced a toy-like ball; this
# bounded profile follows the authorized structural reference while retaining
# Robert-specific placement and proportions.
parts.append(
    add_swept_shaft(
        "Robert_Implicit_Glans_Surface",
        [
            ((0.000, -0.106, 0.738), (0.0195, 0.0175)),
            ((0.000, -0.107, 0.734), (0.0205, 0.0180)),
            ((0.000, -0.108, 0.729), (0.0210, 0.0185)),
            ((0.000, -0.109, 0.723), (0.0208, 0.0185)),
            ((0.000, -0.109, 0.716), (0.0195, 0.0178)),
            ((0.000, -0.109, 0.710), (0.0170, 0.0160)),
            ((0.000, -0.109, 0.705), (0.0130, 0.0125)),
            ((0.000, -0.109, 0.701), (0.0060, 0.0058)),
            ((0.000, -0.109, 0.699), (0.000, 0.000)),
        ],
        radial_segments=48,
    )
)
parts += add_curved_capsule_chain(
    "Robert_Implicit_Scrotal_Root",
    [
        (0.000, -0.020, 0.748),
        (0.000, -0.037, 0.733),
    ],
    [
        (0.028, 0.035, 0.024),
        (0.025, 0.030, 0.022),
    ],
)
for side, center_z in ((-1.0, 0.712), (1.0, 0.709)):
    pouch = add_uv_ellipsoid(
        f"Robert_Implicit_Scrotal_Pouch_{'L' if side < 0 else 'R'}",
        (0.0100 * side, -0.048, center_z),
        (0.0185, 0.0260, 0.0300),
        segments=40,
        rings=28,
    )
    for vertex in pouch.data.vertices:
        vertical = max(-1.0, min(1.0, vertex.co.z / 0.030))
        # Keep the bilateral form compact and pear-shaped: narrower at the
        # superior attachment, with modest dependent fullness.  The two lobes
        # overlap before remeshing and never survive as detached objects.
        width_factor = 0.82 + 0.18 * (1.0 - vertical) * 0.5
        vertex.co.x *= width_factor
        vertex.co.y *= 0.90 + 0.10 * (1.0 - vertical) * 0.5
    pouch.data.update()
    parts.append(pouch)
parts.append(
    add_uv_ellipsoid(
        "Robert_Implicit_Scrotal_Sack_Envelope",
        (0.000, -0.045, 0.718),
        (0.028, 0.026, 0.027),
        segments=40,
        rings=28,
    )
)

# Posterior perineal transition overlaps the clean body and the one scrotal
# pouch.  It is intentionally compact so the side silhouette does not resemble
# a second hanging sphere.
parts.append(
    add_uv_ellipsoid(
        "Robert_Implicit_Perineal_Transition",
        (0.000, 0.018, 0.714),
        (0.023, 0.026, 0.021),
        segments=36,
        rings=24,
    )
)

for part in parts:
    # Match the target's slot ordering so Boolean material transfer keeps
    # the authored surface on the dedicated local review-skin material.
    part.data.materials.clear()
    for material in skin.data.materials:
        part.data.materials.append(material)
    for polygon in part.data.polygons:
        polygon.material_index = review_skin_index
active_only(parts[0])
for part in parts[1:]:
    part.select_set(True)
bpy.ops.object.join()
anatomy = bpy.context.object
anatomy.name = "Robert_Local_Implicit_Anatomy_Intermediate"

# One voxel pass on the compact donor only.  This removes internal overlapping
# primitive sheets before the donor ever intersects Robert's V1 skin.
anatomy.data.remesh_voxel_size = VOXEL_SIZE
anatomy.data.remesh_voxel_adaptivity = 0.0
active_only(anatomy)
bpy.ops.object.voxel_remesh()
for polygon in anatomy.data.polygons:
    polygon.use_smooth = True
smooth_modifier = anatomy.modifiers.new(
    "CompactImplicitSurfaceFairing", "SMOOTH"
)
smooth_modifier.factor = 0.38
smooth_modifier.iterations = 5
active_only(anatomy)
bpy.ops.object.modifier_apply(modifier=smooth_modifier.name)
anatomy_bm = bmesh.new()
anatomy_bm.from_mesh(anatomy.data)
bmesh.ops.recalc_face_normals(anatomy_bm, faces=anatomy_bm.faces)
anatomy_signed_volume = anatomy_bm.calc_volume(signed=True)
anatomy_bm.to_mesh(anatomy.data)
anatomy_bm.free()
anatomy.data.update()
anatomy_topology_before_union = topology_counts(anatomy.data)
anatomy_components = connected_components(anatomy.data)
removed_donor_fragment_sizes = []
if len(anatomy_components) > 1:
    # Voxel remesh can occasionally leave a sub-voxel closed fragment where a
    # deeply overlapping primitive was entirely consumed.  It is not part of
    # the authored anatomy surface.  Remove only tiny detached fragments; a
    # second substantial component remains a hard failure.
    anatomy_components.sort(key=len, reverse=True)
    detached = anatomy_components[1:]
    if detached and all(len(component) <= 64 for component in detached):
        removed_donor_fragment_sizes = [len(component) for component in detached]
        cleanup_bm = bmesh.new()
        cleanup_bm.from_mesh(anatomy.data)
        cleanup_bm.verts.ensure_lookup_table()
        bmesh.ops.delete(
            cleanup_bm,
            geom=[
                cleanup_bm.verts[index]
                for component in detached
                for index in component
            ],
            context="VERTS",
        )
        bmesh.ops.recalc_face_normals(cleanup_bm, faces=cleanup_bm.faces)
        cleanup_bm.to_mesh(anatomy.data)
        cleanup_bm.free()
        anatomy.data.update()
        anatomy_components = connected_components(anatomy.data)
if len(anatomy_components) != 1:
    raise RuntimeError(
        "authored implicit anatomy did not become one connected volume: "
        f"{[len(component) for component in anatomy_components]}"
    )

# Exact union only against the clean primary V1 skin component.
active_only(skin)
modifier = skin.modifiers.new("CleanV1_LocalImplicitAnatomyUnion", "BOOLEAN")
modifier.operation = "UNION"
modifier.solver = BOOLEAN_SOLVER
modifier.object = anatomy
# The inherited V1 SUBSURF/DISPLACE modifiers remain live for review.  The
# topology operation must run on the preserved low-resolution skin *before*
# either one; otherwise Blender evaluates the Boolean against a displaced
# subdivision surface and can create thousands of overlapping intersection
# edges.
while list(skin.modifiers).index(modifier) > 0:
    bpy.ops.object.modifier_move_up(modifier=modifier.name)
bpy.ops.object.modifier_apply(modifier=modifier.name)
boolean_raw_topology = topology_counts(skin.data)
bpy.data.objects.remove(anatomy, do_unlink=True)

# Restore the three remote V1 mouth/eye openings by deleting only the tagged
# temporary cap faces, then perform conservative cleanup.  No global remesh
# touches Robert's body.
bm = bmesh.new()
bm.from_mesh(skin.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
faces_to_remove = [
    face
    for face in bm.faces
    if face.material_index == temporary_cap_material_index
    and face.calc_center_median().z > 1.58
]
restored_remote_cap_face_count = len(faces_to_remove)
if faces_to_remove:
    bmesh.ops.delete(bm, geom=faces_to_remove, context="FACES")
# The manifold solver may leave a few tiny cap-only fragments after the three
# remote sentinel caps are deleted.  The pre-Boolean V1 skin was one connected
# component, so retain only the largest connected skin component here.  This
# does not touch the pelvis form; it removes only detached temporary-cap
# artifacts created around the mouth/eye holes.
bm.verts.ensure_lookup_table()
unseen = set(bm.verts)
post_cap_components = []
while unseen:
    seed = unseen.pop()
    members = {seed}
    stack = [seed]
    while stack:
        current = stack.pop()
        for edge in current.link_edges:
            neighbor = edge.other_vert(current)
            if neighbor in unseen:
                unseen.remove(neighbor)
                members.add(neighbor)
                stack.append(neighbor)
    post_cap_components.append(members)
post_cap_components.sort(key=len, reverse=True)
removed_temporary_fragment_sizes = [
    len(component) for component in post_cap_components[1:]
]
if len(post_cap_components) > 1:
    bmesh.ops.delete(
        bm,
        geom=[
            vertex
            for component in post_cap_components[1:]
            for vertex in component
        ],
        context="VERTS",
    )
# Repair only zero-area Boolean intersection faces.  This is deliberately
# narrower than the rejected generic cleanup pass: no valid local edge is
# considered, and the post-operation topology gate still requires a closed
# two-manifold surface.
bm.faces.ensure_lookup_table()
degenerate_faces_before_targeted_cleanup = [
    face for face in bm.faces if face.calc_area() < 1.0e-11
]
targeted_degenerate_edge_count = 0
if degenerate_faces_before_targeted_cleanup:
    targeted_edges = {
        edge
        for face in degenerate_faces_before_targeted_cleanup
        for edge in face.edges
    }
    targeted_degenerate_edge_count = len(targeted_edges)
    bmesh.ops.dissolve_degenerate(
        bm,
        dist=2.0e-6,
        edges=list(targeted_edges),
    )
# MANIFOLD returns a closed, intersection-clean primary surface.  A generic
# remove-doubles pass at this stage can collapse legitimate tiny intersection
# triangles and *create* boundary/wire/nonmanifold defects, so no post-Boolean
# welding or dissolving is performed.
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(skin.data)
bm.free()
skin.data.update()
for polygon in skin.data.polygons:
    polygon.use_smooth = True

# Constrain the dedicated anatomy material to the actual local authored
# surface.  Manifold Boolean material propagation can otherwise label a large
# downstream part of the target skin as the operand material even though the
# geometry itself is correct.
current_review_skin_index = next(
    index
    for index, material in enumerate(skin.data.materials)
    if material == review_skin
)
current_v1_surface_skin_index = next(
    index
    for index, material in enumerate(skin.data.materials)
    if material == v1_surface_skin_material
)
# Keep V1's material on every preserved body face.  New implicit faces do not
# inherit usable V1 UV coordinates, so assign the dedicated procedural match
# to the complete compact anatomy volume.  A narrow geometric envelope, rather
# than face area, avoids the alternating white/dark bands seen when large donor
# quads were accidentally sent back to zero-UV V1 skin.
for polygon in skin.data.polygons:
    center = polygon.center
    local_anatomy_surface = (
        abs(center.x) <= 0.050
        and 0.675 <= center.z <= 0.825
        and (
            center.y <= -0.075
            or (center.z <= 0.750 and center.y <= 0.005)
        )
    )
    if (
        polygon.material_index == current_review_skin_index
        and local_anatomy_surface
    ):
        pass
    elif polygon.material_index == current_review_skin_index:
        polygon.material_index = current_v1_surface_skin_index
skin.data.update()

skin_topology_after_union = topology_counts(skin.data)
skin_components_after_union = connected_components(skin.data)
skin_local_report = local_topology_report(skin.data)

# Keep the untouched V1 eyes/teeth/nails and other non-skin components as a
# separate preserved object.  Blender's Object Join collapses V1's intentional
# duplicate skin slots and can remap the body surface to tongue/nail materials.
# Separate rendering is visually identical and keeps every source material
# assignment truthful.  The primary skin itself remains one connected surface.
final_body = skin
final_body.name = BODY_OUTPUT_NAME
final_body.data.name = f"{BODY_OUTPUT_NAME}_MESH"
other_components.name = f"{BODY_OUTPUT_NAME}_PRESERVED_NONSKIN"
other_components.data.name = (
    f"{BODY_OUTPUT_NAME}_PRESERVED_NONSKIN_MESH"
)
other_components["source"] = "UNTOUCHED V1 NONSKIN COMPONENTS"
other_components["static_review_only"] = True
for polygon in final_body.data.polygons:
    polygon.use_smooth = True

final_primary_topology = topology_counts(final_body.data)
final_non_skin_topology = topology_counts(other_components.data)
final_topology = {
    key: final_primary_topology[key] + final_non_skin_topology[key]
    for key in final_primary_topology
}
final_local_report = local_topology_report(final_body.data)
final_primary_components = connected_components(final_body.data)
final_non_skin_components = connected_components(other_components.data)
final_components = final_primary_components + final_non_skin_components
final_components.sort(key=len, reverse=True)

topology_gate = (
    len(skin_components_after_union) == 1
    and skin_local_report["roi_boundary_edges"] == 0
    and skin_local_report["roi_wire_edges"] == 0
    and skin_local_report["roi_nonmanifold_gt2_edges"] == 0
    and skin_local_report["roi_degenerate_faces"] == 0
)
final_body["status"] = (
    "ENGINEERING CANDIDATE — VISUAL REVIEW REQUIRED"
    if topology_gate
    else "BLOCKED — LOCAL TOPOLOGY GATE FAILED"
)
final_body["source_foundation"] = "FINAL V1 DOMINANT BODY"
final_body["source_sha256"] = source_sha256
final_body["external_anatomy_objects_retained"] = False
final_body["v14_or_later_union_mesh_used"] = False
final_body["local_implicit_method"] = (
    "COMPACT DONOR VOXEL-UNIFIED BEFORE MANIFOLD UNION WITH V1 PRIMARY SKIN"
)
final_body["global_body_remesh_used"] = False
final_body["v1_face_preserved"] = True
final_body["v1_skin_preserved"] = True
final_body["head_touched_by_slimming"] = False
final_body["hands_touched_by_slimming"] = False
final_body["central_pelvis_touched_by_slimming"] = False
final_body["static_review_only"] = True
final_body["owner_approved"] = False
final_body["runtime_activation_allowed"] = False
final_body["movement_started"] = False
final_body["synthetic_robert_started"] = False

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

report = {
    "schema": "kira.avatar.biological_robert.clean_v1_implicit_trial.v1",
    "status": final_body["status"],
    "owner_approved": False,
    "source": str(SOURCE),
    "source_sha256": source_sha256,
    "output": str(BLEND_PATH),
    "output_sha256": sha256_file(BLEND_PATH),
    "trial": TRIAL,
    "parameters": {
        "z_offset_m": Z_OFFSET,
        "y_offset_m": Y_OFFSET,
        "donor_voxel_size_m": VOXEL_SIZE,
        "boolean_solver": BOOLEAN_SOLVER,
    },
    "removed_v1_external_anatomy_objects": removed_external_anatomy,
    "removed_external_anatomy_count": len(removed_external_anatomy),
    "v14_or_later_union_mesh_used": False,
    "source_body_topology": source_body_topology,
    "source_component_vertex_counts_top10": [
        len(component) for component in source_components[:10]
    ],
    "largest_v1_skin_component_vertices": len(largest_component),
    "slimming": {
        "method": "BOUNDED V1-COORDINATE REFINEMENT",
        "moved_vertex_count": len(slimmed_vertices),
        "head_or_face_touched": False,
        "hands_or_fingers_touched": False,
        "central_pelvis_or_root_touched": False,
        "feet_touched": False,
    },
    "skin_topology_before_union": skin_topology_before_union,
    "skin_topology_temporarily_closed_for_boolean": (
        skin_topology_temporarily_closed
    ),
    "skin_temporarily_closed_signed_volume_m3": skin_closed_signed_volume,
    "temporary_remote_cap_face_count": len(temporary_cap_faces),
    "restored_remote_cap_face_count": restored_remote_cap_face_count,
    "removed_temporary_cap_fragment_vertex_counts": (
        removed_temporary_fragment_sizes
    ),
    "targeted_degenerate_cleanup": {
        "faces_before": len(degenerate_faces_before_targeted_cleanup),
        "candidate_edges": targeted_degenerate_edge_count,
        "method": "DISSOLVE_DEGENERATE_ON_ZERO_AREA_FACE_EDGES_ONLY",
    },
    "untouched_non_skin_topology": other_topology,
    "anatomy_intermediate_topology": anatomy_topology_before_union,
    "anatomy_intermediate_signed_volume_m3": anatomy_signed_volume,
    "anatomy_intermediate_component_count": len(anatomy_components),
    "boolean_raw_topology_before_cleanup": boolean_raw_topology,
    "skin_topology_after_union": skin_topology_after_union,
    "skin_component_count_after_union": len(skin_components_after_union),
    "skin_component_vertex_counts_after_union": [
        len(component) for component in skin_components_after_union[:10]
    ],
    "skin_local_topology_after_union": skin_local_report,
    "final_topology": final_topology,
    "final_primary_skin_topology": final_primary_topology,
    "final_preserved_non_skin_topology": final_non_skin_topology,
    "final_object_structure": {
        "primary_skin_object": final_body.name,
        "preserved_non_skin_object": other_components.name,
        "reason_not_joined": (
            "PRESERVE V1 MATERIAL SLOT SEMANTICS; PRIMARY SKIN REMAINS "
            "ONE CONNECTED SURFACE"
        ),
    },
    "final_component_count": len(final_components),
    "final_component_vertex_counts_top10": [
        len(component) for component in final_components[:10]
    ],
    "final_local_topology": final_local_report,
    "technical_local_topology_gate_pass": topology_gate,
    "visual_gate": "REQUIRED — FRONT/SIDE/THREE-QUARTER MUST ALL BE SUPERIOR",
    "method_truth": {
        "global_body_voxel_remesh": False,
        "compact_anatomy_intermediate_voxel_remesh": True,
        "closed_manifold_union_with_clean_v1_primary_skin": True,
        "v14_plus_union_mesh_used": False,
        "old_window_patch_used": False,
        "separate_anatomy_objects_in_output": False,
    },
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
REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(BLEND_PATH)
print(json.dumps(report, indent=2))
