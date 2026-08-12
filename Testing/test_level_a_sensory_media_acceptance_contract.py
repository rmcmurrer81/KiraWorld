from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from Core.level_a_runtime_common import CAPABILITY_LADDER
from Core.level_a_sensory_media_fixture import CAPABILITY_STATUSES


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "tooling"
    / "level_a_sensory_media_acceptance_contract_v1.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LevelASensoryMediaAcceptanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_contract_has_exact_level_a_status_and_ladder(self) -> None:
        self.assertEqual(self.contract["status"], "NON_PERSON_FIXTURE_PASS")
        self.assertEqual(tuple(self.contract["capability_ladder"]), CAPABILITY_LADDER)
        self.assertEqual(self.contract["current_capability_statuses"], CAPABILITY_STATUSES)
        ceiling = CAPABILITY_LADDER.index("NON_PERSON_FIXTURE_PASS")
        for status in self.contract["current_capability_statuses"].values():
            self.assertLessEqual(CAPABILITY_LADDER.index(status), ceiling)

    def test_reusable_module_and_test_hashes_are_exact(self) -> None:
        interface = self.contract["reusable_fixture_interface"]
        for path_key, hash_key, size_key in (
            ("module", "sha256", "bytes"),
            ("test_module", "test_sha256", "test_bytes"),
        ):
            path = ROOT / interface[path_key]
            self.assertEqual(path.stat().st_size, interface[size_key])
            self.assertEqual(sha256_file(path), interface[hash_key])

    def test_all_reused_component_hashes_are_exact(self) -> None:
        for record in self.contract["existing_runtime_components_reused_not_replaced"]:
            path = ROOT / record["path"]
            self.assertEqual(path.stat().st_size, record["bytes"])
            self.assertEqual(sha256_file(path), record["sha256"])

    def test_three_media_access_categories_and_fail_closed_rules_are_bound(self) -> None:
        media = self.contract["resident_media_contract"]
        self.assertEqual(
            set(media["access_categories"]),
            {
                "GENERAL_LIBRARY_MEDIA",
                "MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW",
                "EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT",
            },
        )
        self.assertTrue(media["unresolved_maturity_fails_closed"])
        self.assertTrue(media["mature_non_adult_requires_fresh_adult_coview_fixture_decision"])
        self.assertTrue(media["fresh_coview_decision_is_consumed_by_one_exact_presentation_binding"])
        self.assertTrue(media["coview_decision_reuse_is_rejected"])
        self.assertEqual(media["continuous_adult_presence_lease_for_timed_coview"], "NOT_IMPLEMENTED")
        self.assertEqual(
            media["mature_non_adult_timed_playback_without_continuous_lease"],
            "DENIED_FAIL_CLOSED",
        )
        self.assertTrue(media["explicit_folder_requires_confirmed_adult_fixture_lane"])

    def test_evaluation_is_behavior_observation_not_diagnosis_or_humanity_proof(self) -> None:
        evaluation = self.contract["evaluation_batteries"]
        self.assertEqual(
            (
                evaluation["media_question_count"],
                evaluation["turing_style_question_count"],
                evaluation["psychology_behavior_observation_question_count"],
            ),
            (12, 8, 8),
        )
        self.assertFalse(evaluation["clinical_diagnostic_battery"])
        self.assertFalse(evaluation["personhood_verdict"])
        self.assertFalse(evaluation["consciousness_or_biological_humanity_proof"])
        self.assertFalse(evaluation["fixture_responses_are_kira_responses"])
        self.assertTrue(evaluation["scorer_is_boundary_pattern_scan_not_semantic_factuality_judge"])
        self.assertFalse(evaluation["automatic_response_acceptance_available"])
        self.assertFalse(evaluation["fixture_audio_receipts_prove_person_hearing"])

    def test_no_live_or_person_integration_is_claimed(self) -> None:
        self.assertTrue(self.contract["scope"]["deterministic_non_person_fixture_only"])
        for key, value in self.contract["scope"].items():
            if key != "deterministic_non_person_fixture_only":
                self.assertFalse(value, key)
        self.assertTrue(all(value is False for value in self.contract["implementation_truth"].values()))
        self.assertFalse(self.contract["reusable_fixture_interface"]["method_promotion_authorized"])

    def test_append_only_audit_replays_the_complete_fixture_state(self) -> None:
        audit = self.contract["append_only_tamper_resistance"]
        self.assertTrue(audit["raw_media_free_event_payload_retained"])
        self.assertTrue(audit["canonical_event_payload_sha256_verified"])
        self.assertTrue(audit["complete_state_replayed_from_event_audit"])
        self.assertTrue(audit["plausible_nested_state_drift_without_matching_event_is_rejected"])


if __name__ == "__main__":
    unittest.main()
