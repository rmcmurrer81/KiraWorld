import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_public_export_candidate import validate_public_export_candidate  # noqa: E402


class PublicExportCandidateValidatorTests(unittest.TestCase):
    def test_draft_candidate_requires_robert_approval_now(self) -> None:
        data = {
            "export_id": "export_test_001",
            "title": "Draft Clip",
            "created_by": "kira_lisa",
            "content_type": "video",
            "source_world_id": "world_001",
            "visibility_scope": "public_export_candidate",
            "autonomy_state": {
                "current_level": "request_mode",
                "posting_without_robert_permission_allowed": False,
                "maturity_gate_id": "request_mode",
            },
            "privacy_review": {
                "contains_private_memory": False,
                "contains_robert_personal_info": False,
                "contains_kira_lisa_private_content": False,
                "redactions_needed": [],
            },
            "content_notes": {"description": "", "intended_platforms": ["youtube"]},
            "approval": {
                "robert_approval_required_now": True,
                "kira_approval": True,
                "lisa_approval": True,
                "approved_at": "",
            },
            "status": "draft",
        }

        self.assertEqual(validate_public_export_candidate(data), [])

    def test_non_mature_autonomy_cannot_post_without_robert_permission(self) -> None:
        data = {
            "export_id": "export_test_002",
            "title": "Bad Clip",
            "created_by": "kira",
            "content_type": "video",
            "source_world_id": "world_001",
            "visibility_scope": "approved_public",
            "autonomy_state": {
                "current_level": "approved_autonomy",
                "posting_without_robert_permission_allowed": True,
                "maturity_gate_id": "approved_autonomy",
            },
            "privacy_review": {
                "contains_private_memory": False,
                "contains_robert_personal_info": False,
                "contains_kira_lisa_private_content": False,
                "redactions_needed": [],
            },
            "content_notes": {"description": "", "intended_platforms": ["youtube"]},
            "approval": {
                "robert_approval_required_now": False,
                "kira_approval": True,
                "lisa_approval": False,
                "approved_at": "",
            },
            "status": "draft",
        }

        errors = validate_public_export_candidate(data)
        self.assertTrue(any("mature_autonomy" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
