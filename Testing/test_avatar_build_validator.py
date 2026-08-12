import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_avatar_build import validate_avatar_config, validate_avatar_metadata, validate_avatar_request  # noqa: E402


class AvatarBuildValidatorTests(unittest.TestCase):
    def test_user_config_requires_real_robert_separation(self) -> None:
        data = {
            "build_id": "user_avatar_v1",
            "target_type": "user",
            "build_mode": "reconstruction_real",
            "input_sources": {},
            "reconstruction_rules": {},
            "identity_foundation": {"real_robert_separation_required": True},
            "processing_steps": {},
            "output": {"visibility": "private", "approval_required": True},
            "validation": {},
            "revision_settings": {},
        }

        self.assertEqual(validate_avatar_config(data), [])

    def test_pre_gpu_request_cannot_claim_rendered_avatar_exists(self) -> None:
        data = {
            "request_id": "avatar_request_bad",
            "target_type": "user",
            "target_id": "robert_user_avatar",
            "requested_by": "robert",
            "build_mode": "reconstruction_real",
            "stage": "pre_gpu",
            "purpose": "bad request",
            "source_policy": {},
            "privacy": {
                "owner_controls_visibility": True,
                "body_generation_private": True,
                "pre_clothing_visibility_allowed": False,
                "underwear_or_clothing_required_before_default_visibility": True,
                "allowed_preview_levels": ["no_preview", "shoulders_up", "clothed_only"],
            },
            "private_reference_policy": {
                "owner_controlled": True,
                "may_be_used_for_other_avatars": False,
                "may_be_used_for_public_exports": False,
            },
            "feature_selection": {"owner_final_decision": True, "allowed_features": ["eyes"]},
            "wardrobe_plan": {
                "starts_after_body_creation": True,
                "minimum_starter_outfits": ["casual", "relaxed_home", "social_event"],
            },
            "output_expectation": {"claim_rendered_avatar_exists": True},
            "status": "draft",
        }

        errors = validate_avatar_request(data)
        self.assertTrue(any("pre-GPU" in error for error in errors))

    def test_request_blocks_default_pre_clothing_visibility(self) -> None:
        data = {
            "request_id": "avatar_request_bad_visibility",
            "target_type": "kira",
            "target_id": "kira_core_avatar",
            "requested_by": "kira",
            "build_mode": "generated",
            "stage": "pre_gpu",
            "purpose": "bad request",
            "source_policy": {},
            "privacy": {
                "owner_controls_visibility": True,
                "body_generation_private": True,
                "pre_clothing_visibility_allowed": True,
                "underwear_or_clothing_required_before_default_visibility": True,
                "allowed_preview_levels": ["no_preview", "shoulders_up"],
            },
            "private_reference_policy": {
                "owner_controlled": True,
                "may_be_used_for_other_avatars": False,
                "may_be_used_for_public_exports": False,
            },
            "feature_selection": {"owner_final_decision": True, "allowed_features": ["eyes"]},
            "wardrobe_plan": {
                "starts_after_body_creation": True,
                "minimum_starter_outfits": ["casual", "relaxed_home", "social_event"],
            },
            "output_expectation": {"claim_rendered_avatar_exists": False},
            "status": "draft",
        }

        errors = validate_avatar_request(data)
        self.assertTrue(any("pre_clothing_visibility" in error for error in errors))

    def test_pre_gpu_metadata_cannot_mark_body_generated(self) -> None:
        data = {
            "avatar_id": "robert_user_avatar",
            "target_type": "user",
            "build_id": "user_avatar_v1",
            "build_mode": "reconstruction_real",
            "stage": "pre_gpu",
            "approval_state": "waiting_for_gpu",
            "visibility_state": "private",
            "body_profile": {"status": "generated"},
            "wardrobe": {},
            "voice_link": {},
            "privacy": {"owner_controls_visibility": True, "body_generation_private": True},
            "source_trace": {},
            "status": "waiting_for_gpu",
        }

        errors = validate_avatar_metadata(data)
        self.assertTrue(any("pre-GPU" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
