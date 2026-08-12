"""Inventory V1/V14/V15/V17/V18/V19 sources for a clean root rebuild.

Diagnostic only: no source blend is saved or modified.  The report compares
dominant-body topology, local pelvis boundaries, object separation, materials,
hair availability, and multi-hit front rays through the root zone.  The goal
is to identify the earliest Robert-likeness surface before the overlapping
sheet/tunnel defect entered the lineage.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "Avatar/private_owner_review/dual_robert_20260729"
SOURCES = {
    "foundation": BASE / "foundation/robert_fitting_foundation.blend",
    "v1": (
        BASE
        / "biological_static_likeness_v1/"
        "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend"
    ),
    "v1_previous_save": (
        BASE
        / "biological_static_likeness_v1/"
        "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V1.blend1"
    ),
    "v14": (
        BASE
        / "biological_static_likeness_v14_from_v1/"
        "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V14_FROM_V1.blend"
    ),
    "v15": (
        BASE
        / "biological_static_likeness_v15_from_v14/"
        "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V15_FROM_V14.blend"
    ),
    "v17": (
        BASE
        / "biological_static_likeness_v17_from_v15/"
        "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V17_FROM_V15.blend"
    ),
    "v18": (
        BASE
        / "biological_static_likeness_v18_from_v15/"
        "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V18_FROM_V15.blend"
    ),
    "v19": (
        BASE
        / "biological_static_likeness_v19_from_v18/"
        "BIOLOGICAL_ROBERT_STATIC_LIKENESS_V19_FROM_V18.blend"
    ),
}
OUT = BASE / "anatomy_reference_audit/V15_V18_SOURCE_BRANCH_INVENTORY.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def topology(obj: bpy.types.Object) -> dict[str, object]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
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
    }
    # Connected components are counted from mesh edges.  This distinguishes a
    # closed dominant skin plus normal eyes/teeth/nails from an actually
    # separate external anatomy object.
    unseen = set(bm.verts)
    component_sizes = []
    while unseen:
        seed = unseen.pop()
        size = 1
        stack = [seed]
        while stack:
            current = stack.pop()
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other in unseen:
                    unseen.remove(other)
                    stack.append(other)
                    size += 1
        component_sizes.append(size)
    component_sizes.sort(reverse=True)
    result["connected_components"] = len(component_sizes)
    result["largest_component_vertices"] = component_sizes[0]
    result["top_component_vertex_counts"] = component_sizes[:10]

    local_vertices = [
        vertex
        for vertex in bm.verts
        if (
            abs(vertex.co.x) <= 0.080
            and -0.190 <= vertex.co.y <= 0.120
            and 0.620 <= vertex.co.z <= 0.850
        )
    ]
    local_vertex_set = set(local_vertices)
    result["local_pelvis"] = {
        "vertices": len(local_vertices),
        "boundary_edges": sum(
            len(edge.link_faces) == 1
            and all(vertex in local_vertex_set for vertex in edge.verts)
            for edge in bm.edges
        ),
        "nonmanifold_gt2_edges": sum(
            len(edge.link_faces) > 2
            and all(vertex in local_vertex_set for vertex in edge.verts)
            for edge in bm.edges
        ),
        "bounds": {
            axis: [
                min(getattr(vertex.co, axis) for vertex in local_vertices),
                max(getattr(vertex.co, axis) for vertex in local_vertices),
            ]
            for axis in ("x", "y", "z")
        }
        if local_vertices
        else None,
    }
    bm.free()
    return result


def build_bvhs(mesh_objects: list[bpy.types.Object]):
    result = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in mesh_objects:
        if obj.hide_render:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        polygons = [tuple(poly.vertices) for poly in mesh.polygons]
        if vertices and polygons:
            result.append((obj.name, BVHTree.FromPolygons(vertices, polygons)))
        evaluated.to_mesh_clear()
    return result


def ray_hits(bvhs, x: float, z: float) -> list[dict[str, object]]:
    direction = Vector((0.0, 1.0, 0.0))
    hits = []
    for name, tree in bvhs:
        origin = Vector((x, -0.40, z))
        travelled = 0.0
        for _ in range(16):
            location, normal, face_index, distance = tree.ray_cast(
                origin, direction, 0.80 - travelled
            )
            if location is None:
                break
            hits.append(
                {
                    "object": name,
                    "y": round(float(location.y), 7),
                    "normal_y": round(float(normal.y), 7),
                    "face_index": int(face_index),
                }
            )
            advance = float(distance) + 0.00001
            travelled += advance
            origin = origin + direction * advance
            if travelled >= 0.80:
                break
    hits.sort(key=lambda item: (item["y"], item["object"]))
    return hits


records = {}
for label, source in SOURCES.items():
    if not source.exists():
        records[label] = {"path": str(source), "missing": True}
        continue
    bpy.ops.wm.open_mainfile(filepath=str(source))
    mesh_objects = [
        obj for obj in bpy.context.scene.objects if obj.type == "MESH"
    ]
    dominant = max(mesh_objects, key=lambda obj: len(obj.data.vertices))
    external_named = [
        obj
        for obj in mesh_objects
        if any(
            token in obj.name.lower()
            for token in ("anatomy", "penis", "shaft", "scrot")
        )
    ]
    hair_objects = [
        obj
        for obj in bpy.context.scene.objects
        if (
            "hair" in obj.name.lower()
            or "groom" in obj.name.lower()
            or bool(obj.get("static_review_component"))
            or "HAIR" in str(obj.get("component_type", "")).upper()
        )
    ]
    bvhs = build_bvhs(mesh_objects)
    samples = {}
    for x in (-0.010, 0.0, 0.010):
        for z in (0.775, 0.789, 0.805, 0.815, 0.823):
            samples[f"x={x:+.3f},z={z:.3f}"] = ray_hits(bvhs, x, z)
    records[label] = {
        "path": str(source),
        "sha256": sha256(source),
        "file_size": source.stat().st_size,
        "dominant_body": dominant.name,
        "dominant_topology": topology(dominant),
        "dominant_materials": [
            material.name for material in dominant.data.materials if material
        ],
        "mesh_objects": [
            {
                "name": obj.name,
                "vertices": len(obj.data.vertices),
                "faces": len(obj.data.polygons),
                "hidden_render": bool(obj.hide_render),
                "materials": [
                    material.name for material in obj.data.materials if material
                ],
            }
            for obj in mesh_objects
        ],
        "separate_external_anatomy_objects": [
            obj.name for obj in external_named
        ],
        "hair_objects": [
            {
                "name": obj.name,
                "type": obj.type,
                "hidden_render": bool(obj.hide_render),
            }
            for obj in hair_objects
        ],
        "root_zone_front_ray_hits": samples,
        "dominant_custom_properties": {
            key: dominant[key]
            for key in dominant.keys()
            if isinstance(dominant[key], (str, int, float, bool))
        },
    }

payload = {
    "schema": "kira.avatar.biological_robert.source_branch_inventory.v1",
    "diagnostic_only": True,
    "sources_modified_or_saved": False,
    "records": records,
    "interpretation": {
        "clean_pre_union_candidate": "v1 dominant body",
        "reason": (
            "The V1 dominant Robert body is the likeness/skin authority before "
            "the four separate external anatomy meshes were exact-unioned. Its "
            "central pelvis is closed and contains no local boundary. V14 and "
            "all V15/V17/V18/V19 descendants inherit the high-resolution union "
            "surface and the visible superior tunnel/sheet defect."
        ),
        "preservation_path": (
            "Use the V1 dominant body surface with the four V1 external "
            "anatomy objects excluded, reapply the bounded V15/V18 slimming "
            "coordinates, retain/import the V15/V18 removable hair, and "
            "rebuild the adult pubic-to-root topology directly on the clean "
            "V1 surface. Do not transplant a donor identity/body surface."
        ),
        "caution": (
            "V1 external anatomy is separate and visually unintegrated; V1 is "
            "a clean body-surface starting topology, not an acceptable final "
            "adult anatomy result."
        ),
    },
}
OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(OUT)
