from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from Core.avatar_rapid_body_request import (
    RapidBodyRequestError,
    validate_rapid_body_request,
)


ROOT = Path(__file__).resolve().parents[1]
REQUEST = (
    ROOT
    / "Avatar"
    / "avatar_builder"
    / "rapid_body_pipeline"
    / "requests"
    / "kira_temporary_functional_body_20260730.json"
)


class RapidBodyRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(REQUEST.read_text(encoding="utf-8"))

    def test_kira_request_is_valid_and_inactive(self) -> None:
        result = validate_rapid_body_request(self.payload)
        self.assertEqual(result["owner_id"], "kira")
        self.assertEqual(result["body_class"], "adult_female")
        self.assertFalse(result["robert_private_data_allowed"])
        self.assertFalse(result["runtime_assignment_allowed"])
        self.assertFalse(result["owner_approved"])
        self.assertGreaterEqual(result["runtime_nonmutation_baseline_count"], 3)

    def test_rejects_robert_private_foundation(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["foundation_requirements"]["selected_source_path"] = (
            "Avatar/private_owner_review/dual_robert_20260729/v24.blend"
        )
        with self.assertRaises(RapidBodyRequestError):
            validate_rapid_body_request(payload)

    def test_rejects_robert_reference_input(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["reference_inputs"] = [
            {
                "subject_id": "biological_robert",
                "path": "Desktop/reference/robert_front.png",
            }
        ]
        with self.assertRaises(RapidBodyRequestError):
            validate_rapid_body_request(payload)

    def test_rejects_disguised_robert_path_even_with_generic_subject(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["reference_inputs"] = [
            {
                "subject_id": "generic_non_identifiable",
                "path": "Desktop/reference/robert_front.png",
            }
        ]
        with self.assertRaises(RapidBodyRequestError):
            validate_rapid_body_request(payload)

    def test_rejects_runtime_assignment_at_intake(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["output"]["runtime_assignment_allowed"] = True
        with self.assertRaises(RapidBodyRequestError):
            validate_rapid_body_request(payload)

    def test_rejects_missing_integrated_anatomy_requirement(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["foundation_requirements"]["integrated_adult_anatomy"] = False
        with self.assertRaises(RapidBodyRequestError):
            validate_rapid_body_request(payload)


if __name__ == "__main__":
    unittest.main()
