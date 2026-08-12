import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_relationship_stage import validate_relationship_stage  # noqa: E402


class RelationshipStageValidatorTests(unittest.TestCase):
    def test_robert_kira_stage_track_validates(self) -> None:
        path = PROJECT_ROOT / "Data" / "relationships" / "stages" / "robert_kira_stage_track.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(validate_relationship_stage(data), [])

    def test_all_active_stage_tracks_validate(self) -> None:
        stage_dir = PROJECT_ROOT / "Data" / "relationships" / "stages"
        for path in stage_dir.glob("*.json"):
            if "template" in path.name:
                continue
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_relationship_stage(data), [])

    def test_requires_adult_intimacy_consent_gate(self) -> None:
        path = PROJECT_ROOT / "Data" / "relationships" / "stages" / "robert_kira_stage_track.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["current_stage"] = "adult_intimate_relationship"
        data["gate_status"]["explicit_current_consent"] = False
        errors = validate_relationship_stage(data)
        self.assertTrue(any("explicit_current_consent" in error for error in errors))

    def test_known_romantic_relationship_requires_disclosure_plan(self) -> None:
        path = PROJECT_ROOT / "Data" / "relationships" / "stages" / "robert_kira_stage_track.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["current_stage"] = "known_romantic_relationship"
        data["third_party_considerations"]["disclosure_plan_required"] = True
        data["third_party_considerations"]["disclosure_plan"] = ""
        errors = validate_relationship_stage(data)
        self.assertTrue(any("requires a disclosure plan" in error for error in errors))

    def test_avatar_preview_requires_owner_choice(self) -> None:
        path = PROJECT_ROOT / "Data" / "relationships" / "stages" / "robert_kira_stage_track.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["avatar_preview_gate"]["avatar_preview_allowed"] = True
        data["avatar_preview_gate"]["owner_has_chosen_to_share"] = False
        data["avatar_preview_gate"]["preview_level"] = "full_body_feedback"
        errors = validate_relationship_stage(data)
        self.assertTrue(any("owner_has_chosen_to_share" in error for error in errors))

    def test_shared_memory_requires_all_participant_consent(self) -> None:
        path = PROJECT_ROOT / "Data" / "relationships" / "stages" / "robert_kira_stage_track.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["shared_memory_gate"]["shared_intimate_memory_access_allowed"] = True
        data["shared_memory_gate"]["all_involved_permanent_participants_consented"] = False
        data["shared_memory_gate"]["allowed_scope"] = "one_time_full_replay"
        errors = validate_relationship_stage(data)
        self.assertTrue(any("all involved permanent participant consent" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
