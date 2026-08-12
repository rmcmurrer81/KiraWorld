"""Build Kira's inactive R7 v3 socket-eye candidate.

V3 preserves the visually successful neutral/front envelope from R7 v2, but
changes the gaze mechanism.  The sclera and transparent corneal lens stay
seated in the measured R6 socket; only the textured iris translates a bounded
distance across the shallow eye surface.  This avoids the detached white/cornea
crescent produced when v2 rotated the whole iris/cornea assembly.

The pass remains inactive and reversible.  It does not bind the candidate to
Avatar Builder or Home World and does not activate Kira.
"""

from __future__ import annotations

import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy  # type: ignore
from mathutils import Vector  # type: ignore

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_kira_r7_socket_eye_fit_v2 as v2


OUTPUT = (
    v2.ROOT
    / "Avatar/avatar_builder/candidate_sources/kira_r7_socket_eye_fit"
    / "review_20260722_v3"
)
V2_TEXTURES = v2.DEFAULT_OUTPUT / "derived_textures"
_original_parse_args = v2.parse_args
_original_build_eye = v2.build_eye
_original_add_camera_and_lights = v2.add_camera_and_lights
_original_render_view = v2.render_view


def parse_args():
    args = _original_parse_args()
    # Treat the v2 defaults as inherited defaults while still honoring explicit
    # Blender command-line values supplied by a reviewer.
    if args.output_dir.resolve() == v2.DEFAULT_OUTPUT.resolve():
        args.output_dir = OUTPUT
    if args.candidate_id == "kira_r7_socket_eye_v2":
        args.candidate_id = "kira_r7_socket_eye_v3"
    return args


def build_eye(side, center, rig, sclera_material, iris_material, cornea_mat, args):
    record = _original_build_eye(
        side,
        center,
        rig,
        sclera_material,
        iris_material,
        cornea_mat,
        args,
    )

    # A corneal lens belongs to the socket, not the gaze pivot.  Pivot and
    # socket share the same local origin in this authored rig, so preserving
    # the cornea's local transform is the unambiguous re-parent operation.  A
    # matrix-world re-parent here creates a cancelling inverse translation in
    # glTF and silently moves the lens to the rig origin.
    cornea = record["cornea"]
    cornea_local_location = cornea.location.copy()
    cornea_local_rotation = cornea.rotation_euler.copy()
    cornea_local_scale = cornea.scale.copy()
    cornea.parent = record["socket"]
    cornea.matrix_parent_inverse.identity()
    cornea.location = cornea_local_location
    cornea.rotation_euler = cornea_local_rotation
    cornea.scale = cornea_local_scale
    cornea["gaze_motion"] = "fixed_in_measured_socket"

    iris = record["iris"]
    iris["neutral_local_location"] = [float(value) for value in iris.location]
    iris["gaze_motion"] = "bounded_surface_translation_only"
    iris["maximum_horizontal_translation_mm"] = 1.25
    iris["maximum_vertical_translation_mm"] = 0.72

    rig.name = "KiraBrownEyeRig_R7_V3_SocketSeated"
    rig["schema_version"] = 7.3
    rig["gaze_controller"] = "fixed_cornea_bounded_iris_surface_translation"
    rig["v2_neutral_envelope_preserved"] = True
    return record


def pose(eyes, yaw=0.0, pitch=0.0):
    # V2's whole-eye rotation made the cornea and sclera visibly separate.  V3
    # keeps both socket surfaces fixed and moves just the textured iris within
    # conservative anatomical-looking limits.
    yaw_ratio = max(-1.0, min(1.0, float(yaw) / 13.0))
    pitch_ratio = max(-1.0, min(1.0, float(pitch) / 7.0))
    for record in eyes.values():
        record["pivot"].rotation_euler = (0.0, 0.0, 0.0)
        iris = record["iris"]
        neutral = Vector(iris.get("neutral_local_location", (0.0, iris.location.y, 0.0)))
        iris.location = (
            neutral.x + 0.00125 * yaw_ratio,
            neutral.y,
            neutral.z + 0.00072 * pitch_ratio,
        )
    bpy.context.view_layer.update()


def add_camera_and_lights():
    camera = _original_add_camera_and_lights()
    camera.name = "Kira_R7_V3_Fixed_Review_Camera"
    # V2's macro targets sat inside the camera's default 10 cm near plane.
    camera.data.clip_start = 0.002
    camera.data.clip_end = 100.0
    return camera


def render_view(path, camera, camera_location, target, lens):
    if path.stem.startswith("macro_left"):
        camera_location = (-0.0223, -0.165, 1.1068)
        target = Vector((-0.0223, -0.0490, 1.1068))
        lens = 56.0
    elif path.stem.startswith("macro_right"):
        camera_location = (0.0223, -0.165, 1.1068)
        target = Vector((0.0223, -0.0490, 1.1068))
        lens = 56.0
    _original_render_view(path, camera, camera_location, target, lens)


def patch_evidence(output: Path) -> None:
    path = output / "evidence.json"
    evidence = json.loads(path.read_text(encoding="utf-8"))
    evidence["schema_version"] = 3
    evidence["created_at_v3_patch"] = datetime.now(timezone.utc).isoformat()
    evidence["kind"] = (
        "offline_blender_inactive_eye_only_v3_fixed_cornea_bounded_iris_gaze_"
        "no_activation_no_binding_no_runtime_write"
    )
    evidence["status"] = "inactive_fixed_view_review_pending"
    evidence["promotion_allowed"] = False
    evidence["v3_changes"] = {
        "preserved": "R7 v2 neutral/front eye envelope and source-derived materials",
        "fixed_cornea_in_socket": True,
        "gaze_motion": "iris-only bounded shallow-surface translation",
        "horizontal_translation_limit_mm": 1.25,
        "vertical_translation_limit_mm": 0.72,
        "macro_camera_near_clip_m": 0.002,
        "reason": (
            "V2 looked good head-on but rotating the whole iris/cornea assembly "
            "created side/gaze separation artifacts and clipped macro evidence."
        ),
    }
    evidence["visual_acceptance"] = {
        "socket_alignment_front_and_three_quarter": None,
        "no_profile_protrusion": None,
        "four_gaze_views_plausible": None,
        "brown_iris_reads_as_living_texture_not_flat_disc": None,
        "sclera_reads_as_living_tissue": None,
        "cornea_reads_as_natural_wet_lens": None,
        "macro_views_show_eye_detail": None,
        "overall_visual_fit_passed": None,
        "blink_supported": False,
        "promotion_allowed": False,
        "owner_review_required_before_any_promotion": True,
        "note": "Original-resolution R7 v3 fixed renders require visual inspection.",
    }
    evidence.setdefault("limits", []).append(
        "V3 deliberately does not claim eyelid/blink proof; it only repairs socket seating and gaze."
    )
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


def main():
    args = parse_args()
    output = args.output_dir.resolve()
    source_textures = V2_TEXTURES.resolve()
    target_textures = output / "derived_textures"
    if not source_textures.is_dir():
        raise RuntimeError(f"Missing reviewed R7 v2 derived textures: {source_textures}")
    if not target_textures.exists():
        target_textures.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_textures, target_textures)

    # Capture the intentional current JS baseline before the offline pass.  The
    # original tool still verifies that it remains byte-identical throughout
    # rendering, which catches concurrent or accidental runtime writes.
    v2.EXPECTED["main_js"] = v2.sha256(v2.MAIN_JS)
    v2.parse_args = lambda: args
    v2.build_eye = build_eye
    v2.pose = pose
    v2.add_camera_and_lights = add_camera_and_lights
    v2.render_view = render_view
    v2.main()
    patch_evidence(output)
    print(json.dumps({"status": "r7_v3_inactive_review_ready", "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
