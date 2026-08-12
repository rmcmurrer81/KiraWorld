import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
sys.path.insert(0, str(CORE_ROOT))

from perception_gateway import PerceptionGateway, validate_perception_session  # noqa: E402


class PerceptionGatewayTests(unittest.TestCase):
    def test_perception_session_state_validates(self) -> None:
        sessions = json.loads((PROJECT_ROOT / "Data" / "perception" / "perception_session_state.json").read_text(encoding="utf-8"))
        for session in sessions:
            with self.subTest(session=session["session_id"]):
                self.assertEqual(validate_perception_session(session), [])

    def test_disabled_session_blocks_observation(self) -> None:
        gateway = PerceptionGateway(PROJECT_ROOT / "Data" / "perception" / "perception_session_state.json")
        event = gateway.process_cues(
            "perception_session_kira_pre_gpu_simulated",
            {"robert_voice_match": True, "addressed_ai": True, "confidence_hint": "high"},
        )
        self.assertTrue(event["blocked"])
        self.assertEqual(event["recommended_action"], "do_not_observe")
        self.assertEqual(event["reason"], "perception_session_not_active")

    def test_active_simulated_session_routes_to_attention(self) -> None:
        with TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "perception_state.json"
            sessions = json.loads((PROJECT_ROOT / "Data" / "perception" / "perception_session_state.json").read_text(encoding="utf-8"))
            sessions[0]["status"] = "active"
            sessions[0]["permissions"]["current_permission_granted"] = True
            state_file.write_text(json.dumps(sessions), encoding="utf-8")
            gateway = PerceptionGateway(state_file, PROJECT_ROOT / "Data" / "attention" / "attention_state.json")
            event = gateway.process_cues(
                "perception_session_kira_pre_gpu_simulated",
                {"robert_voice_match": True, "addressed_ai": True, "confidence_hint": "high"},
            )
            self.assertEqual(event["source_label"], "robert_direct_speech")
            self.assertEqual(event["recommended_action"], "respond_normally")
            saved = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertIn("attention_event", saved[0]["last_event"])

    def test_private_phone_media_with_unspoken_feeling_routes_to_private_reflection(self) -> None:
        with TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "perception_state.json"
            sessions = json.loads((PROJECT_ROOT / "Data" / "perception" / "perception_session_state.json").read_text(encoding="utf-8"))
            sessions[1]["status"] = "active"
            sessions[1]["permissions"]["current_permission_granted"] = True
            state_file.write_text(json.dumps(sessions), encoding="utf-8")
            gateway = PerceptionGateway(state_file, PROJECT_ROOT / "Data" / "attention" / "attention_state.json")
            event = gateway.process_cues(
                "perception_session_lisa_pre_gpu_simulated",
                {
                    "phone_audio_detected": True,
                    "adult_private_audio_detected": True,
                    "confidence_hint": "medium",
                },
                relationship_stage="unspoken_romantic_tension",
                unspoken_feeling_possible=True,
            )
            self.assertEqual(event["source_label"], "robert_phone_media")
            self.assertEqual(event["category_guess"], "adult_or_private_media")
            self.assertEqual(event["recommended_action"], "private_reflection_only")
            self.assertFalse(event["privacy_context"]["should_disclose_to_other_ai"])

    def test_validator_rejects_always_on_monitoring(self) -> None:
        session = json.loads((PROJECT_ROOT / "Data" / "perception" / "perception_session_state.json").read_text(encoding="utf-8"))[0]
        session["permissions"]["always_on_monitoring_allowed"] = True
        errors = validate_perception_session(session)
        self.assertTrue(any("always_on_monitoring_allowed" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
