import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(r"C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1\kira_video_studio\deformation_animation.py")
SPEC = importlib.util.spec_from_file_location("deformation_animation", MODULE)
animation = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = animation
SPEC.loader.exec_module(animation)


class DeformationAnimationPipelineTests(unittest.TestCase):
    def test_rejects_flipbook_and_mouth_overlay(self):
        result = animation.validate_animation_job({
            "technique": "complete_sprite_swap",
            "independent_mouth_overlay_count": 1,
        })
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("rejected_pose_swapping_technique", result["reasons"])
        self.assertIn("second_or_independent_mouth_path_forbidden", result["reasons"])

    def test_accepts_only_internal_authoring_not_production(self):
        result = animation.validate_animation_job({
            "technique": "layered_bone_mesh_deformation",
            "professional_layered_artwork": True,
            "hand_authored_joint_behavior": True,
            "smooth_easing_and_overlap": True,
            "visual_cleanup_required": True,
            "independent_mouth_overlay_count": 0,
            "integrated_face_mesh_mouth": True,
        })
        self.assertEqual("READY_FOR_INTERNAL_AUTHORING", result["status"])
        self.assertFalse(result["production_render_allowed"])

    def test_phonemes_must_bind_to_final_waveform(self):
        with tempfile.TemporaryDirectory() as temp:
            wav = Path(temp) / "voice.wav"
            wav.write_bytes(b"wave")
            cue = animation.PhonemeCue("AH", 0.0, 0.2, 0.9)
            result = animation.validate_phoneme_alignment(
                waveform_path=wav,
                recorded_waveform_sha256="0" * 64,
                cues=[cue],
                audio_duration_seconds=1.0,
            )
            self.assertEqual("FAILED", result["status"])
            self.assertIn(
                "phoneme_timing_not_bound_to_exact_final_waveform",
                result["reasons"],
            )
