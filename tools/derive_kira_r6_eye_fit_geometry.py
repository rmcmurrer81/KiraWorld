"""Read-only geometry audit for fitting Kira's staged eyes to exact R6.

Run this script with Blender in background mode.  It imports the preserved
source body and exact-hash R6 candidate one at a time, measures the visible
eye apertures with front-to-back ray casts, and writes an evidence JSON file.
It never saves a .blend/.glb, changes a runtime binding, or activates Kira.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore
from mathutils.bvhtree import BVHTree  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_BODY = ROOT / "Avatar/models/temp_ai/kira/avatar.glb"
R6_BODY = (
    ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_provisional_body_r6"
    / "r6_20260718_163658/kira_provisional_body_r6.glb"
)
EYE_ASSET = (
    ROOT
    / "Avatar/models/staged/kira/eyes/kira_brown_eye_rig_v3_2"
    / "kira_brown_eye_rig_v3_2.glb"
)
OUTPUT = (
    ROOT
    / "Data/world_tests/kira_r6_eye_fit_candidate_20260721"
    / "geometry_evidence.json"
)

EXPECTED_HASHES = {
    "source_body": "3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e",
    "r6_body": "ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77",
    "eye_asset": "fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413",
}

# Native Blender coordinates used when the v3.2 eyes were authored.
AUTHORED_CENTERS = {
    "left": (-0.02232, -0.03980, 1.10676),
    "right": (0.02232, -0.03980, 1.10676),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes):
        if block.users == 0:
            bpy.data.meshes.remove(block)


def primary_mesh() -> bpy.types.Object:
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    skinned = [
        obj
        for obj in meshes
        if any(modifier.type == "ARMATURE" for modifier in obj.modifiers)
    ]
    candidates = skinned or meshes
    return max(candidates, key=lambda obj: len(obj.data.vertices))


def ray_hit_world(
    bvh: BVHTree,
    local_from_world,
    world_from_local,
    x: float,
    z: float,
) -> tuple[float, float, float] | None:
    world_origin = Vector((x, -0.25, z))
    world_direction = Vector((0.0, 1.0, 0.0))
    local_origin = local_from_world @ world_origin
    local_direction = (local_from_world.to_3x3() @ world_direction).normalized()
    hit, _normal, _face_index, _distance = bvh.ray_cast(
        local_origin,
        local_direction,
        5.0,
    )
    if hit is None:
        return None
    world_hit = world_from_local @ hit
    return tuple(float(value) for value in world_hit)


def aperture_for_side(
    bvh: BVHTree,
    local_from_world,
    world_from_local,
    x_min: float,
    x_max: float,
) -> dict:
    # A dense deterministic grid gives sub-millimetre centroid evidence while
    # remaining independent of vertex names, UVs, or semantic guesses.
    x_steps = 141
    z_steps = 93
    z_min = 1.095
    z_max = 1.118
    hole_points: list[tuple[float, float]] = []
    front_hits: list[tuple[float, float, float]] = []
    scanlines: dict[str, list[float]] = {}
    for z_index in range(z_steps):
        z = z_min + (z_max - z_min) * z_index / (z_steps - 1)
        xs: list[float] = []
        for x_index in range(x_steps):
            x = x_min + (x_max - x_min) * x_index / (x_steps - 1)
            hit = ray_hit_world(bvh, local_from_world, world_from_local, x, z)
            # At eye height a positive-Y first hit means the ray passed through
            # the open front aperture and reached the rear of the hollow head.
            if hit is not None and hit[1] > 0.0:
                hole_points.append((x, z))
                xs.append(x)
            elif hit is not None:
                front_hits.append(hit)
        if xs:
            scanlines[f"{z:.7f}"] = [min(xs), max(xs)]
    if not hole_points:
        return {"detected": False, "point_count": 0, "scanlines": {}}
    centroid_x = sum(point[0] for point in hole_points) / len(hole_points)
    centroid_z = sum(point[1] for point in hole_points) / len(hole_points)
    return {
        "detected": True,
        "point_count": len(hole_points),
        "centroid_x": centroid_x,
        "centroid_z": centroid_z,
        "min_x": min(point[0] for point in hole_points),
        "max_x": max(point[0] for point in hole_points),
        "min_z": min(point[1] for point in hole_points),
        "max_z": max(point[1] for point in hole_points),
        "width": max(point[0] for point in hole_points) - min(point[0] for point in hole_points),
        "height": max(point[1] for point in hole_points) - min(point[1] for point in hole_points),
        "front_surface_y_range": [
            min((hit[1] for hit in front_hits), default=None),
            max((hit[1] for hit in front_hits), default=None),
        ],
        "scanlines": scanlines,
    }


def measure_body(path: Path) -> dict:
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    mesh = primary_mesh()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(mesh, depsgraph)
    world_from_local = mesh.matrix_world.copy()
    local_from_world = world_from_local.inverted()
    left = aperture_for_side(
        bvh,
        local_from_world,
        world_from_local,
        -0.045,
        -0.010,
    )
    right = aperture_for_side(
        bvh,
        local_from_world,
        world_from_local,
        0.010,
        0.045,
    )
    return {
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256(path),
        "mesh_vertex_count": len(mesh.data.vertices),
        "mesh_dimensions": [float(value) for value in mesh.dimensions],
        "mesh_world_matrix": [list(row) for row in mesh.matrix_world],
        "apertures": {"left": left, "right": right},
    }


def candidate_from_r6(r6: dict) -> dict:
    left = r6["apertures"]["left"]
    right = r6["apertures"]["right"]
    if not left.get("detected") or not right.get("detected"):
        return {"derived": False, "reason": "bilateral_aperture_detection_failed"}
    authored_left = AUTHORED_CENTERS["left"]
    authored_right = AUTHORED_CENTERS["right"]
    measured_center_x = (left["centroid_x"] + right["centroid_x"]) / 2.0
    authored_center_x = (authored_left[0] + authored_right[0]) / 2.0
    measured_half_spacing = (right["centroid_x"] - left["centroid_x"]) / 2.0
    authored_half_spacing = (authored_right[0] - authored_left[0]) / 2.0
    measured_center_z = (left["centroid_z"] + right["centroid_z"]) / 2.0
    authored_center_z = (authored_left[2] + authored_right[2]) / 2.0
    return {
        "derived": True,
        "coordinate_mapping_note": (
            "Blender X maps to runtime X and Blender Z maps to runtime Y. "
            "This aperture measurement cannot derive runtime forwardOffset "
            "because that requires eyelid/globe depth occlusion review."
        ),
        "geometry_centered_candidate": {
            "commonHorizontalOffset": measured_center_x - authored_center_x,
            "horizontalOffset": measured_half_spacing - authored_half_spacing,
            "verticalOffset": measured_center_z - authored_center_z,
            "neutralYawDegrees": 0.0,
            "irisHorizontalOffset": 0.0,
            "irisVerticalOffset": 0.0,
            "forwardOffset": None,
        },
        "measured_bilateral_center": {
            "x": measured_center_x,
            "z": measured_center_z,
        },
        "measured_half_spacing": measured_half_spacing,
        "authored_bilateral_center": {
            "x": authored_center_x,
            "z": authored_center_z,
        },
        "authored_half_spacing": authored_half_spacing,
    }


def main() -> None:
    actual_hashes = {
        "source_body": sha256(SOURCE_BODY),
        "r6_body": sha256(R6_BODY),
        "eye_asset": sha256(EYE_ASSET),
    }
    checks = {
        key: actual_hashes[key] == expected
        for key, expected in EXPECTED_HASHES.items()
    }
    if not all(checks.values()):
        raise RuntimeError(f"Exact-hash input check failed: {checks}")
    source = measure_body(SOURCE_BODY)
    r6 = measure_body(R6_BODY)
    candidate = candidate_from_r6(r6)
    payload = {
        "schema_version": 1,
        "kind": "read_only_blender_geometry_no_activation_no_source_mutation",
        "blender_version": bpy.app.version_string,
        "expected_hashes": EXPECTED_HASHES,
        "actual_hashes": actual_hashes,
        "checks": checks,
        "authored_eye_centers_blender_native": AUTHORED_CENTERS,
        "source_body": source,
        "r6_body": r6,
        "candidate_derivation": candidate,
        "limits": [
            "Ray-cast aperture centroids constrain horizontal and vertical placement only.",
            "Aperture geometry does not prove a forward-depth value or natural appearance.",
            "The candidate remains inactive and must pass fixed-camera visual review.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "checks": checks,
        "candidate": candidate,
    }, indent=2))


if __name__ == "__main__":
    main()
