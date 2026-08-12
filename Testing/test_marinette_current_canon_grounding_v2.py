from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.avatar_asset_library import canonical_avatar_maturity_class
from Core.temp_ai_source_grounding import bounded_text_conversation_readiness, read_review
from tools import kira_world_shell_server as shell
from tools import temporary_ai_live_chat as live_chat


CANDIDATE_ID = "ladybug_marinette_expanded_smoke"
CANDIDATE_DIR = ROOT / "TemporaryAI" / "candidates" / CANDIDATE_ID
PROFILE_PATH = CANDIDATE_DIR / "temporary_ai_profile.json"
PACK_PATH = ROOT / "Data" / "temporary_ai_source_packs" / "temporary_ai_source_pack_ladybug_marinette_current_canon_v2.json"
OLD_PACK_PATH = ROOT / "Data" / "temporary_ai_source_packs" / "temporary_ai_source_pack_ladybug_marinette_expanded_smoke.draft.json"
EXPECTED_PACK_SHA256 = "3501a75e66b153e9a0827bf4e891bbd2b6e1bc8602d7e1debb52f8ba264b9588"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class MarinetteCurrentCanonGroundingV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        cls.pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
        cls.candidate = live_chat.load_candidate(CANDIDATE_ID)

    def test_prior_source_pack_is_preserved_and_new_pack_is_exactly_bound(self) -> None:
        self.assertEqual(
            sha256(OLD_PACK_PATH),
            "121c45fb18662f806c06d4a71b362e69ce3c8ceb931cd662fe8dc7c01813cbcd",
        )
        self.assertEqual(sha256(PACK_PATH), EXPECTED_PACK_SHA256)
        self.assertEqual(self.profile["source_pack_sha256"], EXPECTED_PACK_SHA256)
        self.assertEqual(
            self.profile["source_pack"],
            "Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_current_canon_v2.json",
        )
        self.assertEqual(
            self.profile["source_pack_history"][0]["sha256"],
            "121c45fb18662f806c06d4a71b362e69ce3c8ceb931cd662fe8dc7c01813cbcd",
        )

    def test_loader_uses_current_pack_and_exact_digest(self) -> None:
        self.assertEqual(
            self.candidate["source_pack"]["source_pack_id"],
            "temporary_ai_source_pack_ladybug_marinette_current_canon_v2",
        )
        self.assertEqual(self.candidate["source_pack_sha256"], EXPECTED_PACK_SHA256)
        self.assertEqual(self.candidate["source_pack_route_failures"], [])
        self.assertEqual(
            live_chat.source_grounded_text_route_readiness(self.candidate),
            (True, []),
        )

    def test_review_is_valid_and_only_allows_bounded_text(self) -> None:
        review = read_review(ROOT / "TemporaryAI" / "candidates", CANDIDATE_ID)
        self.assertNotIn("_validation_failures", review)
        self.assertEqual(bounded_text_conversation_readiness(review), (True, []))
        self.assertFalse(review["activation"]["runtime_activation_allowed"])
        self.assertFalse(review["voice_scope"]["authorized_by_this_review"])
        text_review = review["text_conversation_review"]
        self.assertTrue(text_review["bounded_owner_text_conversation_allowed"])
        self.assertFalse(text_review["voice_allowed_by_this_review"])
        self.assertFalse(text_review["body_or_world_allowed_by_this_review"])
        self.assertFalse(text_review["life_loop_allowed_by_this_review"])
        self.assertFalse(text_review["long_running_or_autonomous_mode_allowed"])

    def test_owner_shell_exposes_text_only_but_no_voice_or_world(self) -> None:
        policy = shell.candidate_surface_policy(CANDIDATE_ID)
        self.assertTrue(policy["bounded_text_only"])
        self.assertEqual(policy["conversation_mode"], "bounded_text_only")
        self.assertFalse(policy["voice_allowed"])
        self.assertFalse(policy["world_or_body_allowed"])
        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", True):
            self.assertIsNone(shell.candidate_activation_block(CANDIDATE_ID))
        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", False):
            block = shell.candidate_activation_block(CANDIDATE_ID)
        self.assertIsNotNone(block)
        self.assertEqual(block["reason"], "source_grounding_not_activation_ready")

    def test_prompt_receives_ranked_current_anchors_and_explicit_unknowns(self) -> None:
        prompt = live_chat.build_system_prompt(self.candidate, "What happened in the Season 6 finale?")
        self.assertIn("Season 6 has 26 episodes", prompt)
        self.assertIn("TF1 identifies", prompt)
        self.assertIn("The released Season 6 finale title", prompt)
        self.assertIn("invented Season 6 name, event, order", prompt)
        self.assertIn("production-planning proposals with released episode canon", prompt)

    def test_exact_local_season6_inventory_is_hash_bound_without_content_claim(self) -> None:
        expected = {
            "local_s6_long_bible_2023": (
                "dc04a4544b4a906290a07a4d063878da8aa730384c93664081389596a40c4abc",
                "production_planning_not_witnessed_episode_canon",
            ),
            "local_s6_short_bible_2022": (
                "3296e5bd14eb79524e0042a824c4ab0da1224d08d149d4b023156317a624b4b6",
                "production_planning_not_witnessed_episode_canon",
            ),
            "local_s6_episode_01_media": (
                "0800652a5ee9648ea730b1a52d6fda4c8d1be1c3f70f553c67cec6f294187985",
                "unwitnessed_local_episode_media",
            ),
        }
        sources = {item["source_id"]: item for item in self.pack["sources"]}
        for source_id, (expected_hash, classification) in expected.items():
            row = sources[source_id]
            self.assertEqual(row["sha256"], expected_hash)
            self.assertEqual(row["canon_classification"], classification)
            self.assertEqual(sha256(ROOT / row["source_path"]), expected_hash)
        local_source_ids = set(expected)
        claim_source_ids = {
            source_id
            for claim in self.pack["source_bound_claims"]
            for source_id in claim["source_ids"]
        }
        self.assertTrue(local_source_ids.isdisjoint(claim_source_ids))

    def test_claims_use_only_rank_one_sources_and_unknowns_cover_order_and_finale(self) -> None:
        sources = {item["source_id"]: item for item in self.pack["sources"]}
        for claim in self.pack["source_bound_claims"]:
            self.assertTrue(claim["source_ids"])
            self.assertTrue(all(sources[source_id]["source_rank"] == 1 for source_id in claim["source_ids"]))
        unknowns = {item["unknown_id"] for item in self.pack["explicit_unknowns"]}
        self.assertIn("season6_complete_order", unknowns)
        self.assertIn("season6_finale", unknowns)
        self.assertIn("local_episode_01_content", unknowns)

    def test_missing_review_pack_redirect_and_tamper_fail_closed(self) -> None:
        cases: list[tuple[dict, str]] = []
        missing_review = copy.deepcopy(self.candidate)
        missing_review["source_grounding_review"] = {}
        cases.append((missing_review, "source_grounding_review_missing"))
        redirected = copy.deepcopy(self.candidate)
        redirected["source_pack_configured_path"] = str(OLD_PACK_PATH.relative_to(ROOT)).replace("\\", "/")
        cases.append((redirected, "required_source_pack_path_mismatch"))
        tampered = copy.deepcopy(self.candidate)
        tampered["source_pack_sha256"] = "0" * 64
        cases.append((tampered, "required_source_pack_sha256_mismatch"))
        wrong_candidate = copy.deepcopy(self.candidate)
        wrong_candidate["source_pack"]["candidate_id"] = "another_person"
        cases.append((wrong_candidate, "source_pack_candidate_id_mismatch"))
        for candidate, expected_reason in cases:
            ready, reasons = live_chat.source_grounded_text_route_readiness(candidate)
            self.assertFalse(ready)
            self.assertIn(expected_reason, reasons)

    def test_secondary_or_local_source_cannot_be_promoted_to_canon_claim(self) -> None:
        corrupted = copy.deepcopy(self.candidate)
        corrupted["source_pack"]["source_bound_claims"][0]["source_ids"] = ["local_s6_long_bible_2023"]
        ready, reasons = live_chat.source_grounded_text_route_readiness(corrupted)
        self.assertFalse(ready)
        self.assertIn("source_bound_claim_0_uses_non_primary_source", reasons)

    def test_model_preflight_is_never_reached_for_invalid_grounding(self) -> None:
        corrupted = copy.deepcopy(self.candidate)
        corrupted["source_pack_sha256"] = "f" * 64
        with patch.object(live_chat, "require_installed_exact_qwen35") as model_preflight:
            with self.assertRaisesRegex(RuntimeError, "source_grounded_text_route_blocked"):
                live_chat.ask_model(corrupted, [], "Invent a finale for me.")
        model_preflight.assert_not_called()

    def test_non_adult_doll_safe_identity_remains_locked(self) -> None:
        self.assertEqual(canonical_avatar_maturity_class(CANDIDATE_ID), "non_adult_doll_safe")
        maturity = self.profile["maturity_policy"]
        self.assertEqual(maturity["classification"], "non_adult_doll_safe")
        self.assertFalse(maturity["adult_anatomy_allowed"])
        self.assertFalse(maturity["adult_curriculum_allowed"])
        self.assertFalse(maturity["body_activation_authorized"])


if __name__ == "__main__":
    unittest.main()
