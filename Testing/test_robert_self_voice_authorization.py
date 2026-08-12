from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from Core.private_self_voice_authorization import validate_private_self_voice_authorization
from Core.voice_output import load_candidate_voice_config


ROOT = Path(__file__).resolve().parents[1]
ROBERT_ID = "robert_mcmurrer_presence_ai"
PROFILE_PATH = ROOT / "TemporaryAI" / "candidates" / ROBERT_ID / "temporary_ai_profile.json"


class RobertSelfVoiceAuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8-sig"))

    def test_real_owner_approved_binding_passes_without_generating_or_playing_audio(self) -> None:
        result = validate_private_self_voice_authorization(
            ROBERT_ID,
            self.profile,
            project_root=ROOT,
        )

        self.assertTrue(result["allowed"], result["reasons"])
        self.assertEqual(result["voice_profile_id"], "robert_mcmurrer_authorized_self_voice_v1")
        self.assertEqual(result["engine"], "chatterbox_tts")
        self.assertEqual(result["reviewed_target_clip_count"], 11)
        self.assertAlmostEqual(result["reviewed_target_seconds"], 36.57, places=2)
        self.assertAlmostEqual(result["wav_duration_seconds"], 36.57, places=2)
        self.assertEqual(
            result["approved_reference_sha256"],
            "761458a0fe9c5da1c2671faa738c1e329336630cd47138a4e738f7de2030542b",
        )

    def test_missing_explicit_authorization_fails_closed(self) -> None:
        profile = copy.deepcopy(self.profile)
        profile["voice_and_behavior"].pop("voice_authorization", None)

        result = validate_private_self_voice_authorization(
            ROBERT_ID,
            profile,
            project_root=ROOT,
        )

        self.assertFalse(result["allowed"])
        self.assertIn("authorization_file_missing_or_outside_project", result["reasons"])

    def test_candidate_mismatch_fails_closed(self) -> None:
        result = validate_private_self_voice_authorization(
            "another_candidate",
            self.profile,
            project_root=ROOT,
        )

        self.assertFalse(result["allowed"])
        self.assertIn("authorization_candidate_mismatch", result["reasons"])

    def test_reference_hash_mismatch_fails_closed(self) -> None:
        with patch(
            "Core.private_self_voice_authorization._sha256",
            return_value="0" * 64,
        ):
            result = validate_private_self_voice_authorization(
                ROBERT_ID,
                self.profile,
                project_root=ROOT,
            )

        self.assertFalse(result["allowed"])
        self.assertIn("approved_reference_hash_mismatch", result["reasons"])

    def test_runtime_resolver_selects_robert_profile_and_exact_reference(self) -> None:
        config = load_candidate_voice_config(
            {
                "candidate_id": ROBERT_ID,
                "display_name": "Synthetic Robert (text + approved voice)",
                "gender_preference": "male",
            }
        )

        self.assertEqual(config.engine, "chatterbox_tts")
        self.assertEqual(
            config.chatterbox_reference_audio,
            "Voice/reference_packs/robert_mcmurrer/robert_mcmurrer_online_source_20260714_230541/model_input/approved_reference.wav",
        )
        self.assertEqual(
            config.output_dir,
            str(Path("Voice") / "generated" / "temp_ai" / "robert_mcmurrer"),
        )
        self.assertAlmostEqual(config.pcm_output_gain_db, -9.5)
        self.assertAlmostEqual(config.proximity_cut_hz, 95.0)
        self.assertAlmostEqual(config.proximity_cut_mix, 0.30)


if __name__ == "__main__":
    unittest.main()
