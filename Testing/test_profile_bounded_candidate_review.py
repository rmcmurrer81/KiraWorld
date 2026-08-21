from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

from Core.profile_bounded_candidate_review import (
    DRAFT_REVIEW_LABEL,
    ProfileBoundedReviewError,
    build_profile_bounded_system_prompt,
    label_profile_bounded_reply,
    load_profile_bounded_candidate,
    profile_bounded_context,
)


BOUNDED_CANDIDATES = (
    "h_h_holmes_h_h_holmes_20260605_221432",
    "jessica_hale_robotics_engineer_20260611_041314",
    "kathryn_merteuil_kathryn_merteuil_20260605_213017",
    "ladybug_marinette_expanded_smoke",
    "peter_parker_spider_man_no_way_home_final_suit",
    "ryan_hale_quantum_mechanics_expert_20260608_200749",
)


class ProfileBoundedCandidateReviewTests(unittest.TestCase):
    def test_incomplete_checked_in_candidates_load_without_full_source_gate_bypass(self) -> None:
        for candidate_id in BOUNDED_CANDIDATES:
            with self.subTest(candidate_id=candidate_id):
                candidate = load_profile_bounded_candidate(ROOT, candidate_id)
                self.assertEqual(candidate["candidate_id"], candidate_id)
                self.assertEqual(candidate["review_mode"], "profile_bounded_draft")
                self.assertNotIn("source_pack", candidate)
                self.assertNotIn("source_grounding_review", candidate)

    def test_allowlisted_context_excludes_source_and_runtime_state(self) -> None:
        candidate = load_profile_bounded_candidate(
            ROOT, "ladybug_marinette_expanded_smoke"
        )
        context = profile_bounded_context(candidate)
        encoded = json.dumps(context, sort_keys=True)

        self.assertIn("canon_fact_sheet", encoded)
        self.assertIn("identity_boundaries", encoded)
        self.assertNotIn("recent_chat_records", encoded)
        self.assertNotIn("attached_workspaces", encoded)
        self.assertNotIn("source_grounding_review", encoded)
        self.assertNotIn("reliable_source_pack", encoded)

    def test_system_prompt_states_exact_nonactivation_boundaries(self) -> None:
        candidate = load_profile_bounded_candidate(
            ROOT, "peter_parker_spider_man_no_way_home_final_suit"
        )
        prompt = build_profile_bounded_system_prompt(candidate)

        self.assertIn("PROFILE-BOUNDED DRAFT REVIEW, not activation", prompt)
        self.assertIn("Do not claim verified canon", prompt)
        self.assertIn("an authentic voice", prompt)
        self.assertIn("body", prompt)
        self.assertIn("world presence", prompt)
        self.assertIn("Keep Kira, Lisa, Synthetic Robert", prompt)

    def test_reply_label_is_programmatically_guaranteed(self) -> None:
        self.assertEqual(
            label_profile_bounded_reply("Hello, Robert."),
            f"{DRAFT_REVIEW_LABEL} Hello, Robert.",
        )
        labelled = f"{DRAFT_REVIEW_LABEL} Already labelled."
        self.assertEqual(label_profile_bounded_reply(labelled), labelled)

    def test_candidate_path_traversal_is_rejected(self) -> None:
        with self.assertRaisesRegex(ProfileBoundedReviewError, "invalid_candidate_id"):
            load_profile_bounded_candidate(ROOT, "../outside")

    def test_explicit_all_false_text_permissions_remain_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            folder = root / "TemporaryAI" / "candidates" / "blocked_candidate"
            folder.mkdir(parents=True)
            (folder / "temporary_ai_profile.json").write_text(
                json.dumps(
                    {
                        "display_name": "Blocked Candidate",
                        "status": "draft",
                        "activation_policy": {
                            "owner_probe_allowed": False,
                            "bounded_text_only_conversation_allowed": False,
                            "text_chat_allowed": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ProfileBoundedReviewError, "explicit_text_review_denial"
            ):
                load_profile_bounded_candidate(root, "blocked_candidate")


if __name__ == "__main__":
    unittest.main()
