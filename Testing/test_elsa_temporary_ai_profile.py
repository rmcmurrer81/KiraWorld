from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = (
    ROOT
    / "TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716"
)
PROFILE = CANDIDATE / "temporary_ai_profile.json"
SOURCE_PACK = CANDIDATE / "reliable_source_pack.json"
ACTIVATION = CANDIDATE / "activation_plan.json"
VOICE = CANDIDATE / "voice_discovery_request.json"
VOICE_INDEX = CANDIDATE / "voice_discovery_index.json"
AVATAR = (
    ROOT
    / "Avatar/temp_ai/elsa_frozen_frozen_fever_frozen_ii_20260716/avatar_profile.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ElsaTemporaryAIProfileTests(unittest.TestCase):
    def test_exact_owner_selected_sequence_ends_at_frozen_ii(self) -> None:
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        continuity = profile["continuity_selection"]
        self.assertEqual(
            continuity["ordered_titles"],
            ["Frozen (2013)", "Frozen Fever (2015)", "Frozen II (2019)"],
        )
        self.assertEqual(continuity["present_timepoint"], "end of Frozen II")
        self.assertTrue(continuity["unrelated_titles_are_not_lived_continuity"])
        self.assertNotIn(
            "Olaf's Frozen Adventure", continuity["ordered_titles"]
        )

    def test_profile_is_adult_inactive_and_not_doll_safe(self) -> None:
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        continuity = profile["continuity_selection"]
        self.assertEqual(continuity["maturity_lane"], "adult")
        self.assertTrue(continuity["adult_topology_required"])
        self.assertFalse(continuity["non_adult_doll_safe_treatment_allowed"])
        self.assertFalse(profile["boundaries"]["runtime_activation_allowed"])
        self.assertFalse(profile["activation_policy"]["owner_probe_allowed"])

    def test_source_pack_is_hash_bound_and_uses_official_pages(self) -> None:
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        pack = json.loads(SOURCE_PACK.read_text(encoding="utf-8"))
        self.assertEqual(profile["source_pack_sha256"], sha256(SOURCE_PACK))
        urls = {source.get("url", "") for source in pack["sources"]}
        self.assertIn("https://movies.disney.com/frozen", urls)
        self.assertIn(
            "https://www.disneyplus.com/en-gs/browse/entity-c3883166-7a8e-4a55-96be-ebc8fc25161a",
            urls,
        )
        self.assertIn("https://movies.disney.com/frozen-2", urls)

    def test_voice_metadata_was_ranked_without_media_voice_or_activation(self) -> None:
        voice = json.loads(VOICE.read_text(encoding="utf-8"))
        index = json.loads(VOICE_INDEX.read_text(encoding="utf-8"))
        self.assertEqual(
            voice["status"],
            "metadata_discovery_requested_owner_authorized_no_media_or_voice_operation",
        )
        self.assertTrue(voice["discovery"]["enabled_now"])
        self.assertFalse(voice["discovery"]["allow_voice_synthesis"])
        self.assertFalse(voice["discovery"]["allow_voice_assignment"])
        self.assertFalse(voice["policy"]["activation_allowed"])
        self.assertGreaterEqual(len(index["recording_candidates"]), 5)
        self.assertEqual(index["ranked_recording_review_queue"][0]["rank"], 1)
        self.assertFalse(index["operation_evidence"]["media_download_attempted"])
        self.assertFalse(index["operation_evidence"]["audio_extraction_attempted"])
        self.assertFalse(index["selection"]["voice_assigned"])
        self.assertFalse(index["readiness_gates"]["voice_reference_ready"])
        self.assertFalse(index["readiness_gates"]["temporary_ai_activation_ready"])

    def test_source_grounding_review_allows_only_bounded_text_probe(self) -> None:
        from Core.temp_ai_source_grounding import (
            bounded_text_conversation_readiness,
            read_review,
        )

        review = read_review(ROOT / "TemporaryAI/candidates", CANDIDATE.name)
        self.assertNotIn("_validation_failures", review)
        self.assertEqual(bounded_text_conversation_readiness(review), (True, []))
        self.assertFalse(review["activation"]["runtime_activation_allowed"])
        self.assertFalse(review["activation"]["owner_probe_allowed"])
        self.assertTrue(review["activation"]["bounded_owner_text_probe_allowed"])
        self.assertFalse(review["voice_scope"]["authorized_by_this_review"])
        self.assertIn("ready_for_short", review["blocks"]["bounded_text_owner_probe"])

    def test_reference_model_does_not_claim_a_complete_body(self) -> None:
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        avatar = json.loads(AVATAR.read_text(encoding="utf-8"))
        self.assertTrue(profile["avatar_and_movement"]["reference_only"])
        self.assertFalse(
            profile["avatar_and_movement"]["copy_reference_mesh_as_body_allowed"]
        )
        self.assertFalse(profile["avatar_and_movement"]["complete_body_proven"])
        self.assertFalse(avatar["source_limits"]["complete_body_proven"])
        self.assertFalse(avatar["positive_proof_gate"]["released"])

    def test_activation_plan_is_fail_closed(self) -> None:
        activation = json.loads(ACTIVATION.read_text(encoding="utf-8"))
        self.assertFalse(activation["runtime_activation_allowed"])
        self.assertFalse(activation["owner_probe_allowed"])
        self.assertFalse(any(activation["may_be_activated_by"].values()))
        self.assertTrue(activation["bounded_owner_text_probe_allowed"])
        self.assertTrue(activation["mode_readiness"]["bounded_text_owner_probe"]["ready"])
        self.assertFalse(activation["mode_readiness"]["voice_chat"]["ready"])
        self.assertFalse(activation["mode_readiness"]["runtime_3d"]["ready"])


if __name__ == "__main__":
    unittest.main()
