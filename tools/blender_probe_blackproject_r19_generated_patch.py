#!/usr/bin/env python3
"""Generate a clean R19 patch from only BlackProject's exact 34-point interface.

No vertex or face from the rejected 702-vertex source interior is retained.
The source boundary coordinates, native deform data, and permitted material
binding are the only source-patch inputs.  This is an append-only inactive
private probe and never writes the licensed source or live runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_author_kira_r7_adult_surface_trial as helpers  # noqa: E402
from blender_build_kira_temporary_functional_body_blackproject import ordered_boundary_cycles  # noqa: E402
from blender_exact_mesh_intersections import exact_nonadjacent_intersection_report  # noqa: E402


SOURCE_SHA256 = "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"
ADULT_MESH_NAME = "Ariel_Mesh_Genitalia_0"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def smoothstep01(value: float) -> float:
    value = max(0.0, min(1.0, float(value)))
    return value * value * (3.0 - 2.0 * value)


def gaussian(value: float, center: float, sigma: float) -> float:
    return math.exp(-0.5 * ((float(value) - float(center)) / float(sigma)) ** 2)


def weight_digest(obj: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    names = {group.index: group.name for group in obj.vertex_groups}
    for vertex in obj.data.vertices:
        digest.update(f"v|{vertex.index}".encode("ascii"))
        for element in sorted(vertex.groups, key=lambda row: int(row.group)):
            digest.update(
                f"|{names.get(element.group, element.group)}:{float(element.weight):.9f}".encode("utf-8")
            )
        digest.update(b"\n")
    return digest.hexdigest()


def reconstruct_from_boundary(
    adult: bpy.types.Object,
    boundary_cycle: list[int],
    *,
    cuts: int,
    poke_passes: int,
    fairing_iterations: int,
    fairing_strength: float,
    feature_strength: float,
) -> dict[str, object]:
    source_vertex_count = len(adult.data.vertices)
    source_face_count = len(adult.data.polygons)
    boundary_set = set(boundary_cycle)
    boundary_before = {
        int(index): adult.data.vertices[int(index)].co.copy() for index in boundary_cycle
    }
    def coordinate_key(point: Vector) -> tuple[float, float, float]:
        return tuple(round(float(value), 9) for value in point)

    expected_boundary_segments = {
        tuple(
            sorted(
                (
                    coordinate_key(boundary_before[int(boundary_cycle[index])]),
                    coordinate_key(
                        boundary_before[int(boundary_cycle[(index + 1) % len(boundary_cycle)])]
                    ),
                )
            )
        )
        for index in range(len(boundary_cycle))
    }
    bm = bmesh.new()
    bm.from_mesh(adult.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    deform = bm.verts.layers.deform.active
    boundary_deform = {
        int(index): dict(bm.verts[int(index)][deform]) if deform is not None else {}
        for index in boundary_cycle
    }
    # Delete every source face first, including the few faces composed only of
    # interface vertices.  This is the hard proof that no rejected source
    # interior face can survive into the generated derivative.
    bmesh.ops.delete(bm, geom=list(bm.faces), context="FACES_ONLY")
    interior = [vert for vert in bm.verts if int(vert.index) not in boundary_set]
    bmesh.ops.delete(bm, geom=interior, context="VERTS")
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    if bm.faces:
        raise RuntimeError("source interior faces survived deletion")
    # The source also has two rejected interior chords whose endpoints both
    # happen to lie on the interface.  Retain only the exact ordered-cycle
    # segments; otherwise those source edges would bias the new triangulation.
    extra_edges = [
        edge
        for edge in bm.edges
        if tuple(sorted(coordinate_key(vert.co) for vert in edge.verts))
        not in expected_boundary_segments
    ]
    if extra_edges:
        bmesh.ops.delete(bm, geom=extra_edges, context="EDGES")
    boundary_edges = list(bm.edges)
    if len(boundary_edges) != 34:
        raise RuntimeError(f"expected 34 surviving boundary edges, got {len(boundary_edges)}")
    fill = bmesh.ops.triangle_fill(bm, edges=boundary_edges, use_beauty=True)
    if not fill.get("geom"):
        raise RuntimeError("triangle_fill produced no geometry")
    bm.faces.ensure_lookup_table()
    initial_fill_faces = len(bm.faces)
    if initial_fill_faces != 32:
        raise RuntimeError(f"34-point disk should produce 32 triangles, got {initial_fill_faces}")

    internal_edges = [edge for edge in bm.edges if len(edge.link_faces) == 2]
    if poke_passes > 0:
        # Repeatedly add one weighted center per face.  Unlike subdividing the
        # boundary, this raises interior resolution while the exact 34
        # interface vertices and edges remain unchanged.
        for _pass in range(int(poke_passes)):
            bmesh.ops.poke(
                bm,
                faces=list(bm.faces),
                offset=0.0,
                center_mode="MEAN_WEIGHTED",
            )
    elif cuts > 0:
        bmesh.ops.subdivide_edges(
            bm,
            edges=internal_edges,
            cuts=int(cuts),
            use_grid_fill=True,
            smooth=0.0,
        )
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.faces.index_update()

    # Recover the 34 original boundary vertices by exact coordinate match;
    # subdividing internal edges cannot add or split a boundary edge.
    boundary_vertices: set[int] = set()
    for vert in bm.verts:
        if any((vert.co - point).length <= 1.0e-9 for point in boundary_before.values()):
            boundary_vertices.add(int(vert.index))
    if len(boundary_vertices) != 34:
        raise RuntimeError(f"generated patch boundary drifted: {len(boundary_vertices)}")

    # Harmonic relaxation of generated interior only.  The initial triangulated
    # fill provides a deterministic disk; relaxation removes long diagonal
    # creases while the exact interface stays pinned.
    maximum_step_local = 0.0
    for _iteration in range(int(fairing_iterations)):
        snapshot = [vert.co.copy() for vert in bm.verts]
        pending: dict[int, Vector] = {}
        for vert in bm.verts:
            index = int(vert.index)
            if index in boundary_vertices:
                continue
            neighbors = {int(edge.other_vert(vert).index) for edge in vert.link_edges}
            if len(neighbors) < 3:
                continue
            average = sum((snapshot[row] for row in neighbors), Vector((0.0, 0.0, 0.0))) / len(neighbors)
            delta = (average - snapshot[index]) * float(fairing_strength)
            if delta.length > 0.025:
                delta.normalize()
                delta *= 0.025
            pending[index] = snapshot[index] + delta
            maximum_step_local = max(maximum_step_local, float(delta.length))
        for index, value in pending.items():
            bm.verts[index].co = value
        bm.normal_update()

    # External landmark field is evaluated in world meters and then converted
    # back to the imported object's local coordinates.  The patch remains one
    # capped continuous external skin and makes no internal-function claim.
    inverse = adult.matrix_world.inverted()
    feature_changed = 0
    feature_maximum_world = 0.0
    memberships = {
        "mons_pubis": 0,
        "left_labium_majus": 0,
        "right_labium_majus": 0,
        "left_labium_minus": 0,
        "right_labium_minus": 0,
        "clitoral_hood_and_glans": 0,
        "vestibule": 0,
        "external_urethral_recess": 0,
        "vaginal_opening_recess": 0,
        "fourchette": 0,
        "perineal_transition": 0,
    }
    for vert in bm.verts:
        if int(vert.index) in boundary_vertices:
            continue
        world = adult.matrix_world @ vert.co
        x, y, z = map(float, world)
        front = 1.0 - smoothstep01((y + 0.024) / 0.030)
        vertical_window = smoothstep01((z - 0.826) / 0.012) * (
            1.0 - smoothstep01((z - 0.906) / 0.012)
        )
        if front * vertical_window <= 0.0:
            continue
        mons = gaussian(x, 0.0, 0.033) * gaussian(z, 0.899, 0.022)
        left_major = gaussian(x, 0.0115, 0.0075) * gaussian(z, 0.868, 0.024)
        right_major = gaussian(x, -0.0115, 0.0075) * gaussian(z, 0.868, 0.024)
        left_minor = gaussian(x, 0.0040, 0.0027) * gaussian(z, 0.863, 0.017)
        right_minor = gaussian(x, -0.0040, 0.0027) * gaussian(z, 0.863, 0.017)
        hood = gaussian(x, 0.0, 0.0052) * gaussian(z, 0.884, 0.0065)
        glans = gaussian(x, 0.0, 0.0024) * gaussian(z, 0.879, 0.0028)
        vestibule = gaussian(x, 0.0, 0.0058) * gaussian(z, 0.8635, 0.012)
        urethral = gaussian(x, 0.0, 0.0021) * gaussian(z, 0.870, 0.0023)
        vaginal = gaussian(x, 0.0, 0.0048) * gaussian(z, 0.8555, 0.0067)
        fourchette = gaussian(x, 0.0, 0.0065) * gaussian(z, 0.844, 0.0058)
        perineum = gaussian(x, 0.0, 0.011) * gaussian(z, 0.835, 0.0075)
        relief = (
            0.00115 * mons
            + 0.00265 * (left_major + right_major)
            + 0.00120 * (left_minor + right_minor)
            + 0.00095 * hood
            + 0.00050 * glans
            - 0.00080 * vestibule
            - 0.00058 * urethral
            - 0.00118 * vaginal
            + 0.00038 * fourchette
            - 0.00018 * perineum
        )
        delta_y = max(-0.0032, min(0.0020, -relief * feature_strength * front * vertical_window))
        if abs(delta_y) <= 1.0e-8:
            continue
        world.y += delta_y
        vert.co = inverse @ world
        feature_changed += 1
        feature_maximum_world = max(feature_maximum_world, abs(delta_y))
        values = {
            "mons_pubis": mons,
            "left_labium_majus": left_major,
            "right_labium_majus": right_major,
            "left_labium_minus": left_minor,
            "right_labium_minus": right_minor,
            "clitoral_hood_and_glans": max(hood, glans),
            "vestibule": vestibule,
            "external_urethral_recess": urethral,
            "vaginal_opening_recess": vaginal,
            "fourchette": fourchette,
            "perineal_transition": perineum,
        }
        for name, value in values.items():
            if value * front * vertical_window > 0.16:
                memberships[name] += 1
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    exact = exact_nonadjacent_intersection_report(bm, include_pair_details=False)
    bm.to_mesh(adult.data)
    bm.free()
    adult.data.update()
    for polygon in adult.data.polygons:
        polygon.use_smooth = True
    adult.data.update()
    boundary_after = ordered_boundary_cycles(adult)
    return {
        "method": "generated_constrained_34_point_disk_v1",
        "source_vertex_count": source_vertex_count,
        "source_face_count": source_face_count,
        "source_interior_vertex_count_retained": 0,
        "source_face_count_retained": 0,
        "source_boundary_vertex_count_retained": 34,
        "initial_triangle_fill_face_count": initial_fill_faces,
        "subdivision_cuts_on_internal_edges": int(cuts),
        "interior_poke_refinement_passes": int(poke_passes),
        "generated_vertex_count": len(adult.data.vertices),
        "generated_face_count": len(adult.data.polygons),
        "generated_boundary_cycles": [len(row) for row in boundary_after],
        "fairing_iterations": int(fairing_iterations),
        "fairing_strength": float(fairing_strength),
        "maximum_fairing_step_world_m": maximum_step_local * 0.01,
        "feature_strength": float(feature_strength),
        "feature_changed_vertex_count": feature_changed,
        "maximum_feature_displacement_world_m": feature_maximum_world,
        "landmark_support_vertex_counts": memberships,
        "exact_nonadjacent_intersections": exact,
        "internal_anatomy_or_function_claimed": False,
        "source_boundary_deform_records": {
            str(index): {str(group): float(value) for group, value in sorted(values.items())}
            for index, values in sorted(boundary_deform.items())
        },
    }


def add_lights(scene: bpy.types.Scene) -> None:
    for name, location, energy, size in (
        ("R19_KEY", (2.0, -3.0, 2.9), 760.0, 4.0),
        ("R19_FILL", (-2.3, -2.0, 1.7), 430.0, 3.0),
        ("R19_RIM", (0.8, 2.2, 2.5), 620.0, 3.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector((0.0, 0.0, 1.0)) - obj.location).to_track_quat("-Z", "Y").to_euler()


def render(scene, camera, path, location, target, scale):
    camera.location = location
    camera.data.ortho_scale = scale
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> int:
    args = parse_args()
    config = json.loads(Path(args.config).resolve(strict=True).read_text(encoding="utf-8"))
    root = Path(config["project_root"]).resolve(strict=True)
    source = (root / config["source_path"]).resolve(strict=True)
    output_dir = (root / config["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("source hash mismatch")
    helpers.clear_scene()
    imported = helpers.import_glb(source)
    meshes = {obj.data.name: obj for obj in imported if obj.type == "MESH"}
    adult = meshes[ADULT_MESH_NAME]
    cycles = ordered_boundary_cycles(adult)
    if len(cycles) != 1 or len(cycles[0]) != 34:
        raise ValueError("source boundary mismatch")
    source_weight_digest = weight_digest(adult)
    generated = reconstruct_from_boundary(
        adult,
        cycles[0],
        cuts=int(config["subdivision_cuts"]),
        poke_passes=int(config.get("poke_passes", 0)),
        fairing_iterations=int(config["fairing_iterations"]),
        fairing_strength=float(config["fairing_strength"]),
        feature_strength=float(config["feature_strength"]),
    )
    removed_hair = []
    for obj in list(imported):
        if obj.type == "MESH" and obj.data.name.startswith("Hair_"):
            removed_hair.append(obj.data.name)
            bpy.data.objects.remove(obj, do_unlink=True)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.012, 0.018, 0.026)
    add_lights(scene)
    camera_data = bpy.data.cameras.new("R19_GENERATED_PATCH_CAMERA")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R19_GENERATED_PATCH_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    render(scene, camera, output_dir / "body_bald_front.png", (0.0, -3.0, 0.88), (0.0, 0.0, 0.88), 1.80)
    render(scene, camera, output_dir / "adult_surface_front.png", (0.0, -2.0, 0.865), (0.0, -0.025, 0.865), 0.19)
    render(scene, camera, output_dir / "adult_surface_three_quarter.png", (0.22, -0.34, 0.87), (0.0, -0.02, 0.865), 0.19)
    render(scene, camera, output_dir / "adult_surface_side.png", (0.30, 0.0, 0.865), (0.0, -0.01, 0.865), 0.19)
    blend = output_dir / "r19_generated_patch_probe.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), check_existing=False)
    report = {
        "schema_version": 1,
        "mode": "R19_GENERATED_PATCH_PRIVATE_INACTIVE_PROBE",
        "source": {
            "path": str(source.relative_to(root)).replace("\\", "/"),
            "sha256": SOURCE_SHA256,
            "license": "CC BY 4.0",
            "source_weight_digest": source_weight_digest,
            "source_unchanged": sha256_file(source) == SOURCE_SHA256,
        },
        "generated_patch": generated,
        "hair_components_removed": sorted(removed_hair),
        "runtime_or_assignment_changed": False,
        "complete_candidate_built": False,
        "owner_approval_claimed": False,
        "outputs": {
            "blend": blend.name,
            "blend_sha256": sha256_file(blend),
            "renders": sorted(path.name for path in output_dir.glob("*.png")),
        },
    }
    (output_dir / "GENERATED_PATCH_PROBE.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
