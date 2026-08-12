import sys
import unittest
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_memory_sharing_request import validate_memory_sharing_request  # noqa: E402


def base_request() -> dict:
    return {
        "request_id": "share_req_test",
        "reconstruction_id": "memworld_shared_kira_lisa_college_phase_001",
        "source_memory_id": "shared_kira_lisa_college_phase_001",
        "requested_by": "kira",
        "intended_viewer": "real_robert",
        "reason_for_request": "Kira wants Robert to understand the memory.",
        "requested_scope": "verbal_details_only",
        "required_approvals": ["kira", "lisa"],
        "approval_status": "partial",
        "participant_responses": [
            {
                "participant_id": "kira",
                "response": "yes",
                "denial_reason": "",
                "visual_body_exposure_allowed": False,
                "notes": "",
            },
            {
                "participant_id": "lisa",
                "response": "verbal_details_only",
                "denial_reason": "",
                "visual_body_exposure_allowed": False,
                "notes": "Verbal details only; no visual replay.",
            },
        ],
        "approved_scope": "verbal_details_only",
        "denial_reasons": [],
        "visual_body_exposure_allowed": False,
        "permanent_replay_access_granted": False,
        "privacy_rules": {
            "full_replay_blocked_if_any_no": True,
            "single_viewing_does_not_grant_replay_access": True,
            "internal_thoughts_hidden_unless_owner_allows": True,
            "viewer_may_not_save_artifacts_without_new_permission": True,
            "visual_body_exposure_requires_explicit_participant_consent": True,
            "verbal_details_only_does_not_grant_visual_replay": True,
            "speaker_may_share_only_own_perspective_unless_other_approves": True,
        },
        "audit": {"created_at": "", "resolved_at": "", "decision_log_id": ""},
        "status": "ready_for_review",
    }


class MemorySharingRequestValidatorTests(unittest.TestCase):
    def test_verbal_details_only_passes_without_visual_replay(self) -> None:
        self.assertEqual(validate_memory_sharing_request(base_request()), [])

    def test_no_blocks_visual_replay(self) -> None:
        request = deepcopy(base_request())
        request["requested_scope"] = "one_time_full_replay"
        request["approved_scope"] = "one_time_full_replay"
        request["participant_responses"][1]["response"] = "no"
        request["participant_responses"][1]["denial_reason"] = "does_not_want_visual_body_exposure"

        errors = validate_memory_sharing_request(request)
        self.assertTrue(any("cannot be approved" in error for error in errors))

    def test_one_time_replay_cannot_grant_permanent_access(self) -> None:
        request = deepcopy(base_request())
        request["requested_scope"] = "one_time_full_replay"
        request["approved_scope"] = "one_time_full_replay"
        request["approval_status"] = "approved"
        request["participant_responses"][1]["response"] = "yes"
        request["participant_responses"][0]["visual_body_exposure_allowed"] = True
        request["participant_responses"][1]["visual_body_exposure_allowed"] = True
        request["visual_body_exposure_allowed"] = True
        request["permanent_replay_access_granted"] = True

        errors = validate_memory_sharing_request(request)
        self.assertTrue(any("one_time_full_replay must not grant permanent replay access" in error for error in errors))

    def test_visual_body_exposure_requires_each_participant(self) -> None:
        request = deepcopy(base_request())
        request["requested_scope"] = "one_time_full_replay"
        request["approved_scope"] = "one_time_full_replay"
        request["approval_status"] = "approved"
        request["participant_responses"][1]["response"] = "yes"
        request["participant_responses"][0]["visual_body_exposure_allowed"] = True
        request["participant_responses"][1]["visual_body_exposure_allowed"] = False
        request["visual_body_exposure_allowed"] = True

        errors = validate_memory_sharing_request(request)
        self.assertTrue(any("explicit consent from lisa" in error for error in errors))

    def test_non_intimate_lead_in_passes_with_boundary_stop(self) -> None:
        request = deepcopy(base_request())
        request["requested_scope"] = "non_intimate_lead_in"
        request["approved_scope"] = "non_intimate_lead_in"
        request["approval_status"] = "partial"
        request["stop_at_locked_boundary"] = True
        request["locked_boundary_behavior"] = "pause"
        request["privacy_rules"]["non_intimate_lead_in_must_stop_at_locked_boundary"] = True
        request["participant_responses"][1]["response"] = "selected_zones_only"

        self.assertEqual(validate_memory_sharing_request(request), [])

    def test_non_intimate_lead_in_requires_boundary_stop(self) -> None:
        request = deepcopy(base_request())
        request["requested_scope"] = "non_intimate_lead_in"
        request["approved_scope"] = "non_intimate_lead_in"
        request["stop_at_locked_boundary"] = False
        request["locked_boundary_behavior"] = "pause"
        request["privacy_rules"]["non_intimate_lead_in_must_stop_at_locked_boundary"] = True

        errors = validate_memory_sharing_request(request)
        self.assertTrue(any("stop_at_locked_boundary true" in error for error in errors))

    def test_duplicate_required_participant_and_response_are_rejected(self) -> None:
        request = deepcopy(base_request())
        request["required_approvals"] = ["kira", "kira"]
        request["participant_responses"] = [
            deepcopy(request["participant_responses"][0]),
            deepcopy(request["participant_responses"][0]),
        ]
        errors = validate_memory_sharing_request(request)
        self.assertTrue(any("required_approvals must not contain duplicate" in error for error in errors))
        self.assertTrue(any("participant_responses must not contain duplicate" in error for error in errors))

    def test_missing_and_unexpected_participant_responses_are_rejected(self) -> None:
        request = deepcopy(base_request())
        request["participant_responses"] = [
            deepcopy(request["participant_responses"][0]),
            {
                "participant_id": "mallory",
                "response": "yes",
                "denial_reason": "",
                "visual_body_exposure_allowed": False,
                "notes": "",
            },
        ]
        errors = validate_memory_sharing_request(request)
        self.assertTrue(any("missing required participant: lisa" in error for error in errors))
        self.assertTrue(any("unexpected participant: mallory" in error for error in errors))

    def test_requested_summary_cannot_be_approved_as_full_replay(self) -> None:
        request = deepcopy(base_request())
        request["requested_scope"] = "summary"
        request["approved_scope"] = "full_replay"
        request["participant_responses"][1]["response"] = "yes"
        errors = validate_memory_sharing_request(request)
        self.assertTrue(any("approved_scope must not exceed requested_scope" in error for error in errors))

    def test_summary_only_response_cannot_authorize_one_time_replay(self) -> None:
        request = deepcopy(base_request())
        request["requested_scope"] = "one_time_full_replay"
        request["approved_scope"] = "one_time_full_replay"
        request["participant_responses"][0]["response"] = "yes"
        request["participant_responses"][1]["response"] = "summary_only"
        request["participant_responses"][0]["visual_body_exposure_allowed"] = True
        request["participant_responses"][1]["visual_body_exposure_allowed"] = True
        request["visual_body_exposure_allowed"] = True
        errors = validate_memory_sharing_request(request)
        self.assertTrue(any("exceeds the response scope for lisa" in error for error in errors))

    def test_approved_request_requires_fresh_bounded_expiry(self) -> None:
        request = deepcopy(base_request())
        request["approval_status"] = "approved"
        request["status"] = "approved"
        request["audit"] = {
            "created_at": "2020-01-01T00:00:00Z",
            "resolved_at": "2020-01-01T00:01:00Z",
            "decision_log_id": "decision_1",
        }
        errors = validate_memory_sharing_request(request)
        self.assertTrue(any("expires_at is required" in error for error in errors))

    def test_approved_request_with_bounded_lifecycle_passes_structurally(self) -> None:
        request = deepcopy(base_request())
        request["approval_status"] = "approved"
        request["status"] = "approved"
        request["audit"] = {
            "created_at": "2026-08-09T10:00:00Z",
            "resolved_at": "2026-08-09T10:01:00Z",
            "expires_at": "2026-08-09T10:06:00Z",
            "decision_log_id": "decision_1",
        }
        self.assertEqual(validate_memory_sharing_request(request), [])


if __name__ == "__main__":
    unittest.main()
