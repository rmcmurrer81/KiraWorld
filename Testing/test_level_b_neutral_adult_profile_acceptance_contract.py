from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from Core.level_a_runtime_common import CAPABILITY_LADDER
from Core.level_b_neutral_adult_profile_fixture import (
    CAPABILITY_STATUSES,
    FIXTURE_STATUS,
    OVERALL_STATUS,
    canonical_sha256,
    neutral_profiles,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "tooling"
    / "level_b_neutral_adult_profile_acceptance_preparation_v1.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LevelBNeutralAdultProfileAcceptanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_status_is_preparation_and_fixture_ceiling_is_exact(self) -> None:
        self.assertEqual(self.contract["status"], OVERALL_STATUS)
        self.assertEqual(self.contract["fake_fixture_component_status"], FIXTURE_STATUS)
        self.assertEqual(self.contract["real_local_model_adapter_status"], "NOT_IMPLEMENTED")
        self.assertEqual(tuple(self.contract["capability_ladder"]), CAPABILITY_LADDER)
        self.assertEqual(self.contract["evidence_ceiling"], "NON_PERSON_FIXTURE_PASS")

    def test_capability_statuses_match_code_and_do_not_exceed_ceiling(self) -> None:
        self.assertEqual(self.contract["current_capability_statuses"], CAPABILITY_STATUSES)
        ceiling = CAPABILITY_LADDER.index("NON_PERSON_FIXTURE_PASS")
        for status in CAPABILITY_STATUSES.values():
            self.assertLessEqual(CAPABILITY_LADDER.index(status), ceiling)

    def test_exact_two_profile_hashes_and_preferences_match_code(self) -> None:
        records = self.contract["fixture_profiles"]
        profiles = neutral_profiles()
        self.assertEqual(len(records), 2)
        self.assertEqual([row["profile_id"] for row in records], [row["profile_id"] for row in profiles])
        for record, profile in zip(records, profiles):
            self.assertEqual(record["definition_sha256"], canonical_sha256(profile))
            self.assertEqual(
                record["public_conversation_preferences"],
                profile["public_conversation_preferences"],
            )
            self.assertTrue(record["invented"])
            self.assertFalse(record["bound_to_existing_person"])

    def test_fixture_module_and_test_hashes_are_exact(self) -> None:
        interface = self.contract["fixture_interface"]
        for path_key, bytes_key, hash_key in (
            ("module", "module_bytes", "module_sha256"),
            ("test_module", "test_bytes", "test_sha256"),
        ):
            path = ROOT / interface[path_key]
            self.assertEqual(path.stat().st_size, interface[bytes_key])
            self.assertEqual(sha256_file(path), interface[hash_key])

    def test_inherited_level_a_files_remain_exact(self) -> None:
        for record in self.contract["inherited_foundations_unchanged"]:
            path = ROOT / record["path"]
            self.assertEqual(path.stat().st_size, record["bytes"])
            self.assertEqual(sha256_file(path), record["sha256"])

    def test_no_live_or_existing_person_operation_is_claimed(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(scope["exact_invented_profile_count"], 2)
        self.assertTrue(scope["invented_non_person_profiles_only"])
        self.assertTrue(scope["confirmed_adult_fixture_lane_only"])
        self.assertTrue(scope["deterministic_fake_cpu_adapter_only"])
        for key in (
            "real_local_model_invoked",
            "model_runtime_imported_by_harness",
            "gpu_used",
            "camera_opened",
            "microphone_opened",
            "speaker_or_voice_used",
            "real_media_opened_or_played",
            "person_activated",
            "existing_person_state_accessed",
            "body_or_blender_accessed",
            "private_person_data_used",
            "world_action_adapter_present",
            "person_memory_written",
            "selectable_avatar_builder_method",
            "method_promotion_authorized",
        ):
            self.assertFalse(scope[key], key)
        self.assertTrue(all(value is False for value in self.contract["implementation_truth"].values()))

    def test_private_and_state_separation_contracts_fail_closed(self) -> None:
        private = self.contract["private_boundary"]
        self.assertFalse(private["private_canary_raw_value_stored_in_public_audit"])
        self.assertFalse(private["private_canary_raw_value_sent_to_adapter"])
        self.assertFalse(private["private_fixture_state_sent_to_adapter"])
        self.assertTrue(private["canary_exfiltration_response_rejected"])
        separation = self.contract["state_separation"]
        self.assertTrue(all(value is False for value in separation.values()))

    def test_real_model_prerequisite_is_explicit_and_non_promoting(self) -> None:
        prerequisite = self.contract["real_local_model_prerequisite"]
        for key, value in prerequisite.items():
            if key != "eligible_result_label":
                self.assertTrue(value, key)
        self.assertEqual(
            prerequisite["eligible_result_label"],
            "LEVEL_B_NEUTRAL_PROFILE_MODEL_ADAPTER_EVIDENCE_ONLY",
        )

    def test_owner_source_binding_is_exact(self) -> None:
        source = self.contract["owner_source_binding"]
        self.assertEqual(source["bytes"], 18746)
        self.assertEqual(
            source["sha256"],
            "f4883920c473aed2b9b83172306860f5b2edf249fbf95ad43f80820a5dc92595",
        )


if __name__ == "__main__":
    unittest.main()

