#!/usr/bin/env python3
"""Author an inactive Kira R7 same-mesh viseme-set v2 review candidate.

The worker starts from the pinned R7 authoring workspace.  It deforms only the
already-visible welded face surface around the manually proven lip rim.  The
existing 207-vertex backing component remains fixed.  No second mouth, teeth,
overlay, mesh object, model export, runtime binding, or activation is created.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
import blender_author_kira_r7_visible_lip_visemes as base  # noqa: E402


KEY_SPECS = {
    "ah": "KW_V2_AH_OPEN_REVIEW",
    "o": "KW_V2_O_REVIEW",
    "ee": "KW_V2_EE_REVIEW",
    "fv": "KW_V2_FV_REVIEW",
    "mbp": "KW_V2_MBP_REVIEW",
}
TRIAL_KEY_NAMES = set(KEY_SPECS.values())
base.TRIAL_KEY_NAMES = TRIAL_KEY_NAMES


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--candidate-blend", required=True)
    parser.add_argument("--run-token", required=True)
    return parser.parse_args(argv)


def center_factor(x: float) -> float:
    edge = min(abs(x) / 0.085, 1.0)
    return max(0.12, (1.0 - edge) ** 0.48)


def edge_factor(x: float) -> float:
    return min(abs(x) / 0.085, 1.0) ** 0.68


def deformation_delta(role: str, upper: bool, point: Vector) -> Vector:
    """Return a deliberately small, review-only local-space deformation."""
    x = float(point.x)
    side = 1.0 if x > 1e-9 else -1.0 if x < -1e-9 else 0.0
    center = center_factor(x)
    edge = edge_factor(x)

    if role == "ah":
        if upper:
            return Vector((side * 0.0025 * edge, -0.0025, 0.0140 * center))
        return Vector((side * 0.0035 * edge, -0.0055, -0.0500 * center))

    if role == "o":
        contraction = 0.62 if upper else 0.66
        horizontal = -x * contraction * (0.50 + 0.50 * edge)
        if upper:
            return Vector((horizontal, -0.0250, 0.0320 * center))
        return Vector((horizontal, -0.0280, -0.0500 * center))

    if role == "ee":
        widening = (0.0200 if upper else 0.0230) * (0.25 + 0.75 * edge)
        if upper:
            return Vector((side * widening, -0.0030, 0.0060 * center))
        return Vector((side * widening, -0.0040, -0.0100 * center))

    if role == "fv":
        # Lower lip is raised and tucked inward relative to the upper rim.  No
        # teeth are invented, so this remains an FV surface approximation.
        horizontal = -x * (0.025 if upper else 0.060) * edge
        if upper:
            return Vector((horizontal, -0.0030, 0.0120 * center))
        return Vector((horizontal, 0.0090, 0.0060 * center))

    if role == "mbp":
        # A closed, narrowed, forward lip press.  The very small opposed
        # vertical motion intentionally closes the seam without a new surface.
        horizontal = -x * 0.10 * (0.40 + 0.60 * edge)
        if upper:
            return Vector((horizontal, -0.0090, -0.0018 * center))
        return Vector((horizontal, -0.0090, 0.0015 * center))

    raise ValueError(f"unknown viseme role: {role}")


def create_shape_key(
    body: bpy.types.Object,
    role: str,
    upper_weights: dict[int, float],
    lower_weights: dict[int, float],
    hidden: set[int],
) -> dict[str, object]:
    name = KEY_SPECS[role]
    key = body.shape_key_add(name=name, from_mix=False)
    basis = body.data.shape_keys.key_blocks["Basis"]
    moved: dict[int, Vector] = {}

    def add(index: int, delta: Vector) -> None:
        if index in hidden:
            raise ValueError(f"{role} deformation reached hidden backing vertex {index}")
        moved[index] = moved.get(index, Vector()) + delta

    for index, weight in upper_weights.items():
        add(index, deformation_delta(role, True, basis.data[index].co) * weight)
    for index, weight in lower_weights.items():
        add(index, deformation_delta(role, False, basis.data[index].co) * weight)

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
        "role": role,
        "same_existing_surface": True,
        "moved_vertex_count": len(moved),
        "moved_vertex_index_sha256": base.index_sha256(sorted(moved)),
        "maximum_displacement_m": round(max(displacement.values()), 9),
        "minimum_nonzero_displacement_m": round(min(displacement.values()), 9),
        "hidden_backing_maximum_displacement_m": round(float(hidden_maximum), 12),
    }


def rim_metrics(body: bpy.types.Object, key_name: str | None) -> dict[str, float]:
    points = body.data.shape_keys.key_blocks[key_name or "Basis"].data
    upper = set(
        base.VISIBLE_RIM_PATHS["upper_right"]
        + base.VISIBLE_RIM_PATHS["upper_left"]
    )
    lower = set(
        base.VISIBLE_RIM_PATHS["lower_right"]
        + base.VISIBLE_RIM_PATHS["lower_left"]
    )
    all_rim = sorted(upper | lower)
    upper_centers = (7066, 7523)
    lower_centers = (7140, 7595)
    upper_z = sum(float(points[index].co.z) for index in upper_centers) / 2.0
    lower_z = sum(float(points[index].co.z) for index in lower_centers) / 2.0
    upper_y = sum(float(points[index].co.y) for index in upper_centers) / 2.0
    lower_y = sum(float(points[index].co.y) for index in lower_centers) / 2.0
    xs = [float(points[index].co.x) for index in all_rim]
    return {
        "vertical_center_separation_m": round(upper_z - lower_z, 9),
        "visible_rim_width_m": round(max(xs) - min(xs), 9),
        "upper_center_y_m": round(upper_y, 9),
        "lower_center_y_m": round(lower_y, 9),
        "mean_rim_y_m": round(
            sum(float(points[index].co.y) for index in all_rim) / len(all_rim), 9
        ),
    }


def geometry_checks(metrics: dict[str, dict[str, float]]) -> dict[str, dict[str, object]]:
    basis = metrics["Basis"]
    checks: dict[str, dict[str, object]] = {}

    ah = metrics[KEY_SPECS["ah"]]
    checks["ah"] = {
        "passed": ah["vertical_center_separation_m"] - basis["vertical_center_separation_m"] >= 0.055,
        "criterion": "center opening increases by at least 0.055 m in authoring local space",
    }
    o = metrics[KEY_SPECS["o"]]
    checks["o"] = {
        "passed": (
            o["vertical_center_separation_m"] - basis["vertical_center_separation_m"] >= 0.050
            and o["visible_rim_width_m"] <= basis["visible_rim_width_m"] * 0.72
        ),
        "criterion": "open oval with rim width at most 72% of Basis",
    }
    ee = metrics[KEY_SPECS["ee"]]
    checks["ee"] = {
        "passed": (
            ee["vertical_center_separation_m"] - basis["vertical_center_separation_m"] >= 0.014
            and ee["visible_rim_width_m"] >= basis["visible_rim_width_m"] * 1.15
        ),
        "criterion": "shallow opening with rim width at least 115% of Basis",
    }
    fv = metrics[KEY_SPECS["fv"]]
    checks["fv"] = {
        "passed": (
            0.004 <= fv["vertical_center_separation_m"] <= 0.010
            and fv["lower_center_y_m"] - basis["lower_center_y_m"] >= 0.008
        ),
        "criterion": "small gap plus inward-tucked raised lower lip",
    }
    mbp = metrics[KEY_SPECS["mbp"]]
    checks["mbp"] = {
        "passed": (
            mbp["vertical_center_separation_m"] <= 0.0
            and mbp["visible_rim_width_m"] <= basis["visible_rim_width_m"] * 0.94
            and mbp["mean_rim_y_m"] - basis["mean_rim_y_m"] <= -0.008
        ),
        "criterion": "closed/narrowed seam with forward lip press",
    }
    return checks


def render_all(
    body: bpy.types.Object,
    hidden: set[int],
    render_dir: Path,
) -> dict[str, dict[str, object]]:
    scene, camera = base.configure_transient_render(body, hidden)
    mouth_center = body.matrix_world @ Vector((0.0, -0.37, 6.582))
    face_center = body.matrix_world @ Vector((0.0, -0.36, 6.72))
    front_mouth_camera = mouth_center + Vector((0.0, -1.0, 0.015))
    front_face_camera = face_center + Vector((0.0, -1.35, 0.02))
    oblique_camera = mouth_center + Vector((0.36, -0.8, 0.035))
    renders: dict[str, dict[str, object]] = {}
    selections = [("basis", None)] + list(KEY_SPECS.items())
    for label, key_name in selections:
        renders[f"{label}_close"] = base.render_view(
            scene,
            camera,
            body,
            render_dir / f"{label}_mouth_closeup.png",
            key_name,
            front_mouth_camera,
            mouth_center,
            0.23,
        )
        renders[f"{label}_front"] = base.render_view(
            scene,
            camera,
            body,
            render_dir / f"{label}_front_face.png",
            key_name,
            front_face_camera,
            face_center,
            0.50,
        )
        renders[f"{label}_oblique"] = base.render_view(
            scene,
            camera,
            body,
            render_dir / f"{label}_oblique.png",
            key_name,
            oblique_camera,
            mouth_center,
            0.24,
        )
    return renders


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
    topology_before = {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "objects": len(bpy.data.objects),
        "mesh_objects": sum(1 for obj in bpy.data.objects if obj.type == "MESH"),
    }

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
        [key.name for key in body.data.shape_keys.key_blocks]
        if body.data.shape_keys is not None
        else []
    )
    if any(name in existing_shape_keys for name in TRIAL_KEY_NAMES):
        raise ValueError(f"v2 trial keys already exist in source: {existing_shape_keys}")
    if body.data.shape_keys is None:
        basis = body.shape_key_add(name="Basis", from_mix=False)
    else:
        basis = body.data.shape_keys.key_blocks.get("Basis")
    if basis is None or len(basis.data) != len(mesh.vertices):
        raise ValueError("valid Basis shape key is required")

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

    shape_keys = [
        create_shape_key(body, role, upper_weights, lower_weights, hidden)
        for role in KEY_SPECS
    ]
    if any(record["hidden_backing_maximum_displacement_m"] != 0.0 for record in shape_keys):
        raise ValueError("a v2 viseme moved the hidden backing component")

    metrics = {"Basis": rim_metrics(body, None)}
    metrics.update({name: rim_metrics(body, name) for name in KEY_SPECS.values()})
    checks = geometry_checks(metrics)
    for record in shape_keys:
        role = str(record["role"])
        record["geometry_check"] = checks[role]
        record["visual_review_disposition"] = "pending_fixed_render_review"

    topology_after = {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "objects": len(bpy.data.objects),
        "mesh_objects": sum(1 for obj in bpy.data.objects if obj.type == "MESH"),
    }
    if topology_after != topology_before:
        raise ValueError(f"v2 authoring changed topology: {topology_before} -> {topology_after}")

    body["kw_trial_status"] = "inactive_same_mesh_viseme_v2_owner_review_only"
    body["kw_trial_run_token"] = args.run_token
    body["kw_trial_source_workspace"] = str(source_workspace)
    body["kw_second_mouth_created"] = False
    body["kw_runtime_export_allowed"] = False
    body["kw_audio_binding_allowed"] = False
    body["kw_live_promotion_allowed"] = False
    base.set_key(body, None)
    bpy.ops.wm.save_as_mainfile(filepath=str(candidate_blend), check_existing=False)

    # Camera, lights, diagnostic materials, and the dark existing backing are
    # transient and are added only after the inactive candidate is saved.
    renders = render_all(body, hidden, render_dir)
    evidence = {
        "schema_version": 2,
        "mode": "inactive_isolated_same_existing_face_surface_viseme_set_v2",
        "run_token": args.run_token,
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
        "rim_metrics": metrics,
        "geometry_checks": checks,
        "fixed_renders": renders,
        "jaw_control": {
            "independent_jaw_control_authored": False,
            "reason": "no separate jaw region was semantically selected; AH moves only the proven same-surface lip neighborhood",
        },
        "engineering_verdict": {
            "same_existing_face_mesh_deformed": True,
            "all_geometry_checks_passed": all(item["passed"] for item in checks.values()),
            "visual_review_completed": False,
            "per_viseme_visual_result": {
                role: "pending_fixed_render_review" for role in KEY_SPECS
            },
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
            "audio_binding_touched": False,
            "person_state_touched": False,
            "activation_attempted": False,
        },
    }
    evidence_path = output_dir / "topology_and_viseme_evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "candidate": str(candidate_blend), "evidence": str(evidence_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
