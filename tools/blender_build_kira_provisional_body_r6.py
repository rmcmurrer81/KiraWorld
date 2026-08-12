#!/usr/bin/env python3
"""Build one private, inactive Kira provisional body R6 candidate.

R6 is derived only from the exact enrolled adult base.  Adult-anatomy assets
are study evidence and are never imported or copied into this worker.  The
pass authors a reversible body-only external-form morph, preserves the exact
79-joint rig and existing head/mouth surface, renders only with opaque review
coverage, and refuses any activation request.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


def load_r5_helpers():
    helper_path = Path(__file__).resolve().with_name("blender_build_kira_provisional_body_r5.py")
    spec = importlib.util.spec_from_file_location("kira_r5_helpers", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load R5 helper module: {helper_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r5 = load_r5_helpers()


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def gaussian(value: float, center: float, sigma: float) -> float:
    return math.exp(-0.5 * ((value - center) / sigma) ** 2)


def position_hash(points: list[Vector], indices: list[int]) -> str:
    digest = hashlib.sha256()
    for index in indices:
        point = points[index]
        digest.update(struct.pack("<Ifff", index, float(point.x), float(point.y), float(point.z)))
    return digest.hexdigest()


def face_index_hash(mesh: bpy.types.Mesh) -> str:
    digest = hashlib.sha256()
    for polygon in mesh.polygons:
        vertices = tuple(int(value) for value in polygon.vertices)
        digest.update(struct.pack("<II", int(polygon.index), len(vertices)))
        digest.update(struct.pack(f"<{len(vertices)}I", *vertices))
    return digest.hexdigest()


def group_index(body: bpy.types.Object, name: str) -> int:
    group = body.vertex_groups.get(name)
    if group is None:
        raise ValueError(f"required vertex group is missing: {name}")
    return int(group.index)


def vertex_weight(vertex: bpy.types.MeshVertex, indices: set[int]) -> float:
    return max(
        (float(item.weight) for item in vertex.groups if int(item.group) in indices),
        default=0.0,
    )


def author_private_adult_external_form(body: bpy.types.Object) -> dict[str, object]:
    """Author modest adult surface differentiation without reference copying.

    This is a shape study, not an anatomical-completeness claim.  The source
    topology, head, mouth, hands, and feet are unchanged.  Numeric centers are
    valid only for the exact enrolled 3ec62 cage and are guarded by its hash in
    the caller.
    """

    mesh = body.data
    low, high = r5.local_bounds(body)
    extent = high - low
    if not (
        abs(float(extent.x) - 5.172152) <= 0.01
        and abs(float(extent.y) - 1.058242) <= 0.01
        and abs(float(extent.z) - 7.342842) <= 0.01
    ):
        raise ValueError(f"enrolled cage bounds changed unexpectedly: {tuple(extent)}")

    hips = {group_index(body, r5.HIPS)}
    torso = {group_index(body, name) for name in (r5.SPINE, r5.SPINE1, r5.SPINE2)}

    basis = body.shape_key_add(name="Basis", from_mix=False)
    key = body.shape_key_add(name="Kira_Adult_External_Form_R6", from_mix=False)
    key.value = 1.0
    key.slider_min = 0.0
    key.slider_max = 1.0

    source_points = [basis.data[index].co.copy() for index in range(len(mesh.vertices))]
    head_indices = [index for index, point in enumerate(source_points) if point.z >= 6.0]
    mouth_indices = [
        index
        for index, point in enumerate(source_points)
        if 6.30 <= point.z <= 6.90 and abs(point.x) <= 0.34 and point.y <= -0.14
    ]
    face_hash_before = face_index_hash(mesh)
    head_hash_before = position_hash(source_points, head_indices)
    mouth_hash_before = position_hash(source_points, mouth_indices)

    moved = 0
    sum_displacement = 0.0
    max_displacement = 0.0
    protected_head_max = 0.0
    protected_mouth_max = 0.0
    region_counts: collections.Counter[str] = collections.Counter()
    region_max: collections.defaultdict[str, float] = collections.defaultdict(float)

    for vertex in mesh.vertices:
        original = basis.data[vertex.index].co.copy()
        target = original.copy()
        hip_weight = vertex_weight(vertex, hips)
        torso_weight = vertex_weight(vertex, torso)

        # Subtle adult proportion support.  It affects only the torso/pelvis
        # and is secondary to the external-form study below.
        hip_band = gaussian(original.z, 4.08, 0.34)
        waist_band = gaussian(original.z, 4.67, 0.25)
        if hip_weight > 1e-5:
            target.x *= 1.0 + 0.012 * hip_weight * hip_band
            if original.y > 0.05:
                target.y *= 1.0 + 0.014 * hip_weight * hip_band
            region_counts["adult_pelvic_proportion"] += 1
        if torso_weight > 1e-5 and original.z < 5.65:
            target.x *= 1.0 - 0.009 * torso_weight * waist_band
            region_counts["adult_torso_proportion"] += 1

        # Adult breast surface differentiation on the existing torso mesh.
        # Only the forward-facing surface is affected.  The broad, shallow
        # areolar support and small central papilla are geometric form cues;
        # no intimate texture or retained uncovered render is created.
        if original.y <= -0.30 and 5.14 <= original.z <= 5.68:
            front_gate = clamp((-0.30 - original.y) / 0.22)
            for side, center_x in (("left", 0.31), ("right", -0.31)):
                broad = gaussian(original.x, center_x, 0.105) * gaussian(original.z, 5.40, 0.105)
                central = gaussian(original.x, center_x, 0.038) * gaussian(original.z, 5.40, 0.040)
                delta = -(0.0060 * broad + 0.0200 * central) * front_gate
                if abs(delta) > 1e-7:
                    target.y += delta
                    label = f"adult_breast_surface_{side}"
                    region_counts[label] += 1
                    region_max[label] = max(region_max[label], abs(delta))

        # Adult external pelvic surface differentiation, authored directly on
        # the enrolled cage.  Paired outer contours, a central cleft, a small
        # superior hood contour, and a shallow mons transition replace a fully
        # undifferentiated doll-safe plane.  This remains provisional and does
        # not by itself prove complete anatomy or functional simulation.
        if original.y <= -0.10 and 3.34 <= original.z <= 4.02 and abs(original.x) <= 0.27:
            front_gate = clamp((-0.10 - original.y) / 0.26)
            left_outer = gaussian(original.x, 0.052, 0.038) * gaussian(original.z, 3.59, 0.145)
            right_outer = gaussian(original.x, -0.052, 0.038) * gaussian(original.z, 3.59, 0.145)
            central_cleft = gaussian(original.x, 0.0, 0.020) * gaussian(original.z, 3.58, 0.125)
            hood = gaussian(original.x, 0.0, 0.040) * gaussian(original.z, 3.72, 0.055)
            mons = gaussian(original.x, 0.0, 0.17) * gaussian(original.z, 3.88, 0.15)
            delta = (
                -0.0210 * (left_outer + right_outer)
                + 0.0100 * central_cleft
                - 0.0080 * hood
                - 0.0060 * mons
            ) * front_gate
            if abs(delta) > 1e-7:
                target.y += delta
                region_counts["adult_external_pelvic_surface"] += 1
                region_max["adult_external_pelvic_surface"] = max(
                    region_max["adult_external_pelvic_surface"], abs(delta)
                )

        displacement = (target - original).length
        if displacement > 1e-9:
            moved += 1
            sum_displacement += displacement
            max_displacement = max(max_displacement, displacement)
        if vertex.index in head_indices:
            protected_head_max = max(protected_head_max, displacement)
        if vertex.index in mouth_indices:
            protected_mouth_max = max(protected_mouth_max, displacement)
        key.data[vertex.index].co = target

    target_points = [key.data[index].co.copy() for index in range(len(mesh.vertices))]
    head_hash_after = position_hash(target_points, head_indices)
    mouth_hash_after = position_hash(target_points, mouth_indices)
    face_hash_after = face_index_hash(mesh)
    if protected_head_max > 1e-12 or head_hash_before != head_hash_after:
        raise ValueError("R6 body authoring changed protected head geometry")
    if protected_mouth_max > 1e-12 or mouth_hash_before != mouth_hash_after:
        raise ValueError("R6 body authoring changed the existing mouth surface")
    if face_hash_before != face_hash_after:
        raise ValueError("R6 shape authoring changed source face topology")

    body.active_shape_key_index = 1
    body.show_only_shape_key = False
    world_scale = sum(abs(float(body.matrix_world[axis][axis])) for axis in range(3)) / 3.0
    return {
        "shape_key": key.name,
        "default_value": 1.0,
        "reversible_to_exact_source_basis": True,
        "moved_vertex_count": moved,
        "mean_local_displacement": round(sum_displacement / max(moved, 1), 9),
        "maximum_local_displacement": round(max_displacement, 9),
        "mean_world_displacement_m": round(sum_displacement / max(moved, 1) * world_scale, 9),
        "maximum_world_displacement_m": round(max_displacement * world_scale, 9),
        "region_vertex_visits": dict(region_counts),
        "region_maximum_local_displacement": {
            key_name: round(value, 9) for key_name, value in region_max.items()
        },
        "source_face_index_sha256_before": face_hash_before,
        "source_face_index_sha256_after": face_hash_after,
        "source_face_indices_preserved": face_hash_before == face_hash_after,
        "protected_head": {
            "method": "all source vertices at local Z >= 6.0",
            "vertex_count": len(head_indices),
            "position_sha256_before": head_hash_before,
            "position_sha256_after": head_hash_after,
            "maximum_displacement": protected_head_max,
            "exactly_preserved": head_hash_before == head_hash_after,
        },
        "protected_existing_mouth_surface": {
            "method": "conservative central lower-face envelope within protected head",
            "vertex_count": len(mouth_indices),
            "position_sha256_before": mouth_hash_before,
            "position_sha256_after": mouth_hash_after,
            "maximum_displacement": protected_mouth_max,
            "exactly_preserved": mouth_hash_before == mouth_hash_after,
            "second_mouth_mesh_created": False,
        },
        "doll_safe_external_body_limitation": {
            "undifferentiated_surface_reduced": True,
            "removal_or_completeness_proven": False,
            "reason": "R6 adds reversible adult external-form differentiation but lacks an independent anatomy-completeness review.",
        },
        "likeness_claimed": False,
        "anatomical_completeness_claimed": False,
        "truth_note": "Private provisional adult-form study only; no reference mesh geometry was imported or copied.",
    }


def add_review_coverage(body: bpy.types.Object) -> dict[str, object]:
    material = bpy.data.materials.new("R6_Temporary_Opaque_Review_Coverage_Not_Exported")
    material.diffuse_color = (0.025, 0.12, 0.19, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = (0.018, 0.075, 0.12, 1.0)
        principled.inputs["Roughness"].default_value = 0.78
        principled.inputs["Metallic"].default_value = 0.0
    body.data.materials.append(material)
    covered = 0
    for polygon in body.data.polygons:
        center = polygon.center
        if 3.30 <= center.z <= 5.96 and abs(center.x) <= 0.94:
            polygon.material_index = 1
            covered += 1
        else:
            polygon.material_index = 0
    return {
        "method": "temporary opaque torso/pelvis material assignment for retained renders",
        "covered_polygon_count": covered,
        "exported": False,
        "wardrobe_claimed": False,
        "truth_note": "Privacy coverage only, not a garment or clothing-system pass.",
    }


def remove_review_coverage(body: bpy.types.Object) -> None:
    for polygon in body.data.polygons:
        polygon.material_index = 0
    while len(body.data.materials) > 1:
        body.data.materials.pop(index=len(body.data.materials) - 1)


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    project_root = Path(config["project_root"]).resolve(strict=True)
    source = Path(config["source_model"]).resolve(strict=True)
    output_dir = Path(config["output_dir"]).resolve()
    allowed_root = (
        project_root
        / "Avatar"
        / "avatar_builder"
        / "candidate_sources"
        / "kira_provisional_body_r6"
    ).resolve()
    output_dir.relative_to(allowed_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    if sha256_file(source) != config["source_sha256"]:
        raise ValueError("exact enrolled adult base SHA-256 mismatch")
    if bool(config.get("runtime_activation_requested")):
        raise ValueError("R6 worker refuses runtime activation requests")

    r5.clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    body, armature = r5.primary_body_and_armature()
    removed_helpers = r5.remove_source_helpers(body)
    original_body_name = body.name
    original_mesh_name = body.data.name
    original_armature_name = armature.name
    original_bones = [bone.name for bone in armature.data.bones]
    original_vertex_group_names = [group.name for group in body.vertex_groups]
    original_topology = r5.topology_counts(body.data)
    original_weights = r5.weight_health(body.data)
    original_uv = r5.uv_multiset_hash(body.data)
    if len(original_bones) != 79 or not set(r5.REQUIRED_BONES).issubset(original_bones):
        raise ValueError("source rig is not the expected 79-joint humanoid rig")

    # Keep the source node/mesh/armature names for existing runtime selectors.
    for owner in (body, armature):
        owner["candidate_id"] = "kira"
        owner["candidate_revision"] = "provisional_body_r6"
        owner["maturity_policy"] = "adult"
        owner["private_inactive_review_only"] = True
        owner["runtime_activation_allowed"] = False
        owner["owner_approved"] = False
        owner["autobuild_approved"] = False
        owner["likeness_approved"] = False
        owner["anatomy_approved"] = False
        owner["existing_mouth_surface_preserved"] = True
        owner["second_mouth_created"] = False

    adult_form = author_private_adult_external_form(body)
    skin_material, pbr_audit = r5.author_skin_material(output_dir)
    r5.assign_single_material(body, skin_material)
    coverage_audit = add_review_coverage(body)

    neutral_low, neutral_high = r5.bounds_for_body(body, evaluated=True)
    height = neutral_high.z - neutral_low.z
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.012, 0.016, 0.024)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -0.45
    r5.add_ground(neutral_low, neutral_high)
    seat = r5.add_seat_helper(height)
    r5.add_lighting((neutral_low + neutral_high) * 0.5, height)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "R6_Covered_Private_Review_Camera_Not_Exported"
    camera["private_diagnostic_helper"] = True
    scene.camera = camera

    render_specs = (
        ("covered_neutral_front", "neutral", Vector((0.0, -1.0, 0.035)), False),
        ("covered_neutral_side", "neutral", Vector((1.0, 0.0, 0.025)), False),
        ("covered_neutral_back", "neutral", Vector((0.0, 1.0, 0.035)), False),
        ("covered_reach", "reach", Vector((0.68, -1.0, 0.075)), False),
        ("covered_stride", "stride", Vector((0.68, -1.0, 0.075)), False),
        ("covered_seated", "seated", Vector((0.68, -1.0, 0.070)), True),
    )
    renders: dict[str, object] = {}
    pose_metrics: dict[str, object] = {}
    for label, pose, direction, show_seat in render_specs:
        pose_metrics[pose] = r5.apply_pose(armature, body, pose, neutral_low, neutral_high)
        seat.hide_render = not show_seat
        if show_seat:
            pose_metrics[pose]["seat_support"] = r5.seat_support_metrics(body, seat)
        render_path = output_dir / "renders" / f"{label}.png"
        renders[label] = r5.render_view(render_path, body=body, camera=camera, direction=direction)
    seat.hide_render = True

    actions = [
        r5.create_action(
            armature,
            body,
            name=f"Kira_R6_{pose.title()}_Evidence",
            pose=pose,
            low=neutral_low,
            high=neutral_high,
        )
        for pose in ("neutral", "reach", "stride", "seated")
    ]
    r5.reset_pose(armature)
    remove_review_coverage(body)
    if body.data.shape_keys:
        body.data.shape_keys.key_blocks["Kira_Adult_External_Form_R6"].value = 1.0
    bpy.context.view_layer.update()

    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    body.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    model_path = output_dir / "kira_provisional_body_r6.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(model_path),
        export_format="GLB",
        use_selection=True,
        export_apply=False,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_def_bones=True,
        export_yup=True,
        export_morph=True,
        export_extras=True,
    )
    if not model_path.is_file():
        raise RuntimeError("Blender exporter did not create the R6 candidate GLB")

    final_bones = [bone.name for bone in armature.data.bones]
    final_vertex_group_names = [group.name for group in body.vertex_groups]
    final_topology = r5.topology_counts(body.data)
    final_weights = r5.weight_health(body.data)
    final_uv = r5.uv_multiset_hash(body.data)
    if original_bones != final_bones or original_vertex_group_names != final_vertex_group_names:
        raise ValueError("R6 authoring changed the required rig or vertex-group ordering")
    if original_topology != final_topology:
        raise ValueError("R6 authoring changed source topology")
    if original_uv["sha256"] != final_uv["sha256"]:
        raise ValueError("R6 authoring changed source UV topology")

    manifest = {
        "schema_version": 1,
        "created_at": now_iso(),
        "candidate_id": "kira",
        "candidate_revision": "provisional_body_r6",
        "status": "private_inactive_reversible_review_candidate",
        "source": {
            "project_path": config["source_project_path"],
            "sha256": config["source_sha256"],
            "removed_source_helpers": removed_helpers,
            "body_name_preserved": original_body_name == body.name,
            "mesh_name_preserved": original_mesh_name == body.data.name,
            "armature_name_preserved": original_armature_name == armature.name,
        },
        "model": {
            "path": str(model_path),
            "sha256": sha256_file(model_path),
            "size_bytes": model_path.stat().st_size,
            "genuinely_transformed_derivative": sha256_file(model_path) != config["source_sha256"],
        },
        "adult_external_form": adult_form,
        "source_topology_preservation": {
            "before": original_topology,
            "after": final_topology,
            "exact_counts_preserved": original_topology == final_topology,
            "uv_sha256_before": original_uv["sha256"],
            "uv_sha256_after": final_uv["sha256"],
            "uv_multiset_preserved": original_uv["sha256"] == final_uv["sha256"],
            "weights_before": original_weights,
            "weights_after": final_weights,
        },
        "skin_surface": pbr_audit,
        "rig": {
            "bone_count": len(final_bones),
            "bone_order_and_names_exactly_preserved": original_bones == final_bones,
            "vertex_group_order_and_names_exactly_preserved": original_vertex_group_names == final_vertex_group_names,
            "required_core_bones_present": all(name in final_bones for name in r5.REQUIRED_BONES),
            "finger_bone_count": sum(1 for name in final_bones if "Hand" in name and name not in (r5.LEFT_HAND, r5.RIGHT_HAND)),
            "actions": [action.name for action in actions],
            "stable_working_rig_proven": False,
        },
        "existing_mouth_contract": {
            "existing_head_and_mouth_surface_preserved": adult_form["protected_existing_mouth_surface"]["exactly_preserved"],
            "second_mouth_mesh_created": False,
            "body_mesh_count_exported": 1,
            "runtime_lip_sync_playback_proven": False,
        },
        "eye_rig_contract": {
            "head_surface_preserved_for_staged_eye_fit": adult_form["protected_head"]["exactly_preserved"],
            "staged_eye_rig_assembled_into_candidate": False,
            "runtime_eye_fit_proven_on_exact_candidate": False,
        },
        "pose_metrics": pose_metrics,
        "privacy_safe_renders": renders,
        "temporary_review_coverage": coverage_audit,
        "explicit_absences": {
            "eyes": "not assembled; staged eye compatibility is audited separately",
            "hair": "not authored",
            "clothes": "not authored; render coverage is not a garment",
            "shoes": "not authored",
        },
        "privacy_and_activation": {
            "private_body_builder_review_only": True,
            "retained_uncovered_or_intimate_renders": False,
            "runtime_activation_allowed": False,
            "live_avatar_targeted": False,
            "owner_approved": False,
            "likeness_approved": False,
            "anatomy_approved": False,
            "autobuild_gate_passed_subjects": 0,
            "autobuild_gate_required_subjects": 2,
        },
        "truth_note": (
            "R6 materially advances the exact enrolled adult cage with reversible body-only external-form "
            "differentiation while exactly preserving the head/mouth surface and 79-joint rig. It does not "
            "prove complete anatomy, final deformation, eye fit, lip-sync playback, owner approval, runtime "
            "safety, or permission to autobuild other bodies."
        ),
    }
    manifest_path = output_dir / "kira_provisional_body_r6_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "candidate": str(model_path),
                "candidate_sha256": manifest["model"]["sha256"],
                "manifest": str(manifest_path),
                "bone_count": len(final_bones),
                "protected_head": adult_form["protected_head"]["exactly_preserved"],
                "protected_mouth": adult_form["protected_existing_mouth_surface"]["exactly_preserved"],
                "privacy_safe_renders": len(renders),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
