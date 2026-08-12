#!/usr/bin/env python3
"""Author five inactive review visemes on Kira R7's existing welded mouth.

This is deliberately an authoring/evidence worker, not a runtime exporter.  It
changes coordinates only through shape keys on the already-existing body mesh.
The exact 207-vertex internal backing component is pinned to Basis in every
review key.  Render-only lights, camera, and diagnostic materials are created
after the isolated candidate has been saved.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import bpy
from mathutils import Vector

import blender_author_kira_r7_visible_lip_visemes as base


KEYS = [
    "KW_VISEME_AH_OPEN_REVIEW",
    "KW_VISEME_EE_REVIEW",
    "KW_VISEME_O_REVIEW",
    "KW_VISEME_MBP_REVIEW",
    "KW_VISEME_FV_REVIEW",
]


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--candidate-blend", required=True)
    return parser.parse_args(argv)


def create_key(
    body: bpy.types.Object,
    name: str,
    mode: str,
    upper_weights: dict[int, float],
    lower_weights: dict[int, float],
    hidden: set[int],
) -> dict[str, object]:
    mesh = body.data
    basis = mesh.shape_keys.key_blocks["Basis"]
    key = body.shape_key_add(name=name, from_mix=False)
    moved: dict[int, Vector] = {}

    def add(index: int, delta: Vector) -> None:
        if index in hidden:
            raise ValueError(f"{name} reached protected backing vertex {index}")
        moved[index] = moved.get(index, Vector()) + delta

    for role, weights in (("upper", upper_weights), ("lower", lower_weights)):
        for index, ring_weight in weights.items():
            point = mesh.vertices[index].co
            x = float(point.x)
            side = min(abs(x) / 0.0845, 1.0)
            centre = base.center_taper(mesh, index)
            sign = 1.0 if x > 0.0 else (-1.0 if x < 0.0 else 0.0)

            if mode == "ah_open":
                # Broad vowel: a large vertical aperture with a very small
                # lateral relaxation.  The lower visible lip supplies most of
                # the jaw-like motion because this source has no jaw bone.
                dz = (0.010 if role == "upper" else -0.052) * centre
                dx = sign * 0.0035 * side
                dy = -0.0025 if role == "upper" else -0.0045
            elif mode == "ee":
                # Wide, narrow vowel: corners retract laterally while the
                # centre remains only modestly open.
                dz = (0.0045 if role == "upper" else -0.0135) * centre
                dx = sign * (0.010 + 0.012 * side)
                dy = 0.0040 * (0.40 + 0.60 * side)
            elif mode == "o":
                # Rounded vowel: narrow the aperture and protrude the rim.
                # Lateral narrowing intentionally does not use centre_taper;
                # the v1 O failed because its corners barely moved.
                dz = (0.013 if role == "upper" else -0.032) * centre
                dx = -x * (0.44 + 0.08 * side)
                dy = -0.016 * (0.55 + 0.45 * centre)
            elif mode == "mbp":
                # Bilabial closure: compress both visible rims together and
                # slightly forward.  No cavity or replacement lip is added.
                dz = (-0.0020 if role == "upper" else 0.0020) * centre
                dx = -x * 0.035
                dy = -0.0075 * centre
            elif mode == "fv":
                # Labiodental prototype.  The lower rim tucks back and up;
                # the upper rim advances slightly.  Because the source has no
                # authored teeth, visual review must decide this key fail-closed.
                if role == "upper":
                    dz = -0.0015 * centre
                    dx = 0.0
                    dy = -0.0060 * centre
                else:
                    dz = 0.0090 * centre
                    dx = -x * 0.025
                    dy = 0.0140 * centre
            else:
                raise ValueError(mode)

            add(index, Vector((dx, dy, dz)) * ring_weight)

    for index, delta in moved.items():
        key.data[index].co = basis.data[index].co + delta
    key.value = 0.0

    displacement = {
        index: (key.data[index].co - basis.data[index].co).length
        for index in moved
    }
    hidden_maximum = max(
        (key.data[index].co - basis.data[index].co).length for index in hidden
    )
    return {
        "name": name,
        "mode": mode,
        "moved_vertex_count": len(moved),
        "moved_vertex_index_sha256": base.index_sha256(sorted(moved)),
        "maximum_displacement_m": round(max(displacement.values()), 9),
        "minimum_nonzero_displacement_m": round(min(displacement.values()), 9),
        "hidden_backing_maximum_displacement_m": round(float(hidden_maximum), 12),
        "visual_quality_proven_by_worker": False,
        "worker_disposition": "requires_independent_fixed_render_review",
    }


def set_key(body: bpy.types.Object, active: str | None) -> None:
    for key in body.data.shape_keys.key_blocks:
        if key.name in KEYS:
            key.value = 1.0 if key.name == active else 0.0
    bpy.context.view_layer.update()


def render(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    body: bpy.types.Object,
    output: Path,
    key_name: str | None,
    location: Vector,
    target: Vector,
    ortho_scale: float,
) -> dict[str, object]:
    set_key(body, key_name)
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    base.look_at(camera, target)
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    return {
        "path": str(output),
        "shape_key": key_name or "Basis",
        "camera_location": [round(float(value), 9) for value in location],
        "target": [round(float(value), 9) for value in target],
        "orthographic_scale": ortho_scale,
    }


def core_bounds(body: bpy.types.Object, key_name: str | None) -> dict[str, float]:
    points = (
        body.data.shape_keys.key_blocks["Basis"].data
        if key_name is None
        else body.data.shape_keys.key_blocks[key_name].data
    )
    indices = sorted(
        {
            index
            for path in base.VISIBLE_RIM_PATHS.values()
            for index in path
        }
    )
    xs = [float(points[index].co.x) for index in indices]
    ys = [float(points[index].co.y) for index in indices]
    zs = [float(points[index].co.z) for index in indices]
    return {
        "width_m": round(max(xs) - min(xs), 9),
        "depth_m": round(max(ys) - min(ys), 9),
        "height_m": round(max(zs) - min(zs), 9),
        "minimum_x_m": round(min(xs), 9),
        "maximum_x_m": round(max(xs), 9),
        "minimum_y_m": round(min(ys), 9),
        "maximum_y_m": round(max(ys), 9),
        "minimum_z_m": round(min(zs), 9),
        "maximum_z_m": round(max(zs), 9),
    }


def topology(body: bpy.types.Object) -> dict[str, int]:
    mesh = body.data
    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "objects": len(bpy.data.objects),
        "mesh_objects": sum(1 for obj in bpy.data.objects if obj.type == "MESH"),
    }


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    render_dir = output_dir / "fixed_renders"
    candidate_blend = Path(args.candidate_blend).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    render_dir.mkdir(parents=True, exist_ok=True)
    candidate_blend.parent.mkdir(parents=True, exist_ok=True)

    source_workspace = Path(bpy.data.filepath).resolve()
    bodies = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.get("r7_role") == "working_body_unauthored"
    ]
    if len(bodies) != 1:
        raise ValueError(f"expected one R7 working body, found {len(bodies)}")
    body = bodies[0]
    mesh = body.data
    mesh.update()
    topology_before = topology(body)

    hidden_matches = [
        component
        for component in base.connected_components(mesh)
        if len(component) == base.HIDDEN_VERTEX_COUNT
        and base.index_sha256(component) == base.HIDDEN_INDEX_SHA256
    ]
    if len(hidden_matches) != 1:
        raise ValueError(f"expected one exact hidden backing component, got {len(hidden_matches)}")
    hidden = set(hidden_matches[0])
    rim_evidence = base.validate_visible_rims(mesh, hidden)

    existing_shape_keys = (
        [key.name for key in mesh.shape_keys.key_blocks]
        if mesh.shape_keys is not None
        else []
    )
    if any(name in existing_shape_keys for name in KEYS):
        raise ValueError(f"v2 trial keys already exist in source: {existing_shape_keys}")
    if mesh.shape_keys is None:
        body.shape_key_add(name="Basis", from_mix=False)
    elif mesh.shape_keys.key_blocks.get("Basis") is None:
        raise ValueError(f"existing shape-key stack has no Basis: {existing_shape_keys}")

    adjacency = base.mesh_adjacency(mesh)
    upper_core = set(
        base.VISIBLE_RIM_PATHS["upper_right"]
        + base.VISIBLE_RIM_PATHS["upper_left"]
    )
    lower_core = set(
        base.VISIBLE_RIM_PATHS["lower_right"]
        + base.VISIBLE_RIM_PATHS["lower_left"]
    )
    upper_weights = base.neighborhood_weights(upper_core, adjacency, hidden | lower_core)
    lower_weights = base.neighborhood_weights(lower_core, adjacency, hidden | upper_core)
    for index in sorted(set(upper_weights) & set(lower_weights)):
        if upper_weights[index] >= lower_weights[index]:
            del lower_weights[index]
        else:
            del upper_weights[index]

    definitions = [
        ("KW_VISEME_AH_OPEN_REVIEW", "ah_open"),
        ("KW_VISEME_EE_REVIEW", "ee"),
        ("KW_VISEME_O_REVIEW", "o"),
        ("KW_VISEME_MBP_REVIEW", "mbp"),
        ("KW_VISEME_FV_REVIEW", "fv"),
    ]
    shape_keys = [
        create_key(body, name, mode, upper_weights, lower_weights, hidden)
        for name, mode in definitions
    ]
    if any(record["hidden_backing_maximum_displacement_m"] != 0.0 for record in shape_keys):
        raise ValueError("a v2 shape key moved the protected 207-vertex backing")

    topology_after = topology(body)
    if topology_after != topology_before:
        raise ValueError(f"shape-key authoring changed topology: {topology_before} -> {topology_after}")

    gaps = {"Basis": base.key_center_gap(body, None)}
    bounds = {"Basis": core_bounds(body, None)}
    for name, _mode in definitions:
        gaps[name] = base.key_center_gap(body, name)
        bounds[name] = core_bounds(body, name)

    body["kw_trial_status"] = "inactive_owner_review_only"
    body["kw_trial_version"] = "r7_visible_lip_viseme_v2"
    body["kw_trial_source_workspace"] = str(source_workspace)
    body["kw_second_mouth_created"] = False
    body["kw_runtime_export_allowed"] = False
    set_key(body, None)
    bpy.ops.wm.save_as_mainfile(filepath=str(candidate_blend), check_existing=False)

    scene, camera = base.configure_transient_render(body, hidden)
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    mouth_center = body.matrix_world @ Vector((0.0, -0.37, 6.582))
    face_center = body.matrix_world @ Vector((0.0, -0.36, 6.72))
    front_mouth_camera = mouth_center + Vector((0.0, -1.0, 0.015))
    front_face_camera = face_center + Vector((0.0, -1.35, 0.02))
    oblique_camera = mouth_center + Vector((0.34, -0.82, 0.032))

    renders: dict[str, dict[str, object]] = {
        "basis_face": render(
            scene, camera, body, render_dir / "basis_front_face.png", None,
            front_face_camera, face_center, 0.50,
        ),
        "basis_mouth": render(
            scene, camera, body, render_dir / "basis_mouth_closeup.png", None,
            front_mouth_camera, mouth_center, 0.23,
        ),
    }
    filename_stems = {
        "KW_VISEME_AH_OPEN_REVIEW": "ah_open",
        "KW_VISEME_EE_REVIEW": "ee",
        "KW_VISEME_O_REVIEW": "o",
        "KW_VISEME_MBP_REVIEW": "mbp",
        "KW_VISEME_FV_REVIEW": "fv",
    }
    for name, stem in filename_stems.items():
        renders[f"{stem}_mouth"] = render(
            scene, camera, body, render_dir / f"{stem}_mouth_closeup.png", name,
            front_mouth_camera, mouth_center, 0.23,
        )
        renders[f"{stem}_oblique"] = render(
            scene, camera, body, render_dir / f"{stem}_oblique.png", name,
            oblique_camera, mouth_center, 0.24,
        )

    evidence = {
        "schema_version": 2,
        "mode": "inactive_isolated_same_welded_mouth_five_viseme_trial_v2",
        "source_workspace": str(source_workspace),
        "candidate_blend": str(candidate_blend),
        "body_object": body.name,
        "body_mesh": mesh.name,
        "topology": {
            "before": topology_before,
            "after_shape_keys_before_save": topology_after,
            "unchanged": topology_before == topology_after,
        },
        "hidden_backing": {
            "vertex_count": len(hidden),
            "vertex_index_sha256": base.index_sha256(sorted(hidden)),
            "deformed_by_any_shape_key": False,
            "render_only_dark_material_used_after_candidate_save": True,
        },
        "visible_lip_rim_proof": rim_evidence,
        "shape_keys": shape_keys,
        "preexisting_shape_keys_preserved": existing_shape_keys,
        "center_separation": gaps,
        "visible_rim_bounds": bounds,
        "fixed_renders": renders,
        "engineering_verdict": {
            "same_existing_welded_face_mesh_deformed": True,
            "visible_rim_motion_geometrically_proven": True,
            "individual_visual_quality_proven_by_worker": False,
            "fixed_render_review_required_for_every_viseme": True,
            "owner_approval_recorded": False,
            "runtime_ready": False,
            "promotion_allowed": False,
        },
        "safety": {
            "source_workspace_saved_or_overwritten": False,
            "isolated_candidate_saved": True,
            "second_mouth_created": False,
            "mesh_object_added_to_saved_candidate": False,
            "vertex_or_face_topology_changed": False,
            "runtime_model_exported": False,
            "runtime_binding_touched": False,
            "person_state_touched": False,
            "activation_attempted": False,
        },
    }
    evidence_path = output_dir / "topology_and_shape_key_evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "candidate": str(candidate_blend), "evidence": str(evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
