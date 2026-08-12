import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from validate_voice_profile import validate_voice_profile  # noqa: E402


class VoiceProfileValidatorTests(unittest.TestCase):
    def test_valid_placeholder_ready_profile_passes(self) -> None:
        data = {
            "voice_id": "voice_001",
            "target_name": "Ladybug",
            "target_type": "temp_ai",
            "voice_mode": "reconstruction",
            "voice_characteristics": {
                "pitch_range": "medium_high",
                "tone": "warm",
                "cadence": "quick",
                "energy_level": "high",
            },
            "status": {
                "ready_for_text_tts": True,
                "ready_for_clone": False,
                "source_audio_collected": False,
            },
        }

        self.assertEqual(validate_voice_profile(data), [])

    def test_clone_ready_requires_source_audio(self) -> None:
        data = {
            "voice_id": "voice_002",
            "target_name": "Historical Person",
            "target_type": "temp_ai",
            "voice_mode": "reconstruction",
            "voice_characteristics": {
                "pitch_range": "medium",
                "tone": "formal",
                "cadence": "measured",
                "energy_level": "medium",
            },
            "status": {
                "ready_for_clone": True,
                "source_audio_collected": False,
            },
        }

        errors = validate_voice_profile(data)
        self.assertTrue(any("ready_for_clone" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
