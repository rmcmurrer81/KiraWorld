import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = PROJECT_ROOT / "Core"
sys.path.insert(0, str(CORE_ROOT))

from microphone_metadata_adapter import analyze_audio_metadata, analyze_sample_levels  # noqa: E402
from webcam_metadata_adapter import analyze_frame_metadata  # noqa: E402


class DeviceMetadataAdapterTests(unittest.TestCase):
    def test_audio_sample_levels_are_metadata_only(self) -> None:
        levels = analyze_sample_levels([0.0, 0.2, -0.2, 0.4])
        self.assertGreater(levels["rms_level"], 0.0)
        self.assertEqual(levels["peak_level"], 0.4)

    def test_audio_metadata_marks_robert_direct_speech_cues(self) -> None:
        cues = analyze_audio_metadata(
            rms_level=0.2,
            peak_level=0.5,
            speech_probability=0.8,
            robert_voice_probability=0.8,
            addressed_ai_probability=0.8,
        )
        self.assertTrue(cues["speech_detected"])
        self.assertTrue(cues["robert_voice_match"])
        self.assertTrue(cues["addressed_ai"])
        self.assertFalse(cues["metadata"]["raw_audio_stored"])

    def test_audio_metadata_marks_phone_private_media_cues(self) -> None:
        cues = analyze_audio_metadata(
            rms_level=0.2,
            peak_level=0.5,
            adult_private_probability=0.8,
            phone_audio_probability=0.8,
        )
        self.assertTrue(cues["phone_audio_detected"])
        self.assertTrue(cues["adult_private_audio_detected"])
        self.assertFalse(cues["metadata"]["raw_audio_stored"])

    def test_webcam_metadata_marks_other_person_and_no_raw_frame(self) -> None:
        cues = analyze_frame_metadata(
            brightness=0.5,
            motion_score=0.4,
            person_probability=0.8,
            other_person_probability=0.8,
        )
        self.assertTrue(cues["visual_present"])
        self.assertTrue(cues["other_person_present"])
        self.assertFalse(cues["metadata"]["raw_frame_stored"])

    def test_webcam_metadata_marks_visible_phone_as_phone_cue(self) -> None:
        cues = analyze_frame_metadata(
            brightness=0.6,
            phone_visible_probability=0.8,
        )
        self.assertTrue(cues["phone_visible"])
        self.assertTrue(cues["phone_audio_detected"])


if __name__ == "__main__":
    unittest.main()
