import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_notebook_world_request import validate_notebook_world_request  # noqa: E402


class NotebookWorldValidatorTests(unittest.TestCase):
    def test_private_request_mode_world_passes(self) -> None:
        data = {
            "request_id": "notebook_world_test_001",
            "request_type": "notebook_world",
            "title": "Test World",
            "requested_by": "kira_lisa",
            "trigger": {"source": "curiosity"},
            "subject": {"name": "Test Place", "category": "real_place", "private_use_allowed": True},
            "source_collection_plan": {
                "allowed_source_types": ["local_library", "manual_notes"],
                "requires_robert_approval_now": True,
                "auto_collection_allowed_later": False,
            },
            "world_plan": {
                "starting_area": "Entrance",
                "initial_scope": "small_prototype",
                "confirmed_zones": [],
                "inferred_zones": [],
                "unknown_zones": [],
                "npc_policy": "generic",
                "ride_or_attraction_policy": "none",
            },
            "visibility_scope": "private_only",
            "autonomy_level_required": "request_mode",
            "status": "draft",
        }

        self.assertEqual(validate_notebook_world_request(data), [])

    def test_approved_public_requires_mature_autonomy(self) -> None:
        data = {
            "request_id": "notebook_world_test_002",
            "request_type": "notebook_world",
            "title": "Public Test World",
            "requested_by": "kira",
            "trigger": {},
            "subject": {"name": "Test Place"},
            "source_collection_plan": {
                "allowed_source_types": ["web_search"],
                "requires_robert_approval_now": True,
            },
            "world_plan": {
                "confirmed_zones": [],
                "inferred_zones": [],
                "unknown_zones": [],
                "npc_policy": "generic",
            },
            "visibility_scope": "approved_public",
            "autonomy_level_required": "request_mode",
            "status": "draft",
        }

        errors = validate_notebook_world_request(data)
        self.assertTrue(any("approved_public" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
