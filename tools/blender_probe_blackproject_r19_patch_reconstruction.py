#!/usr/bin/env python3
"""Bounded R19 reconstruction probe for the licensed BlackProject skin patch.

This is append-only private body work.  It validates and imports the exact
licensed source, keeps the reviewed 34-vertex attachment boundary fixed, and
repairs only the rejected central patch interior.  It never writes the source,
registers a body, assigns it to Kira, publishes it, adds hair, or touches a
runtime file.

The probe deliberately retains the source topology/UV/weights for its first
bounded repair family.  A weighted harmonic fairing removes the tangled
central fold while leaving the complete outer body and attachment boundary
unchanged.  An optional low-amplitude anatomical field restores medically
bounded external landmarks on the continuous skin surface.  Exact
nonadjacent-intersection evidence and close renders decide whether this family
is usable before a complete candidate is built.
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
from blender_build_kira_temporary_functional_body_blackproject import (  # noqa: E402
    ordered_boundary_cycles,
)
from blender_exact_mesh_intersections import (  # noqa: E402
    exact_nonadjacent_intersection_report,
)
from blender_repair_bounded_self_intersections import (  # noqa: E402
    BoundedIntersectionRepairError,
    repair_bounded_self_intersections,
)


SOURCE_SHA256 = "26e107ea57c92a0905283d3655cf4e1155e16c2c0c24b0b071a66cccddf567df"
ADULT_MESH_NAME = "Ariel_Mesh_Genitalia_0"
HAIR_MESH_PREFIXES = ("Hair_",)
HAIR_MESH_FRAGMENTS = ("Hair Cap", "Hair_Cap")


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
    if sigma <= 0.0:
        return 0.0
    return math.exp(-0.5 * ((value - center) / sigma) ** 2)


def central_repair_weight(point: Vector) -> float:
    """Localize repair to the source's independently proven intersection zone.

    Coordinates are world meters.  The verified involved bounds were
    approximately X +/-0.00543 m, Y -0.05895..0.03250 m,
    Z 0.83236..0.85209 m.  This smooth support includes two topology rings
    around that zone while fading before the immutable 34-vertex interface.
    """

    lateral = 1.0 - smoothstep01((abs(float(point.x)) - 0.0040) / 0.0155)
    lower = smoothstep01((float(point.z) - 0.8255) / 0.0075)
    upper = 1.0 - smoothstep01((float(point.z) - 0.8545) / 0.0105)
    anterior = smoothstep01((float(point.y) + 0.070) / 0.020)
    posterior = 1.0 - smoothstep01((float(point.y) - 0.036) / 0.020)
    return max(0.0, min(1.0, lateral * lower * upper * anterior * posterior))


def fair_central_patch(
    adult: bpy.types.Object,
    boundary: set[int],
    *,
    iterations: int,
    strength: float,
) -> dict[str, object]:
    bm = bmesh.new()
    bm.from_mesh(adult.data)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    original = [vert.co.copy() for vert in bm.verts]
    selected = {
        int(vert.index): central_repair_weight(adult.matrix_world @ vert.co)
        for vert in bm.verts
        if int(vert.index) not in boundary
        and central_repair_weight(adult.matrix_world @ vert.co) > 0.0
    }
    maximum_step = 0.0
    for _iteration in range(int(iterations)):
        snapshot = [vert.co.copy() for vert in bm.verts]
        pending: dict[int, Vector] = {}
        for index, support in selected.items():
            vert = bm.verts[index]
            neighbors = [other for edge in vert.link_edges for other in edge.verts if other != vert]
            unique = {int(other.index): other for other in neighbors}
            if len(unique) < 3:
                continue
            average = sum(
                (snapshot[neighbor] for neighbor in unique),
                Vector((0.0, 0.0, 0.0)),
            ) / float(len(unique))
            delta = (average - snapshot[index]) * float(strength) * float(support)
            # One iteration may not move a vertex more than 0.30 mm in world
            # units (0.03 source-local cm).  This keeps the probe bounded.
            if delta.length > 0.03:
                delta.normalize()
                delta *= 0.03
            pending[index] = snapshot[index] + delta
            maximum_step = max(maximum_step, float(delta.length))
        for index, value in pending.items():
            bm.verts[index].co = value
        bm.normal_update()
    movement = [float((vert.co - original[int(vert.index)]).length) for vert in bm.verts]
    bm.to_mesh(adult.data)
    bm.free()
    adult.data.update()
    return {
        "method": "bounded_weighted_harmonic_fairing_on_source_topology",
        "selected_vertex_count": len(selected),
        "iterations": int(iterations),
        "strength": float(strength),
        "boundary_vertex_count": len(boundary),
        "boundary_coordinates_changed": False,
        "maximum_single_iteration_step_source_cm": maximum_step,
        "maximum_total_movement_source_cm": max(movement, default=0.0),
        "maximum_total_movement_world_m": max(movement, default=0.0) * 0.01,
    }


def apply_external_landmark_field(
    adult: bpy.types.Object,
    boundary: set[int],
    *,
    strength: float,
) -> dict[str, object]:
    """Restore subtle adult external relationships on the repaired skin.

    Coordinates are source-local centimeters and displacement is along the
    anterior world direction (-Y).  Recesses remain shallow, capped parts of
    the one continuous external surface; this does not claim internal organs
    or reproductive/urinary function.
    """

    bm = bmesh.new()
    bm.from_mesh(adult.data)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    changed = 0
    maximum = 0.0
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
        index = int(vert.index)
        if index in boundary:
            continue
        world = adult.matrix_world @ vert.co
        x = float(world.x)
        y = float(world.y)
        z = float(world.z)
        # Only the anterior-facing portion receives front landmarks.  A smooth
        # threshold avoids moving the under-body/posterior branch of the patch.
        front = 1.0 - smoothstep01((y + 0.0210) / 0.0275)
        if front <= 0.0:
            continue
        outer = gaussian(x, 0.0, 0.0275) * gaussian(z, 0.866, 0.047)
        mons = gaussian(x, 0.0, 0.0325) * gaussian(z, 0.9005, 0.0220)
        left_major = gaussian(x, 0.0112, 0.0072) * gaussian(z, 0.8670, 0.0235)
        right_major = gaussian(x, -0.0112, 0.0072) * gaussian(z, 0.8670, 0.0235)
        left_minor = gaussian(x, 0.0039, 0.0025) * gaussian(z, 0.8625, 0.0166)
        right_minor = gaussian(x, -0.0039, 0.0025) * gaussian(z, 0.8625, 0.0166)
        hood = gaussian(x, 0.0, 0.0048) * gaussian(z, 0.8835, 0.0062)
        glans = gaussian(x, 0.0, 0.0022) * gaussian(z, 0.8788, 0.0025)
        vestibule = gaussian(x, 0.0, 0.0054) * gaussian(z, 0.8633, 0.0120)
        urethral = gaussian(x, 0.0, 0.0020) * gaussian(z, 0.8695, 0.0022)
        vaginal = gaussian(x, 0.0, 0.0045) * gaussian(z, 0.8555, 0.0064)
        fourchette = gaussian(x, 0.0, 0.0062) * gaussian(z, 0.8442, 0.0054)
        perineum = gaussian(x, 0.0, 0.0105) * gaussian(z, 0.8352, 0.0072)

        # Positive relief moves toward the viewer (-Y); negative relief is a
        # shallow recess.  Maximum intended local value stays below 0.32 cm
        # (3.2 mm world) before strength/support blending.
        relief = (
            0.0006 * outer
            + 0.0012 * mons
            + 0.0025 * (left_major + right_major)
            + 0.00115 * (left_minor + right_minor)
            + 0.00090 * hood
            + 0.00050 * glans
            - 0.00075 * vestibule
            - 0.00055 * urethral
            - 0.00115 * vaginal
            + 0.00035 * fourchette
            - 0.00018 * perineum
        )
        support = central_repair_weight(world)
        delta_y = -relief * float(strength) * front * max(0.15, support)
        delta_y = max(-0.0032, min(0.0020, delta_y))
        if abs(delta_y) <= 1.0e-7:
            continue
        changed_world = world.copy()
        changed_world.y += delta_y
        vert.co = adult.matrix_world.inverted() @ changed_world
        changed += 1
        maximum = max(maximum, abs(delta_y))
        tests = {
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
        for name, value in tests.items():
            if value * front > 0.18:
                memberships[name] += 1
    bm.normal_update()
    bm.to_mesh(adult.data)
    bm.free()
    adult.data.update()
    return {
        "method": "bounded_source_topology_external_landmark_field_v1",
        "changed_vertex_count": changed,
        "strength": float(strength),
        "maximum_absolute_displacement_source_cm": maximum * 100.0,
        "maximum_absolute_displacement_world_m": maximum,
        "landmark_support_vertex_counts": memberships,
        "boundary_coordinates_changed": False,
        "internal_anatomy_or_function_claimed": False,
    }


def add_lights(scene: bpy.types.Scene) -> None:
    specifications = (
        ("R19_KEY", "AREA", (2.2, -3.2, 3.0), 850.0, 4.0),
        ("R19_FILL", "AREA", (-2.4, -2.0, 1.8), 520.0, 3.0),
        ("R19_RIM", "AREA", (0.8, 2.2, 2.6), 700.0, 3.0),
    )
    for name, kind, location, energy, size in specifications:
        data = bpy.data.lights.new(name, kind)
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector((0.0, 0.0, 1.0)) - obj.location).to_track_quat("-Z", "Y").to_euler()


def render(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    path: Path,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    ortho_scale: float,
) -> None:
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def mesh_digest(obj: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    for vert in obj.data.vertices:
        digest.update(f"v|{vert.index}|{vert.co.x:.9f}|{vert.co.y:.9f}|{vert.co.z:.9f}\n".encode("ascii"))
    for polygon in obj.data.polygons:
        digest.update(("f|" + "|".join(str(int(value)) for value in polygon.vertices) + "\n").encode("ascii"))
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    project_root = Path(config["project_root"]).resolve(strict=True)
    source = (project_root / config["source_path"]).resolve(strict=True)
    output_dir = (project_root / config["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("BlackProject source SHA-256 mismatch")

    helpers.clear_scene()
    imported = helpers.import_glb(source)
    meshes = {obj.data.name: obj for obj in imported if obj.type == "MESH"}
    adult = meshes.get(ADULT_MESH_NAME)
    if adult is None:
        raise ValueError("licensed adult-region mesh missing")
    cycles = ordered_boundary_cycles(adult)
    if len(cycles) != 1 or len(cycles[0]) != 34:
        raise ValueError(f"unexpected adult boundary cycles: {[len(row) for row in cycles]}")
    boundary = set(cycles[0])
    boundary_before = {index: adult.data.vertices[index].co.copy() for index in boundary}
    source_mesh_digest = mesh_digest(adult)

    fairing = fair_central_patch(
        adult,
        boundary,
        iterations=int(config["fairing_iterations"]),
        strength=float(config["fairing_strength"]),
    )
    landmark = None
    if bool(config.get("apply_external_landmarks", False)):
        landmark = apply_external_landmark_field(
            adult,
            boundary,
            strength=float(config.get("landmark_strength", 1.0)),
        )
    cleanup: dict[str, object] | None = None
    if bool(config.get("run_exact_cleanup", False)):
        boundary_group = adult.vertex_groups.new(name="R19_IMMUTABLE_BOUNDARY")
        boundary_group.add(sorted(boundary), 1.0, "REPLACE")
        try:
            cleanup = repair_bounded_self_intersections(
                adult,
                protected_group_prefixes=("R19_IMMUTABLE_BOUNDARY",),
                maximum_iterations=int(config.get("cleanup_maximum_iterations", 64)),
                maximum_pair_extent_fraction=float(
                    config.get("cleanup_maximum_pair_extent_fraction", 0.30)
                ),
                maximum_changed_vertex_fraction=float(
                    config.get("cleanup_maximum_changed_vertex_fraction", 0.75)
                ),
                maximum_total_displacement_fraction=float(
                    config.get("cleanup_maximum_total_displacement_fraction", 0.02)
                ),
            )
        except BoundedIntersectionRepairError as error:
            cleanup = {
                "status": "REJECTED_WITHOUT_COMMIT",
                "error": str(error),
                "boundary_protection_group": boundary_group.name,
            }
    boundary_delta = max(
        ((adult.data.vertices[index].co - point).length for index, point in boundary_before.items()),
        default=0.0,
    )

    bm = bmesh.new()
    bm.from_mesh(adult.data)
    intersection = exact_nonadjacent_intersection_report(bm, include_pair_details=False)
    bm.free()

    # Hair is excluded from the probe package, not merely hidden from the
    # eventual runtime candidate.  Eyebrows and eyelashes remain.
    removed_hair: list[str] = []
    for obj in list(imported):
        if obj.type != "MESH":
            continue
        mesh_name = obj.data.name
        if mesh_name.startswith(HAIR_MESH_PREFIXES) or any(fragment in mesh_name for fragment in HAIR_MESH_FRAGMENTS):
            removed_hair.append(mesh_name)
            bpy.data.objects.remove(obj, do_unlink=True)

    report = {
        "schema_version": 1,
        "mode": "R19_BLACKPROJECT_BOUNDED_PATCH_RECONSTRUCTION_PROBE",
        "attempt_label": str(config["attempt_label"]),
        "source": {
            "project_relative_path": str(source.relative_to(project_root)).replace("\\", "/"),
            "sha256": SOURCE_SHA256,
            "adult_patch_mesh_digest_before": source_mesh_digest,
            "source_file_unchanged": True,
            "license": "CC BY 4.0",
            "derivative_not_unchanged_copy": True,
        },
        "scope": {
            "private": True,
            "inactive": True,
            "unassigned": True,
            "runtime_assignment_allowed": False,
            "publication_allowed": False,
            "hair_dependency": False,
            "hair_components_removed_from_probe": sorted(removed_hair),
        },
        "interface": {
            "boundary_vertex_count": len(boundary),
            "maximum_boundary_coordinate_delta_source_cm": float(boundary_delta),
            "exact_boundary_preserved": boundary_delta <= 1.0e-12,
        },
        "fairing": fairing,
        "external_landmark_field": landmark,
        "bounded_exact_cleanup": cleanup,
        "exact_nonadjacent_intersections": intersection,
        "result_patch_mesh_digest": mesh_digest(adult),
        "truth_boundary": {
            "external_adult_surface_review_only": True,
            "internal_organs_or_pregnancy_function_proven": False,
            "bathroom_function_proven": False,
            "complete_body_candidate_built": False,
            "owner_visual_approval_claimed": False,
        },
    }

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.012, 0.018, 0.026)
    add_lights(scene)
    camera_data = bpy.data.cameras.new("R19_PATCH_PROBE_CAMERA")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("R19_PATCH_PROBE_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    render(scene, camera, output_dir / "body_bald_front.png", (0.0, -3.0, 0.88), (0.0, 0.0, 0.88), 1.80)
    render(scene, camera, output_dir / "adult_surface_front.png", (0.0, -2.0, 0.865), (0.0, -0.025, 0.865), 0.19)
    render(scene, camera, output_dir / "adult_surface_three_quarter.png", (0.22, -0.34, 0.87), (0.0, -0.02, 0.865), 0.19)
    render(scene, camera, output_dir / "adult_surface_side.png", (0.30, 0.0, 0.865), (0.0, -0.01, 0.865), 0.19)

    # Save a patch-probe Blend for reproducibility only; it is not a complete
    # candidate and contains no runtime registration.
    blend_path = output_dir / "r19_patch_reconstruction_probe.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    report["outputs"] = {
        "blend": blend_path.name,
        "blend_sha256": sha256_file(blend_path),
        "renders": sorted(path.name for path in output_dir.glob("*.png")),
    }
    if sha256_file(source) != SOURCE_SHA256:
        raise RuntimeError("source file changed during reconstruction probe")
    report_path = output_dir / "PATCH_RECONSTRUCTION_PROBE.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
