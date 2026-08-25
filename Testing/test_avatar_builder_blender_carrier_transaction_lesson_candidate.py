"""Fail-closed checks for the unpromoted Avatar Builder lesson candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core import avatar_blender_preimport_controller as preimport


CANDIDATE_PATH = (
    PROJECT_ROOT
    / "Avatar"
    / "avatar_builder"
    / "body_systems"
    / "avatar_builder_blender_carrier_transaction_closure_candidate_v1.json"
)


class AvatarBuilderBlenderCarrierTransactionLessonCandidateTests(unittest.TestCase):
    def test_candidate_sources_are_exact_and_receiver_stays_default_off(self) -> None:
        candidate = preimport.read_strict_json(CANDIDATE_PATH, max_bytes=128 * 1024)
        self.assertEqual(
            "STATIC_AUTHOR_CANDIDATE_NOT_TAUGHT_AWAITING_DIFFERENT_REVIEW",
            candidate["status"],
        )
        self.assertEqual(3, len(candidate["source_bindings"]))
        for binding in candidate["source_bindings"]:
            source = PROJECT_ROOT / Path(binding["path"])
            payload = source.read_bytes()
            self.assertEqual(binding["bytes"], len(payload))
            self.assertEqual(binding["sha256"], hashlib.sha256(payload).hexdigest())

        receiver = candidate["receiver_integration"]
        self.assertTrue(receiver["different_review_required"])
        for key in (
            "teaching_allowed",
            "resident_memory_write_allowed",
            "selectable_method_allowed",
            "default_enabled",
        ):
            self.assertIs(receiver[key], False)

    def test_candidate_preserves_false_runtime_and_body_authority(self) -> None:
        candidate = preimport.read_strict_json(CANDIDATE_PATH, max_bytes=128 * 1024)
        truth = candidate["current_truth"]
        for key in (
            "native_provider_reviewed",
            "native_transaction_interface_available",
            "authorization_present",
            "native_claim_root_selected",
            "native_claim_created",
            "operating_system_evidence_verified",
            "blender_execution_authorized",
            "body_build_authorized",
            "body_created",
            "candidate_assignment_authorized",
            "anatomy_authoring_authorized",
            "runtime_activation_authorized",
            "public_export_authorized",
        ):
            self.assertIs(truth[key], False)
        self.assertIn("create no body", candidate["lesson"])
        self.assertIn("start no process", candidate["lesson"])

    def test_candidate_contains_no_raw_machine_path_or_private_person_payload(self) -> None:
        text = CANDIDATE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("C:\\\\", text)
        self.assertNotIn("\\\\?\\", text)
        self.assertNotIn("Robert user-avatar", text)
        self.assertNotIn("private reference", text)


if __name__ == "__main__":
    unittest.main()
