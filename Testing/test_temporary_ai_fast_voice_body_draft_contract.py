from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import create_temporary_ai_candidate as creator


CONTRACT_PATH = (
    ROOT
    / "TemporaryAI"
    / "config"
    / "temporary_ai_fast_original_voice_body_draft_contract_v1.json"
)


def args_for(
    ai_type: str,
    candidate_id: str,
    *,
    maturity: str = "unresolved",
    no_avatar: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        display_name=candidate_id.replace("_", " ").title(),
        candidate_id=candidate_id,
        ai_type=ai_type,
        requested_by="unit_test",
        goal="bounded static test",
        expert_domain="test domain",
        confirmed_maturity=maturity,
        source_path=[],
        query=[],
        notes="",
        no_avatar=no_avatar,
        include_fanfic=False,
        discover_voice_metadata=False,
    )


class TemporaryAiFastVoiceBodyDraftContractTests(unittest.TestCase):
    def load_contract(self) -> dict:
        return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def create_in_sandbox(self, args: argparse.Namespace) -> tuple[Path, dict]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        sandbox = Path(temporary.name)
        original_root = creator.PROJECT_ROOT
        creator.PROJECT_ROOT = sandbox
        self.addCleanup(setattr, creator, "PROJECT_ROOT", original_root)
        return sandbox, creator.create_candidate(args)

    def test_contract_has_exact_eligible_and_preserved_lanes(self) -> None:
        contract = self.load_contract()
        self.assertEqual(
            contract["eligible_ai_types"],
            ["expert_temp_ai", "generated_original_temp_ai"],
        )
        self.assertIn("canon_reconstruction_temp_ai", contract["preserved_separate_lanes"])
        self.assertIn("historical_person_voice_provenance", contract["preserved_separate_lanes"])
        self.assertFalse(contract["draft_truth"]["activation_allowed"])
        self.assertFalse(contract["draft_truth"]["assignment_allowed"])
        self.assertFalse(contract["draft_truth"]["publication_or_upload_allowed"])

    def test_voice_plan_uses_exact_serial_qwen_models(self) -> None:
        lane = creator.build_original_voice_fast_lane("test_expert")
        sequence = lane["bounded_model_sequence"]
        self.assertEqual(sequence[0]["model"], "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
        self.assertEqual(sequence[1]["action"], "UNLOAD_VOICE_DESIGN_AND_VERIFY_VRAM_RELEASE")
        self.assertEqual(sequence[2]["model"], "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
        self.assertEqual(sequence[3]["action"], "UNLOAD_BASE_AND_VERIFY_VRAM_RELEASE")
        self.assertTrue(lane["one_heavy_gpu_model_at_a_time"])
        self.assertEqual(lane["execution_status"], "PLAN_QUEUED_MODELS_NOT_LOADED_OR_RUN")

    def test_watermark_status_is_qualified_and_circumvention_is_forbidden(self) -> None:
        lane = creator.build_original_voice_fast_lane("test_expert")
        self.assertEqual(
            lane["watermark_status"],
            "NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK",
        )
        self.assertFalse(lane["stronger_watermark_claim_allowed"])
        self.assertEqual(len(lane["stronger_watermark_claim_gates"]), 4)
        self.assertFalse(lane["watermark_removal_or_circumvention_allowed"])
        self.assertEqual(lane["excluded_engines"][0]["engine_family"], "Chatterbox")
        self.assertIn("does not remove", lane["excluded_engines"][0]["reason"])

    def test_voice_mismatch_is_text_plus_silence_only(self) -> None:
        lane = creator.build_original_voice_fast_lane("test_expert")
        self.assertFalse(lane["generic_or_other_person_voice_fallback_allowed"])
        self.assertEqual(lane["exact_profile_mismatch_behavior"], "TEXT_PLUS_SILENCE_ONLY")
        self.assertFalse(lane["profile_assignment_allowed_before_validation"])

    def test_confirmed_adult_routes_only_to_future_sealed_adult_template(self) -> None:
        lane = creator.build_parallel_body_fast_lane(
            "adult_expert", confirmed_maturity="confirmed_adult", avatar_needed=True
        )
        self.assertEqual(lane["template_class"], "CONFIRMED_ADULT_SEALED_TEMPLATE")
        self.assertTrue(lane["adult_anatomy_allowed"])
        self.assertFalse(lane["adulthood_inferred"])
        self.assertFalse(lane["sealed_template_available"])
        self.assertFalse(lane["body_generated_or_completed"])

    def test_nonadult_and_unresolved_route_doll_safe_without_inference(self) -> None:
        for maturity in ("non_adult", "unresolved"):
            with self.subTest(maturity=maturity):
                lane = creator.build_parallel_body_fast_lane(
                    "safe_candidate", confirmed_maturity=maturity, avatar_needed=True
                )
                self.assertEqual(
                    lane["template_class"],
                    "DOLL_SAFE_NON_ANATOMICAL_SEALED_TEMPLATE",
                )
                self.assertTrue(lane["doll_safe_non_anatomical_required"])
                self.assertFalse(lane["adult_anatomy_allowed"])
                self.assertFalse(lane["adulthood_inferred"])

    def test_body_lane_keeps_hair_detached_and_never_activates(self) -> None:
        lane = creator.build_parallel_body_fast_lane(
            "test_expert", confirmed_maturity="unresolved", avatar_needed=True
        )
        self.assertEqual(lane["hair"]["module"], "DETACHED_SEPARATELY_VERSIONED_HAIR")
        self.assertFalse(lane["hair"]["body_regeneration_on_hair_change_allowed"])
        self.assertFalse(lane["activation_allowed"])
        self.assertFalse(lane["assignment_allowed"])
        self.assertFalse(lane["publication_or_upload_allowed"])
        self.assertIn("NO_COMPLETED_HIGH_QUALITY_BODY_CLAIM", lane["quality_claim"])

    def test_expert_creator_immediately_emits_both_private_draft_lanes(self) -> None:
        sandbox, result = self.create_in_sandbox(
            args_for("expert_temp_ai", "fast_expert", maturity="confirmed_adult")
        )
        request = json.loads(
            (sandbox / result["files"]["candidate_request"]).read_text(encoding="utf-8")
        )
        profile = json.loads(
            (sandbox / result["files"]["candidate_profile"]).read_text(encoding="utf-8")
        )
        fast = request["automatic_fast_build"]
        self.assertEqual(fast["status"], "AUTO_DRAFT_PRIVATE_INACTIVE_UNASSIGNED")
        self.assertTrue(fast["created_with_candidate_scaffold"])
        self.assertTrue(fast["validation_runs_asynchronously_after_draft"])
        self.assertEqual(
            fast["body_lane"]["execution_status"],
            "ASYNC_PRIVATE_TEMPLATE_INSTANTIATION_QUEUED_NOT_RUN",
        )
        self.assertEqual(
            profile["automatic_fast_build_status"]["validation_status"],
            "ASYNC_VALIDATION_QUEUED_NOT_RUN",
        )
        self.assertFalse(profile["automatic_fast_build_status"]["body_generated_or_completed"])
        self.assertFalse(profile["automatic_fast_build_status"]["voice_generated_or_assigned"])

    def test_generated_original_gets_lane_but_canon_and_memory_relative_do_not(self) -> None:
        generated_sandbox, generated = self.create_in_sandbox(
            args_for("generated_original_temp_ai", "original_visitor")
        )
        generated_request = json.loads(
            (generated_sandbox / generated["files"]["candidate_request"]).read_text(encoding="utf-8")
        )
        self.assertIn("automatic_fast_build", generated_request)

        for ai_type in ("canon_reconstruction_temp_ai", "memory_relative_temp_ai"):
            with self.subTest(ai_type=ai_type):
                sandbox, result = self.create_in_sandbox(args_for(ai_type, f"separate_{ai_type}"))
                request = json.loads(
                    (sandbox / result["files"]["candidate_request"]).read_text(encoding="utf-8")
                )
                profile = json.loads(
                    (sandbox / result["files"]["candidate_profile"]).read_text(encoding="utf-8")
                )
                self.assertNotIn("automatic_fast_build", request)
                self.assertEqual(profile["voice_and_behavior"]["voice_status"], "to_be_extracted_or_designed")

    def test_explicit_no_avatar_records_plan_without_queueing_body(self) -> None:
        sandbox, result = self.create_in_sandbox(
            args_for("expert_temp_ai", "voice_only_expert", no_avatar=True)
        )
        request = json.loads(
            (sandbox / result["files"]["candidate_request"]).read_text(encoding="utf-8")
        )
        body = request["automatic_fast_build"]["body_lane"]
        self.assertEqual(body["execution_status"], "EXPLICIT_NO_AVATAR_REQUEST_DRAFT_NOT_QUEUED")
        self.assertFalse(body["parallel_with_voice_validation"])

    def test_invalid_maturity_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "confirmed_maturity"):
            creator.build_parallel_body_fast_lane(
                "bad_candidate", confirmed_maturity="adult_guessed", avatar_needed=True
            )


if __name__ == "__main__":
    unittest.main()
