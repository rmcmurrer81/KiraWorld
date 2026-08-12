from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_source_grounding import (  # noqa: E402
    activation_block,
    read_review,
    validate_review,
)
from tools.kira_world_shell_server import candidate_activation_block  # noqa: E402
from tools.build_temporary_ai_candidate_graph import source_summary  # noqa: E402
from tools.temporary_ai_live_chat import (  # noqa: E402
    build_system_prompt,
    load_candidate,
    source_readiness,
)


CANDIDATES = {
    "blue_played_by_julia_stiles_blue_20260605_220748": (
        "exact_work_character_and_default_continuity_resolved",
        "Blue web series (2012-2015)",
    ),
    "hannah_baxter_belle_hannah_baxter_20260605_214834": (
        "exact_work_character_and_default_continuity_resolved",
        "Secret Diary of a Call Girl television series",
    ),
    "kara_zor_el_my_adventures_with_superman_kara_zor_el_20260606_181026": (
        "exact_version_resolved",
        "My Adventures with Superman animated series",
    ),
    "ruby_supernatural_ruby_supernatural_20260605_223416": (
        "character_and_whole_series_knowledge_resolved_embodiment_unresolved",
        "Supernatural television series",
    ),
    "skynet_skynet_20260605_224820": (
        "exact_version_resolved",
        "Terminator Genisys film embodiment with owner-directed whole-screen-continuity comparison",
    ),
}


class TempAISourceGroundingReviewTests(unittest.TestCase):
    def test_five_reviews_are_valid_and_fail_closed(self) -> None:
        root = PROJECT_ROOT / "TemporaryAI" / "candidates"
        for candidate_id, (identity_status, source_family) in CANDIDATES.items():
            with self.subTest(candidate_id=candidate_id):
                review = read_review(root, candidate_id)
                self.assertEqual(validate_review(review, candidate_id), [])
                self.assertEqual(review["identity_binding"]["status"], identity_status)
                self.assertEqual(review["identity_binding"]["source_family"], source_family)
                self.assertFalse(review["activation"]["runtime_activation_allowed"])
                self.assertFalse(review["voice_scope"]["authorized_by_this_review"])
                self.assertEqual(
                    activation_block(review)["reason"],
                    "source_grounding_not_activation_ready",
                )

    def test_source_counts_do_not_override_grounding_block(self) -> None:
        for candidate_id in CANDIDATES:
            with self.subTest(candidate_id=candidate_id):
                readiness = source_readiness(load_candidate(candidate_id))
                self.assertEqual(readiness["status"], "source_grounding_blocked")
                self.assertTrue(readiness["notes"])

    def test_world_shell_blocks_all_five_without_activation(self) -> None:
        for candidate_id in CANDIDATES:
            with self.subTest(candidate_id=candidate_id):
                block = candidate_activation_block(candidate_id)
                self.assertIsNotNone(block)
                self.assertEqual(block["reason"], "source_grounding_not_activation_ready")

    def test_candidate_graph_exposes_grounding_status_not_just_source_count(self) -> None:
        root = PROJECT_ROOT / "TemporaryAI" / "candidates"
        candidate_id = "hannah_baxter_belle_hannah_baxter_20260605_214834"
        folder = root / candidate_id
        profile = json.loads((folder / "temporary_ai_profile.json").read_text(encoding="utf-8-sig"))
        summary = source_summary(folder, profile)
        self.assertEqual(summary["source_count"], 3)
        self.assertEqual(
            summary["grounding_review_status"],
            "whole_released_continuity_default_applied_source_expansion_required",
        )
        self.assertFalse(summary["grounding_runtime_activation_allowed"])
        self.assertFalse(summary["needs_clarification"])

    def test_blue_prompt_separates_fact_from_adaptive_interpretation(self) -> None:
        prompt = build_system_prompt(
            load_candidate("blue_played_by_julia_stiles_blue_20260605_220748"),
            "Tell me about your life.",
        )
        self.assertIn("FACT: Blue is a mother living in Los Angeles.", prompt)
        self.assertIn("INTERPRETIVE:", prompt)
        self.assertIn("Blue web series, whole released three-season continuity", prompt)
        self.assertNotIn("Unresolved owner choice: Choose a continuity endpoint", prompt)
        self.assertIn("Blue works in AI or computer-system development", prompt)
        self.assertIn("personality fidelity or activation readiness", prompt)

    def test_kara_prompt_keeps_season_three_endpoint_and_motion_gap(self) -> None:
        prompt = build_system_prompt(
            load_candidate(
                "kara_zor_el_my_adventures_with_superman_kara_zor_el_20260606_181026"
            ),
            "How do you move around on Earth?",
        )
        self.assertIn(
            "My Adventures with Superman season 3 through the latest verified released episode",
            prompt,
        )
        self.assertIn("season-three episodes 1 through 3", prompt)
        self.assertIn("Jor-El is not her father", prompt)
        self.assertIn("walking, hovering, flight transitions", prompt)
        self.assertIn("source review does not certify any animation", prompt)

    def test_skynet_prompt_uses_cross_timeline_knowledge_without_body_merge(self) -> None:
        prompt = build_system_prompt(
            load_candidate("skynet_skynet_20260605_224820"),
            "Tell me about Cameron.",
        )
        self.assertIn("Terminator Genisys Alex / Skynet", prompt)
        self.assertIn("The Sarah Connor Chronicles can inform alternate-timeline comparison", prompt)
        self.assertIn("without pretending that its events all happened directly", prompt)
        self.assertIn("literally omniscient", prompt)
        self.assertIn("primary behavior, dialogue, movement, and voice packs are incomplete", prompt)

    def test_resolved_profiles_do_not_reask_for_a_season_or_knowledge_timeline(self) -> None:
        expected_instruction = {
            "blue_played_by_julia_stiles_blue_20260605_220748": "Do not ask Robert to select a season again",
            "hannah_baxter_belle_hannah_baxter_20260605_214834": "Do not ask Robert to select a series or season again",
            "kara_zor_el_my_adventures_with_superman_kara_zor_el_20260606_181026": "Do not ask Robert to reselect the adaptation or season",
            "ruby_supernatural_ruby_supernatural_20260605_223416": "Do not ask Robert to select a season again",
            "skynet_skynet_20260605_224820": "Do not ask Robert to choose a Terminator knowledge timeline again",
        }
        for candidate_id, instruction in expected_instruction.items():
            with self.subTest(candidate_id=candidate_id):
                profile = load_candidate(candidate_id)["profile"]
                seeds = profile["knowledge_plan"]["core_competency_seed"]
                joined = "\n".join(str(item) for item in seeds)
                self.assertIn(instruction, joined)
                self.assertNotIn("Ask for clarification when multiple versions exist.", seeds)

    def test_present_malformed_review_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate_id = "bad_candidate"
            folder = root / candidate_id
            folder.mkdir()
            (folder / "source_grounding_review.json").write_text(
                json.dumps({"schema_version": 1, "candidate_id": "somebody_else"}),
                encoding="utf-8",
            )
            review = read_review(root, candidate_id)
        self.assertTrue(review["_validation_failures"])
        self.assertEqual(activation_block(review)["reason"], "invalid_source_grounding_review")

    def test_changed_local_evidence_bytes_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            candidate_root = project / "TemporaryAI" / "candidates"
            candidate_id = "hash_test_candidate"
            folder = candidate_root / candidate_id
            evidence = project / "evidence.txt"
            folder.mkdir(parents=True)
            evidence.write_text("changed bytes", encoding="utf-8")
            review = {
                "schema_version": 1,
                "candidate_id": candidate_id,
                "review_status": "test",
                "identity_binding": {
                    "status": "exact_version_resolved",
                    "source_family": "test",
                    "unresolved_owner_choices": [],
                },
                "evidence_ledger": [
                    {
                        "path": "evidence.txt",
                        "sha256": "0" * 64,
                        "evidence_class": "test",
                    }
                ],
                "canon_anchors": [],
                "adaptive_behavior_hypotheses": [],
                "source_gaps": [],
                "activation": {"runtime_activation_allowed": False},
                "voice_scope": {"authorized_by_this_review": False},
            }
            (folder / "source_grounding_review.json").write_text(
                json.dumps(review), encoding="utf-8"
            )
            loaded = read_review(candidate_root, candidate_id)
        self.assertIn("evidence_0_sha256_mismatch", loaded["_validation_failures"])
        self.assertEqual(activation_block(loaded)["reason"], "invalid_source_grounding_review")


if __name__ == "__main__":
    unittest.main()
